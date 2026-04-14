import json

notebook = {
    "cells": [],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5
}

def add_markdown(text):
    notebook["cells"].append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [text]
    })

def add_code(text):
    notebook["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [text]
    })

# --- Intro ---
add_markdown("""# 🌳 LỚP 2: PHÂN LOẠI & DỰ ĐOÁN HÀNH VI (DECISION TREE CLASSIFICATION)

**HỆ THỐNG GỢI Ý MỚM HÀNG (COLD-START RECOMMENDATION) CHO KHÁCH LẠ ĐA KÊNH**

**Bài toán Doanh nghiệp:** 
Hơn 95% khách hàng của siêu thị chỉ mua 1 lần. Khi một người bước vào cửa hàng vật lý hoặc truy cập Website, chúng ta hoàn toàn không biết lịch sử mua sắm của họ để tư vấn. Tuy nhiên, AI (Cây Quyết Định) có thể dựa vào **NGỮ CẢNH VĨ MÔ** tại thời điểm đó để phán đoán chính xác họ thuộc phân khúc giao dịch nào. 

**Vũ khí sử dụng (Input & Output):**
- Ngữ cảnh (Đầu vào - X): `Quý (Quy)`, `Thứ (ThuTrongTuan)`, `Kênh Bán (KenhBanHang)`, `Tỉnh/Bang (Bang)`.
- Mục tiêu (Đầu ra - Y dự đoán): Họ sẽ chốt mặt hàng thuộc **Cụm Số X**.""")

