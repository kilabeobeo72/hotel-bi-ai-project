import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_assistant.db_context import (
    fetch_diagnostic_breakdowns,
    fetch_etl_batch_logs,
    fetch_kpi_overview,
    fetch_yearly_and_monthly_trends,
)
from ai_assistant.prompts import (
    DEFAULT_GEMINI_MODEL,
    answer_natural_language_query,
    explain_anomaly_and_trends,
    generate_executive_summary,
    inspect_etl_health,
)

st.set_page_config(
    page_title="Hotel BI & AI Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        html, body, [class*="css"] {
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            color: #0f172a;
        }
        .stApp {
            background-color: #f8fafc;
        }
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }
        .stDeployButton, footer, #MainMenu {
            visibility: hidden;
        }
        .main-header {
            background-color: #ffffff;
            padding: 20px 24px;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
            margin-bottom: 16px;
        }
        .main-header h1 {
            font-size: 24px;
            font-weight: 600;
            color: #0f172a;
            margin: 0 0 4px 0;
            padding: 0;
        }
        .main-header p {
            font-size: 13.5px;
            color: #475569;
            margin: 0;
        }
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 14px 16px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
        }
        div[data-testid="stMetricLabel"] {
            font-size: 12.5px !important;
            font-weight: 600 !important;
            color: #64748b !important;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
        div[data-testid="stMetricValue"] {
            font-size: 24px !important;
            font-weight: 700 !important;
            color: #0f172a !important;
        }
        button[data-baseweb="tab"] {
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #475569 !important;
            padding: 10px 20px !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #1e3a8a !important;
            border-bottom-color: #1e3a8a !important;
        }
        .stButton > button[kind="primary"] {
            background-color: #1e3a8a;
            color: #ffffff;
            border: 1px solid #1e3a8a;
            border-radius: 5px;
            font-weight: 600;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #172554;
            border-color: #172554;
            color: #ffffff;
        }
        .stButton > button[kind="secondary"] {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 5px;
            font-weight: 500;
        }
        .stButton > button[kind="secondary"]:hover {
            border-color: #1e3a8a;
            color: #1e3a8a;
        }
        .panel-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 18px 20px;
            margin-top: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="main-header">
        <h1>Hotel Booking BI & AI-Assisted Analytics</h1>
        <p>Hệ thống phân tích dữ liệu đa chiều và giải thích kết quả bằng Generative AI kết nối trực tiếp PostgreSQL Data Warehouse (dds & control)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Cấu hình hệ thống")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        type="password",
        placeholder="Nhập API Key (hoặc dùng từ file .env)",
    )
    st.caption(f"Model: {DEFAULT_GEMINI_MODEL}")
    st.divider()

    st.subheader("Bộ lọc dữ liệu (dds)")
    selected_year_label = st.selectbox(
        "Năm lưu trú (Year)",
        options=["Tất cả", "2015", "2016", "2017"],
        index=0,
    )
    selected_hotel_label = st.selectbox(
        "Loại khách sạn (Hotel)",
        options=["Tất cả", "City Hotel", "Resort Hotel"],
        index=0,
    )
    selected_segment_label = st.selectbox(
        "Phân khúc thị trường (Market Segment)",
        options=[
            "Tất cả",
            "Online TA",
            "Offline TA/TO",
            "Groups",
            "Direct",
            "Corporate",
            "Complementary",
            "Aviation",
        ],
        index=0,
    )

    year_filter = None if selected_year_label == "Tất cả" else int(selected_year_label)
    hotel_filter = None if selected_hotel_label == "Tất cả" else selected_hotel_label
    segment_filter = None if selected_segment_label == "Tất cả" else selected_segment_label
    effective_api_key = api_key_input.strip() if api_key_input.strip() else None

try:
    kpis = fetch_kpi_overview(
        year=year_filter,
        hotel_name=hotel_filter,
        market_segment=segment_filter,
    )
    db_connected = True
except Exception as db_err:
    db_connected = False
    kpis = {}
    st.error(f"Không thể kết nối PostgreSQL Data Warehouse: {db_err}")

if db_connected and kpis:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Bookings", f"{int(kpis.get('total_bookings', 0)):,}")
    c2.metric("Cancellation Rate", f"{kpis.get('cancellation_rate_pct', 0)}%")
    c3.metric("Actual Revenue", f"${float(kpis.get('actual_revenue', 0)):,.0f}")
    c4.metric("Revenue Loss", f"${float(kpis.get('revenue_loss', 0)):,.0f}")
    c5.metric("ADR", f"${kpis.get('avg_adr', 0)}")
    c6.metric("Avg Lead Time", f"{kpis.get('avg_lead_time_days', 0)} ngày")

st.write("")

