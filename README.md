# MINI PROJECT: XÂY DỰNG HỆ THỐNG BUSINESS INTELLIGENCE TÍCH HỢP AI
## Chủ đề: Phân tích Nhu cầu Đặt phòng, Doanh thu & Chẩn đoán Hủy phòng Khách sạn (*Hotel Booking Demand*)

---

### 👥 Thành viên thực hiện (Nhóm 4 người)
1. **Đào Trung Kiên** *(Nhóm trưởng)* – 23120055
2. **Huỳnh Võ Đại Dương** – 23120033
3. **Phạm Ngọc Thanh** – 23120087
4. **Thạch Ý** – 23120411

---

### 📊 Nguồn Dữ Liệu (Kaggle Dataset)
- **Tên Dataset:** [Hotel Booking Demand](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand)
- **Quy mô:** 119.390 dòng × 32 cột thuộc tính (Giai đoạn 2015 – 2017 cho 2 chuỗi *Resort Hotel* và *City Hotel*).
- **Cách chuẩn bị dữ liệu:**
  1. Tải file `hotel_bookings.csv` từ đường dẫn Kaggle trên và đặt vào thư mục `data/`.
  2. Chạy lệnh `python data/split_batches.py` để tách thành các file batch phục vụ **Full Load** (`batch_01_full_2015_2016.csv`), **Incremental Load** (`batch_02_inc_2017_H1.csv`, `batch_03_inc_2017_H2.csv`) và kiểm thử lỗi (`batch_04_corrupted_test.csv`, `batch_05_bad_schema.csv`).

---

### Cấu Trúc Dự Án

```text
hotel-bi-ai-project/
├── compose.yaml                         # Docker chạy PostgreSQL 17 & Mage.ai (port 6789)
├── Dockerfile                           # Cài đặt mage-ai, dbt-postgres
├── .env.example                         # Mẫu biến môi trường
├── postgres/
│   └── init/
│       └── 01_init.sql                  # Tạo 3 schema: stage, dds, control + bảng control.etl_batch_log
├── data/
│   └── split_batches.py                 # Script chia CSV gốc thành các batch Full & Incremental
├── schema/
│   └── star_schema.png                  # Sơ đồ thiết kế kho dữ liệu Star Schema (dds)
└── lab_project/                         # Project Mage.ai
    ├── io_config.yaml                   # Cấu hình kết nối PostgreSQL
    ├── data_loaders/
    │   └── load_hotel_csv.py            # Đọc file CSV batch kèm metadata & record_hash
    ├── transformers/
    │   └── validate_hotel_data.py       # Kiểm tra cấu trúc và lọc dòng lỗi dữ liệu
    ├── data_exporters/
    │   └── load_stage_hotel.py          # Nạp vào stage.raw_hotel_bookings & ghi log vào control.etl_batch_log
    └── dbt/
        └── hotel_dw/                    # Project dbt chuyển đổi từ stage sang dds (Star Schema)
            ├── dbt_project.yml
            ├── profiles.yml
            ├── macros/
            │   └── generate_schema_name.sql
            └── models/
                ├── staging/             # stg_hotel_bookings.sql & sources.yml
                └── marts/               # dim_date, dim_hotel, dim_customer, dim_channel, dim_room_policy, fact_bookings, schema.yml
```

---

### Hướng Dẫn Khởi Chạy Nhanh

```bash
# 1. Tạo file .env từ mẫu
cp .env.example .env

# 2. Khởi chạy Docker (PostgreSQL 17 + Mage.ai + dbt)
docker compose up -d --build

# 3. Truy cập Mage.ai tại: http://localhost:6789
# 4. Chạy dbt tạo Star Schema (bên trong container lab-mage):
docker exec -it lab-mage bash -c "cd /home/src/lab_project/dbt/hotel_dw && dbt run --profiles-dir . && dbt test --profiles-dir ."
```