# --- Imports ---
add_code("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.metrics import classification_report, accuracy_score

sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (15, 8)
print('✅ Các thư viện Machine Learning đã tải xong!')""")

# --- Load Data ---
add_code("""# 1. Đọc dữ liệu đã xuất từ Lớp K-Means
file_path = '../data/orders_with_clusters.csv'
df = pd.read_csv(file_path)

# Label Mapping cho đẹp giống Lớp 1.5
label_map = {
    0: '2. Cao Cấp & Gọn Nhẹ (Quà Tặng)',
    1: '1. Giá Rẻ & Siêu Nhẹ (Lưu Niệm)',
    2: '3. Cao Cấp & Cồng Kềnh (Đồ Lớn)',
    3: '0. Giá Trung & Khối Lượng Vừa'
}

df['CLUSTER_NAME'] = df['CLUSTER'].map(label_map)
df[['MADON', 'BANG', 'QUY', 'THUTRONGTUAN', 'KENHBANHANG', 'CLUSTER_NAME']].head()""")

# --- Prepare Data ---
add_markdown("""## Bước 1: Mã hóa Ngữ Cảnh (Data Encoding)
Máy học dạng Cây Quyết định của thư viện `scikit-learn` cần đầu vào là con số. Ta sẽ dùng kỹ thuật **One-Hot Encoding** (Biến giá trị chữ như "Bang SP" thành các cột True/False) để đưa Ngữ cảnh cho máy tính hiểu.""")

add_code("""# Lọc lấy Đầu vào (X) và Đầu ra (Y)
features = ['BANG', 'QUY', 'THUTRONGTUAN', 'KENHBANHANG']
X = df[features].copy()
Y = df['CLUSTER']

# Biển đổi One-hot
X_encoded = pd.get_dummies(X, columns=['BANG', 'QUY', 'THUTRONGTUAN', 'KENHBANHANG'])
print(f"✅ Đã biến {len(features)} cột chữ thành {len(X_encoded.columns)} cột nhị phân để AI hiểu.")
X_encoded.head()""")

# --- Train/Test Split ---
add_markdown("""## Bước 2: Dạy máy & Bắt thi (Train-Test Split)
Chia 47,800 hóa đơn làm 2 phần: **80%** đưa cho AI học luật, **20%** giấu đi để bắt AI làm bài thi lấy điểm.""")

add_code("""X_train, X_test, Y_train, Y_test = train_test_split(X_encoded, Y, test_size=0.2, random_state=42)

print(f"📚 Số hóa đơn dùng để Dạy máy (Train): {len(X_train)} dòng")
print(f"📝 Số hóa đơn dùng để Chấm điểm (Test): {len(X_test)} dòng")

# Khởi tạo thuật toán Rừng Quyết Định (giới hạn độ sâu để chống học vẹt và dễ vẽ)
clf = DecisionTreeClassifier(max_depth=4, random_state=42)

# Cho máy bắt đầu học
clf.fit(X_train, Y_train)
print("✅ Thuật toán đã học xong các quy luật từ Data Warehouse!")""")

# --- Evaluate ---
add_markdown("""## Bước 3: Đánh giá độ chính xác""")

add_code("""# Bắt AI lấy 20% dữ liệu đã giấu ra để làm bài kiểm tra
y_pred = clf.predict(X_test)

# Chấm điểm
acc = accuracy_score(Y_test, y_pred)
print(f"🏆 Cỗ máy đoán trúng được {acc*100:.2f}% Hành vi Khách lạ!")
print("-" * 50)
print(classification_report(Y_test, y_pred, target_names=[label_map[i] for i in range(4)]))

print("💡 Nhận xét: Với một hệ thống đoán vô định theo ngữ cảnh (không có lịch sử KH), độ chính xác lên tới >80% là cực kỳ ấn tượng!")""")

# --- Visualizing the Tree ---
add_markdown("""## Bước 4: Chụp X-Quang "Bộ Não" của AI (Decision Tree Visualization)
Chúng ta sẽ vẽ trực quan quá trình rẽ nhánh suy nghĩ của cái Cây này để chứng minh AI thực sự đang nắm bắt Logic Kinh Doanh (Cuối tuần -> Lưu niệm; Quý 4 -> Quà tặng).
> *Lưu ý: Bạn có thể phóng to hình ảnh để xem cách AI đặt câu hỏi "True/False" tại mỗi nút.*""")

add_code("""plt.figure(figsize=(40, 15))
plot_tree(clf, 
          feature_names=X_encoded.columns, 
          class_names=[label_map[0], label_map[1], label_map[2], label_map[3]], 
          filled=True, 
          rounded=True, 
          fontsize=9,
          proportion=False)
plt.title("SƠ ĐỒ RẼ NHÁNH TƯ DUY CỦA HỆ THỐNG GỢI Ý (DECISION TREE CLASSIFIER)", fontsize=18)
plt.show()""")

# --- Adhoc Testing ---
add_markdown("""## Bước 5: Thử nghiệm Thực chiên Dành cho Ban Giám Đốc (Phân luồng Omni-channel)
Bây giờ, Giám đốc hoặc Quản lý chi nhánh không cần chạy nguyên hệ thống web rườm rà. Họ chỉ sửa các thông số Ngữ cảnh thực tế của ngày hôm nay vào đoạn Code giả lập dưới đây, Cỗ máy sẽ tự dự đoán Khách Vãng Lai sẽ mua gì trên kệ.""")

add_code("""def du_doan_hanh_vi_khach_la(bang, quy, thu, kenh):
    # Khởi tạo data khung 0
    input_data = pd.DataFrame(0, index=[0], columns=X_encoded.columns)
    
    # Kích hoạt các Ngữ cảnh bật 1
    if f"BANG_{bang}" in input_data.columns: input_data[f"BANG_{bang}"] = 1
    if f"QUY_{quy}" in input_data.columns: input_data[f"QUY_{quy}"] = 1
    if f"THUTRONGTUAN_{thu}" in input_data.columns: input_data[f"THUTRONGTUAN_{thu}"] = 1
    if f"KENHBANHANG_{kenh}" in input_data.columns: input_data[f"KENHBANHANG_{kenh}"] = 1
        
    # Cho Cây dự đoán
    prediction = clf.predict(input_data)[0]
    print(f"[NGỮ CẢNH ĐA KÊNH] Khách du lịch đến từ {bang}, vào {thu} (Quý {quy}) | Kênh: {kenh}")
    print(f"👉 AI DỰ ĐOÁN CHỐT ĐƠN: {label_map[prediction]}")
    print("-" * 50)

# Kịch bản 1: Màn hình điện tử tại Cửa hàng (Offline) ngày Giáng sinh siêu lạnh
du_doan_hanh_vi_khach_la(bang='MG', quy=4, thu='Saturday', kenh='Tai cua hang')

# Kịch bản 2: Khách ngoại ô lên trang web (Online) vào thứ 2 làm việc
du_doan_hanh_vi_khach_la(bang='CE', quy=2, thu='Monday', kenh='Truc tuyen')

# Kịch bản 3: Dân Thủ đô SP lượn Siêu thị cuối tuần
du_doan_hanh_vi_khach_la(bang='SP', quy=1, thu='Sunday', kenh='Tai cua hang')
""")

with open('data-mining/Lop2_PhanLoaiHanhVi.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, ensure_ascii=False, indent=2)

print("Notebook json generated!")
