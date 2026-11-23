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
    page_title="Hotel BI & AI Copilot",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏨 Hotel Booking BI & AI-Assisted Analytics Copilot")
st.caption(
    "Hệ thống phân tích Business Intelligence kết hợp Generative AI (Google Gemini API) "
    "truy xuất trực tiếp từ PostgreSQL Data Warehouse (`dds` & `control`) – Cam kết 0% Hallucination."
)

with st.sidebar:
    st.header("⚙️ Cấu hình & Bộ lọc Đa chiều")
    api_key_input = st.text_input(
        "Google Gemini API Key (để trống nếu đã khai báo trong .env):",
        type="password",
        placeholder="AIzaSy...",
    )
    st.caption(f"Model mặc định: `{DEFAULT_GEMINI_MODEL}`")
    st.divider()

    st.subheader("🔍 Bộ lọc Dữ liệu (`dds`)")
    selected_year_label = st.selectbox(
        "Năm lưu trú (Year):",
        options=["Tất cả", "2015", "2016", "2017"],
        index=0,
    )
    selected_hotel_label = st.selectbox(
        "Loại khách sạn (Hotel):",
        options=["Tất cả", "City Hotel", "Resort Hotel"],
        index=0,
    )
    selected_segment_label = st.selectbox(
        "Phân khúc thị trường (Market Segment):",
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
    c5.metric("ADR (Avg Daily Rate)", f"${kpis.get('avg_adr', 0)}")
    c6.metric("Avg Lead Time", f"{kpis.get('avg_lead_time_days', 0)} ngày")

st.divider()

tab1, tab2, tab3 = st.tabs([
    "📊 Tab 1: AI Executive Summary & Anomaly Explainer",
    "💬 Tab 2: Hỏi đáp Ngôn ngữ Tự nhiên (NL2SQL)",
    "🛠️ Tab 3: AI ETL Log Inspector (control)",
])

with tab1:
    if not db_connected:
        st.warning("Vui lòng khởi chạy container PostgreSQL (`docker compose up -d`) để tải dữ liệu.")
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

        with st.expander("📋 Xem các bảng số liệu Grounded Context trích xuất từ Data Warehouse (`dds`)", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**1. Xu hướng theo Năm (`dim_date.year`)**")
                st.dataframe(pd.DataFrame(trends["yearly"]), use_container_width=True)
                st.markdown("**2. Phân rã theo Chính sách Đặt cọc (`deposit_type`)**")
                st.dataframe(pd.DataFrame(diag["by_deposit_type"]), use_container_width=True)
            with col_b:
                st.markdown("**3. Phân rã theo Nhóm Thời gian Đặt trước (`lead_time_group`)**")
                st.dataframe(pd.DataFrame(diag["by_lead_time_group"]), use_container_width=True)
                st.markdown("**4. Phân rã theo Kênh bán (`market_segment`)**")
                st.dataframe(pd.DataFrame(diag["by_market_segment"]), use_container_width=True)

        left_col, right_col = st.columns(2)

        with left_col:
            st.subheader("1️⃣ Bản Tóm Tắt Điều Hành (AI Executive Summary)")
            st.write(
                "Tự động tổng hợp bức tranh kinh doanh khách sạn từ các chỉ số KPIs thực tế "
                "trong `dds` và trạng thái vận hành pipeline ETL mới nhất."
            )
            if st.button("✨ Tạo Bản Tóm Tắt Điều Hành bằng AI", type="primary", use_container_width=True):
                with st.spinner("Đang truy xuất Grounded Context từ DB và tổng hợp bằng Gemini..."):
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
                st.markdown(st.session_state["ai_exec_summary"])
                st.download_button(
                    label="📥 Tải Bản Tóm Tắt (.md)",
                    data=st.session_state["ai_exec_summary"],
                    file_name="AI_Executive_Summary.md",
                    mime="text/markdown",
                )

        with right_col:
            st.subheader("2️⃣ Giải Thích Biến Động & Chẩn Đoán Hủy Phòng")
            focus_slice = st.selectbox(
                "Chọn lát cắt / vấn đề trên Dashboard cần AI giải thích:",
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
                "Câu hỏi bổ sung cho lát cắt trên (tùy chọn):",
                placeholder="Ví dụ: Đề xuất ngưỡng lead_time để áp dụng đặt cọc cho kênh Online TA...",
            )
            if st.button("🔍 Phân Tích Nguyên Nhân & Đề Xuất Giải Pháp", use_container_width=True):
                with st.spinner("Đang phân tích bảng phân rã đa chiều bằng Gemini..."):
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
                st.markdown(st.session_state["ai_diag_explanation"])
                st.download_button(
                    label="📥 Tải Báo Cáo Chẩn Đoán (.md)",
                    data=st.session_state["ai_diag_explanation"],
                    file_name="AI_Diagnostic_Analysis.md",
                    mime="text/markdown",
                )

with tab2:
    st.subheader("💬 Hỏi đáp Dữ liệu bằng Ngôn ngữ Tự nhiên (Natural Language to SQL)")
    st.write(
        "Nhập câu hỏi bằng tiếng Việt. Hệ thống AI sẽ tự động chuyển thành câu lệnh PostgreSQL `SELECT` "
        "an toàn trên schema `dds` / `control`, thực thi lấy bảng số liệu thật và diễn giải kết quả."
    )

    sample_questions = [
        "Top 5 quốc gia có doanh thu thực tế (actual_revenue) cao nhất ở Resort Hotel năm 2017?",
        "So sánh tổng số đơn, tỷ lệ hủy phòng và doanh thu thất thoát giữa các nhóm lead_time_group?",
        "Phân khúc thị trường (market_segment) nào có tỷ lệ hủy phòng cao nhất và làm mất bao nhiêu doanh thu?",
        "So sánh doanh thu thực tế, ADR và tỷ lệ hủy phòng giữa City Hotel và Resort Hotel qua từng năm 2015, 2016, 2017?",
    ]

    st.caption("💡 Gợi ý câu hỏi nhanh:")
    q_cols = st.columns(2)
    for idx, sq in enumerate(sample_questions):
        if q_cols[idx % 2].button(sq, key=f"sample_q_{idx}", use_container_width=True):
            st.session_state["nl2sql_input"] = sq

    user_nl_question = st.text_input(
        "Nhập câu hỏi truy vấn của bạn:",
        value=st.session_state.get("nl2sql_input", sample_questions[0]),
    )

    if st.button("🚀 Truy vấn Data Warehouse & Giải thích", type="primary"):
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
        st.markdown("#### 1. Câu lệnh SQL Kiểm chứng (Read-only trên `dds` / `control`)")
        st.code(res["sql"], language="sql")

        st.markdown("#### 2. Bảng Kết quả Thực tế từ PostgreSQL Data Warehouse")
        st.dataframe(res["dataframe"], use_container_width=True)

        st.markdown("#### 3. Giải thích & Nhận định từ AI")
        st.markdown(res["explanation"])

with tab3:
    st.subheader("🛠️ Giám sát & Chẩn đoán Nhật ký ETL (`control.etl_batch_log`)")
    if not db_connected:
        st.warning("Không thể đọc bảng `control.etl_batch_log` khi chưa kết nối PostgreSQL.")
    else:
        etl_info = fetch_etl_batch_logs(limit=20)
        summary = etl_info.get("summary", {})
        logs = etl_info.get("recent_logs", [])

        e1, e2, e3, e4, e5 = st.columns(5)
        e1.metric("Tổng số lần chạy ETL", f"{int(summary.get('total_runs', 0))}")
        e2.metric("Tỷ lệ Thành công", f"{summary.get('success_rate_pct', 0)}%")
        e3.metric("Tổng dòng Hợp lệ", f"{int(summary.get('total_rows_valid', 0)):,}")
        e4.metric("Tổng dòng Bị loại", f"{int(summary.get('total_rows_rejected', 0)):,}")
        e5.metric("Thời gian chạy TB", f"{summary.get('avg_duration_seconds', 0)}s")

        st.markdown("#### Lịch sử các lần chạy Pipeline gần nhất (`control.etl_batch_log`)")
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True)
        else:
            st.info("Bảng `control.etl_batch_log` hiện chưa có bản ghi nào.")

        if st.button("🩺 Phân tích Sức khỏe ETL & Gợi ý Khắc phục Sự cố bằng AI", type="primary"):
            with st.spinner("Đang phân tích nhật ký `control.etl_batch_log` bằng Gemini..."):
                try:
                    etl_report = inspect_etl_health(api_key=effective_api_key)
                    st.session_state["ai_etl_report"] = etl_report
                except Exception as exc:
                    st.error(f"Lỗi khi gọi Gemini API: {exc}")

        if "ai_etl_report" in st.session_state:
            st.markdown(st.session_state["ai_etl_report"])
