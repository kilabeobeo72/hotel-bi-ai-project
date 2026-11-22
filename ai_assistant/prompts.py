import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from google import genai

from ai_assistant.db_context import (
    build_grounded_context_markdown,
    execute_safe_readonly_sql,
    fetch_etl_batch_logs,
)

DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

GROUNDED_SYSTEM_INSTRUCTION = """Bạn là Chuyên gia Phân tích Business Intelligence & DataOps (AI BI Copilot) cho hệ thống Kho dữ liệu Khách sạn (Hotel Booking Demand Data Warehouse).

QUY TẮC BẮT BUỘC (0% HALLUCINATION POLICY):
1. Mọi nhận định, so sánh và kết luận BẮT BUỘC phải trích dẫn con số cụ thể từ phần [DỮ LIỆU THỰC TẾ TRÍCH XUẤT TỪ DATA WAREHOUSE] được cung cấp trong ngữ cảnh.
2. Tuyệt đối KHÔNG tự bịa số liệu, KHÔNG suy diễn các yếu tố nằm ngoài dữ liệu đã truy vấn. Nếu dữ liệu không chứa thông tin người dùng hỏi, hãy trả lời rõ là dữ liệu hiện tại trong kho chưa ghi nhận thuộc tính đó.
3. Trình bày bằng tiếng Việt chuyên nghiệp, cấu trúc Markdown rõ ràng (in đậm các chỉ số quan trọng như Tổng đơn, Tỷ lệ hủy %, Doanh thu thực thu $, Doanh thu thất thoát $, ADR $).
4. Mỗi khuyến nghị quản trị đưa ra phải gắn liền với bằng chứng định lượng cụ thể (ví dụ: tỷ lệ hủy theo nhóm Lead Time, kênh Online TA/Groups, hoặc chính sách No Deposit).
"""

DW_SCHEMA_REFERENCE = """
CẤU TRÚC SCHEMA KHO DỮ LIỆU POSTGRESQL (`dw_lab`):
1. Bảng `dds.fact_bookings` (119.209 dòng):
   - Khóa: `booking_key` (PK), `hotel_key`, `customer_key`, `channel_key`, `policy_key`, `arrival_date_key`, `status_date_key`
   - Các cột số liệu & phân loại:
     * `total_nights` (INT): Tổng số đêm lưu trú
     * `total_guests` (INT): Tổng số khách
     * `adr` (NUMERIC): Giá bán phòng trung bình mỗi đêm ($)
     * `gross_revenue` (NUMERIC): Tổng doanh thu tiềm năng ($)
     * `actual_revenue` (NUMERIC): Doanh thu thực thu từ đơn không hủy (`is_canceled = 0`) ($)
     * `revenue_loss` (NUMERIC): Doanh thu thất thoát từ đơn bị hủy (`is_canceled = 1`) ($)
     * `lead_time` (INT): Số ngày đặt phòng trước
     * `lead_time_group` (TEXT): Nhóm đặt trước ('1. Short (0-7 days)', '2. Medium (8-30 days)', '3. Long (31-90 days)', '4. Very Long (91-180 days)', '5. Extreme (>180 days)')
     * `is_canceled` (INT): 1 = Hủy phòng, 0 = Thành công
     * `booking_changes` (INT): Số lần thay đổi đặt phòng
     * `total_of_special_requests` (INT): Số yêu cầu đặc biệt của khách
2. Bảng `dds.dim_date`: `date_key` (INT YYYYMMDD), `full_date` (DATE), `year` (INT: 2015, 2016, 2017), `quarter` (INT), `month` (INT 1..12), `month_name` (TEXT), `week_of_year` (INT), `day_of_week` (INT), `is_weekend` (BOOLEAN)
3. Bảng `dds.dim_hotel`: `hotel_key` (TEXT), `hotel_name` ('City Hotel', 'Resort Hotel'), `hotel_category` (TEXT)
4. Bảng `dds.dim_customer`: `customer_key` (TEXT), `country_code` (TEXT: 'PRT', 'GBR', 'FRA', 'ESP', 'DEU'...), `customer_type` ('Transient', 'Transient-Party', 'Contract', 'Group'), `is_repeated_guest` (INT: 0, 1), `guest_group_type` ('Solo', 'Couple', 'Family', 'Group')
5. Bảng `dds.dim_channel`: `channel_key` (TEXT), `market_segment` ('Online TA', 'Offline TA/TO', 'Groups', 'Direct', 'Corporate', 'Complementary', 'Aviation'), `distribution_channel` ('TA/TO', 'Direct', 'Corporate', 'GDS'), `agent_code` (TEXT), `company_code` (TEXT)
6. Bảng `dds.dim_room_policy`: `policy_key` (TEXT), `reserved_room_type` (TEXT), `assigned_room_type` (TEXT), `is_room_upgraded` (BOOLEAN), `meal_code` ('BB', 'HB', 'FB', 'SC'), `meal_description` (TEXT), `deposit_type` ('No Deposit', 'Non Refund', 'Refundable')
7. Bảng `control.etl_batch_log`: `batch_id` (INT), `pipeline_name` (TEXT), `batch_file` (TEXT), `load_mode` ('FULL', 'INCREMENTAL'), `rows_extracted` (INT), `rows_valid` (INT), `rows_rejected` (INT), `status` ('SUCCESS', 'WARNING', 'FAILED'), `error_message` (TEXT), `started_at` (TIMESTAMP), `completed_at` (TIMESTAMP), `duration_seconds` (NUMERIC)
"""


