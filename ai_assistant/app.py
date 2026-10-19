"""
Ứng dụng AI-Assisted Analytics cho Hệ thống BI Khách sạn (Phục vụ Seminar 3 - 14/11/2026)
Phụ trách chính: Đào Trung Kiên (Backend Prompt/Context) & Thạch Ý (Streamlit UI & NL2SQL)

Chức năng:
1. Tự động tạo bản tóm tắt (AI-generated Executive Summary) từ các KPIs thật trong schema `dds`.
2. Giải thích xu hướng, biến động tỷ lệ hủy phòng dựa trên bằng chứng định lượng (0% Hallucination).
3. Cho phép người dùng đặt câu hỏi bằng ngôn ngữ tự nhiên (Text-to-SQL) để truy vấn và giải thích kết quả.
"""

import os
import streamlit as st
import pandas as pd
import psycopg2
from google import genai


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "dw_lab"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def fetch_kpi_context() -> dict:
    """Truy vấn số liệu thực tế từ kho dữ liệu dds và bảng log control."""
    conn = get_db_connection()
    kpi_sql = """
        SELECT
            h.hotel_name,
            COUNT(*) AS total_bookings,
            SUM(f.is_canceled) AS canceled_bookings,
            ROUND(100.0 * SUM(f.is_canceled) / NULLIF(COUNT(*), 0), 2) AS cancel_rate_pct,
            ROUND(AVG(f.adr), 2) AS avg_adr,
            ROUND(SUM(f.actual_revenue), 2) AS actual_revenue,
            ROUND(SUM(f.revenue_loss), 2) AS revenue_loss
        FROM dds.fact_bookings f
        JOIN dds.dim_hotel h ON f.hotel_key = h.hotel_key
        GROUP BY h.hotel_name;
    """
    diag_sql = """
        SELECT
            c.market_segment,
            p.deposit_type,
            f.lead_time_group,
            COUNT(*) AS bookings,
            ROUND(100.0 * SUM(f.is_canceled) / NULLIF(COUNT(*), 0), 2) AS cancel_rate_pct,
            ROUND(SUM(f.revenue_loss), 2) AS revenue_loss
        FROM dds.fact_bookings f
        JOIN dds.dim_channel c ON f.channel_key = c.channel_key
        JOIN dds.dim_room_policy p ON f.policy_key = p.policy_key
        GROUP BY c.market_segment, p.deposit_type, f.lead_time_group
        ORDER BY revenue_loss DESC
        LIMIT 10;
    """
    etl_sql = """
        SELECT run_id, batch_file, load_mode, rows_valid, rows_rejected, status, started_at, duration_seconds
        FROM control.etl_batch_log
        ORDER BY run_id DESC
        LIMIT 5;
    """
    with conn:
        df_kpi = pd.read_sql(kpi_sql, conn)
        df_diag = pd.read_sql(diag_sql, conn)
        df_etl = pd.read_sql(etl_sql, conn)
    conn.close()
    return {"kpi": df_kpi, "diagnostic": df_diag, "etl_log": df_etl}


st.set_page_config(page_title="Hotel BI - AI Copilot", page_icon="🏨", layout="wide")
st.title("🏨 Hệ Thống BI Khách Sạn Tích Hợp Generative AI")
st.caption("Dữ liệu được kiểm chứng trực tiếp từ Kho dữ liệu PostgreSQL (`dds` & `control`)")

api_key = os.getenv("GEMINI_API_KEY", "")
with st.sidebar:
    st.header("⚙️ Cấu hình AI")
    user_key = st.text_input("Gemini API Key", value=api_key, type="password")
    st.markdown("---")
    st.markdown("**Thành viên nhóm:**\n- Đào Trung Kiên\n- Huỳnh Võ Đại Dương\n- Phạm Ngọc Thanh\n- Thạch Ý")

tab1, tab2, tab3 = st.tabs([
    "📊 1. AI Tóm tắt KPI & Giải thích Biến động",
    "💬 2. Hỏi đáp Ngôn ngữ Tự nhiên (NL2SQL)",
    "🛠️ 3. Giám sát Lịch sử ETL (Control Log)"
])

