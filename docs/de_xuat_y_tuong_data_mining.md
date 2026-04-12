# ĐỀ XUẤT Ý TƯỞNG DATA MINING ĐẠT ĐIỂM CAO TRONG TIÊU CHÍ "TƯ DUY & Ý TƯỞNG"

Với tiêu chí của giảng viên là **"đánh giá dựa trên tư duy, ý tưởng, không trọng code và độ chính xác"**, cách tốt nhất để đạt điểm tối đa là **KHÔNG làm công cụ rời rạc**, mà hãy **xâu chuỗi các phương pháp Data Mining thành một giải pháp kinh doanh tổng thể (Business Solution)**. 

Thay vì nói: *"Nhóm em dùng K-Means để phân cụm và Apriori để tìm luật kết hợp"*.
Hãy nói: *"Nhóm em xây dựng quy trình phân loại khách hàng tự động để tối ưu hóa chiến dịch Marketing bán chéo (Cross-selling) cho doanh nghiệp đa kênh."*

Dưới đây là một ý tưởng hoàn chỉnh "ăn điểm" tuyệt đối về mặt tư duy phân tích:

---

## 🎯 TÊN ĐỀ TÀI (GỢI Ý)
**"Hướng tiếp cận tích hợp Data Mining trong Bán lẻ: Từ Phân khúc Khách hàng đa kênh đến Tối ưu hóa Chiến lược Bán chéo (Cross-selling)"**

---

## 💡 CÚ TWIST TƯ DUY (ĐIỂM NHẤN CỦA BÀI LÀM)
Giảng viên rất hay bắt bẻ điểm yếu của dữ liệu (như đa số giỏ hàng chỉ có 1 sản phẩm). Ý tưởng này của bạn sẽ lật ngược thế cờ: 
*   **Vấn đề:** Khách toàn mua 1 sản phẩm/đơn thì làm sao áp dụng Luật Kết Hợp (Association Rules)? 
*   **Giải pháp Tư duy:** Thay vì xem mỗi "Đơn hàng" là 1 giỏ hàng, ta định nghĩa lại **Giỏ hàng = Toàn bộ lịch sử mua sắm của 1 khách hàng trong suốt vòng đời của họ.** 
*   **Chiến lược:** Ta không đi tìm luật kết hợp trên tất cả mọi người (sẽ bị nhiễu). Ta sẽ **Phân cụm** để tìm ra tập Khách hàng VIP trước, sau đó mới dùng **Luật kết hợp** trên tập VIP này để xem "Đỉnh cao của việc tiêu tiền là người ta thường mua những món gì". Cuối cùng, lấy luật đó đem đi quảng cáo cho người chưa phải VIP.

---

## ⚙️ CHI TIẾT KỊCH BẢN THỰC HIỆN (3 BƯỚC)

### BƯỚC 1: NHẬN DIỆN "AI LÀ AI" — Phân cụm Khách hàng (Clustering - K-Means)
Dựa vào data hiện có (`FACT_ORDER`, `DIM_CUSTOMER`), bạn tính toán mô hình **RFM** (Recency - Ngày mua gần nhất, Frequency - Tần suất, Monetary - Tổng tiền).
- **Thuật toán:** K-Means.
- **Tư duy kinh doanh:** Không phân cụm bừa bãi. Phân ra 3-4 nhóm có ý nghĩa kinh doanh.
  - *Nhóm 1 (Khách VIP - Champions):* Mua nhiều, mua thường xuyên, chi nhiều tiền.
  - *Nhóm 2 (Khách ngủ quên - Sleeping):* Từng mua nhiều nhưng đã lâu không quay lại.
  - *Nhóm 3 (Khách săn sale một lần):* Chi mua 1 lần/1 đơn duy nhất rồi biến mất (rất đông ở data này).

