# 📗 SIDE DOC 2: KẾ HOẠCH GIAI ĐOẠN 2 – SEMINAR 2 (28/10 – 05/11/2026)

> **Chủ đề Seminar 2 (05/11/2026):** *Xây dựng ứng dụng BI trên Kho dữ liệu (`dds`), Nộp Báo cáo phân tích & Source, Video Demo & Trình bày sản phẩm*
> **Thời gian thực hiện:** **28/10/2026 – 05/11/2026 (9 ngày)**
> **Phạm vi yêu cầu đề bài giải quyết trong Giai đoạn 2:** Mục **3.4.A (Semantic Model)**, **3.4.B (Dashboard 1 Overview & Dashboard 2 Diagnostic)**, **Mục 4 (Báo cáo phân tích, Source code, File `.pbix`, Video demo)**.

---

## 1. MỤC TIÊU CỐT LÕI CỦA GIAI ĐOẠN 2

Sau khi đã có Kho dữ liệu chuẩn (`dds.fact_bookings` và 5 bảng `dds.dim_*`) từ Seminar 1, ở Giai đoạn 2 nhóm tập trung biến dữ liệu thành **Insight quản trị cho Ban Giám đốc Khách sạn**:
1. **Xây dựng Semantic Model chuẩn trên Power BI Desktop:** Kết nối trực tiếp vào PostgreSQL schema `dds`, thiết lập quan hệ Hình sao (1-nhiều), tạo các phân cấp (Hierarchies) và bộ **12+ DAX Measures**.
2. **Xây dựng 02 trang Dashboard chuyên sâu:**
   - **Dashboard 1 – Executive Overview (Descriptive Analytics):** Toàn cảnh doanh thu, lượng đặt phòng, tỷ lệ hủy phòng, công suất đêm phòng theo thời gian, địa lý (quốc tịch khách), loại khách sạn và kênh bán.
   - **Dashboard 2 – Cancellation & Revenue Loss Diagnostic (Diagnostic Analytics):** Đi sâu (Drill-through / Drill-down) mổ xẻ **nguyên nhân tại sao tỷ lệ hủy phòng lên tới 37%** và gây mất hàng triệu USD doanh thu (chứng minh bằng số liệu định lượng: mối liên hệ giữa *Online TA*, *No Deposit*, *Lead Time dài*, và *Thay đổi loại phòng*).
3. **Hoàn thiện Báo cáo phân tích & Quay Video Demo sản phẩm BI.**

---

## 2. PHÂN CÔNG THEO HẠNG MỤC CÔNG VIỆC (SEMINAR 2)

### HẠNG MỤC 2.1: Xây dựng Power BI Semantic Model, Hierarchies & Bộ DAX Measures
- **Người phụ trách chính:** **Đào Trung Kiên** *(Nhóm trưởng)*
- **Thời gian hoàn thành:** Ngày 28/10 – 30/10/2026
- **Nhiệm vụ Kỹ thuật (Code DAX & Data Modeling):**
  1. Kết nối Power BI Desktop vào PostgreSQL (`localhost:5432`, database `dw_lab`, schema `dds`), import 6 bảng (`fact_bookings`, `dim_date`, `dim_hotel`, `dim_customer`, `dim_channel`, `dim_room_policy`).
  2. Thiết lập **Model View (Relationships):**
     - Nối 1-nhiều (`1:*`), chiều lọc đơn (`Single`) từ 5 bảng `dim_*` vào `fact_bookings`.
     - Đánh dấu `dim_date` là **Date Table** chuẩn để dùng các hàm Time Intelligence.
  3. Tạo **03 Hierarchies** phục vụ phân tích đa chiều (Drill-down):
     - `Date Hierarchy`: `year` $\rightarrow$ `quarter` $\rightarrow$ `month_name` $\rightarrow$ `full_date`.
     - `Channel Hierarchy`: `distribution_channel` $\rightarrow$ `market_segment` $\rightarrow$ `agent_code`.
     - `Room & Policy Hierarchy`: `deposit_type` $\rightarrow$ `meal_code` $\rightarrow$ `reserved_room_type`.
  4. Tạo bảng `_Measures` chứa **12 DAX Measures cốt lõi**:
     - `Total Bookings = COUNTROWS(fact_bookings)`
     - `Canceled Bookings = CALCULATE([Total Bookings], fact_bookings[is_canceled] = 1)`
     - `Completed Bookings = CALCULATE([Total Bookings], fact_bookings[is_canceled] = 0)`
     - `Cancellation Rate % = DIVIDE([Canceled Bookings], [Total Bookings], 0)`
     - `Total Room Nights = SUM(fact_bookings[total_nights])`
     - `ADR (Average Daily Rate) = AVERAGE(fact_bookings[adr])`
     - `Actual Revenue = SUM(fact_bookings[actual_revenue])` *(Doanh thu thực thu từ các đơn không hủy)*
     - `Revenue Loss (Canceled) = SUM(fact_bookings[revenue_loss])` *(Doanh thu bị bốc hơi do khách hủy)*
     - `Gross Potential Revenue = [Actual Revenue] + [Revenue Loss (Canceled)]`
     - `Revenue YoY Growth %` (Tăng trưởng doanh thu cùng kỳ năm trước bằng `SAMEPERIODLASTYEAR`)
     - `Avg Lead Time (Days) = AVERAGE(fact_bookings[lead_time])`
     - `Room Upgrade Rate % = DIVIDE(CALCULATE([Total Bookings], dim_room_policy[is_room_upgraded] = TRUE()), [Total Bookings], 0)`
