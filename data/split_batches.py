"""
Script cắt bộ dữ liệu gốc hotel_bookings.csv (từ Kaggle) thành các file batch
để mô phỏng cơ chế Full Load, Incremental Load và Error Handling trên Mage.ai.

Link tải Dataset Kaggle:
https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand

Cách chạy (từ thư mục gốc của repo):
    python data/split_batches.py

Đầu ra (cùng thư mục với script):
    batch_01_full_2015_2016.csv  Lịch sử 2015-2016                       -> FULL LOAD
    batch_02_inc_2017_H1.csv     2017, tháng 1-6                         -> INCREMENTAL lần 1
    batch_03_inc_2017_H2.csv     2017, tháng 7-8 + 300 bản ghi CẬP NHẬT   -> INCREMENTAL lần 2 (test UPSERT)
    batch_04_corrupted_test.csv  40 dòng, 13 dòng lỗi giá trị            -> WARNING (loại dòng lỗi, nạp phần còn lại)
    batch_05_bad_schema.csv      20 dòng, thiếu cột `adr`                -> FAILED (sai cấu trúc, dừng pipeline)

Lưu ý thiết kế:
  - Đọc toàn bộ cột dạng chuỗi (dtype=str, keep_default_na=False) để giữ nguyên văn bản gốc
    ('NULL', 'NA', '9.0'...). Nhờ vậy cùng một đơn đặt phòng luôn có cùng văn bản ở mọi batch
    và `record_hash` (tính ở load_hotel_csv.py) khớp nhau giữa các batch.
  - Bản ghi "cập nhật" ở batch_03 chỉ chọn từ các dòng có định danh duy nhất trong batch_02
    (không bị trùng hoàn toàn với dòng khác) để mỗi bản ghi cập nhật khớp đúng 1 dòng cũ.
"""

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}

EXPECTED_COLUMNS = [
    "hotel", "is_canceled", "lead_time", "arrival_date_year", "arrival_date_month",
    "arrival_date_week_number", "arrival_date_day_of_month", "stays_in_weekend_nights",
    "stays_in_week_nights", "adults", "children", "babies", "meal", "country",
    "market_segment", "distribution_channel", "is_repeated_guest", "previous_cancellations",
    "previous_bookings_not_canceled", "reserved_room_type", "assigned_room_type",
    "booking_changes", "deposit_type", "agent", "company", "days_in_waiting_list",
    "customer_type", "adr", "required_car_parking_spaces", "total_of_special_requests",
    "reservation_status", "reservation_status_date",
]

# Các cột trạng thái có thể thay đổi sau khi đặt phòng. Mọi cột còn lại là "định danh".
# PHẢI giống MUTABLE_COLS trong lab_project/data_loaders/load_hotel_csv.py
MUTABLE_COLS = ["is_canceled", "reservation_status", "reservation_status_date"]
IDENTITY_COLS = [c for c in EXPECTED_COLUMNS if c not in MUTABLE_COLS]


def save(df: pd.DataFrame, path: Path, note: str) -> None:
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"[+] Đã tạo {path.name}: {len(df):,} dòng ({note})")


def ensure_source(source_path: Path) -> bool:
    """Nếu chưa có file gốc thì thử tải qua kagglehub (cần: pip install kagglehub)."""
    if source_path.exists():
        return True
    print(f"[!] Không tìm thấy {source_path.name}. Đang thử tải từ Kaggle qua kagglehub...")
    try:
        import kagglehub
    except ImportError:
        print("[x] Chưa cài kagglehub. Hãy tải file thủ công từ link Kaggle ở đầu file này "
              f"và đặt vào {source_path.parent}, hoặc chạy: pip install kagglehub")
        return False
    download_dir = Path(kagglehub.dataset_download("jessemostipak/hotel-booking-demand"))
    downloaded = download_dir / "hotel_bookings.csv"
    if not downloaded.exists():
        print("[x] Không thấy hotel_bookings.csv trong dữ liệu đã tải.")
        return False
    shutil.copy(downloaded, source_path)
    print(f"[+] Đã tải và lưu {source_path.name} vào {source_path.parent}")
    return True


