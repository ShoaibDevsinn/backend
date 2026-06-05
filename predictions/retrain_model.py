# H:\Backend\predictions\retrain_model.py
import pandas as pd
import numpy as np
import warnings
import re
from scipy import stats

from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib
import os

warnings.filterwarnings('ignore')
print("✅ Libraries imported")

# ============================================
# LOAD DATA
# ============================================
df = pd.read_csv(r"H:\City_Deals_Agency.csv")
print(f"✅ Data loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")

# ============================================
# PREPROCESSING
# ============================================

# Remove Arab prices
df = df[~df['Price'].str.contains('Arab', na=False)].copy()

# Convert Area to SqFt
def area_to_sqft(area_str):
    if pd.isna(area_str) or not isinstance(area_str, str):
        return np.nan
    area_str = area_str.strip()
    if 'Marla' in area_str:
        try:
            return float(area_str.split()[0]) * 272.25
        except:
            return np.nan
    if 'Kanal' in area_str:
        try:
            return float(area_str.split()[0]) * 5445
        except:
            return np.nan
    return np.nan

# Convert Price to PKR
def price_to_pkr(price_str):
    if pd.isna(price_str) or not isinstance(price_str, str):
        return np.nan
    price_str = price_str.strip()
    
    total = 0
    if 'Crore' in price_str:
        try:
            crore_part = price_str.split('Crore')[0].strip()
            total += float(crore_part) * 10_000_000
            price_str = price_str.split('Crore')[1]
        except:
            pass
    if 'Lakh' in price_str:
        try:
            lakh_part = price_str.split('Lakh')[0].strip()
            total += float(lakh_part) * 100_000
        except:
            pass
    
    if total > 0:
        return total
    
    price_str = price_str.strip()
    if 'Crore' in price_str:
        try:
            return float(price_str.replace('Crore', '').strip()) * 10_000_000
        except:
            return np.nan
    if 'Lakh' in price_str:
        try:
            return float(price_str.replace('Lakh', '').strip()) * 100_000
        except:
            return np.nan
    return np.nan

df['Area_SqFt'] = df['Area'].apply(area_to_sqft)
df['Price_PKR'] = df['Price'].apply(price_to_pkr)

print(f"✅ Units converted")
df = df.dropna(subset=['Area_SqFt', 'Price_PKR'])
print(f"✅ Rows after dropping missing: {df.shape[0]:,}")

# Clean numeric columns - FIXED: Convert to numeric first
def safe_numeric(series):
    """Convert to numeric, replacing non-numeric with NaN"""
    return pd.to_numeric(series, errors='coerce')

# Clean Bedrooms & Bathrooms
for col in ['Bedrooms', 'Bathrooms']:
    if col in df.columns:
        df[col] = safe_numeric(df[col])
        df[col] = df[col].fillna(df[col].median())

# Clean Kitchens
if 'Kitchens' in df.columns:
    df['Kitchens'] = safe_numeric(df['Kitchens'])
    df['Kitchens'] = df['Kitchens'].fillna(df['Kitchens'].median())
else:
    df['Kitchens'] = 1

# Clean Built Year
if 'Built Year' in df.columns:
    df['Built Year'] = safe_numeric(df['Built Year'])
    df = df[(df['Built Year'] >= 1900) & (df['Built Year'] <= 2025)]
    df['Built Year'] = df['Built Year'].fillna(df['Built Year'].median()).astype(int)
else:
    df['Built Year'] = 2020

print(f"✅ Numeric columns cleaned. Rows: {df.shape[0]:,}")

# Number of floors extraction
def extract_floors_from_title(title):
    if pd.isna(title):
        return np.nan
    title_lower = str(title).lower()
    
    patterns = [
        (r'triple\s*(?:storey|story)', 3),
        (r'(?:3|three)\s*(?:storey|story)', 3),
        (r'double\s*(?:storey|story)', 2),
        (r'(?:2|two)\s*(?:storey|story)', 2),
        (r'single\s*(?:storey|story)', 1),
        (r'(?:1|one)\s*(?:storey|story)', 1),
    ]
    
    for pattern, floors in patterns:
        if re.search(pattern, title_lower):
            return floors
    return np.nan