tab1, tab2, tab3 = st.tabs([
    "Tóm tắt điều hành & Chẩn đoán biến động",
    "Truy vấn dữ liệu bằng ngôn ngữ tự nhiên (NL2SQL)",
    "Giám sát & Chẩn đoán nhật ký ETL",
])

with tab1:
    if not db_connected:
        st.warning("Vui lòng khởi chạy container PostgreSQL (docker compose up -d) để tải dữ liệu.")
    else:
        trends = fetch_yearly_and_monthly_trends(
            year=year_filter,
            hotel_name=hotel_filter,
            market_segment=segment_filter,
        )
        diag = fetch_diagnostic_breakdowns(
            year=year_filter,
            hotel_name=hotel_filter,
            market_segment=segment_filter,
        )

        with st.expander("Bảng số liệu Grounded Context trích xuất từ Data Warehouse (dds)", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**1. Xu hướng theo Năm (dim_date.year)**")
                st.dataframe(pd.DataFrame(trends["yearly"]), use_container_width=True, hide_index=True)
                st.markdown("**2. Phân rã theo Chính sách Đặt cọc (deposit_type)**")
                st.dataframe(pd.DataFrame(diag["by_deposit_type"]), use_container_width=True, hide_index=True)
            with col_b:
                st.markdown("**3. Phân rã theo Nhóm Thời gian Đặt trước (lead_time_group)**")
                st.dataframe(pd.DataFrame(diag["by_lead_time_group"]), use_container_width=True, hide_index=True)
                st.markdown("**4. Phân rã theo Kênh bán (market_segment)**")
                st.dataframe(pd.DataFrame(diag["by_market_segment"]), use_container_width=True, hide_index=True)

        left_col, right_col = st.columns(2, gap="large")

        with left_col:
            st.markdown("#### 1. Bản tóm tắt điều hành (AI Executive Summary)")
            st.caption(
                "Tổng hợp bức tranh kinh doanh khách sạn từ các chỉ số KPIs thực tế "
                "trong tầng dds và trạng thái vận hành pipeline ETL mới nhất."
            )
            if st.button("Tạo bản tóm tắt điều hành", type="primary", use_container_width=True):
                with st.spinner("Đang truy xuất Grounded Context và tổng hợp báo cáo..."):
                    try:
                        summary_md = generate_executive_summary(
                            year=year_filter,
                            hotel_name=hotel_filter,
                            market_segment=segment_filter,
                            api_key=effective_api_key,
                        )
                        st.session_state["ai_exec_summary"] = summary_md
                    except Exception as exc:
                        st.error(f"Lỗi khi gọi Gemini API: {exc}")

            if "ai_exec_summary" in st.session_state:
                with st.container(border=True):
                    st.markdown(st.session_state["ai_exec_summary"])
                st.download_button(
                    label="Tải bản tóm tắt (.md)",
                    data=st.session_state["ai_exec_summary"],
                    file_name="AI_Executive_Summary.md",
                    mime="text/markdown",
                )

        with right_col:
            st.markdown("#### 2. Giải thích biến động & Chẩn đoán hủy phòng")
            focus_slice = st.selectbox(
                "Chọn nội dung cần phân tích nguyên nhân",
                options=[
                    "Toàn hệ thống: Nguyên nhân tỷ lệ hủy phòng 37.19% và thất thoát $16.78M",
                    "Tác động của Thời gian đặt trước (Lead Time Group) đến rủi ro hủy phòng",
                    "Nghịch lý kênh Online TA và phân khúc khách đoàn (Groups)",
                    "Hiệu quả của Chính sách đặt cọc (No Deposit vs Non Refund)",
                    "Biến động mùa vụ cao điểm Hè (Tháng 7-8) vs giao mùa (Tháng 4-6)",
                    "Tác động của Yêu cầu đặc biệt & Nâng hạng phòng đến tỷ lệ giữ chân khách",
                ],
            )
            custom_focus_q = st.text_input(
                "Yêu cầu phân tích chi tiết (tùy chọn)",
                placeholder="Ví dụ: Đề xuất ngưỡng lead_time để áp dụng đặt cọc cho kênh Online TA",
            )
            if st.button("Phân tích nguyên nhân & Đề xuất giải pháp", type="primary", use_container_width=True):
                with st.spinner("Đang phân tích dữ liệu đa chiều..."):
                    try:
                        diag_md = explain_anomaly_and_trends(
                            focus_slice=focus_slice,
                            year=year_filter,
                            hotel_name=hotel_filter,
                            market_segment=segment_filter,
                            user_question=custom_focus_q.strip() or None,
                            api_key=effective_api_key,
                        )
                        st.session_state["ai_diag_explanation"] = diag_md
                    except Exception as exc:
                        st.error(f"Lỗi khi gọi Gemini API: {exc}")

            if "ai_diag_explanation" in st.session_state:
                with st.container(border=True):
                    st.markdown(st.session_state["ai_diag_explanation"])
                st.download_button(
                    label="Tải báo cáo chẩn đoán (.md)",
                    data=st.session_state["ai_diag_explanation"],
                    file_name="AI_Diagnostic_Analysis.md",
                    mime="text/markdown",
                )

with tab2:
    st.markdown("#### Truy vấn kho dữ liệu bằng ngôn ngữ tự nhiên (Text-to-SQL)")
    st.caption(
        "Nhập câu hỏi bằng tiếng Việt. Hệ thống tự động sinh câu lệnh PostgreSQL SELECT chỉ đọc "
        "trên schema dds / control, thực thi lấy bảng số liệu thực tế và giải thích kết quả."
    )

    sample_questions = [
        "Top 5 quốc gia có doanh thu thực tế (actual_revenue) cao nhất ở Resort Hotel năm 2017?",
        "So sánh tổng số đơn, tỷ lệ hủy phòng và doanh thu thất thoát giữa các nhóm lead_time_group?",
        "Phân khúc thị trường (market_segment) nào có tỷ lệ hủy phòng cao nhất và làm mất bao nhiêu doanh thu?",
        "So sánh doanh thu thực tế, ADR và tỷ lệ hủy phòng giữa City Hotel và Resort Hotel qua từng năm 2015, 2016, 2017?",
    ]

    st.markdown("**Câu hỏi mẫu tham khảo:**")
    q_cols = st.columns(2)
    for idx, sq in enumerate(sample_questions):
        if q_cols[idx % 2].button(sq, key=f"sample_q_{idx}", use_container_width=True):
            st.session_state["nl2sql_input"] = sq

    user_nl_question = st.text_input(
        "Nội dung câu hỏi truy vấn",
        value=st.session_state.get("nl2sql_input", sample_questions[0]),
    )

    if st.button("Thực thi truy vấn & Giải thích kết quả", type="primary"):
        if not user_nl_question.strip():
            st.warning("Vui lòng nhập câu hỏi cần truy vấn.")
        else:
            with st.spinner("Đang sinh câu lệnh SQL, truy vấn PostgreSQL và diễn giải kết quả..."):
                try:
                    nl_result = answer_natural_language_query(
                        question=user_nl_question.strip(),
                        api_key=effective_api_key,
                    )
                    st.session_state["nl2sql_result"] = nl_result
                except Exception as exc:
                    st.error(f"Không thể thực hiện truy vấn: {exc}")

    if "nl2sql_result" in st.session_state:
        res = st.session_state["nl2sql_result"]
        col_sql, col_df = st.columns([1, 1], gap="large")
        with col_sql:
            st.markdown("**1. Câu lệnh SQL đã thực thi (Read-only)**")
            st.code(res["sql"], language="sql")
        with col_df:
            st.markdown("**2. Bảng dữ liệu kết quả từ PostgreSQL Data Warehouse**")
            st.dataframe(res["dataframe"], use_container_width=True, hide_index=True)

        st.markdown("**3. Giải thích & Nhận định từ AI**")
        with st.container(border=True):
            st.markdown(res["explanation"])

with tab3:
    st.markdown("#### Giám sát & Chẩn đoán nhật ký thực thi ETL (control.etl_batch_log)")
    if not db_connected:
        st.warning("Không thể đọc bảng control.etl_batch_log khi chưa kết nối PostgreSQL.")
    else:
        etl_info = fetch_etl_batch_logs(limit=20)
        summary = etl_info.get("summary", {})
        logs = etl_info.get("recent_logs", [])

        e1, e2, e3, e4, e5 = st.columns(5)
        e1.metric("Total ETL Runs", f"{int(summary.get('total_runs', 0))}")
        e2.metric("Success Rate", f"{summary.get('success_rate_pct', 0)}%")
        e3.metric("Total Valid Rows", f"{int(summary.get('total_rows_valid', 0)):,}")
        e4.metric("Rejected Rows", f"{int(summary.get('total_rows_rejected', 0)):,}")
        e5.metric("Avg Duration", f"{summary.get('avg_duration_seconds', 0)}s")

        st.write("")
        st.markdown("**Bảng nhật ký chi tiết các lần chạy Pipeline (control.etl_batch_log)**")
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
        else:
            st.info("Bảng control.etl_batch_log hiện chưa có bản ghi nào.")

        if st.button("Phân tích nhật ký ETL & Chẩn đoán sự cố", type="primary"):
            with st.spinner("Đang phân tích nhật ký control.etl_batch_log..."):
                try:
                    etl_report = inspect_etl_health(api_key=effective_api_key)
                    st.session_state["ai_etl_report"] = etl_report
                except Exception as exc:
                    st.error(f"Lỗi khi gọi Gemini API: {exc}")

        if "ai_etl_report" in st.session_state:
            with st.container(border=True):
                st.markdown(st.session_state["ai_etl_report"])
