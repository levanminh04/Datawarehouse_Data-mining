# 📝 DANH SÁCH CÔNG VIỆC TRIỂN KHAI LAYER 1: CLUSTERING

## 1. Chuẩn bị & Xác thực dữ liệu
- [ ] Khởi tạo Jupyter Notebook với cấu trúc chuyên nghiệp (Markdown, Testcase).
- [ ] Verify 1.1: Đảm bảo dữ liệu load thành công, số dòng > 40,000.
- [ ] Verify 1.2: Các cột quan trọng `Gia`, `TrongLuong` không có giá trị NULL hoặc âm rác.

## 2. Tiền xử lý (Preprocessing)
- [ ] Xử lý outlier và dòng có `TrongLuong = 0`.
- [ ] Log-transform cho `Gia` và `TrongLuong`.
- [ ] Verify 2.1: Biểu đồ Histogram trước và sau khi biến đổi phải khác biệt trực quan (từ lệch phải trầm trọng chuyển dần về phân phối chuẩn).
- [ ] Áp dụng StandardScaler.
- [ ] Verify 2.2: Mean của tập đã scale xấp xỉ 0, Std xấp xỉ 1.

## 3. Lựa chọn Hyperparameter (Số cụm K)
- [ ] Tính và vẽ biểu đồ Elbow Method (K từ 2 đến 10).
- [ ] Tính và vẽ biểu đồ Silhouette Score.
- [ ] **STOP & REVIEW**: Người dùng xem biểu đồ và chốt số K dựa trên kết quả thực tế (dự kiến K=3 hoặc K=4).

## 4. Chạy thuật toán K-Means & Lưu trữ
- [ ] Fit mô hình với K đã chốt.
- [ ] Gán nhãn Label (`Cluster`) vào dataframe.
- [ ] Trực quan hoá bằng Scatter Plot 2D với Centroids.
- [ ] Xuất DataFrame đã gán nhãn ra file `data/orders_with_clusters.csv` để chuẩn bị cho Layer 2.

## 5. Báo cáo & Bàn giao
- [ ] Xuất báo cáo sơ bộ tỷ lệ % mỗi cụm.
- [ ] Cung cấp các thông số Median cho từng cụm để người dùng gán Business Name hợp lý.
