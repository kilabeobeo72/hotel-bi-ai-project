import os
from datetime import datetime
from os import path

from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from mage_ai.settings.repo import get_repo_path
from pandas import DataFrame

from lab_project.utils.etl_log import NO_NEW_BATCH, last_status_of, utcnow, write_log

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


def _success_status(batch_file: str, rows_rejected: int) -> tuple:
    """
    Trả về (status, ghi chú) cho lần nạp thành công:
      - có dòng bị loại                    => WARNING
      - sạch, nhưng lần chạy trước của chính batch này là FAILED => RETRY_SUCCESS (chạy lại sau khi sửa lỗi)
      - còn lại                            => SUCCESS
    """
    retried = last_status_of(batch_file) == 'FAILED'
    if rows_rejected > 0:
        return 'WARNING', ('Chạy lại sau lần FAILED trước. ' if retried else '') + f'Đã loại {rows_rejected} dòng lỗi giá trị.'
    if retried:
        return 'RETRY_SUCCESS', 'Chạy lại thành công sau lần FAILED trước đó.'
    return 'SUCCESS', None


@data_exporter
def export_hotel_to_stage_and_log(df: DataFrame, **kwargs) -> dict:
    """
    Block 3 (Data Exporter):
    1. Nạp dữ liệu vào stage.raw_hotel_bookings (hỗ trợ cả FULL và INCREMENTAL load).
    2. Ghi nhận trạng thái, số dòng xử lý và tổng thời gian chạy vào control.etl_batch_log.
    3. Trả về dict tóm tắt cho block dbt phía sau (rows_loaded = 0 => dbt bỏ qua).
    """
    # --- Không có batch mới (chế độ AUTO) ---
    if len(df) == 0:
        now = utcnow()
        write_log(NO_NEW_BATCH, 'INCREMENTAL', 0, 0, 0, 'SUCCESS',
                  'Không có batch mới trong data/ cần nạp.', now, now)
        print('[load_stage_hotel] Không có batch mới, không nạp gì.')
        return {'rows_loaded': 0, 'batch_file': NO_NEW_BATCH, 'load_mode': 'INCREMENTAL', 'status': 'SUCCESS'}

    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'default'

    batch_file = os.path.basename(str(df['batch_file'].iloc[0]))
    load_mode = str(df['load_mode_meta'].iloc[0]).strip().upper() if 'load_mode_meta' in df.columns \
        else str(kwargs.get('load_mode') or 'FULL').strip().upper()
    if load_mode not in ('FULL', 'INCREMENTAL'):
        raise ValueError(f"load_mode không hợp lệ: '{load_mode}' (chỉ nhận FULL hoặc INCREMENTAL).")

    try:
        run_started = datetime.fromisoformat(str(df['run_started_meta'].iloc[0]))
    except Exception:
        run_started = utcnow()

    rows_extracted = int(df['rows_extracted_meta'].iloc[0]) if 'rows_extracted_meta' in df.columns else len(df)
    rows_rejected = int(df['rows_rejected_meta'].iloc[0]) if 'rows_rejected_meta' in df.columns else 0
    rows_valid = len(df)

    export_df = df.drop(
        columns=['rows_extracted_meta', 'rows_rejected_meta', 'load_mode_meta', 'run_started_meta'],
        errors='ignore',
    )

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
        except Exception as exc:
            write_log(batch_file, load_mode, rows_extracted, 0, rows_extracted, 'FAILED',
                      str(exc), run_started)
            raise

    status, note = _success_status(batch_file, rows_rejected)
    write_log(batch_file, load_mode, rows_extracted, rows_valid, rows_rejected, status, note, run_started)
    print(f'[load_stage_hotel] {batch_file} | {load_mode} | đọc {rows_extracted:,} | nạp {rows_valid:,} | '
          f'loại {rows_rejected:,} | {status}')
    return {'rows_loaded': rows_valid, 'batch_file': batch_file, 'load_mode': load_mode, 'status': status}
