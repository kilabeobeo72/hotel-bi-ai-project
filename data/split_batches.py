"""
Script cắt bộ dữ liệu gốc hotel_bookings.csv (từ Kaggle) thành các file batch
để mô phỏng cơ chế Full Load và Incremental Load trên Mage.ai.

Link tải Dataset Kaggle:
https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand
"""

import sys
import shutil
from pathlib import Path
import pandas as pd
import kagglehub

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def split_hotel_dataset(raw_file: str = "hotel_bookings.csv"):
    data_dir = Path(__file__).parent
    source_path = data_dir / raw_file

    # Nếu chưa có file gốc, tự động tải qua kagglehub
    if not source_path.exists():
        print(f"[!] Không tìm thấy {source_path.name}. Đang tải từ Kaggle qua kagglehub...")
        download_dir = Path(kagglehub.dataset_download("jessemostipak/hotel-booking-demand"))
        
        # Copy file hotel_bookings.csv từ cache về thư mục data/
        downloaded_file = download_dir / "hotel_bookings.csv"
        if downloaded_file.exists():
            shutil.copy(downloaded_file, source_path)
            print(f"[+] Đã tải và lưu {source_path.name} vào {data_dir}")
        else:
            print("[x] Không tìm thấy file hotel_bookings.csv trong dữ liệu đã tải.")
            return

    print(f"Đang đọc dữ liệu gốc từ {source_path}...")
    df = pd.read_csv(source_path)


    # Tạo khóa định danh dòng (booking_uid) để hỗ trợ Incremental Upsert
    df["booking_uid"] = [f"BK-{i:06d}" for i in range(1, len(df) + 1)]

    # 1. Batch 01 (Full Load): Dữ liệu lịch sử năm 2015 và 2016
    batch_01 = df[df["arrival_date_year"].isin([2015, 2016])].copy()
    batch_01_path = data_dir / "batch_01_full_2015_2016.csv"
    batch_01.to_csv(batch_01_path, index=False)
    print(f"[+] Đã tạo {batch_01_path.name}: {len(batch_01):,} dòng (Dùng cho Full Load)")

    # 2. Batch 02 (Incremental Load 1): Nửa đầu năm 2017 (Tháng 1 -> Tháng 5)
    h1_months = ["January", "February", "March", "April", "May"]
    batch_02 = df[(df["arrival_date_year"] == 2017) & (df["arrival_date_month"].isin(h1_months))].copy()
    batch_02_path = data_dir / "batch_02_inc_2017_H1.csv"
    batch_02.to_csv(batch_02_path, index=False)
    print(f"[+] Đã tạo {batch_02_path.name}: {len(batch_02):,} dòng (Dùng cho Incremental Load đợt 1)")

    # 3. Batch 03 (Incremental Load 2): Nửa cuối năm 2017 (Tháng 6 -> Tháng 8)
    h2_months = ["June", "July", "August"]
    batch_03 = df[(df["arrival_date_year"] == 2017) & (df["arrival_date_month"].isin(h2_months))].copy()
    batch_03_path = data_dir / "batch_03_inc_2017_H2.csv"
    batch_03.to_csv(batch_03_path, index=False)
    print(f"[+] Đã tạo {batch_03_path.name}: {len(batch_03):,} dòng (Dùng cho Incremental Load đợt 2)")


if __name__ == "__main__":
    split_hotel_dataset()
