import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os

# ================= CONFIG (ĐÃ SỬA) =================
DATA_PATH = "data/BIN5-Processed.csv" # Đã sửa 'sdata' -> 'data'
MODEL_PATH = "app/models/BIN5.pkl"    # Đã bỏ 'smart-waste-backend/' thừa

FEATURES = [
    "trash_generated_today",
    "trash_generated_yesterday",
    "trash_generated_2_days_ago",
    "is_weekend_tomorrow",
    "is_holiday_tomorrow",
]

TARGET = "target_trash_generated_tomorrow"

# ================= LOAD =================
if not os.path.exists(DATA_PATH):
    print(f"❌ Lỗi: Không tìm thấy file {DATA_PATH}. Hãy chạy DataPrepocessing.py trước!")
    exit()

print(f"🔄 Đang đọc dữ liệu từ {DATA_PATH}...")
df = pd.read_csv(DATA_PATH)

X = df[FEATURES]
y = df[TARGET]

# ================= TIME-BASED SPLIT =================
split_idx = int(len(df) * 0.8)

X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

# ================= TRAIN =================
print("🧠 Đang huấn luyện model...")
model = LinearRegression()
model.fit(X_train, y_train)

# ================= EVALUATE =================
y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))

print("📊 Linear Regression Performance")
print(f"MAE  : {mae:.2f}")
print(f"RMSE : {rmse:.2f}")

# ================= COEFFICIENTS =================
coef_df = pd.DataFrame({
    "feature": FEATURES,
    "coefficient": model.coef_
})

print("\n📈 Model coefficients")
print(coef_df)

# ================= SAVE =================
# Đảm bảo thư mục tồn tại
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

joblib.dump(model, MODEL_PATH)
print("\n✅ Linear model saved to:", MODEL_PATH)