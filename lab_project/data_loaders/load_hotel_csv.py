import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from lab_project.utils.etl_log import loaded_batches, utcnow, write_log

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

# Thư mục data/ của repo được mount vào container tại /home/src/data (compose.yaml: .:/home/src)
DATA_DIR = os.environ.get('HOTEL_DATA_DIR', '/home/src/data')

# PHẢI đồng bộ với MUTABLE_COLS / EXPECTED_COLUMNS trong data/split_batches.py
MUTABLE_COLS = ['is_canceled', 'reservation_status', 'reservation_status_date']
ALL_COLUMNS = [
    'hotel', 'is_canceled', 'lead_time', 'arrival_date_year', 'arrival_date_month',
    'arrival_date_week_number', 'arrival_date_day_of_month', 'stays_in_weekend_nights',
    'stays_in_week_nights', 'adults', 'children', 'babies', 'meal', 'country',
    'market_segment', 'distribution_channel', 'is_repeated_guest', 'previous_cancellations',
    'previous_bookings_not_canceled', 'reserved_room_type', 'assigned_room_type',
    'booking_changes', 'deposit_type', 'agent', 'company', 'days_in_waiting_list',
    'customer_type', 'adr', 'required_car_parking_spaces', 'total_of_special_requests',
    'reservation_status', 'reservation_status_date',
]
IDENTITY_COLS = [c for c in ALL_COLUMNS if c not in MUTABLE_COLS]

# Batch hợp lệ để lập lịch tự động: batch_<số>_full_*.csv hoặc batch_<số>_inc_*.csv
# (các file kiểm thử batch_04_corrupted_test / batch_05_bad_schema KHÔNG khớp nên không bao giờ bị tự động nạp)
AUTO_PATTERN = re.compile(r'^batch_\d+_(full|inc)_.+\.csv$', re.IGNORECASE)
AUTO_VALUES = ('', 'AUTO')


def _md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def compute_record_hash(raw: pd.DataFrame) -> pd.Series:
    """
    record_hash = MD5(các cột định danh + số thứ tự xuất hiện trong file).
      - Định danh = mọi cột TRỪ is_canceled, reservation_status, reservation_status_date
        (các cột trạng thái có thể đổi theo thời gian) => cùng một đơn đặt phòng xuất hiện lại ở
        batch sau với trạng thái mới sẽ có CÙNG hash => Incremental Load cập nhật thay vì nhân đôi.
      - Số thứ tự xuất hiện => các dòng trùng hoàn toàn trong dataset gốc (hợp lệ) vẫn có hash
        khác nhau và được giữ lại, không bị gộp nhầm.
    Hash tính trên văn bản gốc của CSV (raw, toàn bộ là chuỗi) nên không phụ thuộc kiểu dữ liệu
    mà pandas suy luận cho từng file.
    """
    base = raw[IDENTITY_COLS].agg('|'.join, axis=1).map(_md5)
    occurrence = base.groupby(base).cumcount()
    return (base + '#' + occurrence.astype(str)).map(_md5)


def infer_load_mode(batch_file: str) -> str:
    return 'FULL' if '_full_' in batch_file.lower() else 'INCREMENTAL'


def pick_next_batch() -> str:
    """
    Chế độ AUTO (dùng cho trigger lập lịch): quét thư mục data/, chọn batch đầu tiên (theo tên)
    chưa được nạp thành công. Batch có lần chạy gần nhất là FAILED vẫn được coi là chưa nạp
    => lần chạy lịch kế tiếp tự động thử lại. Trả về '' nếu không còn batch mới.
    """
    candidates = sorted(p.name for p in Path(DATA_DIR).glob('batch_*.csv') if AUTO_PATTERN.match(p.name))
    done = loaded_batches()
    pending = [c for c in candidates if c not in done]
    print(f'[load_hotel_csv] AUTO: {len(candidates)} batch trong data/, đã nạp {len(done)}, còn chờ {pending}')
    return pending[0] if pending else ''


