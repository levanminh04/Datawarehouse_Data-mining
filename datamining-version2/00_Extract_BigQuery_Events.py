import os
import pandas as pd
import time

# Kiểm tra thư viện cần thiết
try:
    from google.cloud import bigquery
    # Kiểm tra xem có pyarrow không vì to_dataframe() cần nó để chạy nhanh/hiệu quả
    import pyarrow
    import db_dtypes
except ImportError as e:
    print(f"Thiếu thư viện: {e.name}")
    print("Vui lòng cài đặt bằng lệnh: pip install google-cloud-bigquery pandas pyarrow db-dtypes")
    # Dừng chương trình nếu thiếu thư viện quan trọng
    if e.name in ['google.cloud.bigquery', 'pandas']:
        exit()

# 1. Cấu hình đường dẫn file JSON Key
# Tôi đã rà soát và thấy file của bạn nằm ở thư mục cha của 'datamining-version2'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Danh sách các đường dẫn có thể chứa file key
possible_paths = [
    os.path.join(current_dir, "celtic-current-458114-n3-e19980c26af0.json"), # Cùng thư mục code
    os.path.join(parent_dir, "celtic-current-458114-n3-e19980c26af0.json"),  # Thư mục cha (Vị trí hiện tại của bạn)
    r"d:\PTIT\kì 2 năm 4\Kho dữ liệu và khai phá dữ liệu\BTL\celtic-current-458114-n3-e19980c26af0.json" # Đường dẫn tuyệt đối
]

key_path = None
for p in possible_paths:
    if os.path.exists(p):
        key_path = p
        break

if not key_path:
    print("LỖI: Không tìm thấy file JSON key 'celtic-current-458114-n3-e19980c26af0.json'.")
    print("Hãy đảm bảo file này nằm cùng thư mục với file python hoặc ở thư mục gốc của project.")
    exit()

# Thiết lập biến môi trường cho Google SDK
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
print(f"[*] Đã xác thực thành công file key tại: {key_path}")

# 2. Khởi tạo BigQuery Client
try:
    client = bigquery.Client()
    # Kiểm tra kết nối bằng cách lấy project id
    print(f"[*] Đang kết nối tới Project: {client.project}")
except Exception as e:
    print(f"Lỗi khi khởi tạo kết nối BigQuery: {e}")
    exit()

# 3. Viết câu query lấy toàn bộ bảng events
# Bảng events của thelook_ecommerce có khoảng 2.4 triệu dòng
query = """
    SELECT *
    FROM `bigquery-public-data.thelook_ecommerce.events`
"""

print("\n--- BẮT ĐẦU TRÍCH XUẤT DỮ LIỆU ---")
print("Thông báo: Bảng 'events' khá lớn (~2.4M dòng). Quá trình tải có thể mất từ 2 đến 5 phút.")
print("Đang xử lý, vui lòng đợi...")

start_time = time.time()

try:
    # 4. Tải dữ liệu vào DataFrame
    # Sử dụng to_dataframe() với cấu hình mặc định (tối ưu nhất nếu đã cài pyarrow)
    query_job = client.query(query)
    df_events = query_job.to_dataframe()
    
    download_time = time.time() - start_time
    print(f"[*] Tải dữ liệu thành công!")
    print(f"[*] Tổng số dòng: {len(df_events):,}")
    print(f"[*] Thời gian tải: {round(download_time, 2)} giây")

    # 5. Chia nhỏ và lưu thành nhiều file CSV
    # Mỗi file 500,000 dòng để dễ mở bằng Excel hoặc các công cụ khác
    chunk_size = 500000 
    total_rows = len(df_events)
    num_files = (total_rows // chunk_size) + (1 if total_rows % chunk_size != 0 else 0)

    print(f"\n--- ĐANG LƯU DỮ LIỆU THÀNH {num_files} FILE CSV ---")

    for i in range(num_files):
        start_row = i * chunk_size
        end_row = min((i + 1) * chunk_size, total_rows)
        
        # Lấy phần dữ liệu tương ứng
        df_chunk = df_events.iloc[start_row:end_row]
        
        # Đặt tên file
        filename = f"events_part_{i+1}.csv"
        
        # Lưu file (index=False để không lưu thêm cột số thứ tự của Pandas)
        df_chunk.to_csv(filename, index=False)
        print(f"  [+] Đã lưu: {filename} (Dòng {start_row:,} đến {end_row:,})")

    total_execution_time = time.time() - start_time
    print(f"\n--- HOÀN TẤT ---")
    print(f"Tổng thời gian thực hiện: {round(total_execution_time, 2)} giây")
    print(f"Tất cả file đã được lưu tại: {os.getcwd()}")

except Exception as e:
    print(f"\n[!] CÓ LỖI XẢY RA TRONG QUÁ TRÌNH CHẠY:")
    print(f"Chi tiết: {str(e)}")
    print("\nGợi ý khắc phục:")
    print("1. Kiểm tra kết nối Internet.")
    print("2. Đảm bảo bạn đã cài đặt đầy đủ thư viện: pip install google-cloud-bigquery pandas pyarrow db-dtypes")
    print("3. Kiểm tra xem file JSON key có quyền truy cập vào BigQuery Public Data hay không.")
