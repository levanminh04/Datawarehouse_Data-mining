# Hướng dẫn thuyết trình app — H&M Mining

Tài liệu kịch bản demo app trước cô. **Tổng thời lượng: 10–12 phút.** In ra cầm theo, hoặc mở tab kế bên trình duyệt.

---

## 0. Chuẩn bị trước khi bắt đầu (15 phút trước giờ thuyết trình)

```bash
cd Datawarehouse_Data-mining/data-mining/hm_mining_app
source .venv/bin/activate
uvicorn app.main:app --port 8000
```

- Mở **http://localhost:8000** ở browser → đảm bảo dashboard hiển thị số liệu (không phải skeleton trắng).
- Mở **http://localhost:8000/docs** ở tab thứ hai (dự phòng nếu cô hỏi schema).
- Mở **báo cáo Word** ở tab thứ ba — khi cô hỏi "khớp với chương nào?", anh chỉ ngay mục.
- Sẵn 1 terminal khác cho `curl` demo.
- Test trước: click 1 row trong tab Suy luận → chắc chắn 4 card render OK.

> ⚠️ Nếu mạng yếu, lần đầu load tab Tổng quan mất ~10s (`SELECT COUNT(*)` trên 32M giao dịch). Mở dashboard trước **15 phút** để load xong.

---

## 1. Mở đầu (1 phút)

**[SHOW]** Tab Tổng quan, dashboard đã load xong.

**[SAY]** "Em báo cáo phần Chương 5.3 — 'Đóng gói và vận hành hệ thống học liên tục'. Cô đã đọc 3 lớp khai phá ở chương 4 — cụm K-Means, luật Apriori, dự báo Random Forest. App này không phải notebook mới, mà là **hệ thống dịch vụ** chạy cả 3 lớp đó dưới dạng API + dashboard, đáp ứng 2 yêu cầu mở rộng cô đặt ra:"

- (chỉ vào card "Mô hình đang vận hành") **"Thu thập dữ liệu liên tục"** — endpoint `/ingest/*` nhận giao dịch mới qua HTTP.
- (chỉ vào nút Retrain) **"Học liên tục"** — `APScheduler` retrain cron + bảng `model_registry` versioning + flag `is_active=TRUE` để swap mô hình zero-downtime.

---

## 2. Tab Tổng quan — Quy mô thật (1.5 phút)

**[SHOW]** 4 stat cards.

**[SAY]** "App đang nối với DB Postgres của nhóm chứa **toàn bộ H&M dataset** mà bạn levanminh04 đã load:"

- 1,371,980 khách hàng
- 31,788,324 giao dịch
- 1,362,281 đã được Layer 1 phân cụm

"Đây là số thật, không phải mẫu — cô có thể thấy ngày giao dịch cuối là **2020-09-22**, đúng cutoff date trong báo cáo mục 4.3.1."

**[SHOW]** Biểu đồ phân bố cụm.

**[SAY]** "Phân bố 5 cụm phong cách — khớp với Bảng 4.1 báo cáo:"

- Classic Ladieswear ~65% (báo cáo: 60.6%)
- GenZ Trend ~23% (báo cáo: 25.7%)
- 3 cụm còn lại nhỏ hơn

"Sai khác nhẹ vì app train trên snapshot DB hiện tại 1.36M khách, lớn hơn snapshot bạn levanminh04 dùng cho báo cáo (1.09M). Methodology y hệt — chi tiết em ghi trong file [`EQUIVALENCE_CHECK.md`](EQUIVALENCE_CHECK.md)."

---

## 3. Tab Mô hình — 3 lớp đang chạy (2 phút)

**[CLICK]** Tab "Mô hình".

**[SHOW]** Chart "Feature importance Layer 3".

**[SAY]** "3 biến RFM thống trị: recency, frequency, monetary, mỗi cái 20–30%. Đây chính là kết quả em show ở Bảng 4.4 báo cáo. Còn 7 đặc trưng Fashion DNA cộng lại chỉ ~10% — chứng minh hành vi mua RFM là tín hiệu mạnh hơn phong cách."

**[SHOW]** Chart "Số luật Apriori theo cụm" (doughnut).

**[SAY]** "90 luật kết hợp tổng cộng, phân bố không đều: Family/Moms 45 luật cao nhất — đúng tinh thần Chương 4.2.2 'cụm sắc nét nhất' vì hành vi mua đồ trẻ em rất rõ ràng. Sporty Active chỉ 3 luật vì cụm này nhỏ và phân tán."

**[SHOW]** Bảng "Lịch sử các phiên bản". Đổi dropdown sang L3.

