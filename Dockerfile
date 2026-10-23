FROM mageai/mageai:latest

# Các thư viện phục vụ Seminar 1 (Mage.ai + dbt + PostgreSQL + Tải Kaggle)
RUN pip3 install --no-cache-dir \
    "dbt-core<1.9.0" \
    "dbt-postgres<1.9.0" \
    psycopg2-binary \
    kagglehub

# [TẠM COMMENT CHO SEMINAR 3 - 14/11/2026: Thư viện tích hợp AI & Streamlit]
# RUN pip3 install --no-cache-dir google-genai streamlit plotly
