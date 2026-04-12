# KẾ HOẠCH LỚP 1.5: PHÂN TÍCH CHÉO (CROSS-TABULATION)

Chào mừng bạn đến với bước chứng minh tư duy Kinh doanh. Ở Lớp 1 (K-Means), chúng ta đã dùng máy học (Machine learning) để ép dữ liệu ra được 4 **Cụm Sản Phẩm (Clusters)**.
Ở Lớp 1.5, ta sẽ **KHÔNG dùng thêm thuật toán máy học nào nữa**. Thay vào đó, ta mang 4 Cụm vừa tìm được đem đi cắt chéo (Cross-Tabulation) với các chiều dữ liệu (Dimensions) như Thời Gian, Địa Lý, Kênh Bán Hàng.

Cách làm này sẽ lấy trọn vẹn điểm "Tư Duy", vì nó chứng minh Nhóm bạn hiểu rất rõ bản chất của một kho Dữ liệu (Data Warehouse) mô hình Star Schema!

---

## BƯỚC 1: TIỀN XỬ LÝ (BẮT CẦU TỪ LỚP 1 SANG LỚP 1.5)

Chúng ta load lại file `orders_with_clusters.csv` mà thuật toán K-means vừa nhả ra, lúc này mỗi dòng dữ liệu đã được đính kèm Cột `CLUSTER`. Tiếp theo, ta gán Nhãn kinh doanh cho các số 0, 1, 2, 3 bằng các tên gọi đã đặt:

- **0:** Hàng Tầm Trung - Tiêu dùng thiết yếu (Gia dụng nhỏ, Thời trang)
- **1:** Hàng Giá Rẻ - Gọn Nhẹ (Phụ kiện, Văn phòng phẩm)
- **2:** Hàng Cao Cấp - Gọn Nhẹ (Điện tử, Mỹ phẩm đắt tiền)
- **3:** Hàng Cồng Kềnh - Giá trị lớn (Nội thất, Điện máy lớn)

Đoạn code trong Notebook sẽ thực hiện hàm `.map(label_map)` để biến con số vô tri thành Tên gọi cực kêu này.

---

## BƯỚC 2: CÁC KỊCH BẢN PHÂN TÍCH CHÉO (VẼ BẢN ĐỒ NHIỆT / HEATMAP)

Khái niệm **Cross-tabulation (Tính bảng chéo)** rất dễ hiểu. Giả sử tôi có Cột (Các Cụm Sản Phẩm) và Dòng (Các Quý 1, 2, 3, 4). Ở Ô giao nhau giữa Cụm 1 và Quý 4, tôi điền tổng số lượng Đơn hàng bán được. Nếu số càng lớn, tôi tô màu bản đồ rực đỏ (Heatmap) và ngược lại.

### Góc nhìn 1: Dimension Thời Gian (Các cụm hàng bán chạy vào mùa nào?)

> **Bài Toán:** Có phải hàng Cao cấp hay Cồng kềnh (Mua làm quà, sửa nhà sắm Tết) thì sẽ biến động bắn vọt lên ở Quý 2 hay Quý 4 không? Còn hàng Giá Rẻ (Ốp lưng, bút bi) thì bán cực đều cả 4 quý?
> **Thực thi:** Cross-tab *Cụm Hàng* vs *Quý (QUY)*
> **Biểu đồ hiển thị:** Heatmap màu đỏ tía rực rỡ báo hiệu tỷ trọng doanh thu.

### Góc nhìn 2: Dimension Thời Gian (Hành vi cuối tuần vs Đầu tuần)

> **Bài Toán:** Người ta thường mua hàng Hàng Tầm Trung (Áo quần, Gia dụng nhẹ) vào đầu tuần, nhưng các món đồ đắt tiền (Cụm 2, Cụm 3) cần cân nhắc kỹ thì khách lại thích mua vào Thứ 7, Chủ Nhật đúng không?
> **Thực thi:** Tôi sẽ gom nhóm "Saturday, Sunday" thành `Cuối Tuần`, các ngày còn lại là `Trong Tuần`. Cross-tab *Cụm Hàng* vs *Cuối Tuần/Trong Tuần*.
> **Biểu đồ hiển thị:** Heatmap tỷ lệ phần trăm (%).

