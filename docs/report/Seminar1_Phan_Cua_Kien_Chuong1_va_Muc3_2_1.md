# PHẦN BÁO CÁO SEMINAR 1 – PHỤ TRÁCH: ĐÀO TRUNG KIÊN (NHÓM TRƯỞNG)
*(Bao gồm: Chương 1 – Kiến trúc Hệ thống Tổng thể & Chương 3, Mục 3.2.1 – Chuẩn hóa và Làm sạch Dữ liệu Tầng Staging với dbt)*

---

## CHƯƠNG 1: KIẾN TRÚC HỆ THỐNG TỔNG THỂ (SYSTEM ARCHITECTURE)

### 1.1. Tổng quan Kiến trúc Modern Data Stack
Hệ thống Business Intelligence tích hợp AI cho bài toán **Quản lý Đặt phòng & Phân tích Hủy phòng Khách sạn (*Hotel Booking Demand*)** được thiết kế theo mô hình **ELT (Extract – Load – Transform)** hiện đại, đóng gói đồng bộ bằng **Docker Compose** nhằm đảm bảo tính nhất quán môi trường giữa các thành viên phát triển.

Toàn bộ luồng dữ liệu đi qua 5 tầng xử lý chính:
1. **Data Source Layer (Nguồn dữ liệu):** Bộ dữ liệu *Hotel Booking Demand* từ Kaggle (119.390 bản ghi, 32 cột thuộc tính giai đoạn 2015–2017) được chia thành các gói dữ liệu lịch sử (`batch_01_full_2015_2016.csv`) và các gói dữ liệu phát sinh theo kỳ (`batch_02_inc_2017_H1.csv`, `batch_03_inc_2017_H2.csv`) để mô phỏng thực tế vận hành Full Load và Incremental Load.
2. **Data Ingestion & Orchestration Layer (`Mage.ai`):** Đóng vai trò thu thập dữ liệu từ các batch CSV, kiểm tra chất lượng sơ bộ (Data Validation), nạp vào vùng `stage` với cơ chế chống trùng lặp (`unique_conflict_method = 'UPDATE'` trên khóa `booking_uid`), đồng thời ghi nhận toàn bộ trạng thái thực thi vào vùng `control`.
3. **Storage & Data Warehouse Layer (`PostgreSQL 17`):** Được phân tách vật lý thành 3 tầng Schema rõ ràng:
   - **Schema `stage` (Staging Area):** Lưu trữ dữ liệu thô đã qua kiểm tra cấu trúc từ Mage.ai (`stage.raw_hotel_bookings`).
   - **Schema `dds` (Dimensional Data Store):** Lưu trữ Kho dữ liệu đa chiều theo lược đồ Hình sao (**Star Schema**) gồm 1 bảng sự kiện trung tâm (`dds.fact_bookings`) và 5 bảng chiều (`dds.dim_date`, `dds.dim_hotel`, `dds.dim_customer`, `dds.dim_channel`, `dds.dim_room_policy`).
   - **Schema `control` (Audit & Control Area):** Lưu trữ lịch sử chạy pipeline, số dòng trích xuất/hợp lệ/từ chối, thời gian thực thi và thông báo lỗi (`control.etl_batch_log`).
4. **Data Transformation & Quality Layer (`dbt - Data Build Tool`):** Thực hiện làm sạch, chuẩn hóa dữ liệu từ `stage` sang `dds`, tự động hóa 42 bài kiểm thử chất lượng dữ liệu (`dbt test`: `unique`, `not_null`, `accepted_values`, `relationships`) và khởi tạo tài liệu mô hình dữ liệu (`dbt docs` & Lineage DAG).
5. **BI Analytics & Generative AI Layer (`Power BI` & `Gemini AI Copilot`):** Khai thác trực tiếp kho dữ liệu `dds` và `control` để trực quan hóa các KPIs, phân tích chẩn đoán nguyên nhân hủy phòng (Diagnostic Analytics) và tự động tóm tắt/giải thích kết quả bằng mô hình ngôn ngữ lớn (LLM).

---

## CHƯƠNG 3 – MỤC 3.2.1: CHUẨN HÓA VÀ LÀM SẠCH DỮ LIỆU TẦNG STAGING (`stg_hotel_bookings.sql`)

