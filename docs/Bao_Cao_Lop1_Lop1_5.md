# BÁO CÁO ĐỒ ÁN: KHO DỮ LIỆU & KHAI PHÁ DỮ LIỆU
## Đề tài: Giải mã Cỗ máy Bán hàng - Phân cụm Sản phẩm và Đặc tả Hành vi Khách hàng trong Chuỗi Bán lẻ Đa kênh

---

## PHẦN 1: BỐI CẢNH VÀ VẤN ĐỀ DOANH NGHIỆP (BUSINESS UNDERSTANDING)

### 1. Tổng quan Dữ liệu & Nền tảng Data Warehouse
Hệ thống bán lẻ đa kênh của doanh nghiệp được xây dựng trên nền tảng Kho dữ liệu (Data Warehouse) với cấu trúc Start-Schema, lưu trữ toàn bộ dữ liệu lịch sử từ năm 2015 đến 2018. Khối lượng dữ liệu bao gồm:
- Hơn **47,800** hóa đơn bán lẻ (`FACT_ORDER`).
- Bảng chiều `DIM_CUSTOMER` (~44,000 khách hàng), `DIM_PRODUCT` (~20,000 sản phẩm).
- Bảng chiều `DIM_LOCATION` (130 chi nhánh) và `DIM_TIME`.

### 2. Vấn đề "Nút thắt cổ chai" trong Khai phá Dữ liệu truyền thống
Khi khảo sát sơ bộ (Exploratory Data Analysis - EDA), chúng tôi phát hiện một đặc thù dị biệt của mô hình kinh doanh này:
- **95.2%** khách hàng chỉ xuất hiện và mua sắm đúng **1 lần duy nhất** trong suốt 3 năm.
- **92.7%** giỏ hàng của khách chỉ chứa đúng **1 món đồ**.

**Nhận định học thuật:**
Với đặc điểm dữ liệu "Cold Start" (Khách hàng một lần) và "Giỏ hàng mỏng" (Đơn hàng 1 món), các phương pháp Khai phá dữ liệu kinh điển được sử dụng phổ biến ở mức sinh viên như: 
1. *Mô hình Lòng trung thành RFM (Recency, Frequency, Monetary)* 
2. *Khai phá Luật kết hợp (Association Rules / Market Basket Analysis)*
...đều hoàn toàn vô tác dụng (Frequency luôn bằng 1, Support của luật kết hợp luôn tiến về 0).

**Hướng đi Đột phá:**
Thay vì phân tích "Sự lặp lại của Khách hàng" (điều không tồn tại), đồ án lựa chọn xoay trục sang phân tích bản chất của **Cỗ Máy Bán Hàng**: Chúng tôi sẽ Phân cụm (Clustering) Dữ liệu cấp độ **Sản phẩm (Product)** kết hợp với **Đơn hàng (Order)**, từ đó đặc tả hành vi mua sắm ẩn giấu dựa trên Không gian (Bang), Thời gian (Quý/Thứ) và Kênh (Online/Offline).

---

## PHẦN 2: LỚP 1 - PHÂN CỤM DỮ LIỆU BẰNG THUẬT TOÁN K-MEANS (CLUSTERING)

### 1. Chuẩn bị Dữ liệu (Data Pre-processing)
Sau quá trình làm sạch, hai thuộc tính (Features) mạnh nhất của hệ thống được giữ lại để đưa vào máy học:
- **Giá (Price):** Tính bằng USD.
- **Trọng Lượng (Weight):** Tính bằng Gram.

Dữ liệu gốc có đặc tính lệch phải cực đoan (Right-skewed) với một số sản phẩm lên tới 6,700$ hoặc nặng tới 30kg. Để thuật toán tính toán khoảng cách (Euclidean Distance) không bị méo mó, chúng tôi áp dụng kỹ thuật **Log-Transformation** để kéo phân phối dữ liệu về chuẩn (Normal Distribution), sau đó dùng **StandardScaler** để chuẩn hóa thang đo (Mean=0, Variance=1).

