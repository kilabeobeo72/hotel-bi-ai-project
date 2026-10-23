# ==============================================================================
# File này thuộc Seminar 3 (14/11/2026): Tích hợp Generative AI.
# Ở Seminar 1 và Seminar 2, CHƯA CẦN chạy hoặc đụng tới file này.
# ==============================================================================

'''
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
'''
