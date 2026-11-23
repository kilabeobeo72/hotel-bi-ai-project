# KỊCH BẢN KIỂM THỬ & DEMO TOÀN TRÌNH (END-TO-END TEST SCRIPT)

Tài liệu này hướng dẫn từng bước để kiểm thử hoặc quay Video Demo toàn bộ hệ thống từ **Data Ingestion (Mage.ai)** -> **Data Warehouse (`dds` & `control` trên PostgreSQL / dbt)** -> **Power BI (03 Dashboards)** -> **Web App Generative AI Copilot (Streamlit)**.

---

## BƯỚC 1: Khởi động Hạ tầng Docker & Chuẩn bị Dữ liệu Batch

Mở Terminal (PowerShell) tại thư mục gốc `D:\12_Src`:

```powershell
cd D:\12_Src

# 1. Cắt file hotel_bookings.csv gốc thành 5 file batch (Full, Incremental 1, Incremental 2, Corrupted, Bad Schema)
python data/split_batches.py

# 2. Bật Docker containers (lab-postgres ở port 5433 & lab-mage ở port 6789)
docker compose up -d
```

---

## BƯỚC 2: Nạp kịch bản Lịch sử ETL (`control.etl_batch_log`) & Xây dựng Kho `dds`

Để **Dashboard 3 (ETL Monitoring)** trên Power BI và **Tab 3 (AI ETL Log Inspector)** trên Web App có sẵn 14 dòng lịch sử chạy ETL sinh động (bao gồm `FULL`, `INCREMENTAL`, `DBT`, `SUCCESS`, `WARNING`, `FAILED`, `RETRY_SUCCESS`):

```powershell
# 1. Nạp 14 dòng lịch sử ETL mẫu vào bảng control.etl_batch_log
Get-Content postgres/seed/seed_etl_history.sql | docker exec -i lab-postgres psql -U postgres -d dw_lab

# 2. Kiểm tra số dòng trong bảng stage.raw_hotel_bookings và 6 bảng kho dds
docker exec lab-postgres psql -U postgres -d dw_lab -c "SELECT 'stage.raw_hotel_bookings' AS table_name, COUNT(*) FROM stage.raw_hotel_bookings UNION ALL SELECT 'dds.dim_date', COUNT(*) FROM dds.dim_date UNION ALL SELECT 'dds.dim_hotel', COUNT(*) FROM dds.dim_hotel UNION ALL SELECT 'dds.dim_customer', COUNT(*) FROM dds.dim_customer UNION ALL SELECT 'dds.dim_channel', COUNT(*) FROM dds.dim_channel UNION ALL SELECT 'dds.dim_room_policy', COUNT(*) FROM dds.dim_room_policy UNION ALL SELECT 'dds.fact_bookings', COUNT(*) FROM dds.fact_bookings;"

# 3. (Nếu cần chạy lại dbt run & dbt test):
docker exec lab-mage bash -c "cd /home/src/lab_project/dbt/hotel_dw && dbt run --profiles-dir . && dbt test --profiles-dir ."
```

---

## BƯỚC 3: Kiểm thử Lập lịch Tự động (Mage.ai Triggers – Seminar 1 & 3)

1. Mở trình duyệt truy cập Mage.ai: **`http://localhost:6789`**
   - **Email / Username:** `admin@admin.com`
   - **Password:** `admin`
2. Vào pipeline **`hotel_ingestion_pipeline`**:
   - **Tab Edit Pipeline:** Chiếu cấu trúc 4 blocks nối tiếp nhau:
     1. `load_hotel_csv` (Data Loader – hỗ trợ chế độ `AUTO` tự phát hiện batch chưa nạp)
     2. `validate_hotel_data` (Transformer – kiểm tra 32 cột & lọc dòng lỗi vào `data/rejected/`)
     3. `load_stage_hotel` (Data Exporter – nạp Full/Incremental Upsert vào `stage.raw_hotel_bookings` & ghi `control.etl_batch_log`)
     4. `run_dbt_build` (Custom Block – tự động kích hoạt `dbt run` & `dbt test` cập nhật tầng `dds`)
   - **Tab Triggers:** Chiếu 3 Triggers lập lịch tự động đã cấu hình trong `triggers.yaml`:
     - `daily_hotel_incremental_schedule` (`0 2 * * *` – chạy tự động 02:00 sáng hàng ngày với `batch_file=AUTO`, `load_mode=AUTO`)
     - `demo_every_5_minutes_schedule` (`*/5 * * * *` – dùng khi demo trực tiếp)
     - `manual_rerun_with_params` (`@once` – dùng để chạy lại một batch cụ thể)
   - Bấm **Run@once** hoặc **Execute pipeline** để demo pipeline tự chạy từ đầu tới `dbt test` và ghi thêm dòng mới vào `control.etl_batch_log`.

---

## BƯỚC 4: Kiểm thử 03 Trang Dashboard trên Power BI Desktop (Seminar 2 & 3)