### 2. Huấn luyện Mô hình K-Means
- **Tìm "K" Tối Ưu:** Sử dụng phương pháp Khuỷu tay (Elbow Method) kết hợp với Hệ số nội cực (Silhouette Score). Đồ thị Elbow gãy rõ rệt tại `K=4`, và tốc độ giảm WCSS chững lại.
- **Quyết định:** Chốt mô hình `K-Means(n_clusters=4)`.

### 3. Diễn giải 4 Cụm Sản phẩm (Cluster Interpretation)
Thuật toán chia 47,800 hóa đơn thành 4 Cụm hành vi hoàn toàn tách biệt. Thông qua việc quan sát tọa độ tâm cụm (Centroids), chúng ta có thể đặt tên (Gắn Nhãn Kinh Doanh) cho chúng:

| ID | Nhãn Cụm (Business Name) | Mức Giá Trung Bình | Trọng Lượng Trung Bình | Tỷ trọng |
|----|--------------------------|-------------------|------------------------|----------|
| **0** | **2. Cao Cấp & Gọn Nhẹ (Quà Tặng)** | Rất cao (~146$) | Rất nhẹ (~400g) | 20.49% |
| **1** | **1. Giá Rẻ & Siêu Nhẹ (Lưu Niệm)** | Thấp (~30$) | Siêu nhẹ (~225g) | 30.80% |
| **2** | **3. Cao Cấp & Cồng Kềnh (Đồ Lớn)** | Cao nhất (~167$)| Nặng nề (~6.2kg) | 18.34% |
| **3** | **0. Giá Trung & Khối Lượng Vừa** | Trung bình (~69$)| Vừa phải (~1.2kg) | 30.37% |

*Đánh giá:* Mô hình máy học phân chia hoàn toàn hợp lý với tư duy con người. Sự khác biệt về Giá+Khối lượng này chính là mỏ vàng để tiến hành bước Khai phá chéo (Cross-tabulation).

---

## PHẦN 3: LỚP 1.5 - KHAI PHÁ HÀNH VI VÀ INSIGHT DOANH NGHIỆP (CROSS-TABULATION)

Lớp "1.5" đóng vai trò chiếu sáng 4 Cụm Khách hàng vừa tìm được vào các Đa chiều không gian của Data Warehouse (như DIM_TIME, Kênh Bán Hàng) để tìm kiếm quy luật (Pattern). 

### Insight 1: Quy luật Mang vác & Kênh Phân Phối
**Góc chiếu:** So sánh Tỷ lệ mua Online (`Kênh Trực Tuyến` - Qua Bưu điện) và Offline (`Tại Cửa Hàng` - Khách Du lịch) giữa các Cụm.

**Kết quả thống kê:**
- Nhóm *Cụm 2 (Cao cấp & Cồng Khềnh 6.2kg)*: Hơn **60%** hóa đơn được thanh toán qua Kênh Trực Tuyến.
- Nhóm *Cụm 1 (Siêu nhẹ 225g)* và *Cụm 0 (Gọn Nhẹ 400g)*: Hơn **85%** hóa đơn được thanh toán trực tiếp tại Quầy.

**Diễn giải Insight Kinh doanh:**
Hành vi mua sắm bị chi phối tuyệt đối bởi **Yếu tố Vận chuyển (Logistics)**. Khách hàng rất thực dụng: Với những đồ có trọng lượng nặng (Máy giặt, Tủ lạnh), họ ưu tiên chọn Kênh Trực Tuyến (Online Commerce) để tận dụng dịch vụ giao hàng tận nhà của Bưu điện. Ngược lại, những đồ xách tay nhỏ gọn, họ sẵn sàng đến tận nơi lấy ngay (Cash & Carry).

### Insight 2: Bước chân Khách Du Lịch (Hành vi Cuối Tuần)
**Góc chiếu:** Tách số lượng đơn hàng của từng Cụm theo *Ngày Cuối Tuần (T7, CN)* và *Ngày Trong Tuần (T2-T6)*.

