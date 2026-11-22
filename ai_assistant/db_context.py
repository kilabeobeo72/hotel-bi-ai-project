"""
Module: ai_assistant/db_context.py
Người phụ trách: Đào Trung Kiên (Hạng mục 3.3 - Seminar 3)
Chức năng:
  - Kết nối trực tiếp vào PostgreSQL Data Warehouse (schema `dds` và `control`).
  - Truy xuất các bảng số liệu tổng hợp (KPIs, xu hướng tháng, phân rã hủy phòng theo
    kênh bán, chính sách cọc, nhóm Lead Time, và nhật ký chạy ETL `control.etl_batch_log`).
  - Đóng gói dữ liệu thực tế thành Grounded Context (Markdown/JSON) chống Hallucination
    để cung cấp cho Google Gemini API.
  - Cung cấp hàm `execute_safe_readonly_sql` (chỉ cho phép SELECT trên `dds` và `control`)
    hỗ trợ tính năng Hỏi đáp ngôn ngữ tự nhiên (NL2SQL).
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """
    Khởi tạo kết nối tới PostgreSQL Data Warehouse (`dw_lab`).
    Tự động ưu tiên biến môi trường hoặc thử cổng 5433 (chạy trên máy host Windows)
    rồi fallback sang cổng 5432 (chạy bên trong Docker container).
    """
    db_name = os.environ.get("POSTGRES_DB", "dw_lab")
    db_user = os.environ.get("POSTGRES_USER", "postgres")
    db_password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    env_host = os.environ.get("POSTGRES_HOST")
    env_port = os.environ.get("POSTGRES_PORT")

    candidates: List[Tuple[str, int]] = []
    if env_host and env_port:
        candidates.append((env_host, int(env_port)))
    candidates.extend([
        ("localhost", 5433),
        ("127.0.0.1", 5433),
        ("postgres", 5432),
        ("localhost", 5432),
    ])

    last_err = None
    for host, port in candidates:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=3,
            )
            return conn
        except Exception as exc:
            last_err = exc
    raise ConnectionError(f"Không thể kết nối tới PostgreSQL Data Warehouse: {last_err}")


def _build_where_clause(
    year: Optional[int] = None,
    hotel_name: Optional[str] = None,
    market_segment: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    """Tạo mệnh đề WHERE động theo bộ lọc người dùng chọn trên giao diện."""
    conditions: List[str] = []
    params: List[Any] = []

    if year is not None and str(year).strip().upper() not in ("", "ALL", "TẤT CẢ"):
        conditions.append("d.year = %s")
        params.append(int(year))

    if hotel_name and str(hotel_name).strip().upper() not in ("", "ALL", "TẤT CẢ"):
        conditions.append("h.hotel_name = %s")
        params.append(str(hotel_name).strip())

    if market_segment and str(market_segment).strip().upper() not in ("", "ALL", "TẤT CẢ"):
        conditions.append("ch.market_segment = %s")
        params.append(str(market_segment).strip())

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where_sql, params


def fetch_kpi_overview(
    year: Optional[int] = None,
    hotel_name: Optional[str] = None,
    market_segment: Optional[str] = None,
) -> Dict[str, Any]:
    """Lấy bộ 12 chỉ số KPI tổng quan từ schema `dds` theo bộ lọc."""
    where_sql, params = _build_where_clause(year, hotel_name, market_segment)
    sql = f"""
        SELECT
            COUNT(*) AS total_bookings,
            COALESCE(SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END), 0) AS canceled_bookings,
            COALESCE(SUM(CASE WHEN f.is_canceled = 0 THEN 1 ELSE 0 END), 0) AS completed_bookings,
            ROUND(100.0 * COALESCE(AVG(f.is_canceled), 0), 2) AS cancellation_rate_pct,
            COALESCE(SUM(f.total_nights), 0) AS total_room_nights,
            ROUND(COALESCE(AVG(f.adr), 0), 2) AS avg_adr,
            COALESCE(SUM(f.actual_revenue), 0.00) AS actual_revenue,
            COALESCE(SUM(f.revenue_loss), 0.00) AS revenue_loss,
            COALESCE(SUM(f.gross_revenue), 0.00) AS gross_potential_revenue,
            ROUND(COALESCE(AVG(f.lead_time), 0), 1) AS avg_lead_time_days,
            ROUND(
                100.0 * COALESCE(
                    AVG(CASE WHEN rp.is_room_upgraded THEN 1.0 ELSE 0.0 END),
                    0
                ),
                2
            ) AS room_upgrade_rate_pct
        FROM dds.fact_bookings f
        INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
        INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
        INNER JOIN dds.dim_channel ch ON f.channel_key = ch.channel_key
        INNER JOIN dds.dim_room_policy rp ON f.policy_key = rp.policy_key
        {where_sql};
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else {}


