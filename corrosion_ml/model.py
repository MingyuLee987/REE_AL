"""The sole model: environment SVR plus a bootstrap selection committee."""
import numpy as np,pandas as pd
from sklearn.base import BaseEstimator,RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline,make_pipeline
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.svm import SVR
from sklearn.metrics import pairwise_distances
from .composition import CompositionDonorImputer
from .features import CorrosionFeatures
STRATEGIES=['random','uncertainty','diverse_uncertainty']
def make_pre(f):
    cats=list(f.select_dtypes(include=['object','str','string']).columns)
    nums=[c for c in f if c not in cats]
    return ColumnTransformer([
        ('num',make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),StandardScaler()),nums),
        ('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),cats)])

class BootstrapSVR(RegressorMixin,BaseEstimator):
    """Central full-label SVR prediction; bootstrap standard deviation is uncalibrated."""
    def __init__(self,n_members=15,seed=42,C=10.,epsilon=.15):
        self.n_members=n_members;self.seed=seed;self.C=C;self.epsilon=epsilon
    def fit(self,X,y):
        if self.n_members<2:raise ValueError('At least two bootstrap members required')
        self.central_=SVR(C=self.C,epsilon=self.epsilon).fit(X,y)
        rng=np.random.default_rng(self.seed);self.members_=[]
        self.bootstrap_indices_=[]
        for _ in range(self.n_members):
            idx=rng.integers(0,len(y),size=len(y));self.bootstrap_indices_.append(idx)
            self.members_.append(SVR(C=self.C,epsilon=self.epsilon).fit(X[idx],np.asarray(y)[idx]))
        return self
    def predict(self,X):return self.central_.predict(X)
    def uncertainty(self,X):return np.std([m.predict(X) for m in self.members_],axis=0,ddof=1)

def fitted(d,y,n_members=15,seed=42):
    donor=CompositionDonorImputer().fit(d);filled=donor.transform(d)
    features=CorrosionFeatures('environment');x=features.fit_transform(filled)
    pre=make_pre(x);z=pre.fit_transform(x)
    model=BootstrapSVR(n_members=n_members,seed=seed).fit(z,y)
    pipeline=Pipeline([('composition',donor),('features',features),('preprocessor',pre),('model',model)])
    pipeline.training_record_ids_=list(d.record_id)
    assert set(donor.pool_.record_id).issubset(set(d.record_id))
    return pipeline,z

def rank_batch(known_z,known_groups,pool_z,pool_groups,sigma,count,strategy,rng):
    """Aggregate by query group; no outcome labels or test features accepted."""
    if strategy not in STRATEGIES:raise ValueError('Unknown query strategy')
    if count<1:raise ValueError('count must be positive')
    kp=pd.DataFrame(known_z).groupby(np.asarray(known_groups),sort=True).mean().to_numpy()
    centroids=pd.DataFrame(pool_z).groupby(np.asarray(pool_groups),sort=True).mean()
    unc=pd.Series(sigma).groupby(np.asarray(pool_groups),sort=True).mean()
    remaining=list(centroids.index)
    if strategy=='random':
        return list(rng.permutation(remaining)[:count])
    chosen=[]
    for _ in range(min(count,len(remaining))):
        u=unc.loc[remaining]
        if strategy=='uncertainty':score=u
        else:
            distance=pd.Series(pairwise_distances(centroids.loc[remaining].to_numpy(),kp).min(axis=1),index=remaining)
            score=.5*u.rank(pct=True)+.5*distance.rank(pct=True)
        take=score.sort_values(ascending=False,kind='stable').index[0]
        chosen.append(take);remaining.remove(take)
        kp=np.vstack([kp,centroids.loc[take].to_numpy()])
    return chosen