**Kết quả thống kê:**
- Về mặt lý thuyết tự nhiên, số lượng đơn của bộ 5 ngày Trong tuần phải gấp khoảng 2.5 lần so với bộ 2 ngày Cuối tuần. Điều này đúng với *Cụm 2 (Cồng Kềnh)* (23% Cuối tuần vs 77% Trong tuần).
- Tín hiệu Dị Biệt nằm ở *Cụm 1 (Đồ lưu niệm giá rẻ)*: Chỉ cần 2 ngày Cuối Tuần đã tạo ra **68%** số lượng hóa đơn, hoàn toàn đè bẹp cả 5 ngày Trong tuần cộng lại!

**Diễn giải Insight Kinh doanh:**
Cụm 1 chính là "Cục nam châm" thu hút các Đoàn Tour Du Lịch. Cuối tuần là thời điểm các khách thập phương đổ bộ vào chuỗi cửa hàng, chốt đơn hàng loạt các món đồ giá rẻ nhưng mang yếu tố lưu niệm. Điều này cho phép Bộ phận Vận hành tăng cường điều thêm Nhân sự thu ngân vào Thứ 7/CN và tung các Combo giá rẻ tại quầy thu tiền để kích sale.

### Insight 3: Mùa Lễ Hội "Gifting Season"
**Góc chiếu:** Bản đồ Nhiệt (Heatmap) quan sát sự dao động số lượng đơn của từng Cụm trải dài qua 4 Quý trong năm.

**Kết quả thống kê:**
- Cụm 1 (Đồ Rẻ), Cụm 3 (Tầm Trung) và Cụm 2 (Đồ Cồng Kềnh) bán đều và rải rác đan xen suốt các Quý 1, 2, 3. Q4 có sự sụt giảm nhẹ do hiệu ứng kết thúc năm.
- Tín hiệu Chấn Động lộ diện tại *Cụm 0 (Quà tặng Cao Cấp & Gọn Nhẹ)*: Doanh số Quý 4 **(4,529 đơn)** là một điểm đen rực rỡ trên Heatmap, làm lu mờ hoàn toàn Quý 1 và Quý 3 (quanh mức 1,600 đơn).

**Diễn giải Insight Kinh doanh:**
Khách hàng không mua một món hàng >140$ nhưng chưa nặng tới Nửa Ký (Trang sức, Nước hoa, Điện thoại xịn) một cách tùy hứng quanh năm. Họ chờ vào ngày Mùa Lễ Hội (Giáng Sinh - Black Friday - Quý 4) để mua chúng với mục đích làm QUÀ TẶNG. Doanh thu mảng này bung nổ và "Cân cống" toàn bộ doanh số cho các mảng khác đang chững lại dịp cuối năm.

---

## KẾT LUẬN & BƯỚC CHUYỂN TIẾP (TRANSITION TO CLASSIFICATION)

Hai Lớp khảo sát đầu tiên (Clustering & Cross-tabulation) đã thực hiện xuất sắc vai trò Khai Phá Dữ Liệu Mô Tả (Descriptive Data Mining), giúp vẽ lên bức tranh chân thực nhất đằng sau hàng vạn con số khô khan. 

Tuy nhiên, giới hạn của 2 Lớp này là mới chỉ dùng để làm "Báo cáo quá khứ". Để tiến vào kỷ nguyên AI/Hệ thống thông minh, Đồ án sẽ tiếp tục phát triển **LỚP THỨ 3: PHÂN LOẠI & DỰ ĐOÁN HÀNH VI BẰNG CÂY QUYẾT ĐỊNH (Decision Tree Classification)**.

Mô hình AI sắp tới sẽ học toàn bộ các Quy luật chéo ở Lớp 1.5. Kể cả khi 95% khách hàng của ta là Khách Mới Toanh (Không có lịch sử mua sắm), Cỗ máy AI chỉ cần nhìn vào Ngữ cảnh của họ như: *Đang là Cuối tuần hay Trong tuần? Mùa Hè hay Giáng Sinh? Trực tiếp hay Web?* là Cây Phân Loại sẽ tự động rẽ nhánh và dự đoán: **Khách hàng Mới này sẽ chốt đơn thuộc Phân cụm Sản phẩm số mấy!** (Cold-start Recommendation Engine).
