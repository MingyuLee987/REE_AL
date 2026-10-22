import warnings
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import r2_score

warnings.filterwarnings("ignore", category=ConvergenceWarning)

# ========================================================
# 1. 데이터 로드 및 타깃 변환
# ========================================================
df = pd.read_excel('ML_FINAL.xlsx', sheet_name='ML_DATA')
y = np.log10(df['icorr_A_cm2'].values)

# ========================================================
# 2. 전 컬럼을 유기적으로 엮는 도메인 피처 엔지니어링
# ========================================================
# (1) 결측 대입 임시 벡터 (상호작용 연산용 기본 조성)
C_f  = df['C'].fillna(0.05)
Si_f = df['Si'].fillna(0.20)
Mn_f = df['Mn'].fillna(0.50)
P_f  = df['P'].fillna(0.01)
S_f  = df['S'].fillna(0.005)
Cr_f = df['Cr'].fillna(0.0)
Ni_f = df['Ni'].fillna(0.0)
Mo_f = df['Mo'].fillna(0.0)
Cu_f = df['Cu'].fillna(0.0)
N_f  = df['N'].fillna(0.0)
RE_f = df['RE_ppm'].fillna(0.0)

# (2) 합금 원소 간 유기적 결합
df['PREN']          = Cr_f + 3.3 * Mo_f + 16.0 * N_f                       # 내공식 지수
df['Cr_eq']         = Cr_f + Mo_f + 1.5 * Si_f                             # 페라이트 안정화
df['Ni_eq']         = Ni_f + 30.0 * C_f + 30.0 * N_f + 0.5 * Mn_f          # 오스테나이트 안정화
df['Cr_Ni_ratio']   = df['Cr_eq'] / (df['Ni_eq'] + 1e-4)                   # 미세조직 경쟁비
df['Mn_S_ratio']    = Mn_f / (S_f + 1e-4)                                  # MnS 개재물 생성비
df['RE_to_S_ratio'] = RE_f / (S_f * 10000.0 + 1.0)                         # 희토류-황 개재물 개질 지표
df['Alloy_Total']   = C_f + Si_f + Mn_f + P_f + S_f + Cr_f + Ni_f + Mo_f + Cu_f + N_f # 총 합금도

# (3) 환경 & 전기화학 조건 간 유기적 결합
T_f     = df['temperature_C'].fillna(25.0)
pH_f    = df['pH'].fillna(7.0)
t_exp_f = df['exposure_h'].fillna(1.0)
scan_f  = df['scan_rate_mV_s'].fillna(1.0)

df['inv_Temp_K']        = 1000.0 / (T_f + 273.15)                          # 아레니우스 열역학 항
df['pH_dev_neutral']    = np.abs(pH_f - 7.0)                               # 산/염기 가혹도
df['log_exposure']      = np.log10(t_exp_f + 0.1)                          # 시간 비선형 확산 항
df['kinetic_intensity'] = scan_f * np.sqrt(t_exp_f + 1.0)                  # 동전위 스캔-침지 반응 속도
df['env_severity']      = df['inv_Temp_K'] * (df['pH_dev_neutral'] + 1.0)   # 환경 복합 가혹도

# (4) 5대 미세조직 상분율 결측 처리 및 정량성 지표
phase_cols = ['austenite', 'ferrite', 'martensite', 'bainite', 'pearlite']
for p in phase_cols:
    df[p + '_clean'] = df[p + '_fraction_reported_pct'].fillna(0.0)

df['total_reported_phase']    = sum(df[p + '_clean'] for p in phase_cols)
df['has_quantitative_phase'] = (df['total_reported_phase'] > 0).astype(float)

# (5) 전해질 표기 화학적 대분류화
def categorize_electrolyte(val):
    if pd.isna(val): return 'unknown'
    s = str(val).lower()
    if any(k in s for k in ['nacl', 'seawater', '해수', 'yellow_sea']): return 'chloride_seawater'
    elif any(k in s for k in ['h2so4', 'hcl', 'acid', 'nahso3']): return 'acidic'
    elif any(k in s for k in ['naoh', 'koh', 'caoh', 'pore']): return 'alkaline'
    elif any(k in s for k in ['hanks', 'saliva']): return 'biological'
    return 'other'

df['electrolyte_grouped'] = df['electrolyte_condition_cat'].apply(categorize_electrolyte)

# ========================================================
# 3. 전체 컬럼 리스트업 및 전처리 파이프라인
# ========================================================
num_cols = [
    # 원본 기본 원소 (11개)
    'C', 'Si', 'Mn', 'P', 'S', 'Cr', 'Ni', 'Mo', 'Cu', 'N', 'RE_ppm',
    # 원본 환경 및 동전위 파라미터 (4개)
    'temperature_C', 'pH', 'exposure_h', 'scan_rate_mV_s',
    # 원본 5대 미세조직 상분율 (5개)
    'austenite_clean', 'ferrite_clean', 'martensite_clean', 'bainite_clean', 'pearlite_clean',
    # 유기적 상호작용 피처 (14개)
    'PREN', 'Cr_eq', 'Ni_eq', 'Cr_Ni_ratio', 'Mn_S_ratio', 'RE_to_S_ratio', 'Alloy_Total',
    'inv_Temp_K', 'pH_dev_neutral', 'log_exposure', 'kinetic_intensity', 'env_severity',
    'total_reported_phase', 'has_quantitative_phase'
]

cat_cols = ['RE_element_cat', 'matrix_phase_group', 'steel_family', 'electrolyte_grouped']

preprocessor = ColumnTransformer(
    transformers=[
        ('num', Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ]), num_cols),
        ('cat', Pipeline([
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ]), cat_cols)
    ]
)

X_matrix = preprocessor.fit_transform(df)
print(f">> 총 사용 입력 차원 수: {X_matrix.shape[1]}개 (피처 엔지니어링 38개 변수 확장)")

# ========================================================
# 4. 강종별 층화 75개 샘플링 학습 및 평가
# ========================================================
X_train, X_test, y_train, y_test = train_test_split(
    X_matrix, y, 
    train_size=75, 
    stratify=df['steel_family'], 
    random_state=42
)

# Gradient Boosting 모델
gbr = GradientBoostingRegressor(
    n_estimators=120, max_depth=3, learning_rate=0.07, subsample=0.85, random_state=42
)
gbr.fit(X_train, y_train)

# Random Forest 모델
rf = RandomForestRegressor(
    n_estimators=150, max_depth=9, min_samples_split=3, random_state=42
)
rf.fit(X_train, y_train)

print(f"\n[Gradient Boosting] Train R^2: {r2_score(y_train, gbr.predict(X_train)):.4f} | Test R^2: {r2_score(y_test, gbr.predict(X_test)):.4f}")
print(f"[Random Forest]     Train R^2: {r2_score(y_train, rf.predict(X_train)):.4f} | Test R^2: {r2_score(y_test, rf.predict(X_test)):.4f}")