with tab1:
    if st.button("🚀 Trích xuất KPI từ Data Warehouse & Tạo Phân tích AI", type="primary"):
        try:
            ctx = fetch_kpi_context()
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Bảng KPI Tổng hợp (từ `dds.fact_bookings`)")
                st.dataframe(ctx["kpi"], use_container_width=True)
            with col2:
                st.subheader("Top 10 Tổ hợp gây Thất thoát Doanh thu do Hủy phòng")
                st.dataframe(ctx["diagnostic"], use_container_width=True)

            if user_key:
                client = genai.Client(api_key=user_key)
                prompt = f"""
Bạn là Chuyên gia Phân tích Business Intelligence. Hãy đọc BẢNG SỐ LIỆU THỰC TẾ dưới đây từ Data Warehouse của khách sạn và viết báo cáo bằng tiếng Việt gồm:
1. Tóm tắt điều hành (AI-generated Executive Summary) về tổng lượt đặt, tỷ lệ hủy phòng, ADR, doanh thu thực thu và doanh thu mất đi ở 2 khách sạn.
2. Giải thích nguyên nhân gốc rễ (Diagnostic Explanation) tại sao tỷ lệ hủy phòng cao dựa trên bảng Top 10 tổ hợp (Market Segment, Deposit Type, Lead Time Group).
3. Đề xuất 3 giải pháp quản trị cụ thể có căn cứ định lượng.
TUYỆT ĐỐI chỉ sử dụng con số trong bảng dưới đây, không tự suy diễn số liệu ngoài:

--- BẢNG KPI ---
{ctx['kpi'].to_markdown(index=False)}

--- BẢNG PHÂN RÃ NGUYÊN NHÂN HỦY PHÒNG ---
{ctx['diagnostic'].to_markdown(index=False)}
"""
                with st.spinner("Gemini AI đang phân tích số liệu từ Data Warehouse..."):
                    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                    st.markdown("### 🤖 Báo cáo Phân tích & Giải thích từ Generative AI")
                    st.markdown(resp.text)
            else:
                st.info("Nhập Gemini API Key ở thanh bên trái để kích hoạt AI sinh báo cáo tự động.")
        except Exception as e:
            st.error(f"Không thể kết nối CSDL hoặc chưa chạy dbt: {e}")

with tab2:
    st.subheader("Đặt câu hỏi bằng Tiếng Việt trên Kho dữ liệu (`dds`)")
    question = st.text_input(
        "Nhập câu hỏi nghiệp vụ của bạn:",
        value="Top 5 quốc gia nào có doanh thu thực tế (actual_revenue) cao nhất và tỷ lệ hủy phòng của họ là bao nhiêu?"
    )
    if st.button("🔍 Truy vấn & Giải thích bằng AI") and user_key:
        client = genai.Client(api_key=user_key)
        sql_prompt = f"""
Dựa trên lược đồ Star Schema PostgreSQL thuộc schema `dds`:
- `dds.fact_bookings` (booking_id, hotel_key, customer_key, channel_key, policy_key, arrival_date_key, is_canceled, lead_time, lead_time_group, total_nights, total_guests, adr, actual_revenue, revenue_loss)
- `dds.dim_hotel` (hotel_key, hotel_name)
- `dds.dim_customer` (customer_key, country_code, customer_type, is_repeated_guest)
- `dds.dim_channel` (channel_key, market_segment, distribution_channel)
- `dds.dim_room_policy` (policy_key, reserved_room_type, assigned_room_type, meal_code, deposit_type)
- `dds.dim_date` (date_key, full_date, year, quarter, month, month_name)

Hãy chỉ trả về duy nhất 1 câu lệnh SQL PostgreSQL SELECT (không bọc trong markdown ```sql) trả lời câu hỏi: "{question}"
"""
        sql_query = client.models.generate_content(model="gemini-2.5-flash", contents=sql_prompt).text.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        st.code(sql_query, language="sql")
        try:
            conn = get_db_connection()
            df_ans = pd.read_sql(sql_query, conn)
            conn.close()
            st.dataframe(df_ans, use_container_width=True)
            explain_prompt = f"Dựa trên câu hỏi '{question}' và bảng kết quả truy vấn thực tế sau:\n{df_ans.to_markdown(index=False)}\nHãy giải thích ngắn gọn, rõ ràng kết quả này bằng tiếng Việt."
            explanation = client.models.generate_content(model="gemini-2.5-flash", contents=explain_prompt).text
            st.success(explanation)
        except Exception as e:
            st.error(f"Lỗi thực thi truy vấn: {e}")

with tab3:
    st.subheader("Lịch sử Thực thi ETL (`control.etl_batch_log`)")
    if st.button("🔄 Làm mới trạng thái ETL"):
        try:
            ctx = fetch_kpi_context()
            st.dataframe(ctx["etl_log"], use_container_width=True)
        except Exception as e:
            st.error(f"Lỗi kết nối bảng control.etl_batch_log: {e}")
