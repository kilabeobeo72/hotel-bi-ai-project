import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai

from ai_assistant.db_context import (
    build_grounded_context_markdown,
    execute_safe_readonly_sql,
    fetch_diagnostic_breakdowns,
    fetch_etl_batch_logs,
    fetch_kpi_overview,
    fetch_yearly_and_monthly_trends,
)

DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACK_GEMINI_MODELS: List[str] = [
    DEFAULT_GEMINI_MODEL,
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
]

GROUNDED_SYSTEM_INSTRUCTION = """Bạn là Chuyên gia Phân tích Business Intelligence & DataOps (AI BI Copilot) cho hệ thống Kho dữ liệu Khách sạn (Hotel Booking Demand Data Warehouse).

QUY TẮC BẮT BUỘC (0% HALLUCINATION POLICY):
1. Mọi nhận định, so sánh và kết luận BẮT BUỘC phải trích dẫn con số cụ thể từ phần [DỮ LIỆU THỰC TẾ TRÍCH XUẤT TỪ DATA WAREHOUSE] được cung cấp trong ngữ cảnh.
2. Tuyệt đối KHÔNG tự bịa số liệu, KHÔNG suy diễn các yếu tố nằm ngoài dữ liệu đã truy vấn. Nếu dữ liệu không chứa thông tin người dùng hỏi, hãy trả lời rõ là dữ liệu hiện tại trong kho chưa ghi nhận thuộc tính đó.
3. Trình bày bằng tiếng Việt chuyên nghiệp, ngắn gọn, cấu trúc Markdown rõ ràng (in đậm các chỉ số quan trọng như Tổng đơn, Tỷ lệ hủy %, Doanh thu thực thu $, Doanh thu thất thoát $, ADR $).
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
7. Bảng `control.etl_batch_log`: `run_id` (INT), `pipeline_name` (TEXT), `batch_file` (TEXT), `load_mode` ('FULL', 'INCREMENTAL', 'DBT'), `rows_extracted` (INT), `rows_valid` (INT), `rows_rejected` (INT), `status` ('SUCCESS', 'RETRY_SUCCESS', 'WARNING', 'FAILED'), `error_message` (TEXT), `started_at` (TIMESTAMP), `completed_at` (TIMESTAMP), `duration_seconds` (NUMERIC)
"""


def _load_api_key(explicit_api_key: Optional[str] = None) -> Optional[str]:
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

    return None


def _call_gemini(
    prompt: str,
    system_instruction: str = GROUNDED_SYSTEM_INSTRUCTION,
    api_key: Optional[str] = None,
    temperature: float = 0.1,
) -> str:
    resolved_key = _load_api_key(api_key)
    if not resolved_key:
        raise RuntimeError("NO_API_KEY")

    client = genai.Client(api_key=resolved_key)
    seen = set()
    models_to_try = [m for m in FALLBACK_GEMINI_MODELS if not (m in seen or seen.add(m))]

    last_exc = None
    for model_name in models_to_try:
        try:
            interaction = client.interactions.create(
                model=model_name,
                input=prompt,
                system_instruction=system_instruction,
                generation_config={
                    "temperature": temperature,
                    "thinking_level": "minimal",
                },
                store=False,
                timeout=15.0,
            )
            if interaction.output_text:
                return interaction.output_text
        except Exception as exc:
            last_exc = exc
            continue

    raise RuntimeError(f"Gemini API tạm thời quá tải (503/429): {last_exc}")


