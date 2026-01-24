import firebase_admin
from firebase_admin import credentials, firestore

# 1. Thử kết nối
print("--- BẮT ĐẦU KIỂM TRA ---")
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    print("✅ Bước 1: Kết nối Firebase thành công!")
except Exception as e:
    print(f"❌ Bước 1 Thất bại: Lỗi file key hoặc cấu hình. \nChi tiết: {e}")
    exit()

# 2. Thử đọc dữ liệu
print("\n🔄 Bước 2: Đang đọc collection 'devices'...")
try:
    # Lấy collection 'devices'
    users_ref = db.collection('devices')
    docs = users_ref.stream()

    found_any = False
    for doc in docs:
        found_any = True
        data = doc.to_dict()
        print(f"\n🔥 TÌM THẤY DEVICE: {doc.id}")
        print(f"📦 Dữ liệu gốc: {data}")
        
        # Kiểm tra kỹ trường fullness_RM
        if 'fullness_RM' in data:
            print(f"🎯 Đọc được fullness_RM: {data['fullness_RM']}")
        else:
            print("⚠️ Cảnh báo: Không thấy trường 'fullness_RM'!")
            
        break # Chỉ đọc 1 cái rồi dừng để tiết kiệm

    if not found_any:
        print("⚠️ Kết nối được nhưng không tìm thấy document nào trong 'devices'.")
    else:
        print("\n✅ KẾT LUẬN: Backend đọc dữ liệu NGON LÀNH!")

except Exception as e:
    print(f"❌ Bước 2 Thất bại: Lỗi khi đọc dữ liệu. \nChi tiết: {e}")