### Góc nhìn 3: Dimension Kênh Phân Phối (Tại cửa hàng vs Trực tuyến)

> **Bài Toán:** Với mặt hàng giá trị lớn hoặc cồng kềnh (Cụm 3), tâm lý khách hàng là muốn ra tận nơi đo đạc sờ nắn (Tai Cua Hang). Trong khi đồ Rẻ Tiền, Tiêu Dùng (Cụm 1, 0) thì khách cứ đặt luôn qua App (Truc Tuyen) cho lẹ?
> **Thực thi:** Dùng Barchart (Biểu đồ cột) hiển thị chênh lệch Trực Tuyến/Tại cửa hàng của 4 Cụm. Nếu Cụm 3 cột "Tại cửa hàng" cao vọt $\rightarrow$ Phân tích hoàn hảo!

### Góc nhìn 4: Dimension Địa Lý (Tỉnh Bang nào là đại gia?)

> **Bài Toán:** Trong file `plan_tong_quat.md`, ta thấy riêng Bang SP (Sao Paulo) đã chiếm tới 54% tổng đơn. Vậy có phải Bang này "Gánh team" tiêu thụ hết đống Hàng Cao Cấp (Cụm 2) không?
> **Thực thi:** Lấy TOP 3 bang (SP, RJ, MG) đại diện cho 75% doanh thu, đem đi Cross-Tab với 4 Cụm hàng.
> **Biểu đồ hiển thị:** Heatmap Tỷ lệ.

---

## BƯỚC 3: CÂU CHUYỆN BÁO CÁO KINH DOANH CHỐT HẠ (KDD - Knowledge Discovery)

Data Mining không phải chỉ là tìm ra sự thật hiển nhiên. Bạn dựa vào các biểu đồ Heatmap ở trên và ghi chốt hạ vào mặt Slide báo cáo những đề xuất như sau để Giảng viên phải thốt lên "Xuất sắc":

1. **Về Khía cạnh Vận hành & Kho bãi (Operations):**
   - Hàng Phân khúc Rẻ & Tầm Trung (Cụm 1, 0) không có khái niệm "Mùa". Chúng bán quanh năm và đóng góp "Mỡ máu" (Dòng tiền) cho công ty. Do đó phải Đảm bảo tồn kho (Fact_Inventory) liên tục, kho luôn đầy.
   - Hàng Cồng Kềnh Cụm 3 chỉ thực sự "Nhảy số" (Đột biến Heatmap) vào khung giờ xê xích nhất định (Qúy/Tháng). Ta khuyên sếp không nên để tồn kho Cụm 3 suốt cả năm tốn tiền lưu kho, chỉ dồn kho lớn gần các cửa hàng trước Quý Mùa Vụ.

2. **Về Khía cạnh Kênh Phân Phối (Marketing Strategy):**
   - Sự khác biệt về Kênh Trực Tuyến và Tại Cửa Hàng giữa các Cụm yêu cầu đổi chiến lược. Tiền hoa hồng / Chạy quảng cáo Online thì dập mạnh cho 2 Cụm Hàng Rẻ và Tầm Trung. 
   - Đồ cồng kềnh (Cụm 3) thì phải đổi kịch bản: Chạy quảng cáo là "Hãy tới Showroom thử sờ nắn ngay", chứ cấm chạy là "Hãy điền form mua liền" vì khách sẽ không mua qua điện thoại đâu.

**(Bạn hãy vào thư mục `data-mining/Lop1.5_PhanTichCheo.ipynb` để chạy code và lấy biểu đồ đẹp nhé!)**
