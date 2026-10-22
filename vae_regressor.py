"""Small mixed-data VAE + regression; no synthetic labels or test pretraining."""
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted


class MixedVAE(nn.Module):
    def __init__(self, inputs, outputs, latent):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(inputs, 32), nn.ReLU(), nn.Linear(32, 16), nn.ReLU())
        self.mu = nn.Linear(16, latent)
        self.logvar = nn.Linear(16, latent)
        self.decoder = nn.Sequential(nn.Linear(latent, 16), nn.ReLU(), nn.Linear(16, 32), nn.ReLU(), nn.Linear(32, outputs))
        self.head = nn.Linear(latent, 1)

    def encode(self, x):
        h = self.encoder(x)
        return self.mu(h), self.logvar(h).clamp(-8, 6)


class MixedVAERegressor(RegressorMixin, BaseEstimator):
    def __init__(self, latent_dim=4, beta_kl=.02, supervised_weight=0., epochs=150, learning_rate=.001, random_state=42):
        self.latent_dim = latent_dim
        self.beta_kl = beta_kl
        self.supervised_weight = supervised_weight
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.random_state = random_state

    def _inputs(self, X):
        raw = X[self.num_cols_].to_numpy(float)
        mask = np.isfinite(raw).astype('float32')
        numeric = self.scaler_.transform(self.imputer_.transform(raw)).astype('float32')
        cats = X[self.cat_cols_].fillna('missing').astype(str)
        onehot = self.onehot_.transform(cats).astype('float32')
        inputs = torch.from_numpy(np.concatenate([numeric, mask, onehot], axis=1))
        return inputs, torch.from_numpy(numeric), torch.from_numpy(mask)

    def fit(self, X, y):
        if self.epochs < 1 or self.latent_dim < 1 or self.beta_kl < 0 or self.supervised_weight < 0:
            raise ValueError('Invalid VAE training options.')
        torch.manual_seed(self.random_state)
        torch.set_num_threads(1)
        self.num_cols_ = X.select_dtypes(include=np.number).columns.tolist()
        self.cat_cols_ = X.select_dtypes(exclude=np.number).columns.tolist()
        self.imputer_ = SimpleImputer(strategy='median', keep_empty_features=True)
        values = self.imputer_.fit_transform(X[self.num_cols_].to_numpy(float))
        self.scaler_ = StandardScaler().fit(values)
        self.onehot_ = OneHotEncoder(handle_unknown='ignore', sparse_output=False).fit(X[self.cat_cols_].fillna('missing').astype(str))
        self.category_sizes_ = [len(c) for c in self.onehot_.categories_]
        inputs, numeric, mask = self._inputs(X)
        d = len(self.num_cols_)
        self.network_ = MixedVAE(inputs.shape[1], d + sum(self.category_sizes_), self.latent_dim)
        optimizer = torch.optim.Adam(self.network_.parameters(), lr=self.learning_rate, weight_decay=1e-4)
        self.y_mean_, self.y_std_ = float(np.mean(y)), max(float(np.std(y)), 1e-6)
        target = torch.tensor((np.asarray(y) - self.y_mean_) / self.y_std_, dtype=torch.float32)
        # Training categories are all known; numeric missing values are never reconstruction targets.
        categories = []
        offset = d * 2
        for size in self.category_sizes_:
            categories.append(inputs[:, offset:offset + size].argmax(1))
            offset += size
        self.history_ = []
        self.network_.train()
        for epoch in range(self.epochs):
            mu, logvar = self.network_.encode(inputs)
            z = mu + torch.randn_like(mu) * torch.exp(.5 * logvar)
            output = self.network_.decoder(z)
            rec_num = (((output[:, :d] - numeric) ** 2) * mask).sum() / mask.sum().clamp_min(1)
            rec_cat = torch.zeros(())
            offset = d
            for label, size in zip(categories, self.category_sizes_):
                rec_cat = rec_cat + F.cross_entropy(output[:, offset:offset + size], label)
                offset += size
            rec_cat = rec_cat / max(1, len(categories))
            kl = -.5 * (1 + logvar - mu.square() - logvar.exp()).sum(1).mean()
            reg = F.mse_loss(self.network_.head(mu).squeeze(1), target)
            # Gradual KL warm-up is fixed, not selected using validation/test values.
            loss = rec_num + rec_cat + self.beta_kl * min(1., (epoch + 1) / 30.) * kl + self.supervised_weight * reg
            if not torch.isfinite(loss):
                raise ValueError('VAE loss became non-finite.')
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(self.network_.parameters(), 5.)
            optimizer.step()
            self.history_.append(dict(epoch=epoch + 1, loss=float(loss.detach()), kl=float(kl.detach())))
        self.network_.eval()
        latent = self.transform(X)
        self.latent_scaler_ = StandardScaler().fit(latent)
        self.regressor_ = Ridge(alpha=1.).fit(self.latent_scaler_.transform(latent), np.asarray(y))
        return self

    def transform(self, X):
        check_is_fitted(self, 'network_')
        inputs, _, _ = self._inputs(X)
        with torch.no_grad():
            mu, _ = self.network_.encode(inputs)
        return mu.numpy()

    def predict(self, X):
        check_is_fitted(self, 'regressor_')
        return self.regressor_.predict(self.latent_scaler_.transform(self.transform(X)))
