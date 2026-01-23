from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
import joblib
import datetime
import os
import random
# Import sklearn để tránh lỗi nếu máy chưa load thư viện
from sklearn.linear_model import LinearRegression 
import firebase_admin
from firebase_admin import credentials, db

# --- 1. CẤU HÌNH KẾT NỐI FIREBASE ---
if not firebase_admin._apps:
    # Đảm bảo file firebase-key.json đang nằm cùng thư mục
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred, {
        # THAY LINK CỦA BẠN VÀO ĐÂY NHÉ !!!
        'databaseURL': 'https://introcecs-default-rtdb.asia-southeast1.firebasedatabase.app/' 
    })

# Hàm lấy dữ liệu Bin 5
def get_bin5_data_from_firebase():
    try:
        # Sửa đường dẫn này cho khớp với cây thư mục trên Firebase của bạn
        ref = db.reference('Bin5') # Ví dụ: Nếu data nằm ngay folder gốc tên Bin5
        data = ref.get()
        if data:
            print(f"🔥 Data Bin 5 từ Firebase: {data}")
            return data
        else:
            return None
    except Exception as e:
        print("❌ Lỗi đọc Firebase:", e)
        return None
    
app = Flask(__name__)
CORS(app)

# --- CẤU HÌNH ĐƯỜNG DẪN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "app", "models")

# --- HÀM DỰ BÁO ---
def predict_trash_tomorrow(bin_id, current_fill_level):
    try:
        model_path = os.path.join(MODEL_DIR, f"{bin_id}.pkl")
        if not os.path.exists(model_path):
            return 10.0 

        model = joblib.load(model_path)
        X_input = pd.DataFrame([{
            "trash_generated_today": current_fill_level,
            "trash_generated_yesterday": 15, 
            "trash_generated_2_days_ago": 10, 
            "is_weekend_tomorrow": 0,
            "is_holiday_tomorrow": 0
        }])
        features = ["trash_generated_today", "trash_generated_yesterday", "trash_generated_2_days_ago", "is_weekend_tomorrow", "is_holiday_tomorrow"]
        X_input = X_input[features]
        prediction = model.predict(X_input)[0]
        return max(0.0, float(prediction))
    except Exception as e:
        print(f"⚠️ Lỗi model {bin_id}: {e}")
        return 5.0

@app.route('/api/get-bins', methods=['GET'])
def get_bins_api():
    bins_response = []
    
    bins_config = [
        {"short_id": "BIN1", "id": "BIN-001", "name": "Hoan Kiem Lake", "lat": 21.0285, "lng": 105.8542, "type": "General"},
        {"short_id": "BIN2", "id": "BIN-002", "name": "Old Quarter Center", "lat": 21.0333, "lng": 105.8500, "type": "Recyclable"},
        {"short_id": "BIN3", "id": "BIN-003", "name": "St. Joseph's Cathedral", "lat": 21.0288, "lng": 105.8489, "type": "Organic"},
        {"short_id": "BIN4", "id": "BIN-004", "name": "Hanoi Opera House", "lat": 21.0254, "lng": 105.8575, "type": "General"},
        {"short_id": "BIN5", "id": "BIN-005", "name": "Ba Dinh Square", "lat": 21.0368, "lng": 105.8347, "type": "Hazardous"},
    ]

    for bin_info in bins_config:
        s_id = bin_info['short_id']
        
        # Mặc định các bin khác giữ nguyên
        current_fill = 50 
        battery = 90

        if s_id == "BIN1":
            current_fill = 82; battery = 45
        elif s_id == "BIN2":
            current_fill = 45; battery = 90
        elif s_id == "BIN3":
            current_fill = 48; battery = 65
        elif s_id == "BIN4":
            current_fill = 88; battery = 95
        
        elif s_id == "BIN5":
            # --- ĐÂY LÀ CHỖ QUAN TRỌNG ĐÃ SỬA ---
            fb_data = get_bin5_data_from_firebase() # Gọi hàm lấy data thật
            
            if fb_data:
                # TH1: Nếu Firebase trả về số nguyên (ví dụ: 85)
                try:
                    current_fill = int(fb_data)
                except:
                    # TH2: Nếu Firebase trả về Dictionary (ví dụ: {'fill': 85})
                    # Bạn phải sửa key 'fill' thành tên key thật trên Firebase của bạn
                    if isinstance(fb_data, dict):
                         current_fill = int(fb_data.get('fill', 75))
            else:
                # Nếu mất mạng hoặc lỗi key thì Random chống cháy
                current_fill = random.randint(60, 98)

        # --- DỰ BÁO ---
        added_val = predict_trash_tomorrow(s_id, current_fill)
        predicted_total = current_fill + added_val
        
        is_fill = (current_fill >= 85 or predicted_total >= 85)
        status = "Fill" if is_fill else "Not Fill"

        bins_response.append({
            "id": bin_info['id'],
            "name": bin_info['name'],
            "lat": bin_info['lat'],
            "lng": bin_info['lng'],
            "type": bin_info['type'],
            "fillLevel": int(current_fill),
            "predictedLevel": int(predicted_total),
            "status": status,
            "battery": battery,
            "lastUpdate": "Just now"
        })

    return jsonify(bins_response)

if __name__ == '__main__':
    app.run(debug=True, port=5000)