- **Nhiệm vụ Tài liệu (Document):**
  - Viết **Mục 3.4.A (Thiết kế Semantic Model, Relationships, Hierarchies và Giải thích công thức DAX)** trong Báo cáo phân tích.

---

### HẠNG MỤC 2.2: Thiết kế Dashboard 1 – Overview (Descriptive Analytics)
- **Người phụ trách chính:** **Phạm Ngọc Thanh**
- **Thời gian hoàn thành:** Ngày 30/10 – 02/11/2026
- **Nhiệm vụ Kỹ thuật (Power BI Visuals):**
  1. Thiết kế bố cục (Layout) chuyên nghiệp theo chuẩn UI/UX hiện đại:
     - **Hàng trên cùng (5 KPI Cards):** `Total Bookings`, `Actual Revenue ($)`, `Revenue Loss ($)`, `Cancellation Rate %` (tô màu cảnh báo đỏ nếu > 35%), `ADR ($)`.
     - **Cột bên trái / Thanh trên (Slicers lọc đa chiều):** Năm (`2015, 2016, 2017`), Loại khách sạn (`City Hotel`, `Resort Hotel`), Phân khúc thị trường (`market_segment`).
     - **Biểu đồ 1 (Line and Clustered Column Chart):** Xu hướng Doanh thu thực tế (`Actual Revenue`), Doanh thu mất do hủy (`Revenue Loss`) và đường `Cancellation Rate %` theo từng tháng/quý (Hỗ trợ Drill-down theo `Date Hierarchy`).
     - **Biểu đồ 2 (Clustered Bar Chart):** So sánh hiệu quả kinh doanh theo Kênh phân phối (`market_segment` – thấy ngay *Online TA* chiếm lượng đặt lớn nhất nhưng cũng hủy nhiều nhất).
     - **Biểu đồ 3 (Filled Map / Shape Map):** Phân bố lượng khách và doanh thu theo Quốc tịch (`country_code`: PRT, GBR, FRA, ESP, DEU...).
     - **Biểu đồ 4 (Donut / Matrix Chart):** Cơ cấu khách hàng (`customer_type`) và tỷ lệ khách quay lại (`is_repeated_guest`).
- **Nhiệm vụ Tài liệu (Document):**
  - Viết **Mục 3.4.B.1 (Phân tích Mô tả - Descriptive Analytics trên Dashboard 1: Nhận diện các xu hướng mùa vụ và biến động bất thường)** kèm số liệu trích xuất từ biểu đồ.

---

### HẠNG MỤC 2.3: Thiết kế Dashboard 2 – Detailed / Diagnostic Analytics (Phân tích Nguyên nhân)
- **Người phụ trách chính:** **Huỳnh Võ Đại Dương**
- **Thời gian hoàn thành:** Ngày 30/10 – 02/11/2026
- **Nhiệm vụ Kỹ thuật (Power BI Diagnostic Visuals):**
  1. Thiết lập tính năng **Drill-through** từ Dashboard 1 sang Dashboard 2 (Người dùng click chuột phải vào một Tháng hoặc một Kênh bán trên Dashboard 1 $\rightarrow$ chọn *"Drill through to Cancellation Diagnostic"* để nhảy sang Dashboard 2 xem nguyên nhân gốc rễ).
  2. Xây dựng 4 biểu đồ chẩn đoán định lượng:
     - **Biểu đồ 1 (Decomposition Tree - Cây phân rã):** Phân rã chỉ số `Canceled Bookings` hoặc `Revenue Loss` theo chuỗi nguyên nhân: `Hotel Name` $\rightarrow$ `Market Segment` $\rightarrow$ `Deposit Type` $\rightarrow$ `Lead Time Group` $\rightarrow$ `Customer Type`.
     - **Biểu đồ 2 (Column/Line Chart theo nhóm Lead Time):** Chia `lead_time` thành các bậc (`0-7 ngày`, `8-30 ngày`, `31-90 ngày`, `91-180 ngày`, `>180 ngày`) để chứng minh định lượng: *Đặt trước dưới 7 ngày tỷ lệ hủy chỉ ~10%, nhưng đặt trước >180 ngày tỷ lệ hủy vọt lên >60%!*
     - **Biểu đồ 3 (100% Stacked Bar Chart – Tác động của Yêu cầu đặc biệt & Nâng hạng phòng):** Chứng minh khách có `total_of_special_requests >= 2` hoặc được giữ đúng loại phòng (`is_room_upgraded`) có tỷ lệ hủy thấp hơn hẳn khách không có yêu cầu đặc biệt.
     - **Biểu đồ 4 (Detailed Evidence Matrix):** Bảng bằng chứng định lượng tổng hợp các yếu tố đóng góp vào tổn thất doanh thu và khuyến nghị hành động (ví dụ: áp dụng đặt cọc một phần cho các đơn *Online TA* có *Lead Time > 90 ngày*).