**[SAY]** "Mỗi lần retrain ghi 1 dòng vào bảng `model_registry`. Dòng có nhãn ACTIVE là version đang phục vụ predict. Đây là **bằng chứng kỹ thuật** cho 'học liên tục': lịch sử mô hình lưu lại, không bị overwrite, có thể rollback."

---

## 4. Tab Suy luận — Demo predict trực tiếp (3 phút)

**[CLICK]** Tab "Suy luận".

**[SHOW]** Browser khách hàng, 5 tab cụm.

**[SAY]** "Em pick 1 khách Family/Moms thật để demo. Cụm này nhỏ — chỉ ~53k khách trong 1.36M tổng — nhưng có luật Apriori sắc nhất."

**[CLICK]** Tab cụm "Family/Moms" → click row đầu tiên có age 35–45, club ACTIVE, n_transactions cao.

**[SAY]** Đợi 1–2 giây cho 4 card hiện ra, đọc theo:

- **Hồ sơ:** "Khách 38 tuổi, ACTIVE member, đã mua X giao dịch, top sản phẩm là Garment Lower body và Children Accessories — đúng profile mẹ đi mua đồ cho con."
- **Cụm:** "App phân chính xác vào Family/Moms."
- **Recommendations:** "Apriori đề xuất Shoes — đây chính là luật `Accessories + Garment Full body → Shoes` cô thấy ở Bảng 4.2 báo cáo, lift 1.75."
- **Will-buy 7 ngày:** "Random Forest dự xác suất X%. Nếu cao, marketing target khách này; nếu thấp, bỏ qua để tiết kiệm chi phí."

**[CLICK]** Tab cụm "Menswear" → click 1 row khác.

**[SAY]** "So sánh: cụm Menswear thì recommendations xoay quanh underwear + socks — đúng luật `Socks & Tights → Underwear` trong báo cáo. Đây là **Segment-then-Mine**: luật riêng từng cụm, không dùng luật chung chung."

> Nếu cô hỏi "tại sao recommendations rỗng cho 1 khách?" → đáp: "Khách đó mua quá ít sản phẩm gần đây nên basket không match luật nào — fallback an toàn."

---

## 5. Tab Nạp dữ liệu — Demo "thu thập liên tục" (2 phút)

**[CLICK]** Tab "Nạp dữ liệu".

**[SAY]** "Đây là endpoint cho phép gửi giao dịch mới qua HTTP, đáp ứng yêu cầu 'thu thập liên tục'."

**[CLICK]** Click nút "Mẫu" để reset JSON về template chuẩn.

**[CLICK]** Click "POST /ingest/transactions".

> Nếu báo lỗi 400 ("customer_id chưa tồn tại") — bình thường, vì `demo_001` là ID giả. Đổi sang form "Tạo / cập nhật khách hàng" trên cùng, paste `demo_001`, age 28, status ACTIVE → POST → quay lại form transactions → POST lại.

**[SAY]** "Sau POST, giao dịch đã vào bảng `transactions` ngay lập tức. Lần retrain kế tiếp — dù là cron tự động lúc 02:00 UTC hay click tay — sẽ thấy giao dịch này và học từ nó. Đó là 'thu thập liên tục'."

**[SHOW]** Quay lại tab Tổng quan → số giao dịch đã +1.

---

## 6. Demo Retrain — Closing the loop (1 phút)

**[CLICK]** Trở lại tab Tổng quan → click nút "⟳ Retrain toàn bộ".

**[SAY]** "Click → response trả về `scheduled, [L1, L2, L3]`. Train chạy **background** trong process `uvicorn`, không block dashboard.

Khi L1 xong, 1 dòng mới vào `model_registry` với cột `is_active=TRUE`, dòng cũ tự xuống `FALSE`. Tất cả endpoint `/predict/*` đang phục vụ traffic vẫn dùng version cũ cho đến khi L1 commit, rồi chuyển sang version mới — **zero-downtime swap**."

**[SAY]** "Trên production, `APScheduler` retrain định kỳ Chủ Nhật 02:00 cho L1+L2 (vì Apriori cần cluster mới của L1 trước), hằng ngày 01:00 cho L3. Cô có thể tự xếp lịch khác qua biến `RETRAIN_*_CRON` trong `.env`."

> Không đợi train xong (mất 25–30 phút). Chỉ show trigger.

---

## 7. Tổng kết (1 phút)

**[SAY]** "Tóm lại:

- **Yêu cầu 1 — Thu thập liên tục:** đã có `POST /ingest/customer` và `/ingest/transactions`, demo thực ngay tại tab Nạp dữ liệu.
- **Yêu cầu 2 — Học liên tục:** đã có `model_registry` versioning, scheduler cron, zero-downtime swap, demo qua nút Retrain.
- **Khớp báo cáo Chương 4:** AUC 0.82, Recall 0.76 (báo cáo nói 0.75 là chiến thắng), 5 cụm sociology, top-3 RFM dominate, luật Apriori tái lập được Bảng 4.2.