### 3.2.1.1. Vai trò của mô hình `stg_hotel_bookings`
Mô hình `models/staging/stg_hotel_bookings.sql` được cấu hình dưới dạng `VIEW` (`materialized='view'`) nằm giữa bảng vật lý `stage.raw_hotel_bookings` và tầng Marts (`dds`). Việc sử dụng View ở tầng Staging giúp không tốn thêm dung lượng lưu trữ trùng lặp nhưng đảm bảo mọi mô hình Dimension và Fact phía sau luôn đọc được dữ liệu đã làm sạch theo một chuẩn duy nhất.

### 3.2.1.2. Các quy tắc làm sạch và chuẩn hóa đã triển khai
Trong `stg_hotel_bookings.sql`, 6 nhóm quy tắc biến đổi dữ liệu cốt lõi đã được áp dụng:

1. **Sinh khóa định danh giao dịch ổn định (`booking_key`):**
   - Sử dụng hàm băm `MD5` kết hợp `COALESCE` ưu tiên lấy từ mã định danh gốc `booking_uid` (`BK-000001`...):
     ```sql
     MD5(COALESCE(NULLIF(TRIM(CAST(booking_uid AS TEXT)), ''), CAST(ROW_NUMBER() OVER () AS TEXT))) AS booking_key
     ```
   - Đảm bảo tính duy nhất (`unique`) và tính bất biến của khóa chính qua các đợt nạp Incremental Load.

2. **Tái cấu trúc và chuẩn hóa kiểu dữ liệu Thời gian (`arrival_date`):**
   - Trong dữ liệu gốc Kaggle, ngày nhận phòng bị tách rời thành 3 cột: `arrival_date_year` (số), `arrival_date_month` (tên tháng tiếng Anh dạng chuỗi như `'July'`) và `arrival_date_day_of_month` (số).
   - Mô hình Staging ghép nối và chuyển đổi chính xác sang kiểu `DATE` chuẩn bằng hàm `TO_DATE(..., 'YYYY-FMMonth-DD')`, giúp kết nối 100% với khóa `full_date` của bảng `dds.dim_date`.

3. **Xử lý giá trị khuyết thiếu (`NULL`, `'NULL'`, `'NA'`, `'Undefined'`):**
   - **Cột `children`:** Trong bộ dữ liệu gốc có 4 bản ghi chứa chuỗi `'NA'`. Biểu thức `COALESCE(CAST(NULLIF(TRIM(CAST(children AS TEXT)), 'NA') AS NUMERIC)::INT, 0)` giúp chuyển đổi an toàn về số nguyên `0` mà không gây lỗi ép kiểu.
   - **Cột `country`:** Các bản ghi mang chuỗi `'NULL'` hoặc rỗng được chuẩn hóa về mã `'UNK'` (*Unknown*).
   - **Cột `agent` và `company`:** Loại bỏ hậu tố thập phân `.0` do Pandas sinh ra khi đọc cột số có chứa NULL (`REGEXP_REPLACE(..., '\.0$', '')`), đồng thời chuyển các giá trị `'NULL'` thành `'No Agent'` và `'No Company'`.
   - **Cột `meal`, `market_segment`, `distribution_channel`:** Các giá trị `'Undefined'` hoặc `NULL` được quy về giá trị nghiệp vụ mặc định (`'SC'` cho gói bữa ăn và `'Direct'` cho kênh phân phối).

4. **Ràng buộc miền giá trị không âm (`GREATEST(..., 0)`):**
   - Áp dụng hàm `GREATEST(COALESCE(..., 0), 0)` cho các trường định lượng (`lead_time`, `stays_in_weekend_nights`, `stays_in_week_nights`, `adults`, `children`, `babies`, `adr`, `booking_changes`, `total_of_special_requests`) để ngăn chặn dữ liệu âm bất thường.

5. **Lọc bỏ bản ghi rác vi phạm quy tắc nghiệp vụ (Data Filtering):**
   - Trong bộ dữ liệu gốc có **180 bản ghi** có tổng số khách bằng 0 (`adults = 0 AND children = 0 AND babies = 0`) và 1 bản ghi có giá phòng bình quân `adr < 0`.
   - Mệnh đề `WHERE` ở cuối `stg_hotel_bookings.sql` loại bỏ triệt để các bản ghi vô lý này trước khi đưa vào tính toán KPI và phân nhóm khách hàng (`guest_group_type` trong `dim_customer`).
