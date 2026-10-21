import warnings
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel as C
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score

# 경고 억제
warnings.filterwarnings("ignore", category=ConvergenceWarning)

# 1. 데이터 로드
df = pd.read_excel('ML_FINAL.xlsx', sheet_name='ML_DATA')
y = np.log10(df['icorr_A_cm2'].values)

features = ['C', 'Si', 'Mn', 'P', 'S', 'Cr', 'Ni', 'Mo', 'Cu', 'N', 'RE_ppm', 
            'temperature_C', 'pH', 'exposure_h', 'scan_rate_mV_s']
X = df[features].values

preprocessor = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])
X_proc = preprocessor.fit_transform(X)

# 2. 커널 정의 (상한선 확장 + ConstantKernel 결합)
kernel = C(1.0, (1e-2, 1e3)) * Matern(
    length_scale=1.0, 
    length_scale_bounds=(1e-2, 1e6), 
    nu=2.5
) + WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-5, 2.0))

# 3. normalize_y=True 적용
gpr = GaussianProcessRegressor(
    kernel=kernel, 
    normalize_y=True, 
    n_restarts_optimizer=10, 
    random_state=42
)

# 학습 진행
gpr.fit(X_proc[:75], y[:75])
print("학습 완료 커널:", gpr.kernel_)