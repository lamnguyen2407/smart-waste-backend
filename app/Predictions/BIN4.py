import pandas as pd
import joblib
import os
from datetime import date, timedelta

# Lấy đường dẫn tuyệt đối
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "app", "models", "BIN5.pkl")

print(f"Loading model from: {MODEL_PATH}")

if not os.path.exists(MODEL_PATH):
    print("❌ Lỗi: Không tìm thấy file model. Hãy chạy train_model.py trước.")
    exit()

model = joblib.load(MODEL_PATH)

def predict_trash_generated_tomorrow(
    trash_today,
    trash_yesterday,
    trash_2_days_ago,
    tomorrow_date,
    is_holiday_tomorrow
):
    day_of_week = tomorrow_date.weekday()
    is_weekend = int(day_of_week >= 5)

    X = pd.DataFrame([{
        "trash_generated_today": trash_today,
        "trash_generated_yesterday": trash_yesterday,
        "trash_generated_2_days_ago": trash_2_days_ago,
        "is_weekend_tomorrow": is_weekend,
        "is_holiday_tomorrow": int(is_holiday_tomorrow),
    }])

    prediction = model.predict(X)[0]
    return max(0.0, float(prediction))

# Test thử
if __name__ == "__main__":
    print("Test dự báo:", predict_trash_generated_tomorrow(50, 40, 30, date.today(), 0))