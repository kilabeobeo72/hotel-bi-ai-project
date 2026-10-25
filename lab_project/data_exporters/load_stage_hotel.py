from mage_ai.settings.repo import get_repo_path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from pandas import DataFrame
import os
from os import path
from datetime import datetime

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_hotel_to_stage_and_log(df: DataFrame, **kwargs) -> None:
    """
    Block 3 (Data Exporter):
    1. Nạp dữ liệu vào bảng stage.raw_hotel_bookings (hỗ trợ cả FULL và INCREMENTAL load).
    2. Ghi nhận trạng thái thực thi, số lượng bản ghi xử lý vào bảng control.etl_batch_log.
    """
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'default'

    load_mode = str(kwargs.get('load_mode') or 'FULL').strip().upper()
    batch_file = os.path.basename(str(kwargs.get('batch_file') or 'batch_01_full_2015_2016.csv'))
    if load_mode not in ('FULL', 'INCREMENTAL'):
        raise ValueError(f"load_mode không hợp lệ: '{load_mode}' (chỉ nhận FULL hoặc INCREMENTAL).")

    rows_extracted = int(df['rows_extracted_meta'].iloc[0]) if 'rows_extracted_meta' in df.columns else len(df)
    rows_rejected = int(df['rows_rejected_meta'].iloc[0]) if 'rows_rejected_meta' in df.columns else 0
    rows_valid = len(df)
    # Có dòng bị loại nhưng vẫn nạp được phần còn lại => WARNING (control.etl_batch_log cho phép giá trị này)
    success_status = 'WARNING' if rows_rejected > 0 else 'SUCCESS'

    export_df = df.drop(columns=['rows_extracted_meta', 'rows_rejected_meta'], errors='ignore')

    started_at = datetime.utcnow()
    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        try:
            if load_mode == 'FULL':
                # Mage xóa sạch bảng (DELETE, không DROP nên view dbt không bị hỏng) rồi nạp lại bằng COPY.
                # Truyền unique_constraints để lần tạo bảng đầu tiên có UNIQUE(record_hash).
                loader.export(
                    export_df,
                    schema_name='stage',
                    table_name='raw_hotel_bookings',
                    index=False,
                    if_exists='replace',
                    unique_constraints=['record_hash'],
                )
            else:
                # Incremental: INSERT ... ON CONFLICT (record_hash) DO UPDATE => bản ghi cũ được cập nhật, không nhân đôi.
                loader.export(
                    export_df,
                    schema_name='stage',
                    table_name='raw_hotel_bookings',
                    index=False,
                    if_exists='append',
                    unique_constraints=['record_hash'],
                    unique_conflict_method='UPDATE',
                )
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            # Ghi nhận kết quả thành công vào bảng control.etl_batch_log bằng câu lệnh INSERT chuẩn
            with loader.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO control.etl_batch_log (
                        pipeline_name, batch_file, load_mode,
                        rows_extracted, rows_valid, rows_rejected,
                        status, error_message, started_at, completed_at, duration_seconds
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        'hotel_ingestion_pipeline', batch_file, load_mode,
                        rows_extracted, rows_valid, rows_rejected,
                        success_status, None, started_at, completed_at, round(duration, 2)
                    )
                )
                loader.conn.commit()

        except Exception as exc:
            try:
                loader.conn.rollback()
            except Exception:
                pass
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()
            try:
                with loader.conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO control.etl_batch_log (
                            pipeline_name, batch_file, load_mode,
                            rows_extracted, rows_valid, rows_rejected,
                            status, error_message, started_at, completed_at, duration_seconds
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            'hotel_ingestion_pipeline', batch_file, load_mode,
                            rows_extracted, 0, rows_extracted,
                            'FAILED', str(exc)[:500], started_at, completed_at, round(duration, 2)
                        )
                    )
                    loader.conn.commit()
            except Exception:
                pass
            raise exc