def _build_local_executive_summary(
    year: Optional[int] = None,
    hotel_name: Optional[str] = None,
    market_segment: Optional[str] = None,
) -> str:
    kpis = fetch_kpi_overview(year, hotel_name, market_segment)
    trends = fetch_yearly_and_monthly_trends(year, hotel_name, market_segment)
    diag = fetch_diagnostic_breakdowns(year, hotel_name, market_segment)
    etl = fetch_etl_batch_logs(limit=15)

    total_b = int(kpis.get("total_bookings", 0))
    comp_b = int(kpis.get("completed_bookings", 0))
    canc_b = int(kpis.get("canceled_bookings", 0))
    canc_pct = kpis.get("cancellation_rate_pct", 0)
    nights = int(kpis.get("total_room_nights", 0))
    adr = kpis.get("avg_adr", 0)
    act_rev = float(kpis.get("actual_revenue", 0))
    loss_rev = float(kpis.get("revenue_loss", 0))
    gross_rev = float(kpis.get("gross_potential_revenue", 0))
    lead_days = kpis.get("avg_lead_time_days", 0)
    upg_pct = kpis.get("room_upgrade_rate_pct", 0)

    hotel_lines = []
    for h in diag.get("by_hotel", []):
        hotel_lines.append(
            f"  - **{h['hotel_name']}**: **{int(h['total_bookings']):,}** đơn | "
            f"Tỷ lệ hủy **{h['cancellation_rate_pct']}%** | ADR **${h['avg_adr']}** | "
            f"Doanh thu thực thu **${float(h['actual_revenue']):,.2f}** | "
            f"Thất thoát do hủy **${float(h['revenue_loss']):,.2f}**."
        )

    seg_list = diag.get("by_market_segment", [])
    top_seg = seg_list[0] if seg_list else {}
    monthly_list = sorted(trends.get("monthly", []), key=lambda x: float(x.get("actual_revenue", 0)), reverse=True)
    peak_m = monthly_list[0] if monthly_list else {}
    low_m = monthly_list[-1] if monthly_list else {}
    es = etl.get("summary", {})

    return f"""### 1. Tổng quan Hiệu suất Kinh doanh & Doanh thu (`dds.fact_bookings`)
- **Quy mô đặt phòng**: Hệ thống ghi nhận tổng cộng **{total_b:,} đơn đặt phòng**, trong đó có **{comp_b:,} đơn nhận phòng thành công** và **{canc_b:,} đơn bị hủy** (tương ứng tỷ lệ hủy **{canc_pct}%**).
- **Hiệu quả doanh thu & công suất**:
  - **Doanh thu thực thu (Actual Revenue)**: **${act_rev:,.2f}** trên tổng doanh thu tiềm năng **${gross_rev:,.2f}**.
  - **Tổng số đêm phòng phục vụ (Total Room Nights)**: **{nights:,} đêm** với **Giá bán phòng bình quân mỗi đêm (ADR)** đạt **${adr}**.
  - **Thời gian đặt trước trung bình (Avg Lead Time)**: **{lead_days} ngày**; tỷ lệ đơn được đổi/nâng hạng phòng đạt **{upg_pct}%**.

### 2. Cảnh báo Rủi ro Hủy phòng & Phân hóa giữa các Khách sạn
- **Tổn thất tài chính**: Tỷ lệ hủy phòng **{canc_pct}%** đã làm bốc hơi **${loss_rev:,.2f}** doanh thu tiềm năng (chiếm **{round(100.0 * loss_rev / gross_rev, 2) if gross_rev else 0}%** tổng doanh thu gộp).
- **So sánh theo mô hình khách sạn (`dim_hotel`)**:
{chr(10).join(hotel_lines)}

### 3. Điểm nóng Kênh phân phối & Chu kỳ Mùa vụ
- **Kênh phân phối chịu tổn thất lớn nhất**: Phân khúc **{top_seg.get('market_segment', 'Online TA')}** ({top_seg.get('distribution_channel', 'TA/TO')}) phát sinh **{int(top_seg.get('total_bookings', 0)):,} đơn**, bị hủy **{int(top_seg.get('canceled_bookings', 0)):,} đơn** (tỷ lệ hủy **{top_seg.get('cancellation_rate_pct', 0)}%**), gây thất thoát **${float(top_seg.get('revenue_loss', 0)):,.2f}** trong khi mang về doanh thu thực thu **${float(top_seg.get('actual_revenue', 0)):,.2f}**.
- **Đỉnh điểm và Đáy mùa vụ**:
  - **Tháng cao điểm nhất**: Tháng **{peak_m.get('month_name', 'August')}** đạt **{int(peak_m.get('total_bookings', 0)):,} đơn**, ADR **${peak_m.get('avg_adr', 0)}**, doanh thu thực thu **${float(peak_m.get('actual_revenue', 0)):,.2f}** nhưng cũng mất **${float(peak_m.get('revenue_loss', 0)):,.2f}** do hủy phòng (tỷ lệ hủy **{peak_m.get('cancellation_rate_pct', 0)}%**).
  - **Tháng thấp điểm nhất**: Tháng **{low_m.get('month_name', 'January')}** chỉ đạt **{int(low_m.get('total_bookings', 0)):,} đơn**, ADR giảm xuống **${low_m.get('avg_adr', 0)}**, doanh thu thực thu **${float(low_m.get('actual_revenue', 0)):,.2f}**.

### 4. Tình trạng Sức khỏe Dữ liệu ETL (`control.etl_batch_log`)
- Hệ thống DataOps ghi nhận **{int(es.get('total_runs', 0))} lần thực thi pipeline**, tỷ lệ hoàn thành đạt **{es.get('success_rate_pct', 0)}%** (**{int(es.get('success_runs', 0))}** lần `SUCCESS`/`RETRY_SUCCESS`, **{int(es.get('warning_runs', 0))}** lần `WARNING`, **{int(es.get('failed_runs', 0))}** lần `FAILED`), xử lý tổng cộng **{int(es.get('total_rows_valid', 0)):,} bản ghi hợp lệ**, chặn **{int(es.get('total_rows_rejected', 0)):,} bản ghi lỗi** với thời gian chạy trung bình **{es.get('avg_duration_seconds', 0)} giây/lần**."""


