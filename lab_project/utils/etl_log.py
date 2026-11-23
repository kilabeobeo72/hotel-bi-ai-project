"""
Tiện ích dùng chung cho các block Mage: kết nối PostgreSQL và ghi/đọc control.etl_batch_log.

Import trong block:  from lab_project.utils.etl_log import write_log, ...
(Mage đưa thư mục cha của project vào sys.path nên import theo tên thư mục project là dùng được.)
"""
import os
from datetime import datetime
from typing import Optional, Set

import psycopg2

LOG_TABLE = 'control.etl_batch_log'
SUCCESS_STATUSES = ('SUCCESS', 'WARNING', 'RETRY_SUCCESS')
NO_NEW_BATCH = 'AUTO: không có batch mới'


def get_connection():
    return psycopg2.connect(
        host=os.environ.get('POSTGRES_HOST', 'postgres'),
        port=int(os.environ.get('POSTGRES_PORT', '5432')),
        dbname=os.environ.get('POSTGRES_DB', 'dw_lab'),
        user=os.environ.get('POSTGRES_USER', 'postgres'),
        password=os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        connect_timeout=10,
    )


def utcnow() -> datetime:
    return datetime.utcnow()


def write_log(
    batch_file: str,
    load_mode: str,
    rows_extracted: int,
    rows_valid: int,
    rows_rejected: int,
    status: str,
    error_message: Optional[str],
    started_at: datetime,
    completed_at: Optional[datetime] = None,
    pipeline_name: str = 'hotel_ingestion_pipeline',
) -> bool:
    """Ghi một dòng vào control.etl_batch_log. Không bao giờ raise (log lỗi không được che lỗi gốc)."""
    completed_at = completed_at or utcnow()
    duration = round((completed_at - started_at).total_seconds(), 2)
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {LOG_TABLE} (
                        pipeline_name, batch_file, load_mode,
                        rows_extracted, rows_valid, rows_rejected,
                        status, error_message, started_at, completed_at, duration_seconds
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (pipeline_name, batch_file, load_mode, int(rows_extracted), int(rows_valid),
                     int(rows_rejected), status, (error_message or None) and str(error_message)[:1000],
                     started_at, completed_at, duration),
                )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f'[etl_log] Không ghi được {LOG_TABLE}: {exc}')
        return False


def loaded_batches() -> Set[str]:
    """Các batch đã nạp xong (log gần nhất của batch đó là SUCCESS / WARNING / RETRY_SUCCESS)."""
    sql = f"""
        SELECT batch_file
        FROM (
            SELECT DISTINCT ON (batch_file) batch_file, status
            FROM {LOG_TABLE}
            WHERE pipeline_name = 'hotel_ingestion_pipeline'
            ORDER BY batch_file, run_id DESC
        ) last_run
        WHERE status IN %s;
    """
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (SUCCESS_STATUSES,))
                return {r[0] for r in cur.fetchall()}
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f'Không đọc được {LOG_TABLE} để chọn batch cần nạp: {exc}') from exc


def last_status_of(batch_file: str) -> Optional[str]:
    """Trạng thái của lần chạy gần nhất cho batch này (None nếu chưa từng chạy hoặc không đọc được log)."""
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT status FROM {LOG_TABLE} "
                    "WHERE pipeline_name = 'hotel_ingestion_pipeline' AND batch_file = %s "
                    "ORDER BY run_id DESC LIMIT 1;",
                    (batch_file,),
                )
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f'[etl_log] Không đọc được trạng thái cũ của {batch_file}: {exc}')
        return None
