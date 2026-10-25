# 📙 SIDE DOC 3: KẾ HOẠCH GIAI ĐOẠN 3 – SEMINAR 3 

> **Chủ đề Seminar 3 (14/11/2026):** *Lập lịch ETL tự động, Dashboard theo dõi/giám sát kết quả mỗi lần ETL, và Giải thích kết quả phân tích bằng Generative AI*


## 1. MỤC TIÊU CỐT LÕI CỦA GIAI ĐOẠN 3

Ở chặng cuối cùng (Seminar 3 - 14/11), nhóm nâng cấp hệ thống từ một dự án BI tĩnh thành một **Hệ thống DataOps + AI-BI tự động hóa hoàn chỉnh**, giải quyết trọn vẹn 3 bài toán giảng viên yêu cầu:
1. **Lập lịch ETL tự động (Automated ETL Scheduling trên Mage.ai):** Cấu hình Triggers (Schedule theo thời gian / Cron expression & Event) tự động quét batch mới trong thư mục `data/`, nạp vào `stage`, kích hoạt tiếp `dbt build` cập nhật `dds`, và ghi log chi tiết vào `control.etl_batch_log`.
2. **Dashboard 3 – ETL Monitoring & Data Quality (Giám sát kết quả mỗi lần ETL):** Xây dựng một trang Dashboard chuyên biệt trên Power BI (và trên Web App) đọc trực tiếp từ schema `control` để theo dõi: Lịch sử các lần chạy ETL, tỷ lệ chạy thành công/lỗi, thời gian xử lý (latency), số lượng dòng nạp mới/cập nhật/từ chối qua từng batch, và chi tiết thông báo lỗi khi pipeline gặp sự cố.
3. **Ứng dụng Generative AI (Gemini 2.5 Flash API + Streamlit / Power BI Integration):**
   - **Tự động tạo bản tóm tắt (AI-generated Executive Summary)** từ các KPIs thật trong `dds` và trạng thái ETL trong `control`.
   - **Giải thích xu hướng & biến động (AI Anomaly & Diagnostic Explanation):** Giải thích tại sao tháng X hoặc kênh bán Y có tỷ lệ hủy phòng cao dựa trên số liệu định lượng trích xuất trực tiếp từ DB (cam kết **0% Hallucination** – chỉ nói dựa trên số liệu thực tế).
   - **[Điểm cộng khuyến khích] Hỏi đáp bằng ngôn ngữ tự nhiên (Natural Language Q&A / Text-to-SQL):** Cho phép người dùng nhập câu hỏi tiếng Việt (ví dụ: *"Top 5 quốc gia nào mang lại doanh thu thực tế cao nhất ở Resort Hotel năm 2017?"*) $\rightarrow$ AI tự sinh câu lệnh SQL chuẩn trên `dds`, chạy lấy bảng kết quả thật và diễn giải câu trả lời bằng tiếng Việt.

---

## 2. PHÂN CÔNG THEO HẠNG MỤC CÔNG VIỆC (SEMINAR 3)

### HẠNG MỤC 3.1: Lập lịch ETL Tự động (Mage.ai Triggers) & Chuỗi Pipeline End-to-End
- **Người phụ trách chính:** **Huỳnh Võ Đại Dương**
- **Thời gian hoàn thành:** Ngày 06/11 – 09/11/2026
- **Nhiệm vụ Kỹ thuật (Code & Cấu hình Mage.ai):**
  1. Nối block `dbt build` trực tiếp vào cuối pipeline `hotel_ingestion_pipeline` trên Mage.ai (để khi nạp xong `stage` thành công, Mage tự động gọi `dbt run` và `dbt test` cập nhật luôn `dds` và ghi kết quả test vào `control.etl_batch_log`).
  2. Thiết lập **Triggers (Lập lịch)** trên Mage.ai (`triggers.yaml`):
     - **Trigger 1 (`daily_hotel_incremental_schedule`):** Chạy tự động theo lịch (Cron `0 2 * * *` hoặc mỗi 5 phút khi demo).
     - **Trigger 2 (`manual_rerun_with_params`):** Cho phép truyền biến runtime `batch_file` để chạy lại (re-run) bất kỳ batch nào bị lỗi.
  3. Tạo kịch bản dữ liệu lịch sử 10–15 lần chạy ETL trong bảng `control.etl_batch_log` (bao gồm các lần chạy `FULL_LOAD`, `INCREMENTAL_LOAD` thành công, 1 lần `FAILED` do file sai định dạng cột, 1 lần `WARNING` do có dòng bị từ chối vì `adr < 0`, và lần `RETRY_SUCCESS` sau khi sửa lỗi) để Dashboard giám sát ETL có dữ liệu cực kỳ sinh động.