def fetch_yearly_and_monthly_trends(
    year: Optional[int] = None,
    hotel_name: Optional[str] = None,
    market_segment: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Lấy xu hướng đặt phòng, doanh thu thực, doanh thu mất và tỷ lệ hủy theo Năm và Tháng."""
    where_sql, params = _build_where_clause(year, hotel_name, market_segment)

    yearly_sql = f"""
        SELECT
            d.year,
            COUNT(*) AS total_bookings,
            SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
            ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
            ROUND(AVG(f.adr), 2) AS avg_adr,
            SUM(f.actual_revenue) AS actual_revenue,
            SUM(f.revenue_loss) AS revenue_loss
        FROM dds.fact_bookings f
        INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
        INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
        INNER JOIN dds.dim_channel ch ON f.channel_key = ch.channel_key
        {where_sql}
        GROUP BY d.year
        ORDER BY d.year;
    """

    monthly_sql = f"""
        SELECT
            d.month,
            d.month_name,
            COUNT(*) AS total_bookings,
            SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
            ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
            ROUND(AVG(f.adr), 2) AS avg_adr,
            SUM(f.actual_revenue) AS actual_revenue,
            SUM(f.revenue_loss) AS revenue_loss
        FROM dds.fact_bookings f
        INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
        INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
        INNER JOIN dds.dim_channel ch ON f.channel_key = ch.channel_key
        {where_sql}
        GROUP BY d.month, d.month_name
        ORDER BY d.month;
    """

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(yearly_sql, params)
            yearly = [dict(r) for r in cur.fetchall()]
            cur.execute(monthly_sql, params)
            monthly = [dict(r) for r in cur.fetchall()]

    return {"yearly": yearly, "monthly": monthly}


def fetch_diagnostic_breakdowns(
    year: Optional[int] = None,
    hotel_name: Optional[str] = None,
    market_segment: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Lấy dữ liệu phân rã nguyên nhân hủy phòng (Diagnostic Analytics) theo:
      1. Loại khách sạn (`hotel_name`)
      2. Phân khúc kênh bán (`market_segment`)
      3. Chính sách đặt cọc (`deposit_type`)
      4. Nhóm thời gian đặt trước (`lead_time_group`)
      5. Tác động của đổi/nâng hạng phòng (`is_room_upgraded`) và yêu cầu đặc biệt (`total_of_special_requests`)
    """
    where_sql, params = _build_where_clause(year, hotel_name, market_segment)

    queries = {
        "by_hotel": f"""
            SELECT
                h.hotel_name,
                COUNT(*) AS total_bookings,
                SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
                ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
                ROUND(AVG(f.adr), 2) AS avg_adr,
                SUM(f.actual_revenue) AS actual_revenue,
                SUM(f.revenue_loss) AS revenue_loss
            FROM dds.fact_bookings f
            INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
            INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
            INNER JOIN dds.dim_channel ch ON f.channel_key = ch.channel_key
            {where_sql}
            GROUP BY h.hotel_name
            ORDER BY total_bookings DESC;
        """,
        "by_market_segment": f"""
            SELECT
                ch.market_segment,
                ch.distribution_channel,
                COUNT(*) AS total_bookings,
                SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
                ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
                SUM(f.actual_revenue) AS actual_revenue,
                SUM(f.revenue_loss) AS revenue_loss
            FROM dds.fact_bookings f
            INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
            INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
            INNER JOIN dds.dim_channel ch ON f.channel_key = ch.channel_key
            {where_sql}
            GROUP BY ch.market_segment, ch.distribution_channel
            ORDER BY revenue_loss DESC;
        """,
        "by_deposit_type": f"""
            SELECT
                rp.deposit_type,
                COUNT(*) AS total_bookings,
                SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
                ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
                SUM(f.actual_revenue) AS actual_revenue,
                SUM(f.revenue_loss) AS revenue_loss
            FROM dds.fact_bookings f
            INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
            INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
            INNER JOIN dds.dim_channel ch ON f.channel_key = ch.channel_key
            INNER JOIN dds.dim_room_policy rp ON f.policy_key = rp.policy_key
            {where_sql}
            GROUP BY rp.deposit_type
            ORDER BY total_bookings DESC;
        """,
        "by_lead_time_group": f"""
            SELECT
                f.lead_time_group,
                COUNT(*) AS total_bookings,
                SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
                ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
                ROUND(AVG(f.lead_time), 1) AS avg_lead_time_days,
                SUM(f.actual_revenue) AS actual_revenue,
                SUM(f.revenue_loss) AS revenue_loss
            FROM dds.fact_bookings f
            INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
            INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
            INNER JOIN dds.dim_channel ch ON f.channel_key = ch.channel_key
            {where_sql}
            GROUP BY f.lead_time_group
            ORDER BY f.lead_time_group;
        """,
        "by_special_requests_and_upgrade": f"""
            SELECT
                rp.is_room_upgraded,
                CASE
                    WHEN f.total_of_special_requests = 0 THEN '0 yêu cầu đặc biệt'
                    WHEN f.total_of_special_requests = 1 THEN '1 yêu cầu đặc biệt'
                    ELSE '>= 2 yêu cầu đặc biệt'
                END AS special_request_group,
                COUNT(*) AS total_bookings,
                SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
                ROUND(100.0 * AVG(f.is_canceled), 2) AS cancellation_rate_pct,
                SUM(f.revenue_loss) AS revenue_loss
            FROM dds.fact_bookings f
            INNER JOIN dds.dim_date d ON f.arrival_date_key = d.date_key
            INNER JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
            INNER JOIN dds.dim_channel ch ON f.channel_key = ch.channel_key
            INNER JOIN dds.dim_room_policy rp ON f.policy_key = rp.policy_key
            {where_sql}
            GROUP BY rp.is_room_upgraded, special_request_group
            ORDER BY rp.is_room_upgraded, special_request_group;
        """,
    }

    results: Dict[str, List[Dict[str, Any]]] = {}
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for key, q in queries.items():
                cur.execute(q, params)
                results[key] = [dict(r) for r in cur.fetchall()]
    return results


def fetch_etl_batch_logs(limit: int = 15) -> Dict[str, Any]:
    """
    Lấy thống kê tổng quan và lịch sử các lần chạy ETL gần nhất từ bảng `control.etl_batch_log`.
    """
    summary_sql = """
        SELECT
            COUNT(*) AS total_runs,
            COALESCE(SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END), 0) AS success_runs,
            COALESCE(SUM(CASE WHEN status = 'WARNING' THEN 1 ELSE 0 END), 0) AS warning_runs,
            COALESCE(SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END), 0) AS failed_runs,
            ROUND(
                100.0 * COALESCE(
                    AVG(CASE WHEN status IN ('SUCCESS', 'WARNING') THEN 1.0 ELSE 0.0 END),
                    0
                ),
                2
            ) AS success_rate_pct,
            COALESCE(SUM(rows_extracted), 0) AS total_rows_extracted,
            COALESCE(SUM(rows_valid), 0) AS total_rows_valid,
            COALESCE(SUM(rows_rejected), 0) AS total_rows_rejected,
            ROUND(COALESCE(AVG(duration_seconds), 0), 2) AS avg_duration_seconds
        FROM control.etl_batch_log;
    """
    logs_sql = """
        SELECT
            batch_id,
            pipeline_name,
            batch_file,
            load_mode,
            rows_extracted,
            rows_valid,
            rows_rejected,
            status,
            COALESCE(error_message, '') AS error_message,
            TO_CHAR(started_at, 'YYYY-MM-DD HH24:MI:SS') AS started_at,
            TO_CHAR(completed_at, 'YYYY-MM-DD HH24:MI:SS') AS completed_at,
            duration_seconds
        FROM control.etl_batch_log
        ORDER BY batch_id DESC
        LIMIT %s;
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(summary_sql)
            summary = dict(cur.fetchone() or {})
            cur.execute(logs_sql, (limit,))
            recent_logs = [dict(r) for r in cur.fetchall()]

    return {"summary": summary, "recent_logs": recent_logs}


def build_grounded_context_markdown(
    year: Optional[int] = None,
    hotel_name: Optional[str] = None,
    market_segment: Optional[str] = None,
) -> str:
    """
    Đóng gói toàn bộ dữ liệu thực tế từ `dds` và `control.etl_batch_log` thành tài liệu
    Markdown có cấu trúc rõ ràng để truyền vào Prompt cho Gemini API (0% Hallucination).
    """
    kpis = fetch_kpi_overview(year, hotel_name, market_segment)
    trends = fetch_yearly_and_monthly_trends(year, hotel_name, market_segment)
    diag = fetch_diagnostic_breakdowns(year, hotel_name, market_segment)
    etl = fetch_etl_batch_logs(limit=10)

    filter_desc = (
        f"Năm: {year or 'Tất cả (2015-2017)'} | "
        f"Khách sạn: {hotel_name or 'Tất cả (City Hotel & Resort Hotel)'} | "
        f"Phân khúc: {market_segment or 'Tất cả'}"
    )

    lines = [
        "# DỮ LIỆU THỰC TẾ TRÍCH XUẤT TỪ DATA WAREHOUSE (SCHEMA `dds` & `control`)",
        f"**Bộ lọc hiện tại:** {filter_desc}",
        "",
        "## 1. CHỈ SỐ KPI TỔNG QUAN (`dds.fact_bookings`)",
        f"- Tổng số đơn đặt phòng (Total Bookings): {int(kpis.get('total_bookings', 0)):,} đơn",
        f"- Số đơn thành công (Completed Bookings): {int(kpis.get('completed_bookings', 0)):,} đơn",
        f"- Số đơn bị hủy (Canceled Bookings): {int(kpis.get('canceled_bookings', 0)):,} đơn",
        f"- Tỷ lệ hủy phòng (Cancellation Rate %): {kpis.get('cancellation_rate_pct', 0)}%",
        f"- Tổng số đêm phòng (Total Room Nights): {int(kpis.get('total_room_nights', 0)):,} đêm",
        f"- Giá phòng trung bình mỗi đêm (ADR): ${kpis.get('avg_adr', 0)}",
        f"- Doanh thu thực thu (Actual Revenue): ${float(kpis.get('actual_revenue', 0)):,.2f}",
        f"- Doanh thu thất thoát do hủy (Revenue Loss): ${float(kpis.get('revenue_loss', 0)):,.2f}",
        f"- Tổng doanh thu tiềm năng (Gross Potential Revenue): ${float(kpis.get('gross_potential_revenue', 0)):,.2f}",
        f"- Thời gian đặt trước trung bình (Avg Lead Time): {kpis.get('avg_lead_time_days', 0)} ngày",
        f"- Tỷ lệ đổi/nâng hạng phòng (Room Upgrade Rate %): {kpis.get('room_upgrade_rate_pct', 0)}%",
        "",
        "## 2. XU HƯỚNG THEO NĂM (`dim_date.year`)",
        json.dumps(trends["yearly"], ensure_ascii=False, default=str),
        "",
        "## 3. XU HƯỚNG MÙA VỤ THEO THÁNG (`dim_date.month`)",
        json.dumps(trends["monthly"], ensure_ascii=False, default=str),
        "",
        "## 4. PHÂN RÃ THEO LOẠI KHÁCH SẠN (`dim_hotel`)",
        json.dumps(diag["by_hotel"], ensure_ascii=False, default=str),
        "",
        "## 5. PHÂN RÃ THEO KÊNH BÁN & PHÂN KHÚC (`dim_channel`)",
        json.dumps(diag["by_market_segment"], ensure_ascii=False, default=str),
        "",
        "## 6. PHÂN RÃ THEO CHÍNH SÁCH ĐẶT CỌC (`dim_room_policy.deposit_type`)",
        json.dumps(diag["by_deposit_type"], ensure_ascii=False, default=str),
        "",
        "## 7. PHÂN RÃ THEO NHÓM THỜI GIAN ĐẶT TRƯỚC (`fact_bookings.lead_time_group`)",
        json.dumps(diag["by_lead_time_group"], ensure_ascii=False, default=str),
        "",
        "## 8. TÁC ĐỘNG CỦA NÂNG HẠNG PHÒNG & YÊU CẦU ĐẶC BIỆT",
        json.dumps(diag["by_special_requests_and_upgrade"], ensure_ascii=False, default=str),
        "",
        "## 9. TRẠNG THÁI VẬN HÀNH PIPELINE ETL (`control.etl_batch_log`)",
        f"- Tổng quan ETL: {json.dumps(etl['summary'], ensure_ascii=False, default=str)}",
        f"- Lịch sử chạy ETL gần nhất: {json.dumps(etl['recent_logs'], ensure_ascii=False, default=str)}",
    ]
    return "\n".join(lines)


def execute_safe_readonly_sql(sql_query: str) -> pd.DataFrame:
    """
    Thực thi câu lệnh SQL chỉ đọc (SELECT / WITH ... SELECT) phục vụ tính năng
    Hỏi đáp bằng ngôn ngữ tự nhiên (NL2SQL).
    Chặn tuyệt đối mọi từ khóa thay đổi dữ liệu hoặc cấu trúc DB.
    """
    cleaned = sql_query.strip().rstrip(";")
    forbidden = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|COPY|EXECUTE)\b",
        re.IGNORECASE,
    )
    if forbidden.search(cleaned):
        raise ValueError("Câu lệnh SQL bị từ chối vì chứa từ khóa không thuộc chế độ chỉ đọc (Read-only).")
    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise ValueError("Chỉ cho phép thực thi câu lệnh bắt đầu bằng SELECT hoặc WITH.")

    with get_db_connection() as conn:
        df = pd.read_sql_query(cleaned, conn)
    return df