def _load_api_key(explicit_api_key: Optional[str] = None) -> str:
    if explicit_api_key and explicit_api_key.strip() and explicit_api_key.strip() != "your_gemini_api_key_here":
        return explicit_api_key.strip()

    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key and env_key != "your_gemini_api_key_here":
        return env_key

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and val != "your_gemini_api_key_here":
                    return val

    raise ValueError(
        "Chưa cấu hình GEMINI_API_KEY hợp lệ. Hãy cập nhật GEMINI_API_KEY trong file .env "
        "hoặc nhập API Key trực tiếp trên giao diện."
    )


def _call_gemini(
    prompt: str,
    system_instruction: str = GROUNDED_SYSTEM_INSTRUCTION,
    api_key: Optional[str] = None,
    temperature: float = 0.1,
) -> str:
    resolved_key = _load_api_key(api_key)
    client = genai.Client(api_key=resolved_key)
    interaction = client.interactions.create(
        model=DEFAULT_GEMINI_MODEL,
        input=prompt,
        system_instruction=system_instruction,
        generation_config={"temperature": temperature},
        store=False,
    )
    return interaction.output_text or ""


def generate_executive_summary(
    year: Optional[int] = None,
    hotel_name: Optional[str] = None,
    market_segment: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    grounded_context = build_grounded_context_markdown(
        year=year,
        hotel_name=hotel_name,
        market_segment=market_segment,
    )

    prompt = f"""Dựa HOÀN TOÀN vào dữ liệu thực tế dưới đây, hãy tạo **Bản Tóm Tắt Điều Hành (AI-Generated Executive Summary)** dành cho Ban Giám đốc Khách sạn:

{grounded_context}

---
YÊU CẦU CẤU TRÚC BẢN TÓM TẮT:
1. **Tổng quan Hiệu suất Kinh doanh & Doanh thu**: Trình bày rõ Tổng số đơn đặt phòng, Số đơn hoàn thành, Doanh thu thực thu ($), Giá phòng trung bình ADR ($), Tổng số đêm phòng và Thời gian đặt trước trung bình.
2. **Cảnh báo Rủi ro Hủy phòng & Thất thoát Doanh thu**: Nêu rõ Số đơn bị hủy, Tỷ lệ hủy phòng (%) và Tổng doanh thu bị thất thoát ($), so sánh giữa City Hotel và Resort Hotel hoặc giữa các năm trong bộ lọc.
3. **Điểm nóng Kênh phân phối & Mùa vụ**: Chỉ ra kênh bán (`market_segment`) và tháng cao điểm/thấp điểm đang đóng góp doanh thu lớn nhất cũng như gây tổn thất hủy phòng lớn nhất (kèm con số định lượng).
4. **Tình trạng Sức khỏe Dữ liệu ETL (`control.etl_batch_log`)**: Tóm tắt ngắn gọn tổng số lần chạy ETL, tỷ lệ thành công, tổng số bản ghi hợp lệ/bị từ chối từ nhật ký ETL.
"""
    return _call_gemini(prompt=prompt, api_key=api_key)


def explain_anomaly_and_trends(
    focus_slice: str = "Toàn hệ thống (Tỷ lệ hủy phòng & Thất thoát doanh thu)",
    year: Optional[int] = None,
    hotel_name: Optional[str] = None,
    market_segment: Optional[str] = None,
    user_question: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    grounded_context = build_grounded_context_markdown(
        year=year,
        hotel_name=hotel_name,
        market_segment=market_segment,
    )
    extra_question = f"\nCâu hỏi cụ thể của người dùng: {user_question}" if user_question else ""

    prompt = f"""Dựa HOÀN TOÀN vào dữ liệu phân rã định lượng dưới đây, hãy thực hiện **Phân Tích Chẩn Đoán Nguyên Nhân (AI Diagnostic & Anomaly Explanation)** cho trọng tâm: **{focus_slice}**.{extra_question}

{grounded_context}

---
YÊU CẦU CẤU TRÚC PHÂN TÍCH CHẨN ĐOÁN:
1. **Phát hiện Biến động & Nghịch lý Dữ liệu**: Chỉ ra các bất thường nổi bật trong lát cắt **{focus_slice}** (ví dụ: sự chênh lệch tỷ lệ hủy giữa các nhóm Lead Time từ `0-7 ngày` tới `>180 ngày`, nghịch lý kênh `Online TA` và `Groups`, hoặc tác động của chính sách `No Deposit` / `Non Refund`).
2. **Bằng chứng Định lượng Giải thích Nguyên nhân (Root-Cause Analysis)**:
   - Tác động của **Thời gian đặt trước (`lead_time_group`)**: So sánh tỷ lệ hủy và doanh thu mất giữa nhóm đặt sát ngày và đặt xa ngày.
   - Tác động của **Kênh bán (`market_segment`) & Chính sách đặt cọc (`deposit_type`)**: Trích dẫn số đơn hủy và doanh thu thất thoát.
   - Tác động của **Đổi/Nâng hạng phòng (`is_room_upgraded`) & Yêu cầu đặc biệt (`total_of_special_requests`)**: Chứng minh bằng số liệu nhóm khách có cam kết cao hoặc được nâng hạng phòng có tỷ lệ hủy thấp hơn như thế nào.
3. **Khuyến nghị Hành động Quản trị (Actionable Recommendations)**: Đề xuất 3 giải pháp cụ thể có gắn ngưỡng định lượng (ví dụ: ngưỡng ngày `lead_time`, chính sách cọc theo kênh bán, kiểm soát mùa cao điểm).
"""
    return _call_gemini(prompt=prompt, api_key=api_key)


def answer_natural_language_query(
    question: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    sql_gen_system = f"""Bạn là chuyên gia PostgreSQL cho hệ thống Data Warehouse Khách sạn.
Nhiệm vụ của bạn là chuyển câu hỏi tiếng Việt của người dùng thành DUY NHẤT 1 câu lệnh SQL SELECT hợp lệ trên PostgreSQL.
{DW_SCHEMA_REFERENCE}
QUY TẮC SINH SQL:
- Chỉ trả về câu lệnh SQL thuần túy (không bọc trong giải thích dài dòng), chỉ sử dụng các bảng thuộc schema `dds` hoặc `control`.
- Luôn đặt bí danh cột rõ ràng và giới hạn `LIMIT 50` nếu truy vấn danh sách chi tiết.
- Khi tính tỷ lệ phần trăm, nhân `100.0` và dùng `ROUND(..., 2)`.
"""
    raw_sql_output = _call_gemini(
        prompt=f"Sinh câu lệnh PostgreSQL SELECT trả lời câu hỏi sau: {question}",
        system_instruction=sql_gen_system,
        api_key=api_key,
        temperature=0.0,
    )

    cleaned_sql = re.sub(r"^```(?:sql)?\s*", "", raw_sql_output.strip(), flags=re.IGNORECASE)
    cleaned_sql = re.sub(r"\s*```$", "", cleaned_sql.strip())

    df = execute_safe_readonly_sql(cleaned_sql)
    records_json = json.dumps(df.to_dict(orient="records"), ensure_ascii=False, default=str)

    explain_prompt = f"""Câu hỏi của người dùng: "{question}"
Câu lệnh SQL đã thực thi trên Data Warehouse:
```sql
{cleaned_sql}
```
Bảng kết quả thực tế truy vấn được từ PostgreSQL ({len(df)} dòng):
{records_json}

Hãy trả lời câu hỏi của người dùng bằng tiếng Việt ngắn gọn, rõ ràng, trích dẫn chính xác các con số từ bảng kết quả trên và giải thích ý nghĩa kinh doanh của kết quả đó."""

    explanation = _call_gemini(
        prompt=explain_prompt,
        system_instruction=GROUNDED_SYSTEM_INSTRUCTION,
        api_key=api_key,
        temperature=0.1,
    )

    return {
        "sql": cleaned_sql,
        "dataframe": df,
        "explanation": explanation,
    }


def inspect_etl_health(api_key: Optional[str] = None) -> str:
    etl_data = fetch_etl_batch_logs(limit=20)
    prompt = f"""Dựa trên dữ liệu nhật ký thực thi ETL từ bảng `control.etl_batch_log` dưới đây:

- Thống kê tổng hợp: {json.dumps(etl_data['summary'], ensure_ascii=False, default=str)}
- Chi tiết các lần chạy gần nhất: {json.dumps(etl_data['recent_logs'], ensure_ascii=False, default=str)}

Hãy phân tích sức khỏe hệ thống ETL (Mage.ai -> PostgreSQL `stage` -> dbt `dds`):
1. **Đánh giá Tổng quan Vận hành**: Số lần chạy, tỷ lệ thành công, tổng lượng bản ghi đã xử lý và thời gian thực thi trung bình (`duration_seconds`).
2. **Chẩn đoán Sự cố (`WARNING` / `FAILED`)**: Liệt kê chính xác `batch_id`, `batch_file`, `status`, số dòng bị từ chối (`rows_rejected`) và nội dung `error_message` (nếu có).
3. **Hướng dẫn Khắc phục cho Kỹ sư DataOps**: Đề xuất bước xử lý cụ thể cho từng batch bị lỗi hoặc cảnh báo và cách chạy lại (re-run) pipeline trên Mage.ai.
"""
    return _call_gemini(prompt=prompt, api_key=api_key)
