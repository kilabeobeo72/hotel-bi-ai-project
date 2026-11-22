# AI-ASSISTED ANALYTICS ENGINE (`ai_assistant/`) – SEMINAR 3

Thư mục này chứa mã nguồn tích hợp **Generative AI (Google Gemini API)** kết nối trực tiếp với Kho dữ liệu PostgreSQL (`dds` & `control`), đảm bảo **0% Hallucination** (mọi phân tích đều trích dẫn từ số liệu thực tế trong Data Warehouse).

---

## 1. Cấu trúc Module & Phân công

### Hạng mục 3.3 – Core Engine Generative AI *(Đào Trung Kiên đã hoàn thành)*
- **`ai_assistant/db_context.py`**:
  - `fetch_kpi_overview(year, hotel_name, market_segment)`: Truy vấn 11 chỉ số KPI cốt lõi từ `dds.fact_bookings`.
  - `fetch_yearly_and_monthly_trends(year, hotel_name, market_segment)`: Truy vấn xu hướng theo Năm và Tháng.
  - `fetch_diagnostic_breakdowns(year, hotel_name, market_segment)`: Truy vấn 5 bảng phân rã nguyên nhân hủy phòng (theo Khách sạn, Kênh bán, Loại cọc, Nhóm Lead Time, Nâng hạng phòng & Yêu cầu đặc biệt).
  - `fetch_etl_batch_logs(limit)`: Truy vấn thống kê và lịch sử chạy ETL từ `control.etl_batch_log`.
  - `build_grounded_context_markdown(year, hotel_name, market_segment)`: Đóng gói toàn bộ dữ liệu thực tế thành tài liệu Markdown có cấu trúc để đưa vào Prompt của Gemini.
  - `execute_safe_readonly_sql(sql_query)`: Thực thi câu lệnh `SELECT` an toàn (chặn mọi lệnh ghi/xóa) phục vụ tính năng NL2SQL.
- **`ai_assistant/prompts.py`** *(Sử dụng SDK `google-genai`, model `gemini-3.8-flash`)*:
  - `generate_executive_summary(year, hotel_name, market_segment, api_key)`: Tự động tạo **Bản Tóm Tắt Điều Hành (AI-Generated Executive Summary)** từ KPIs thật và trạng thái ETL.
  - `explain_anomaly_and_trends(focus_slice, year, hotel_name, market_segment, user_question, api_key)`: Giải thích nguyên nhân biến động, nghịch lý hủy phòng và đề xuất giải pháp quản trị định lượng.
  - `answer_natural_language_query(question, api_key)`: Chuyển câu hỏi tiếng Việt thành câu lệnh SQL `SELECT`, chạy trên PostgreSQL trả về `{"sql": str, "dataframe": pd.DataFrame, "explanation": str}`.
  - `inspect_etl_health(api_key)`: Đọc `control.etl_batch_log`, tóm tắt sức khỏe hệ thống ETL và hướng dẫn xử lý batch lỗi.

---

## 2. Hướng dẫn cho Thạch Ý (Hạng mục 3.4 – Xây dựng `ai_assistant/app.py` bằng Streamlit)

Thạch Ý chỉ cần tạo file `ai_assistant/app.py` và import trực tiếp các hàm Backend đã viết sẵn của Kiên:

```python
from ai_assistant.db_context import (
    fetch_kpi_overview,
    fetch_diagnostic_breakdowns,
    fetch_etl_batch_logs,
)
from ai_assistant.prompts import (
    generate_executive_summary,
    explain_anomaly_and_trends,
    answer_natural_language_query,
    inspect_etl_health,
)
```

### Cài đặt thư viện & Chạy thử:
```bash
pip install -r ai_assistant/requirements.txt
# Điền GEMINI_API_KEY vào file .env rồi chạy:
streamlit run ai_assistant/app.py
```