- **Nhiệm vụ Tài liệu (Document):**
  - Viết phần **Cấu hình Lập lịch ETL tự động (Mage Schedules/Triggers) & Kịch bản vận hành/chạy lại khi có lỗi** trong Báo cáo cuối kỳ.

---

### HẠNG MỤC 3.2: Xây dựng Dashboard 3 – Theo dõi & Giám sát Kết quả mỗi lần ETL
- **Người phụ trách chính:** **Phạm Ngọc Thanh**
- **Thời gian hoàn thành:** Ngày 07/11 – 10/11/2026
- **Nhiệm vụ Kỹ thuật (Power BI ETL Monitoring Dashboard):**
  1. Trong file `Hotel_BI_Dashboard.pbix`, kết nối thêm bảng `control.etl_batch_log` từ PostgreSQL.
  2. Thiết kế trang **Dashboard 3 – ETL Pipeline & Data Quality Monitor**:
     - **KPI Cards Giám sát:** `Tổng số lần chạy ETL (Total Runs)`, `Tỷ lệ Thành công (Success Rate %)`, `Tổng số dòng đã nạp (Total Rows Ingested)`, `Số dòng bị từ chối (Rejected Rows)`, `Thời gian chạy trung bình (Avg Duration Sec)`.
     - **Biểu đồ 1 (Combo Bar & Line Chart):** Số lượng bản ghi nạp thành công (`rows_valid`) vs bản ghi lỗi (`rows_rejected`) và Thời gian thực thi (`duration_seconds`) qua từng lần chạy batch.
     - **Biểu đồ 2 (Donut / Status Chart):** Tỷ lệ trạng thái các lần chạy (`SUCCESS`, `FAILED`, `WARNING`) và phân bổ theo loại nạp (`FULL` vs `INCREMENTAL`).
     - **Biểu đồ 3 (Audit Log Table có Conditional Formatting):** Bảng chi tiết từng lần chạy (`run_id`, `started_at`, `batch_file`, `load_mode`, `status` tô màu Xanh/Đỏ/Vàng, `rows_valid`, `error_message` hiển thị rõ nguyên nhân lỗi để kỹ sư dữ liệu xử lý).
- **Nhiệm vụ Tài liệu (Document):**
  - Viết phần **Thiết kế & Phân tích Dashboard Giám sát ETL (ETL Monitoring Dashboard)** trong Báo cáo cuối kỳ.

---