def empty_result(run_started: datetime) -> pd.DataFrame:
    """DataFrame rỗng báo hiệu 'không có batch mới' cho các block phía sau."""
    df = pd.DataFrame({c: pd.Series(dtype='object') for c in
                       ALL_COLUMNS + ['batch_file', 'ingested_at', 'record_hash', 'booking_uid']})
    df['load_mode_meta'] = pd.Series(dtype='object')
    df['run_started_meta'] = pd.Series(dtype='object')
    return df


@data_loader
def load_hotel_from_csv(*args, **kwargs):
    """
    Block 1 (Data Loader): Đọc dữ liệu Hotel Booking từ file CSV trong thư mục /home/src/data.
    Runtime Variables:
      - batch_file: tên file CSV cần nạp, hoặc 'AUTO' (mặc định) để tự chọn batch mới chưa nạp.
      - load_mode:  'FULL' | 'INCREMENTAL' | 'AUTO' (mặc định: suy ra từ tên file, *_full_* => FULL).
    Gắn thêm cột metadata: batch_file, ingested_at, record_hash, booking_uid (= record_hash,
    để tương thích với stg_hotel_bookings.sql đang dùng booking_uid làm khóa) và hai cột điều phối
    load_mode_meta / run_started_meta (block exporter dùng rồi bỏ đi).
    """
    run_started = utcnow()
    requested_file = str(kwargs.get('batch_file') or '').strip()
    requested_mode = str(kwargs.get('load_mode') or '').strip().upper()
    if requested_mode not in ('FULL', 'INCREMENTAL') + AUTO_VALUES:
        raise ValueError(f"load_mode không hợp lệ: '{requested_mode}' (chỉ nhận FULL, INCREMENTAL hoặc AUTO).")

    if requested_file.upper() in AUTO_VALUES:
        batch_file = pick_next_batch()
        if not batch_file:
            print('[load_hotel_csv] Không có batch mới cần nạp.')
            return empty_result(run_started)
    else:
        batch_file = os.path.basename(requested_file)
    load_mode = requested_mode if requested_mode in ('FULL', 'INCREMENTAL') else infer_load_mode(batch_file)

    file_path = Path(DATA_DIR) / batch_file
    if not file_path.exists():
        msg = f'Không tìm thấy file batch: {file_path}'
        write_log(batch_file, load_mode, 0, 0, 0, 'FAILED', msg, run_started)
        raise FileNotFoundError(msg)

    try:
        # Bản chuỗi gốc: chỉ dùng để tính hash ổn định.
        raw = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        # Bản có kiểu: cột số là int/float, 'NULL' / 'NA' thành NULL => stage lưu đúng kiểu cho dbt.
        df = pd.read_csv(file_path)
    except Exception as exc:
        write_log(batch_file, load_mode, 0, 0, 0, 'FAILED', f'Không đọc được file CSV: {exc}', run_started)
        raise

    if all(c in raw.columns for c in IDENTITY_COLS):
        df['record_hash'] = compute_record_hash(raw).to_numpy()
    else:
        # Thiếu cột định danh: để block validate báo lỗi cấu trúc rõ ràng thay vì lỗi KeyError.
        df['record_hash'] = None
    df['booking_uid'] = df['record_hash']

    df['batch_file'] = batch_file
    df['ingested_at'] = datetime.now(timezone.utc).replace(tzinfo=None)
    df['load_mode_meta'] = load_mode
    df['run_started_meta'] = run_started.isoformat()

    print(f'[load_hotel_csv] {batch_file} | mode={load_mode} | {len(df):,} dòng')
    return df


@test
def test_output(output, *args) -> None:
    assert output is not None, 'The output is undefined'
    # Output rỗng là hợp lệ: chế độ AUTO không có batch mới
    for col in ('batch_file', 'ingested_at', 'record_hash', 'booking_uid', 'load_mode_meta', 'run_started_meta'):
        assert col in output.columns, f'Thiếu cột metadata {col}'