- **Nhiệm vụ Tài liệu (Document):**
  - Viết **Mục 3.4.B.2 (Phân tích Chẩn đoán - Diagnostic Analytics trên Dashboard 2: Bằng chứng định lượng giải thích nguyên nhân hủy phòng và sụt giảm doanh thu)**.

---

### HẠNG MỤC 2.4: Biên tập Báo cáo Phân tích Tổng hợp & Dựng Video Demo Seminar 2
- **Người phụ trách chính:** **Thạch Ý**
- **Thời gian hoàn thành:** Ngày 01/11 – 04/11/2026
- **Nhiệm vụ Kỹ thuật & Sản phẩm:**
  1. Kiểm thử chéo (QA) toàn bộ con số trên Power BI đối chiếu với câu lệnh SQL chạy trực tiếp trên PostgreSQL `dds` để đảm bảo **không sai lệch dù chỉ 1 dòng**.
  2. Xây dựng luồng kể chuyện dữ liệu (**Data Storytelling**) trên Power BI (thêm nút điều hướng Page Navigation giữa Dashboard 1 và Dashboard 2, nút Reset Filters).
  3. Tổng hợp và trình bày **Báo cáo Phân tích (PDF)** hoàn chỉnh từ Chương 1 đến Chương 4 (chuẩn bị nộp lên Moodle ngày 05/11).
  4. Viết kịch bản và quay/dựng **Video Demo Giai đoạn 2 (5–7 phút)**: Minh họa từ kho dữ liệu PostgreSQL (`dds`), mô hình Star Schema trên Power BI, công thức DAX, đến thao tác lọc đa chiều trên Dashboard 1 và Drill-through tìm nguyên nhân trên Dashboard 2.

---

## 3. LỊCH TRÌNH CHI TIẾT GIAI ĐOẠN 2 (28/10 – 05/11/2026)

| Ngày | Mốc công việc cụ thể | Người thực hiện | Kết quả đầu ra (Deliverable) |
| :---: | :--- | :--- | :--- |
| **28/10 – 29/10** | - Kiên tạo file `powerbi/Hotel_BI_Dashboard.pbix`, nối DB `dds`, dựng Star Schema, Hierarchies và 12 DAX Measures.<br>- Kiên push file `.pbix` nền tảng lên GitHub. | Đào Trung Kiên | File `Hotel_BI_Dashboard.pbix` v1.0 có sẵn Model & DAX. |
| **30/10 – 01/11** | - Thanh thiết kế **Dashboard 1 (Overview)**.<br>- Dương thiết kế **Dashboard 2 (Diagnostic + Drill-through)**.<br>- Ý viết SQL đối soát số liệu KPIs và chuẩn bị khung Báo cáo Phân tích. | Thanh, Dương, Ý | Hoàn thiện 2 trang Dashboard Overview & Diagnostic. |
| **02/11 – 03/11** | - Ghép 2 trang Dashboard vào file `.pbix` chung, đồng bộ màu sắc (Theme khách sạn sang trọng: Xanh Navy & Vàng Gold).<br>- Hoàn thành toàn bộ nội dung Báo cáo Phân tích (PDF). | Cả nhóm | File `.pbix` v2.0 hoàn chỉnh & Báo cáo PDF bản nháp. |
| **04/11 – 05/11** | - Quay Video Demo & Trình bày sản phẩm.<br>- Nộp Báo cáo phân tích, Source code và Video Demo đúng hạn Seminar 2 (05/11/2026). | Cả nhóm (Ý dựng video, Kiên kiểm duyệt cuối) | Nộp bài Seminar 2 thành công. |