### BƯỚC 2: KHAI PHÁ HÀNH VI CỦA "NGƯỜI GIÀU" — Tìm luật kết hợp có chọn lọc (Association Rules)
Giảng viên sẽ hỏi: *"Tìm luật kết hợp làm gì?"*
- **Tư duy kinh doanh:** Thay vì bỏ Apriori chạy trên toàn bộ data một cách mù quáng, bạn **chỉ lọc ra danh sách Khách hàng VIP (Nhóm 1 ở Bước 1)**.
- **Tiến hành:** Nhìn vào lịch sử mua sắm của nhóm VIP này. Do các mã sản phẩm (MaMH) quá nhiều và rời rạc, bạn **nhóm sản phẩm theo Kích cỡ / Mức giá (NhomGia)**. 
- **Kết quả kỳ vọng ra quy luật:** *"Khách VIP thường có hành trình mua Hàng mức giá Trung bình -> Nâng cấp lên mua Hàng mức giá Cao"*, hoặc *"Khách mua nhóm sản phẩm A ở cửa hàng vật lý thường sẽ quay lại mua nhóm sản phẩm B trên kênh Online"*.

### BƯỚC 3: PHÁT BIỂU HÀNH ĐỘNG KINH DOANH (The Actionable Insight)
Data Mining không phải chỉ để khoe thuật toán, mà phải chốt hạ bằng hành động. Bạn kết luận bài tập bằng chiến dịch đề xuất:
- **Chiến dịch "Đánh thức khách ngủ quên":** Lấy danh sách Khách nhóm 2 (Sleeping), gửi email mã tựu trường/mã giảm giá vào đúng những sản phẩm mà nhóm VIP (Nhóm 1) hay mua (dựa vào luật kết hợp đã đào ở bước 2).
- **Phát hiện gian lận/Thiếu hàng (Bonus nếu làm Anomaly Detection):** Dùng dữ liệu tồn kho `FACT_INVENTORY`, tìm ra những cửa hàng/ngày mà lượng tồn kho biến động quá nhanh bất thường để báo cho quản lý.

---

## 🏆 TẠI SAO Ý TƯỞNG NÀY SẼ LẤY ĐIỂM TUYỆT ĐỐI VỀ TƯ DUY?

1. **Gắn liền với thực tiễn (Practical):** Đây chính là thứ mà các công ty như Shopee, Lazada hay các chuỗi siêu thị thực sự làm (Customer Segmentation kết hợp Recommendation System).
2. **Che đậy tinh tế khuyết điểm của sinh viên:** Thay vì lo lắng model chạy ra độ chính xác (accuracy) thấp hay luật kết hợp vô nghĩa vì data "xào nấu", bạn chuyển sự chú ý của thầy cô vào kịch bản phân loại. Clustering là unsupervised (không có chuẩn đúng/sai), nên bạn báo cáo cụm kiểu gì hợp logic là được!
3. **Có sự liên kết giữa các thuật toán:** Điểm cộng lớn nhất là bạn dùng Output của thuật toán 1 (Danh sách VIP) làm Input cho Data của thuật toán 2 (Khai phá luật kết hợp). Hầu hết sinh viên sẽ chạy 2 thuật toán trên 2 bài toán chả liên quan gì nhau.

---

## 📝 CÁCH TRÌNH BÀY VÀO SLIDE / BÁO CÁO NHÓM
1. Mở đầu bằng sự kiện: *"Doanh nghiệp X có chi phí marketing cao nhưng tỷ lệ chuyển đổi thấp => Cần Target đúng khách, mời đúng hàng."*
2. Trình bày Data Warehouse: Vẽ cái Star Schema ra và nói *"Nhờ có Data Warehouse thiết kế chuẩn (có Dimension Cửa hàng, Khách hàng, Thời gian) mới hỗ trợ truy xuất nhanh để làm Mining."*
3. Trình bày Bước 1, Bước 2 với vài cái biểu đồ (scatter plot của K-means, biểu đồ dạng mạng lưới của luật kết hợp). Biểu đồ dù ảo cũng nên làm màu mè một chút.
4. Chốt lại bằng "Đề xuất kinh doanh".

> *Chúc nhóm bạn lấy điểm cao. Với hướng tiếp cận "hướng tới bài toán kinh doanh sâu sắc" này, chắc chắn giảng viên sẽ đánh giá rất cao sự trưởng thành trong tư duy của nhóm!*