def derive_floors_from_features(area_sqft, bedrooms):
    area_marla = area_sqft / 272.25
    if area_marla <= 3:
        return 3 if bedrooms >= 3 else 2
    elif area_marla <= 5:
        return 3 if bedrooms >= 6 else (2 if bedrooms >= 3 else 2)
    elif area_marla <= 10:
        return 3 if bedrooms >= 7 else 2
    else:
        return 3 if bedrooms >= 8 else 2

# Extract floors
if 'Title' in df.columns:
    df['Num_Floors'] = df['Title'].apply(extract_floors_from_title)
    missing_mask = df['Num_Floors'].isna()
    df.loc[missing_mask, 'Num_Floors'] = df[missing_mask].apply(
        lambda row: derive_floors_from_features(row['Area_SqFt'], row['Bedrooms']), axis=1
    )
else:
    df['Num_Floors'] = df.apply(
        lambda row: derive_floors_from_features(row['Area_SqFt'], row['Bedrooms']), axis=1
    )

df['Num_Floors'] = df['Num_Floors'].fillna(2).astype(int)
print(f"✅ Num_Floors created")

# Amenities encoding
BOOLEAN_AMENITY_COLS = [
    'Furnished', 'Gym', 'Study Room', 'Drawing Room', 
    'Dining Room', 'Lawn/Garden', 'Swimming Pool', 
    'Electricity Backup', 'Lounge/Sitting Room',
]

for col in BOOLEAN_AMENITY_COLS:
    if col in df.columns:
        df[col] = df[col].apply(
            lambda val: 1 if (
                (isinstance(val, str) and val.strip().upper() == 'TRUE') or
                (isinstance(val, bool) and val) or
                (isinstance(val, (int, float)) and val == 1)
            ) else 0
        )
    else:
        df[col] = 0

# Clean Servant Quarters & Store Rooms
for col in ['Servant Quarters', 'Store Rooms']:
    if col in df.columns:
        df[col] = safe_numeric(df[col]).fillna(0).astype(int)
    else:
        df[col] = 0

print(f"✅ Amenities encoded")

# Feature engineering
CURRENT_YEAR = 2025
df['House_Age'] = CURRENT_YEAR - df['Built Year']

AMENITY_SUBSET = [
    'Gym', 'Study Room', 'Drawing Room', 'Dining Room',
    'Lawn/Garden', 'Swimming Pool', 'Electricity Backup', 'Lounge/Sitting Room'
]
df['Total_Amenities'] = df[AMENITY_SUBSET].sum(axis=1)

# Main Location
def extract_main_location(location_str):
    if pd.isna(location_str):
        return 'Unknown'
    parts = str(location_str).strip().split(',')
    return parts[-1].strip() if parts else 'Unknown'

df['Main_Location'] = df['Location'].apply(extract_main_location)
TOP_N_LOCATIONS = 15
top_locations = df['Main_Location'].value_counts().nlargest(TOP_N_LOCATIONS).index
df['Main_Location'] = df['Main_Location'].apply(lambda loc: loc if loc in top_locations else 'Other')

# Corner & Park Facing
if 'Title' in df.columns:
    df['Title'] = df['Title'].fillna('')
    df['Is_Corner'] = df['Title'].str.contains('corner', case=False, na=False).astype(int)
    df['Facing_Park'] = df['Title'].str.contains('facing park', case=False, na=False).astype(int)
else:
    df['Is_Corner'] = 0
    df['Facing_Park'] = 0

# Derived features
df['Area_per_Bedroom'] = df['Area_SqFt'] / df['Bedrooms'].clip(lower=1)
df['Bathroom_Ratio'] = df['Bathrooms'] / df['Bedrooms'].clip(lower=1)
df['Beds_x_Floors'] = df['Bedrooms'] * df['Num_Floors']
df['Age_x_Amenities'] = df['House_Age'] * df['Total_Amenities']

print(f"✅ Features engineered. Shape: {df.shape}")

# Remove outliers
rows_before = df.shape[0]
area_lower = df['Area_SqFt'].quantile(0.005)
area_upper = df['Area_SqFt'].quantile(0.995)
df = df[(df['Area_SqFt'] >= area_lower) & (df['Area_SqFt'] <= area_upper)]

log_price = np.log1p(df['Price_PKR'])
log_lower = log_price.quantile(0.005)
log_upper = log_price.quantile(0.995)
df = df[(log_price >= log_lower) & (log_price <= log_upper)]