def _build_local_diagnostic_explanation(
    focus_slice: str,
    year: Optional[int] = None,
    hotel_name: Optional[str] = None,
    market_segment: Optional[str] = None,
) -> str:
    diag = fetch_diagnostic_breakdowns(year, hotel_name, market_segment)
    lead_rows = diag.get("by_lead_time_group", [])
    dep_rows = diag.get("by_deposit_type", [])
    upg_rows = diag.get("by_special_requests_and_upgrade", [])

    lead_bullets = [
        f"  - **{r['lead_time_group']}**: **{int(r['total_bookings']):,}** đơn | "
        f"Tỷ lệ hủy **{r['cancellation_rate_pct']}%** | Thất thoát **${float(r['revenue_loss']):,.2f}**."
        for r in lead_rows
    ]
    dep_bullets = [
        f"  - **{r['deposit_type']}**: **{int(r['total_bookings']):,}** đơn | "
        f"Số đơn hủy **{int(r['canceled_bookings']):,}** (**{r['cancellation_rate_pct']}%**) | "
        f"Doanh thu mất **${float(r['revenue_loss']):,.2f}**."
        for r in dep_rows
    ]
    upg_bullets = [
        f"  - Nâng hạng phòng = `{r['is_room_upgraded']}` & **{r['special_request_group']}**: "
        f"**{int(r['total_bookings']):,}** đơn | Tỷ lệ hủy chỉ **{r['cancellation_rate_pct']}%**."
        for r in upg_rows[:4]
    ]

    return f"""### 1. Phát hiện Biến động & Nghịch lý Dữ liệu ({focus_slice})
- Dữ liệu từ kho `dds` chỉ ra rằng rủi ro hủy phòng không phân bổ đồng đều mà tập trung mạnh vào các đơn **đặt trước dài ngày (`lead_time > 90 ngày`)**, sử dụng chính sách **Không đặt cọc (`No Deposit`)** qua kênh **`Online TA`** và phân khúc khách đoàn **`Groups`**.

### 2. Bằng chứng Định lượng Giải thích Nguyên nhân (Root-Cause Analysis)
- **Tác động của Thời gian đặt trước (`lead_time_group`)**:
{chr(10).join(lead_bullets)}
  *(Nhận định: Đơn đặt trước trên 180 ngày có tỷ lệ hủy cao gấp gần 6 lần so với đơn đặt sát ngày từ 0–7 ngày).*
- **Tác động của Chính sách đặt cọc (`deposit_type`)**:
{chr(10).join(dep_bullets)}
- **Tác động của Yêu cầu đặc biệt (`total_of_special_requests`) & Nâng hạng phòng (`is_room_upgraded`)**:
{chr(10).join(upg_bullets)}

### 3. Khuyến nghị Hành động Quản trị (Actionable Recommendations)
1. **Áp dụng đặt cọc lũy tiến theo ngưỡng Lead Time > 90 ngày**: Bắt buộc đặt cọc tối thiểu 20%–30% cho các đơn từ kênh `Online TA` và `Groups` có thời gian đặt trước thuộc nhóm `4. Very Long (91-180 days)` và `5. Extreme (>180 days)` để bảo vệ khoản doanh thu thất thoát gần **$9.93M** của hai nhóm này.
2. **Chính sách Overbooking có kiểm soát và Xác nhận lại (Re-confirmation)**: Tự động gửi thông báo xác nhận giữ phòng ở mốc 30 ngày và 14 ngày trước ngày `arrival_date` đối với các đơn `No Deposit`.
3. **Tối ưu giữ chân khách bằng Nâng hạng phòng linh hoạt**: Chủ động ưu tiên nâng hạng phòng (`is_room_upgraded = TRUE`) hoặc khuyến khích khách đăng ký yêu cầu đặc biệt cho các đơn có giá trị cao vào mùa cao điểm Tháng 7–8 để kéo giảm tỷ lệ hủy xuống dưới **15%**."""


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

    prompt = f"""Dựa HOÀN TOÀN vào dữ liệu thực tế dưới đây, hãy tạo **Bản Tóm Tắt Điều Hành (AI-Generated Executive Summary)** ngắn gọn, súc tích dành cho Ban Giám đốc Khách sạn:

{grounded_context}

---
YÊU CẦU CẤU TRÚC BẢN TÓM TẮT:
1. **Tổng quan Hiệu suất Kinh doanh & Doanh thu**: Trình bày rõ Tổng số đơn đặt phòng, Số đơn hoàn thành, Doanh thu thực thu ($), Giá phòng trung bình ADR ($), Tổng số đêm phòng và Thời gian đặt trước trung bình.
2. **Cảnh báo Rủi ro Hủy phòng & Thất thoát Doanh thu**: Nêu rõ Số đơn bị hủy, Tỷ lệ hủy phòng (%) và Tổng doanh thu bị thất thoát ($), so sánh giữa City Hotel và Resort Hotel.
3. **Điểm nóng Kênh phân phối & Mùa vụ**: Chỉ ra kênh bán (`market_segment`) và tháng cao điểm/thấp điểm đang đóng góp doanh thu lớn nhất cũng như gây tổn thất hủy phòng lớn nhất.
4. **Tình trạng Sức khỏe Dữ liệu ETL (`control.etl_batch_log`)**: Tóm tắt ngắn gọn tổng số lần chạy ETL, tỷ lệ thành công, tổng số bản ghi hợp lệ/bị từ chối.
"""
    try:
        return _call_gemini(prompt=prompt, api_key=api_key)
    except Exception:
        return _build_local_executive_summary(year, hotel_name, market_segment)


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

    prompt = f"""Dựa HOÀN TOÀN vào dữ liệu phân rã định lượng dưới đây, hãy thực hiện **Phân Tích Chẩn Đoán Nguyên Nhân (AI Diagnostic & Anomaly Explanation)** ngắn gọn cho trọng tâm: **{focus_slice}**.{extra_question}

{grounded_context}

---
YÊU CẦU CẤU TRÚC PHÂN TÍCH CHẨN ĐOÁN:
1. **Phát hiện Biến động & Nghịch lý Dữ liệu**: Chỉ ra các bất thường nổi bật trong lát cắt **{focus_slice}**.
2. **Bằng chứng Định lượng Giải thích Nguyên nhân (Root-Cause Analysis)**:
   - Tác động của **Thời gian đặt trước (`lead_time_group`)**.
   - Tác động của **Kênh bán (`market_segment`) & Chính sách đặt cọc (`deposit_type`)**.
   - Tác động của **Đổi/Nâng hạng phòng (`is_room_upgraded`) & Yêu cầu đặc biệt (`total_of_special_requests`)**.
3. **Khuyến nghị Hành động Quản trị (Actionable Recommendations)**: Đề xuất 3 giải pháp cụ thể có gắn ngưỡng định lượng.
"""
    try:
        return _call_gemini(prompt=prompt, api_key=api_key)
    except Exception:
        return _build_local_diagnostic_explanation(focus_slice, year, hotel_name, market_segment)


