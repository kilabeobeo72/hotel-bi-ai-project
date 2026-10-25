import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

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


@data_loader
def load_hotel_from_csv(*args, **kwargs):
    """
    Block 1 (Data Loader): Đọc dữ liệu Hotel Booking từ file CSV trong thư mục /home/src/data.
    Hỗ trợ truyền Runtime Variables:
      - batch_file: Tên file CSV cần nạp (mặc định: 'batch_01_full_2015_2016.csv')
      - load_mode:  'FULL' hoặc 'INCREMENTAL' (không phân biệt hoa thường)
    Gắn thêm cột metadata: batch_file, ingested_at, record_hash, booking_uid (= record_hash,
    để tương thích với stg_hotel_bookings.sql đang dùng booking_uid làm khóa).
    """
    batch_file = os.path.basename(str(kwargs.get('batch_file') or 'batch_01_full_2015_2016.csv'))
    load_mode = str(kwargs.get('load_mode') or 'FULL').strip().upper()
    if load_mode not in ('FULL', 'INCREMENTAL'):
        raise ValueError(f"load_mode không hợp lệ: '{load_mode}' (chỉ nhận FULL hoặc INCREMENTAL).")

    file_path = Path(DATA_DIR) / batch_file
    if not file_path.exists():
        raise FileNotFoundError(f'Không tìm thấy file batch: {file_path}')

    # Bản chuỗi gốc: chỉ dùng để tính hash ổn định.
    raw = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    # Bản có kiểu: cột số là int/float, 'NULL' / 'NA' thành NULL => stage lưu đúng kiểu cho dbt.
    df = pd.read_csv(file_path)

    if all(c in raw.columns for c in IDENTITY_COLS):
        df['record_hash'] = compute_record_hash(raw).to_numpy()
    else:
        # Thiếu cột định danh: để block validate báo lỗi cấu trúc rõ ràng thay vì lỗi KeyError.
        df['record_hash'] = None
    df['booking_uid'] = df['record_hash']

    df['batch_file'] = batch_file
    df['ingested_at'] = datetime.now(timezone.utc).replace(tzinfo=None)

    print(f'[load_hotel_csv] {batch_file} | mode={load_mode} | {len(df):,} dòng')
    return df


@test
def test_output(output, *args) -> None:
    assert output is not None, 'The output is undefined'
    assert len(output) > 0, 'Dataset loaded is empty'
    for col in ('batch_file', 'ingested_at', 'record_hash', 'booking_uid'):
        assert col in output.columns, f'Thiếu cột metadata {col}'
