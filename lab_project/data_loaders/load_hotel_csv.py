import pandas as pd
from pathlib import Path
from datetime import datetime

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_hotel_from_csv(*args, **kwargs):
    """
    Block 1 (Data Loader): Đọc dữ liệu Hotel Booking từ file CSV trong thư mục /home/src/data.
    Hỗ trợ truyền Runtime Variables:
      - batch_file: Tên file CSV cần nạp (mặc định: 'batch_01_full_2015_2016.csv')
      - load_mode:  'FULL' hoặc 'INCREMENTAL'
    """
    batch_file = kwargs.get('batch_file', 'batch_01_full_2015_2016.csv')
    load_mode = kwargs.get('load_mode', 'FULL')

    file_path = Path('/home/src/data') / batch_file
    df = pd.read_csv(file_path)

    if 'booking_uid' not in df.columns:
        df['booking_uid'] = [f"{batch_file[:8]}-{i:06d}" for i in range(1, len(df) + 1)]

    df['source_file'] = batch_file
    df['load_mode'] = load_mode
    df['ingested_at'] = datetime.utcnow()

    return df


@test
def test_output(output, *args) -> None:
    assert output is not None, 'The output is undefined'
    assert len(output) > 0, 'Dataset loaded is empty'