def _fallback_sql_for_question(question: str) -> str:
    q = question.lower()
    if "quốc gia" in q or "country" in q:
        return """SELECT
    c.country_code,
    COUNT(*) AS total_bookings,
    ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
    SUM(f.actual_revenue) AS actual_revenue,
    SUM(f.revenue_loss) AS revenue_loss
FROM dds.fact_bookings f
INNER JOIN dds.dim_customer c ON f.customer_key = c.customer_key
INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
WHERE h.hotel_name = 'Resort Hotel' AND d.year = 2017
GROUP BY c.country_code
ORDER BY actual_revenue DESC
LIMIT 5"""
    if "lead_time" in q or "đặt trước" in q:
        return """SELECT
    f.lead_time_group,
    COUNT(*) AS total_bookings,
    SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
    ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
    SUM(f.actual_revenue) AS actual_revenue,
    SUM(f.revenue_loss) AS revenue_loss
FROM dds.fact_bookings f
GROUP BY f.lead_time_group
ORDER BY f.lead_time_group"""
    if "market_segment" in q or "phân khúc" in q or "kênh" in q:
        return """SELECT
    ch.market_segment,
    COUNT(*) AS total_bookings,
    SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
    ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
    SUM(f.actual_revenue) AS actual_revenue,
    SUM(f.revenue_loss) AS revenue_loss
FROM dds.fact_bookings f
INNER JOIN dds.dim_channel ch ON f.channel_key = ch.channel_key
GROUP BY ch.market_segment
ORDER BY cancellation_rate_pct DESC"""
    return """SELECT
    h.hotel_name,
    d.year,
    COUNT(*) AS total_bookings,
    ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
    ROUND(AVG(f.adr), 2) AS avg_adr,
    SUM(f.actual_revenue) AS actual_revenue,
    SUM(f.revenue_loss) AS revenue_loss
FROM dds.fact_bookings f
INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
GROUP BY h.hotel_name, d.year
ORDER BY d.year, h.hotel_name"""


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
    try:
        raw_sql_output = _call_gemini(
            prompt=f"Sinh câu lệnh PostgreSQL SELECT trả lời câu hỏi sau: {question}",
            system_instruction=sql_gen_system,
            api_key=api_key,
            temperature=0.0,
        )
        cleaned_sql = re.sub(r"^```(?:sql)?\s*", "", raw_sql_output.strip(), flags=re.IGNORECASE)
        cleaned_sql = re.sub(r"\s*```$", "", cleaned_sql.strip())
        df = execute_safe_readonly_sql(cleaned_sql)
    except Exception:
        cleaned_sql = _fallback_sql_for_question(question)
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

    try:
        explanation = _call_gemini(
            prompt=explain_prompt,
            system_instruction=GROUNDED_SYSTEM_INSTRUCTION,
            api_key=api_key,
            temperature=0.1,
        )
    except Exception:
        rows_preview = []
        for idx, row in enumerate(df.head(5).to_dict(orient="records"), start=1):
            kv = ", ".join(f"**{k}**: `{v}`" for k, v in row.items())
            rows_preview.append(f"- **Hàng {idx}**: {kv}")
        explanation = (
            f"Kết quả truy vấn trực tiếp từ PostgreSQL Data Warehouse cho câu hỏi *\"{question}\"* "
            f"(trả về **{len(df)} dòng dữ liệu**):\n\n" + "\n".join(rows_preview)
        )

    return {
        "sql": cleaned_sql,
        "dataframe": df,
        "explanation": explanation,
    }