temp_pps = df['Price_PKR'] / df['Area_SqFt']
pps_lower = temp_pps.quantile(0.01)
pps_upper = temp_pps.quantile(0.99)
df = df[(temp_pps >= pps_lower) & (temp_pps <= pps_upper)]

print(f"✅ Outliers removed: {rows_before - df.shape[0]} rows")
print(f"   Remaining: {df.shape[0]:,} rows")

# ============================================
# FEATURE SELECTION
# ============================================
CATEGORICAL_FEATURES = ['Main_Location']

NUMERICAL_FEATURES = [
    'Area_SqFt', 'Bedrooms', 'Bathrooms', 'Kitchens', 'House_Age', 'Num_Floors',
    'Servant Quarters', 'Store Rooms', 'Furnished', 'Gym', 'Study Room',
    'Drawing Room', 'Dining Room', 'Lawn/Garden', 'Swimming Pool',
    'Electricity Backup', 'Lounge/Sitting Room', 'Total_Amenities',
    'Is_Corner', 'Facing_Park', 'Area_per_Bedroom', 'Bathroom_Ratio',
    'Beds_x_Floors', 'Age_x_Amenities'
]

# Keep only existing columns
CATEGORICAL_FEATURES = [c for c in CATEGORICAL_FEATURES if c in df.columns]
NUMERICAL_FEATURES = [c for c in NUMERICAL_FEATURES if c in df.columns]

feature_cols = CATEGORICAL_FEATURES + NUMERICAL_FEATURES
X = df[feature_cols].copy()
y = np.log1p(df['Price_PKR'])

print(f"✅ Features: {X.shape[1]} columns")

# Handle NaN
X = X.replace([np.inf, -np.inf], np.nan)
for col in NUMERICAL_FEATURES:
    if col in X.columns:
        X[col] = X[col].fillna(X[col].median())

for col in CATEGORICAL_FEATURES:
    if col in X.columns:
        X[col] = X[col].fillna('Unknown')

print(f"✅ Sanitised. Remaining NaN: {X.isna().sum().sum()}")

# ============================================
# TRAIN-TEST SPLIT
# ============================================
price_bins = pd.qcut(df['Price_PKR'], q=10, labels=False, duplicates='drop')
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=price_bins
)
print(f"✅ Train: {X_train.shape[0]:,} | Test: {X_test.shape[0]:,}")

# ============================================
# PREPROCESSOR
# ============================================
numerical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numerical_transformer, NUMERICAL_FEATURES),
        ('cat', categorical_transformer, CATEGORICAL_FEATURES),
    ],
    remainder='drop'
)

# ============================================
# MODEL
# ============================================
xgb_model = xgb.XGBRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.85,
    colsample_bytree=0.85,
    min_child_weight=3,
    reg_alpha=0.1,
    reg_lambda=1.5,
    gamma=0.1,
    random_state=42,
    objective='reg:squarederror',
    verbosity=0,
    n_jobs=-1
)

xgb_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', xgb_model)
])

# ============================================
# TRAIN
# ============================================
print("⏳ Training XGBoost...")
xgb_pipeline.fit(X_train, y_train)

# ============================================
# EVALUATE
# ============================================
y_pred_log_test = xgb_pipeline.predict(X_test)
y_test_pkr = np.expm1(y_test)
y_pred_test_pkr = np.expm1(y_pred_log_test)

test_r2 = r2_score(y_test_pkr, y_pred_test_pkr)
test_mae = mean_absolute_error(y_test_pkr, y_pred_test_pkr)

print(f"\n{'='*60}")
print(f"📊 MODEL PERFORMANCE")
print(f"{'='*60}")
print(f"   Test R² : {test_r2:.4f}")
print(f"   Test MAE: PKR {test_mae:,.0f}")

# ============================================
# SAVE MODEL
# ============================================
print("\n💾 Saving model...")
os.makedirs('predictions/models', exist_ok=True)

pipeline_path = 'predictions/models/property_price_pipeline.pkl'
joblib.dump(xgb_pipeline, pipeline_path)

feature_cols_path = 'predictions/models/feature_columns.pkl'
joblib.dump(X.columns.tolist(), feature_cols_path)

print(f"✅ Model saved to: {pipeline_path}")
print(f"✅ Feature columns saved to: {feature_cols_path}")
print("\n✅ Retraining complete! The model is now compatible.")