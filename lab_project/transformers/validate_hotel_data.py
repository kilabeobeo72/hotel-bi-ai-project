import os

import pandas as pd

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

DATA_DIR = os.environ.get('HOTEL_DATA_DIR', '/home/src/data')
REJECT_DIR = os.path.join(DATA_DIR, 'rejected')

REQUIRED_COLUMNS = [
    'hotel', 'is_canceled', 'lead_time', 'arrival_date_year', 'arrival_date_month',
    'arrival_date_week_number', 'arrival_date_day_of_month', 'stays_in_weekend_nights',
    'stays_in_week_nights', 'adults', 'children', 'babies', 'meal', 'country',
    'market_segment', 'distribution_channel', 'is_repeated_guest', 'previous_cancellations',
    'previous_bookings_not_canceled', 'reserved_room_type', 'assigned_room_type',
    'booking_changes', 'deposit_type', 'agent', 'company', 'days_in_waiting_list',
    'customer_type', 'adr', 'required_car_parking_spaces', 'total_of_special_requests',
    'reservation_status', 'reservation_status_date',
]
METADATA_COLUMNS = ['batch_file', 'ingested_at', 'record_hash', 'booking_uid']


@transformer
def validate_hotel_data(data: pd.DataFrame, *args, **kwargs):
    """
    Block 2 (Transformer): Kiểm tra cấu trúc và chất lượng dữ liệu cơ bản trước khi nạp vào stage.

    1. Lỗi CẤU TRÚC (thiếu cột bắt buộc) -> raise ValueError, dừng cả pipeline (status FAILED).
    2. Lỗi GIÁ TRỊ -> chỉ loại các dòng vi phạm, phần còn lại vẫn được nạp (status WARNING):
         - lead_time không phải số hoặc < 0
         - adr không phải số hoặc < 0
         - is_canceled không thuộc {0, 1}
         - record_hash rỗng
       Dòng bị loại được ghi vào <data>/rejected/<batch>_rejected.csv kèm cột reject_reason.
    Số dòng đọc / bị loại được truyền cho block sau qua cột rows_extracted_meta / rows_rejected_meta
    (block load_stage_hotel dùng để ghi control.etl_batch_log rồi bỏ hai cột này).
    """
    df = data.copy()
    batch_file = str(df['batch_file'].iloc[0]) if 'batch_file' in df.columns and len(df) else 'unknown'
    batch_stem = os.path.splitext(os.path.basename(batch_file))[0]
    rows_extracted = len(df)

    # 1. Kiểm tra cấu trúc
    missing = [c for c in REQUIRED_COLUMNS + METADATA_COLUMNS if c not in df.columns]
    if missing:
        n_data_cols = len([c for c in df.columns if c not in METADATA_COLUMNS])
        raise ValueError(
            f'[validate_hotel_data] {batch_file}: thiếu cột bắt buộc {missing}. '
            f'File có {n_data_cols} cột dữ liệu, yêu cầu {len(REQUIRED_COLUMNS)} cột.'
        )

    # 2. Ép kiểu số (giá trị không chuyển được -> NaN và bị bắt ở bước 3)
    lead_time = pd.to_numeric(df['lead_time'], errors='coerce')
    adr = pd.to_numeric(df['adr'], errors='coerce')
    is_canceled = pd.to_numeric(df['is_canceled'], errors='coerce')

    # 3. Gom lý do vi phạm theo từng dòng
    reasons = pd.Series('', index=df.index)

    def flag(mask, text):
        nonlocal reasons
        reasons = reasons.where(~mask, reasons + text + '; ')

    flag(lead_time.isna() | (lead_time < 0), 'lead_time không hợp lệ')
    flag(adr.isna() | (adr < 0), 'adr không hợp lệ (NaN hoặc < 0)')
    flag(~is_canceled.isin([0, 1]), 'is_canceled ngoài {0,1}')
    flag(df['record_hash'].isna() | (df['record_hash'].astype(str) == ''), 'thiếu record_hash')

    bad_mask = reasons != ''
    rejected = df[bad_mask].copy()
    rejected['reject_reason'] = reasons[bad_mask].str.rstrip('; ')

    valid = df[~bad_mask].copy()
    valid['lead_time'] = lead_time[~bad_mask].astype('int64')
    valid['adr'] = adr[~bad_mask].astype('float64')
    valid['is_canceled'] = is_canceled[~bad_mask].astype('int64')

    # 4. Lưu vết dòng bị loại
    if len(rejected) > 0:
        os.makedirs(REJECT_DIR, exist_ok=True)
        rejected.to_csv(os.path.join(REJECT_DIR, f'{batch_stem}_rejected.csv'), index=False)

    print(f'[validate_hotel_data] {batch_file}: đọc {rows_extracted:,} | '
          f'hợp lệ {len(valid):,} | loại {len(rejected):,}')

    if len(valid) == 0:
        raise ValueError(f'[validate_hotel_data] {batch_file}: không còn dòng hợp lệ nào để nạp.')

    valid['rows_extracted_meta'] = rows_extracted
    valid['rows_rejected_meta'] = int(len(rejected))
    return valid


@test
def test_valid_data(output, *args) -> None:
    assert output is not None and len(output) > 0, 'Không có dữ liệu hợp lệ'
    assert (output['adr'] >= 0).all(), 'ADR cannot be negative'
    assert output['is_canceled'].isin([0, 1]).all(), 'is_canceled phải thuộc {0, 1}'
    assert output['record_hash'].notna().all(), 'record_hash không được rỗng'
    assert output['record_hash'].is_unique, 'record_hash bị trùng trong cùng một batch'
