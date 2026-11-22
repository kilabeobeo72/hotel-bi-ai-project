# AI-ASSISTED ANALYTICS ENGINE (`ai_assistant/`)

Module tích hợp **Generative AI (Google Gemini API)** kết nối trực tiếp với Kho dữ liệu PostgreSQL (`dds` & `control`).

---

## 1. Cấu trúc Module

- **`ai_assistant/db_context.py`**:
  - `fetch_kpi_overview(year, hotel_name, market_segment)`
  - `fetch_yearly_and_monthly_trends(year, hotel_name, market_segment)`
  - `fetch_diagnostic_breakdowns(year, hotel_name, market_segment)`
  - `fetch_etl_batch_logs(limit)`
  - `build_grounded_context_markdown(year, hotel_name, market_segment)`
  - `execute_safe_readonly_sql(sql_query)`
- **`ai_assistant/prompts.py`**:
  - `generate_executive_summary(year, hotel_name, market_segment, api_key)`
  - `explain_anomaly_and_trends(focus_slice, year, hotel_name, market_segment, user_question, api_key)`
  - `answer_natural_language_query(question, api_key)`
  - `inspect_etl_health(api_key)`

---

## 2. Sử dụng trong `ai_assistant/app.py`

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

```bash
pip install -r ai_assistant/requirements.txt
streamlit run ai_assistant/app.py
```