### HẠNG MỤC 3.3: Xây dựng Core Engine Generative AI (Chống suy diễn & Giải thích dựa trên dữ liệu thật)
- **Người phụ trách chính:** **Đào Trung Kiên** *(Nhóm trưởng)*
- **Thời gian hoàn thành:** Ngày 07/11 – 10/11/2026
- **Nhiệm vụ Kỹ thuật (Code Python Backend AI tại `ai_assistant/`):**
  1. Xây dựng module truy xuất ngữ cảnh dữ liệu thực (`ai_assistant/prompts.py` & `db_context.py`):
     - Tự động chạy các câu SQL tổng hợp trên `dds` (lấy KPI tổng quan, xu hướng theo tháng, phân rã tỷ lệ hủy theo kênh bán & loại đặt cọc) và trên `control.etl_batch_log` (lấy trạng thái lần ETL mới nhất) rồi đóng gói thành chuỗi JSON/Markdown có cấu trúc.
  2. Tích hợp **Google Gemini API (`google-genai` SDK - model `gemini-2.5-flash`)** với cơ chế **Grounded Analytics Prompting**:
     - **Chức năng 1 – AI Executive Summary:** Tự động tóm tắt bức tranh kinh doanh khách sạn & tình trạng dữ liệu ETL mới nhất, kèm trích dẫn con số chính xác từ DB.
     - **Chức năng 2 – AI Diagnostic & Trend Explainer:** Cho phép người dùng chọn một lát cắt trên Dashboard (ví dụ: *Kênh Online TA*, *Khách sạn City Hotel*, hoặc *Mùa cao điểm Tháng 7-8*), AI sẽ đọc bảng phân rã định lượng của lát cắt đó để giải thích nguyên nhân biến động và đề xuất giải pháp quản trị (ví dụ: chính sách đặt cọc theo ngưỡng `lead_time`).
     - Thiết lập quy tắc nghiêm ngặt trong System Prompt: *"Mọi nhận định phải trích dẫn con số cụ thể từ bảng dữ liệu Context được cung cấp. Tuyệt đối không suy diễn ngoài dữ liệu."*
- **Nhiệm vụ Tài liệu (Document):**
  - Viết **Mục 3.5.1 (Kiến trúc tích hợp Generative AI, Cơ chế Grounding chống Hallucination và Thiết kế Prompt)** trong Báo cáo cuối kỳ.

---

### HẠNG MỤC 3.4: Giao diện AI-Assisted Analytics, Hỏi đáp Ngôn ngữ Tự nhiên (NL2SQL) & Video Tổng kết
- **Người phụ trách chính:** **Thạch Ý**
- **Thời gian hoàn thành:** Ngày 08/11 – 13/11/2026
- **Nhiệm vụ Kỹ thuật (Streamlit UI & NL2SQL Chat tại `ai_assistant/app.py`):**
  1. Xây dựng giao diện Web App **Hotel BI & AI Copilot** bằng Streamlit (chạy tại `http://localhost:8501`, có thể mở song song hoặc nhúng link từ Power BI):
     - **Tab 1 – AI Executive Summary & Anomaly Explainer:** Giao diện chọn bộ lọc (Năm, Loại khách sạn, Kênh bán) $\rightarrow$ Hiển thị bảng số liệu chuẩn từ `dds` + Bản phân tích chuyên sâu do AI tạo ra (có nút xuất báo cáo Markdown).
     - **Tab 2 – Hỏi đáp dữ liệu bằng Ngôn ngữ Tự nhiên (Natural Language Q&A - Điểm cộng):** Người dùng gõ câu hỏi bất kỳ bằng tiếng Việt $\rightarrow$ AI chuyển thành câu lệnh `SELECT` an toàn (chỉ cho phép `SELECT` trên schema `dds` và `control`) $\rightarrow$ Thực thi trên PostgreSQL $\rightarrow$ Hiển thị **Câu lệnh SQL kiểm chứng + Bảng dữ liệu kết quả + Lời giải thích của AI**.
     - **Tab 3 – AI ETL Log Inspector:** AI đọc bảng `control.etl_batch_log`, tóm tắt sức khỏe hệ thống ETL và gợi ý cách khắc phục nếu phát hiện batch gần nhất bị `FAILED`.
  2. Cùng cả nhóm hoàn thiện **Báo cáo PDF Cuối kỳ** và dựng **Video Demo Tổng hợp End-to-End** (minh họa đầy đủ từ Lập lịch ETL $\rightarrow$ Dashboard Giám sát ETL $\rightarrow$ Power BI Overview/Diagnostic $\rightarrow$ AI giải thích & hỏi đáp).


