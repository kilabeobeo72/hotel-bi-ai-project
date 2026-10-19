import pandas as pd

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def validate_hotel_data(data: pd.DataFrame, *args, **kwargs):
    """
    Block 2 (Transformer): Kiểm tra cấu trúc và chất lượng dữ liệu cơ bản trước khi nạp vào stage.
    """
    df = data.copy()

    df['children'] = pd.to_numeric(df['children'], errors='coerce').fillna(0).astype(int)
    df['country'] = df['country'].fillna('UNK').astype(str)
    df['agent'] = df['agent'].fillna(0).astype(str)
    df['company'] = df['company'].fillna(0).astype(str)

    df['lead_time'] = pd.to_numeric(df['lead_time'], errors='coerce').fillna(0).astype(int)
    df['adr'] = pd.to_numeric(df['adr'], errors='coerce').fillna(0.0)
    df['is_canceled'] = pd.to_numeric(df['is_canceled'], errors='coerce').fillna(0).astype(int)

    total_guests = df['adults'] + df['children'] + df['babies']
    valid_mask = (total_guests > 0) & (df['adr'] >= 0) & (df['booking_uid'].notnull())

    df_valid = df[valid_mask].copy()
    df_valid['rows_extracted_meta'] = len(df)
    df_valid['rows_rejected_meta'] = int((~valid_mask).sum())

    return df_valid


@test
def test_valid_data(output, *args) -> None:
    assert (output['adr'] >= 0).all(), 'ADR cannot be negative'
    assert ((output['adults'] + output['children'] + output['babies']) > 0).all(), 'Total guests must be > 0'
