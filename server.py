from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
import joblib
import os
import time
import random 
# Import sklearn để tránh lỗi
from sklearn.linear_model import LinearRegression 
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. CẤU HÌNH KẾT NỐI FIRESTORE ---
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)

# Khởi tạo Client
db = firestore.client()

# --- BIẾN TOÀN CỤC ĐỂ LƯU CACHE ---
cached_bin5_data = None   # Lưu dữ liệu thô từ Firestore
last_read_time = 0        # Lưu thời điểm đọc gần nhất

# ============================================================
# 🛡️ HÀM LẤY DỮ LIỆU AN TOÀN TUYỆT ĐỐI (FIX LỖI 27K READS) 🛡️
# ============================================================
def get_bin5_data_safe():
    global cached_bin5_data, last_read_time
    
    current_time = time.time()
    
    # 🛑 1. KIỂM TRA THỜI GIAN:
    # Nếu chưa quá 10 giây kể từ lần gọi trước
    if (current_time - last_read_time < 10):
        if cached_bin5_data is not None:
            print("⏳ Đang dùng Cached Data (Tiết kiệm quota)...")
            return cached_bin5_data
        else:
            # TRƯỜNG HỢP QUAN TRỌNG:
            # Nếu chưa có cache (lần đầu chạy) mà Web gọi liên tục
            # -> Trả về None ngay để chặn việc đọc Firestore dồn dập
            print("🚫 Đang chờ dữ liệu đầu tiên (Chặn Spam)...")
            return None

    # 🔒 2. KHÓA CỬA NGAY LẬP TỨC (QUAN TRỌNG NHẤT)
    # Cập nhật thời gian TRƯỚC khi đọc. Để các request đến sau bị chặn ngay.
    last_read_time = current_time 

    # ✅ 3. TIẾN HÀNH ĐỌC TỪ GOOGLE
    try:
        print("🔄 Đang đọc dữ liệu mới từ Firestore...")
        users_ref = db.collection('devices')
        docs = users_ref.stream()

        for doc in docs:
            data = doc.to_dict()
            print(f"🔥 Tìm thấy Device ID: {doc.id}")
            
            # Cập nhật Cache
            cached_bin5_data = data
            return data
            
        return None 
    except Exception as e:
        print("❌ Lỗi đọc Firestore:", e)
        # Nếu lỗi thì reset thời gian về 0 để lần sau thử lại ngay
        last_read_time = 0 
        return None 

app = Flask(__name__)
CORS(app)

# --- CẤU HÌNH ĐƯỜNG DẪN MODEL ---
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
        current_fill = 50 
        battery = 90

        # Data giả lập cho Bin 1-4
        if s_id == "BIN1": current_fill = 82
        elif s_id == "BIN2": current_fill = 45
        elif s_id == "BIN3": current_fill = 48
        elif s_id == "BIN4": current_fill = 88
        
        # --- XỬ LÝ BIN 5 (DỮ LIỆU THẬT + RANDOM DỰ PHÒNG) ---
        elif s_id == "BIN5":
            fb_data = get_bin5_data_safe()
            
            # 1. Random trước (đề phòng lỗi mạng hoặc chưa lấy được data)
            current_fill = random.randint(60, 95) 

            # 2. Nếu có data thật thì ghi đè lên
            if fb_data:
                # Ưu tiên đọc trường 'fullness_RM' (Database Mới)
                if 'fullness' in fb_data:
                    try:
                        current_fill = int(fb_data['fullness'])
                    except:
                        pass
                # Nếu không có thì thử đọc 'fullness' (Database Cũ - đề phòng)
                elif 'fullness_RM' in fb_data:
                    try:
                        current_fill = int(fb_data['fullness_RM'])
                    except:
                        pass
            
            # Nếu fb_data là None (do bị chặn spam hoặc lỗi) -> Nó sẽ giữ giá trị Random ở trên

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