def make_update_rows(source: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Chọn n dòng có định danh duy nhất và đảo trạng thái hủy / không hủy."""
    unique_mask = ~source.duplicated(subset=IDENTITY_COLS, keep=False)
    pool = source[unique_mask]
    n = min(n, len(pool))
    upd = pool.sample(n=n, random_state=seed).copy()
    was_canceled = upd["is_canceled"] == "1"
    upd.loc[was_canceled, ["is_canceled", "reservation_status"]] = ["0", "Check-Out"]
    upd.loc[~was_canceled, ["is_canceled", "reservation_status"]] = ["1", "Canceled"]
    return upd


def make_corrupted(source: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """40 dòng, trong đó 13 dòng lỗi giá trị: 5 adr âm, 5 lead_time không phải số, 3 is_canceled = 2."""
    bad = source.sample(n=n, random_state=seed).copy().reset_index(drop=True)
    bad.loc[0:4, "adr"] = "-6.38"
    bad.loc[5:9, "lead_time"] = "abc"
    bad.loc[10:12, "is_canceled"] = "2"
    return bad


def split_hotel_dataset(raw_file: str, outdir: Path, seed: int, n_updates: int) -> int:
    data_dir = Path(__file__).parent
    source_path = Path(raw_file) if raw_file else data_dir / "hotel_bookings.csv"
    if not ensure_source(source_path):
        return 1
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Đang đọc dữ liệu gốc từ {source_path}...")
    df = pd.read_csv(source_path, dtype=str, keep_default_na=False)
    if list(df.columns) != EXPECTED_COLUMNS:
        print("[x] Cấu trúc file gốc không khớp 32 cột mong đợi. "
              f"Thiếu: {sorted(set(EXPECTED_COLUMNS) - set(df.columns))} | "
              f"Thừa: {sorted(set(df.columns) - set(EXPECTED_COLUMNS))}")
        return 1

    year = df["arrival_date_year"].astype(int)
    month = df["arrival_date_month"].map(MONTHS)
    if month.isna().any():
        print("[x] Có giá trị arrival_date_month không hợp lệ.")
        return 1

    batch_01 = df[year <= 2016]
    batch_02 = df[(year == 2017) & (month <= 6)]
    batch_03_new = df[(year == 2017) & (month >= 7)]

    # batch_03 = dữ liệu mới + một số bản ghi của batch_02 đổi trạng thái hủy (test cập nhật bản ghi trùng)
    updates = make_update_rows(batch_02, n_updates, seed)
    batch_03 = pd.concat([batch_03_new, updates], ignore_index=True)

    batch_04 = make_corrupted(batch_03_new, n=40, seed=seed)
    batch_05 = batch_03_new.sample(n=20, random_state=seed).drop(columns=["adr"])

    save(batch_01, outdir / "batch_01_full_2015_2016.csv", "Dùng cho Full Load")
    save(batch_02, outdir / "batch_02_inc_2017_H1.csv", "Dùng cho Incremental Load đợt 1")
    save(batch_03, outdir / "batch_03_inc_2017_H2.csv",
         f"Incremental Load đợt 2: {len(batch_03_new):,} dòng mới + {len(updates):,} dòng cập nhật")
    save(batch_04, outdir / "batch_04_corrupted_test.csv", "13/40 dòng lỗi giá trị, test lọc dòng lỗi")
    save(batch_05, outdir / "batch_05_bad_schema.csv", "thiếu cột adr, test pipeline FAILED")

    clean_total = len(batch_01) + len(batch_02) + len(batch_03_new)
    ok = clean_total == len(df)
    print(f"\nKiểm tra: batch_01 + batch_02 + phần dòng mới của batch_03 = {clean_total:,} "
          f"(file gốc: {len(df):,}) -> {'OK' if ok else 'LỆCH'}")
    return 0 if ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tách hotel_bookings.csv thành các batch.")
    parser.add_argument("--input", default="", help="Đường dẫn file gốc (mặc định: data/hotel_bookings.csv)")
    parser.add_argument("--outdir", default=str(Path(__file__).parent), help="Thư mục ghi các batch")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-updates", type=int, default=300, help="Số bản ghi cập nhật trong batch_03")
    args = parser.parse_args()
    sys.exit(split_hotel_dataset(args.input, Path(args.outdir), args.seed, args.n_updates))