Mở file **`D:\12_Src\powerbi\Hotel_BI_Dashboard.pbix`** bằng Power BI Desktop:

1. **Trang 1 – Executive Overview (Descriptive Analytics):**
   - Kiểm tra 5 KPI Cards khớp số liệu chuẩn: `Total Bookings = 119,209`, `Actual Revenue = $25.94M`, `Revenue Loss = $16.78M`, `Cancellation Rate = 37.19%`, `ADR = $101.97`.
   - Thử bấm Slicer lọc theo Năm (`2016`, `2017`) hoặc Loại khách sạn (`City Hotel`, `Resort Hotel`) để thấy sự phân hóa mùa vụ (đỉnh điểm Tháng 7–8, thấp điểm Tháng 11–1).
2. **Trang 2 – Cancellation Diagnostic (Diagnostic Analytics):**
   - Từ Trang 1, click chuột phải vào cột kênh **`Online TA`** hoặc **`Groups`** -> chọn **Drill through** -> **Cancellation Diagnostic**.
   - Trình bày bằng chứng định lượng trên 4 biểu đồ chẩn đoán:
     - Nhóm đặt sát ngày `1. Short (0-7 days)` tỷ lệ hủy chỉ **`9.80%`**, trong khi nhóm đặt xa `5. Extreme (>180 days)` tỷ lệ hủy vọt lên **`57.06%`**.
     - Khách có từ `>= 2` yêu cầu đặc biệt hoặc được nâng hạng phòng (`is_room_upgraded = TRUE`) có tỷ lệ hủy thấp hơn rõ rệt.
3. **Trang 3 – ETL Pipeline & Data Quality Monitor (DataOps Monitoring):**
   - Bấm nút **Refresh** trên Power BI để cập nhật bảng `control.etl_batch_log`.
   - Kiểm tra 5 thẻ KPI giám sát ETL, biểu đồ số dòng hợp lệ vs dòng lỗi, thời gian chạy và bảng Audit Log tô màu trạng thái (`SUCCESS`, `WARNING`, `FAILED`, `RETRY_SUCCESS`) kèm `error_message`.

---

## BƯỚC 5: Kiểm thử Ứng dụng Web AI-Assisted Analytics Copilot (Streamlit – Seminar 3)

1. Mở file `.env` tại `D:\12_Src\.env` và điền Google Gemini API Key của bạn vào dòng:
   ```env
   GEMINI_API_KEY=AIzaSy...
   ```
   *(Hoặc có thể dán trực tiếp API Key vào ô nhập ở thanh Sidebar bên trái của giao diện Web).*
2. Mở Terminal tại `D:\12_Src` và chạy:
   ```powershell
   pip install -r ai_assistant/requirements.txt
   streamlit run ai_assistant/app.py
   ```
3. Trình duyệt tự động mở tại **`http://localhost:8501`**. Thực hiện 3 bài test tương ứng 3 Tab:
   - **Test Tab 1 (AI Executive Summary & Anomaly Explainer):**
     - Mở khung *"Xem các bảng số liệu Grounded Context trích xuất từ Data Warehouse (`dds`)"* để chứng minh dữ liệu đầu vào là số liệu thật 100% từ PostgreSQL.
     - Bấm nút **"✨ Tạo Bản Tóm Tắt Điều Hành bằng AI"** -> Kiểm tra bản tóm tắt của Gemini trích dẫn đúng `119,209` đơn, tỷ lệ hủy `37.19%`, doanh thu thực `$25,938,319.77`, doanh thu mất `$16,775,893.38`.
     - Ở cột bên phải, chọn lát cắt *"Tác động của Thời gian đặt trước (Lead Time Group) đến rủi ro hủy phòng"* -> bấm **"🔍 Phân Tích Nguyên Nhân & Đề Xuất Giải Pháp"**.
   - **Test Tab 2 (Hỏi đáp Ngôn ngữ Tự nhiên – NL2SQL):**
     - Bấm vào câu hỏi mẫu: *"Top 5 quốc gia có doanh thu thực tế (actual_revenue) cao nhất ở Resort Hotel năm 2017?"* (hoặc gõ câu hỏi tiếng Việt bất kỳ) -> Bấm **"🚀 Truy vấn Data Warehouse & Giải thích"**.
     - Kiểm tra 3 kết quả hiển thị: (1) Câu lệnh SQL `SELECT` sinh tự động, (2) Bảng dữ liệu thực từ PostgreSQL, (3) Lời giải thích tiếng Việt của AI.
   - **Test Tab 3 (AI ETL Log Inspector):**
     - Xem 5 thẻ KPI giám sát ETL và bảng lịch sử `control.etl_batch_log`.
     - Bấm nút **"🩺 Phân tích Sức khỏe ETL & Gợi ý Khắc phục Sự cố bằng AI"** -> AI sẽ chỉ đích danh các batch bị `WARNING` (`batch_02`, `batch_04` có dòng lỗi bị loại) và `FAILED` (`batch_05_bad_schema.csv` thiếu cột `adr`) kèm hướng dẫn khắc phục.