Phần code do em phụ trách độc lập, không reuse notebook của bạn levanminh04 vì notebook là scope global ad-hoc, không thể `import`. App là re-implementation theo cùng spec Chương 4. Em đã verify equivalence và document trong file `EQUIVALENCE_CHECK.md`."

---

## 8. Q&A — anticipated questions

| Cô có thể hỏi | Câu trả lời |
|---|---|
| Sao kết quả app khác báo cáo nhẹ? | Snapshot DB của app lớn hơn (1.36M vs 1.09M lúc viết báo cáo) + K-Means random init khác → cluster sizes lệch ±5pp, nhưng cấu trúc 5 cụm + AUC/Recall/feature importance đều khớp. |
| Sao không reuse code notebook? | Notebook = scope global, viết theo cell, save CSV/PNG → không có function clean để `import`. App cần train/predict/save/load là module rạch ròi. Em verify hyperparam y hệt notebook (xem EQUIVALENCE_CHECK.md). |
| App scale được không nếu DB to gấp 10? | Có. Mọi JOIN/AGG đẩy xuống PostgreSQL bằng SQL (mục 3.3 báo cáo, chống OOM). Layer 1 K-Means train trên sample 100k, infer trên toàn bộ batch. Layer 3 sample 300k. |
| Vì sao Recall chỉ 0.76? | Dataset imbalanced — chỉ 5% khách thực sự mua trong 7 ngày. Báo cáo mục 4.3.2 đã giải thích: ưu tiên Recall > Precision vì gửi email thừa rẻ hơn rất nhiều so với bỏ sót khách hàng mua. |
| Continuous learning thật sự chạy chưa? | Có. Cron schedule live (xem `app/scheduler.py`), 3 cron job đã đăng ký trong scheduler ngay khi `uvicorn` start. Chỉ cần để app chạy, đến giờ là tự retrain. Em vừa demo trigger tay; cron chỉ là cùng function đó nhưng auto. |
| Nếu DB drop kết nối giữa retrain? | Train fail thì commit cuối không xảy ra → version mới không vào registry → app vẫn dùng version cũ. Không corrupt. Em verify scenario này khi viết — `init_db.py` cũng dùng autocommit để bảo toàn progress. |
| Có unit test không? | Manual smoke test end-to-end. Chưa có pytest formal — đó là hạn chế em sẽ note ở phần "hướng phát triển". |
| `prediction_log` có dùng không? | Có. Mọi response `/predict/*` ghi 1 dòng vào đó. Sau N ngày join với `transactions` thực để đo accuracy drift, trigger retrain ngoài lịch nếu giảm — chưa implement, là next step. |
| Tại sao L2 dùng confidence ranking, không dùng lift như notebook? | Confidence = "nếu khách mua A thì xác suất % mua B" — diễn giải trực tiếp được cho marketing. Lift = "A và B đi cùng hơn ngẫu nhiên bao nhiêu lần" — chỉ số thống kê. Cùng dataset, 2 ranking đều hợp lý. |

---

## 9. Hạn chế (chủ động nói trước khi cô hỏi)

- Frontend tối giản — Tailwind CDN + Alpine.js, đủ demo nhưng không phải production UI.
- Không có authentication — endpoint `/ingest` mở public; production cần API key + rate limit.
- Drift detection (PSI / KS test) chưa implement — hiện chỉ retrain định kỳ, chưa retrain "có điều kiện" khi accuracy giảm.
- Postgres là single-instance — production cần read replica để retrain không block predict.
- Test suite chưa có — chỉ smoke test bằng tay.

> Note 4 hạn chế trên trùng với phần 5.4 báo cáo "Hạn chế và hướng phát triển", show consistency.

---

## 10. Nếu app down giữa demo

- `curl http://localhost:8000/health` → nếu không phản hồi, terminal khác chạy lại `uvicorn`.
- Nếu DB remote AWS rớt, fall back: `curl http://localhost:8000/docs` chỉ Swagger UI ra → giải thích spec, không demo predict được.
- Last resort: chuyển sang screenshot. Mở trước 1 vài screenshot dashboard sẵn ở `~/Desktop/demo-screens/`.

---

**Lời chốt:** "App này demo được vận hành thật trên dataset H&M 32M giao dịch, kết quả khớp báo cáo Chương 4 và đáp ứng đầy đủ 2 yêu cầu mở rộng Chương 5.3. Em xin nhận câu hỏi của cô."