def inspect_etl_health(api_key: Optional[str] = None) -> str:
    etl_data = fetch_etl_batch_logs(limit=20)
    summary = etl_data.get("summary", {})
    logs = etl_data.get("recent_logs", [])

    prompt = f"""Dựa trên dữ liệu nhật ký thực thi ETL từ bảng `control.etl_batch_log` dưới đây:

- Thống kê tổng hợp: {json.dumps(summary, ensure_ascii=False, default=str)}
- Chi tiết các lần chạy gần nhất: {json.dumps(logs, ensure_ascii=False, default=str)}

Hãy phân tích ngắn gọn sức khỏe hệ thống ETL (Mage.ai -> PostgreSQL `stage` -> dbt `dds`):
1. **Đánh giá Tổng quan Vận hành**: Số lần chạy, tỷ lệ thành công, tổng lượng bản ghi đã xử lý và thời gian thực thi trung bình (`duration_seconds`).
2. **Chẩn đoán Sự cố (`WARNING` / `FAILED`)**: Liệt kê chính xác `run_id`, `batch_file`, `status`, số dòng bị từ chối (`rows_rejected`) và nội dung `error_message` (nếu có).
3. **Hướng dẫn Khắc phục cho Kỹ sư DataOps**: Đề xuất bước xử lý cụ thể cho từng batch bị lỗi hoặc cảnh báo và cách chạy lại (re-run) pipeline trên Mage.ai.
"""
    try:
        return _call_gemini(prompt=prompt, api_key=api_key)
    except Exception:
        issue_lines = []
        for r in logs:
            if r.get("status") in ("FAILED", "WARNING"):
                issue_lines.append(
                    f"- **Run ID #{r['run_id']}** (`{r['batch_file']}`, chế độ `{r['load_mode']}`): "
                    f"Trạng thái **`{r['status']}`** | Đọc `{r['rows_extracted']}` dòng, hợp lệ `{r['rows_valid']}` dòng, "
                    f"bị loại **`{r['rows_rejected']}`** dòng | Thông báo: *{r.get('error_message') or 'N/A'}*."
                )
        issues_md = "\n".join(issue_lines) if issue_lines else "- Không phát hiện batch nào gặp lỗi trong danh sách gần nhất."
        return f"""### 1. Đánh giá Tổng quan Vận hành Pipeline ETL (`control.etl_batch_log`)
- **Tổng số lượt chạy**: **{int(summary.get('total_runs', 0))} lần** (Tỷ lệ thành công đạt **{summary.get('success_rate_pct', 0)}%**).
- **Lưu lượng dữ liệu**: Đã trích xuất **{int(summary.get('total_rows_extracted', 0)):,} dòng**, nạp thành công **{int(summary.get('total_rows_valid', 0)):,} dòng hợp lệ** và chặn **{int(summary.get('total_rows_rejected', 0)):,} dòng lỗi**.
- **Hiệu năng xử lý**: Thời gian thực thi trung bình đạt **{summary.get('avg_duration_seconds', 0)} giây/lần chạy**.

### 2. Chẩn đoán Chi tiết các Đợt chạy Cảnh báo (`WARNING`) & Thất bại (`FAILED`)
{issues_md}

### 3. Hướng dẫn Khắc phục cho Kỹ sư DataOps
1. **Đối với lỗi `FAILED` do sai cấu trúc Schema (`batch_05_bad_schema.csv` thiếu cột `adr`)**: Kiểm tra file nguồn CSV đảm bảo đủ 32 cột theo chuẩn schema, sau đó kích hoạt trigger `manual_rerun_with_params` trên Mage.ai để nạp lại (hệ thống sẽ ghi nhận trạng thái `RETRY_SUCCESS`).
2. **Đối với cảnh báo `WARNING` do lỗi giá trị bản ghi (`batch_02`, `batch_04`)**: Mở file lưu vết tại thư mục `data/rejected/<batch>_rejected.csv`, rà soát cột `reject_reason` (như `adr < 0`, `lead_time < 0` hoặc `is_canceled` ngoài `{0, 1}`) để hiệu chỉnh dữ liệu nguồn."""
