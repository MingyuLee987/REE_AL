"""Fold-local models and deterministic feature engineering for corrosion data."""
import re

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR


def electrolyte_descriptors(value):
    """Parse only explicitly specified concentrations; preserve unknown bases."""
    s = str(value).lower().replace('\u200b', '')
    if any(w in s for w in ['naoh', 'koh', 'ca(oh)2', 'caoh2', 'pore_solution']):
        family = 'alkaline'
    elif any(w in s for w in ['h2so4', 'hcl']):
        family = 'acid'
    elif 'nahso3' in s:
        family = 'sulfite'
    elif any(w in s for w in ['hanks', 'saliva']):
        family = 'biological'
    elif 'soil' in s:
        family = 'soil_mixture'
    elif any(w in s for w in ['seawater', '해수']):
        family = 'seawater'
    elif 'nacl' in s:
        family = 'chloride'
    elif 'na2so4' in s:
        family = 'sulfate'
    else:
        family = 'unknown'
    # Supports "NaCl_3.5wtpct" and "3.5 wt.% NaCl". Plain % is not assumed wt%.
    wt = re.search(r'nacl[_\s]*(\d+(?:\.\d+)?)\s*wt(?:pct|\.?\s*%)', s)
    if wt is None:
        wt = re.search(r'(\d+(?:\.\d+)?)\s*wt\.?\s*%\s*nacl', s)
    mol = re.search(r'nacl[_\s]*(\d+(?:\.\d+)?)\s*mol[_/\s]*l', s)
    return family, float(wt[1]) if wt else np.nan, float(mol[1]) if mol else np.nan


class PhysicalFeatures(TransformerMixin, BaseEstimator):
    def __init__(self, mode='basic'):
        self.mode = mode

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        x = X.copy()
        if self.mode == 'physical':
            desc = x.electrolyte_condition_cat.map(electrolyte_descriptors)
            x['electrolyte_family'] = desc.map(lambda v: v[0])
            x['NaCl_explicit_wt_pct'] = desc.map(lambda v: v[1])
            x['NaCl_explicit_mol_L'] = desc.map(lambda v: v[2])
            for c in ['RE_ppm', 'exposure_h', 'heat_treatment_time_min']:
                if c in x:
                    x['log1p_' + c] = np.log1p(x[c].where(x[c] >= 0))
        return x


def preprocessor():
    return ColumnTransformer([
        ('numeric', make_pipeline(SimpleImputer(strategy='median', add_indicator=True, keep_empty_features=True), StandardScaler()), make_column_selector(dtype_include=np.number)),
        ('categorical', OneHotEncoder(handle_unknown='ignore', sparse_output=False), make_column_selector(dtype_exclude=np.number)),
    ])


def configurations(include_vae=False):
    """A fixed small search space, declared before looking at holdout results."""
    candidates = [('mean', {})]
    candidates += [('ridge', {'alpha': a}) for a in [1., 10., 100.]]
    candidates += [('extra_trees', {'min_samples_leaf': leaf}) for leaf in [2, 5]]
    candidates += [('random_forest', {'min_samples_leaf': leaf}) for leaf in [2, 5]]
    candidates += [('hist_boost', {'l2_regularization': l2, 'min_samples_leaf': leaf}) for l2, leaf in [(1., 10), (10., 20)]]
    candidates += [('svr', {'C': c}) for c in [1., 10.]]
    result = [dict(model=name, params=params, features=mode) for mode in ['basic', 'physical'] for name, params in candidates]
    if include_vae:
        result += [dict(model='vae', params={'latent_dim': dim, 'supervised_weight': weight}, features='physical') for dim, weight in [(2, 0.), (4, 0.), (4, 1.)]]
    return result


def build_model(config, seed=42, vae_epochs=150):
    name, params = config['model'], config['params']
    if name == 'vae':
        from vae_regressor import MixedVAERegressor
        return Pipeline([('features', PhysicalFeatures(config['features'])), ('model', MixedVAERegressor(random_state=seed, epochs=vae_epochs, **params))])
    if name == 'mean':
        model = DummyRegressor(strategy='mean')
    elif name == 'ridge':
        model = Ridge(**params)
    elif name == 'extra_trees':
        model = ExtraTreesRegressor(n_estimators=150, max_features=.8, random_state=seed, n_jobs=-1, **params)
    elif name == 'random_forest':
        model = RandomForestRegressor(n_estimators=150, max_features=.8, random_state=seed, n_jobs=-1, **params)
    elif name == 'hist_boost':
        model = HistGradientBoostingRegressor(max_iter=150, learning_rate=.05, early_stopping=False, random_state=seed, **params)
    elif name == 'svr':
        model = SVR(kernel='rbf', epsilon=.1, **params)
    else:
        raise ValueError(f'Unknown model {name}')
    return Pipeline([('features', PhysicalFeatures(config['features'])), ('preprocess', preprocessor()), ('model', model)])
