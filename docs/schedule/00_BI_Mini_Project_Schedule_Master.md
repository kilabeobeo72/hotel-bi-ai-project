# 📋 BI MINI PROJECT SCHEDULE (TÀI LIỆU TỔNG QUAN & ĐIỀU PHỐI)

> **Đề tài:** Xây dựng Hệ thống Business Intelligence Tích hợp Generative AI phân tích Nhu cầu Đặt phòng, Doanh thu & Nguyên nhân Hủy phòng Khách sạn (*Hotel Booking Demand Analytics & AI Assistant*)
> **Repository GitHub chính thức:** [https://github.com/kilabeobeo72/hotel-bi-ai-project](https://github.com/kilabeobeo72/hotel-bi-ai-project)
> **Dataset Kaggle:** [Hotel Booking Demand (32 cột, 119.390 dòng)](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand)



## 1. LỘ TRÌNH 3 GIAI ĐOẠN (3 SIDE DOCS CHI TIẾT)


1. 📘 **[SIDE DOC 1: Giai đoạn Seminar 1 (Hạn 25/10 – Trình bày 27/10/2026)](./01_SideDoc_Seminar1_25Oct_ETL_DW.md)**
   - **Trọng tâm:** *Modeling & Nạp dữ liệu từ Source vào Kho dữ liệu (`stage` $\rightarrow$ `dds` & `control`)*.
   - **Sản phẩm bàn giao:** Thiết kế Star Schema, Pipeline Mage.ai (Full/Incremental + Audit Log), Models & Tests trên `dbt`, Báo cáo Giai đoạn 1.
2. 📗 **[SIDE DOC 2: Giai đoạn Seminar 2 (Hạn 05/11/2026)](./02_SideDoc_Seminar2_05Nov_PowerBI.md)**
   - **Trọng tâm:** *Xây dựng ứng dụng BI trên Kho dữ liệu (`dds` $\rightarrow$ Power BI Semantic Model + Dashboard Overview & Diagnostic)*.
   - **Sản phẩm bàn giao:** File `Hotel_BI_Dashboard.pbix`, Báo cáo phân tích chuyên sâu & Video Demo Giai đoạn 2.
3. 📙 **[SIDE DOC 3: Giai đoạn Seminar 3 (Hạn 14/11/2026)](./03_SideDoc_Seminar3_14Nov_Schedule_Monitor_AI.md)**
   - **Trọng tâm:** *Lập lịch ETL tự động, Dashboard giám sát kết quả mỗi lần ETL (`control`), và Giải thích kết quả phân tích bằng Generative AI*.
   - **Sản phẩm bàn giao:** Trigger lập lịch trên Mage.ai, Dashboard ETL Monitoring, Ứng dụng AI Assistant (Tóm tắt KPI + Giải thích biến động + Hỏi đáp tự nhiên), Báo cáo & Video Demo hoàn chỉnh.

---

## 2. THÔNG TIN DATASET & BÀI TOÁN NGHIỆP VỤ (CHỐT CHUNG CHO CẢ NHÓM)

### 2.1. Nguồn dữ liệu Kaggle
- **Tên bộ dữ liệu:** Hotel Booking Demand
- **URL:** `https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand`
- **Mô tả:** Chứa **119.390 bản ghi** đặt phòng của 2 loại hình khách sạn (**Resort Hotel** và **City Hotel**) trong giai đoạn **2015 – 2017**, bao gồm **32 cột** thuộc tính.
- **Lý do chọn (Khác biệt & Giàu chiều phân tích):**
  - Không trùng lặp với các bài toán bán hàng siêu thị (Superstore/E-commerce) phổ biến.
  - Có đầy đủ chiều Thời gian (`arrival_date_year/month/day`, `reservation_status_date`), Địa điểm (`country`), Đối tượng khách (`customer_type`, `is_repeated_guest`, `adults/children/babies`), Kênh phân phối (`market_segment`, `distribution_channel`, `agent`), Chính sách phòng & đặt cọc (`reserved_room_type`, `assigned_room_type`, `deposit_type`, `meal`).
  - Có **vấn đề nghiệp vụ cực kỳ rõ nét** để làm Diagnostic Analytics & AI: **Tỷ lệ hủy phòng (Cancellation Rate) trung bình lên tới ~37%**, gây thất thoát doanh thu lớn, đặc biệt biến động mạnh theo kênh *Online TA*, thời gian đặt trước (*Lead Time*) và chính sách đặt cọc (*Deposit Type*).

### 2.2. Ba tầng Schema trong PostgreSQL Data Warehouse (Kế thừa chuẩn `01_mage_demo_01`)
Hệ thống chạy trên Docker gồm 2 container `lab-postgres` (PostgreSQL 17, port `5432`) và `lab-mage` (Mage.ai + dbt, port `6789`) với 3 schema:
1. **`stage`**: Chứa bảng `stage.raw_hotel_bookings` do Mage.ai nạp từ các file CSV batch.
2. **`dds` (Dimensional Data Store)**: Chứa lược đồ hình sao (Star Schema) gồm 1 bảng Fact và 5 bảng Dimension do **dbt** xây dựng:
   - `dds.fact_bookings` *(Grain: 1 dòng = 1 đơn đặt phòng `booking_id`)*
   - `dds.dim_date` *(Chiều thời gian)*
   - `dds.dim_hotel` *(Chiều khách sạn: Resort Hotel / City Hotel)*
   - `dds.dim_customer` *(Chiều khách hàng: Quốc tịch, Loại khách, Khách quay lại)*
   - `dds.dim_channel` *(Chiều kênh bán: Market Segment, Distribution Channel, Agent, Company)*
   - `dds.dim_room_policy` *(Chiều chính sách phòng: Loại phòng đặt/nhận, Gói ăn, Loại đặt cọc)*
3. **`control`**: Chứa bảng `control.etl_batch_log` lưu trạng thái thực thi của từng lần chạy pipeline Mage.ai (Thời gian chạy, tên batch, kiểu nạp Full/Incremental, số dòng đọc/ghi, trạng thái `SUCCESS`/`FAILED`, thông báo lỗi).

---

## 3. QUY ƯỚC LÀM VIỆC TRÊN GITHUB CHO 4 THÀNH VIÊN

1. **Clone dự án về máy:**
   ```bash
   git clone https://github.com/kilabeobeo72/hotel-bi-ai-project.git
   cd hotel-bi-ai-project
   cp .env.example .env
   docker compose up -d --build
   ```
2. **Chia nhánh Git (Branch) để không đụng code nhau:**
   - Đào Trung Kiên: nhánh `feat/kien-dw-dbt-ai`
   - Huỳnh Võ Đại Dương: nhánh `feat/duong-mage-etl`
   - Phạm Ngọc Thanh: nhánh `feat/thanh-marts-powerbi`
   - Thạch Ý: nhánh `feat/y-control-test-app`
3. **Quy tắc Merge:** Cuối mỗi cột mốc, các thành viên tạo Pull Request (PR) vào nhánh `main`. Nhóm trưởng (Kiên) kiểm tra chạy thử `docker compose` và merge.
