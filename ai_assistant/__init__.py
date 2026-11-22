"""
Package `ai_assistant`: Core Generative AI Engine & Grounded DB Context (Seminar 3).
"""

from ai_assistant.db_context import (
    build_grounded_context_markdown,
    execute_safe_readonly_sql,
    fetch_diagnostic_breakdowns,
    fetch_etl_batch_logs,
    fetch_kpi_overview,
    fetch_yearly_and_monthly_trends,
    get_db_connection,
)
from ai_assistant.prompts import (
    DEFAULT_GEMINI_MODEL,
    GROUNDED_SYSTEM_INSTRUCTION,
    answer_natural_language_query,
    explain_anomaly_and_trends,
    generate_executive_summary,
    inspect_etl_health,
)

__all__ = [
    "DEFAULT_GEMINI_MODEL",
    "GROUNDED_SYSTEM_INSTRUCTION",
    "get_db_connection",
    "fetch_kpi_overview",
    "fetch_yearly_and_monthly_trends",
    "fetch_diagnostic_breakdowns",
    "fetch_etl_batch_logs",
    "build_grounded_context_markdown",
    "execute_safe_readonly_sql",
    "generate_executive_summary",
    "explain_anomaly_and_trends",
    "answer_natural_language_query",
    "inspect_etl_health",
]
