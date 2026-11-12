# POWER BI SEMANTIC MODEL & DASHBOARDS (SEMINAR 2)

Thư mục này chứa file Power BI nền tảng (**Base v1.0**) do **Đào Trung Kiên** khởi tạo, đã tích hợp sẵn dữ liệu từ tầng `dds` (Data Warehouse), thiết lập lược đồ Hình sao (**Star Schema**), **03 Hierarchies** và bộ **12 DAX Measures chuẩn**.

---

## 1. Danh sách File trong thư mục `powerbi/`

- **`Hotel_BI_Dashboard.pbix`**: File Power BI Base v1.0 đã nạp sẵn **119.209 dòng sạch** (giai đoạn 2015–2017) từ 6 bảng `dds` (`fact_bookings`, `dim_date`, `dim_hotel`, `dim_customer`, `dim_channel`, `dim_room_policy`), thiết lập đầy đủ Relationships `1:*`, 3 Hierarchies, 12 DAX Measures trong bảng `_Measures`, và tạo sẵn 2 trang:
  - Tab 1: **`1. Executive Overview`** *(Phụ trách: Phạm Ngọc Thanh)*
  - Tab 2: **`2. Cancellation Diagnostic`** *(Phụ trách: Huỳnh Võ Đại Dương)*
- **`DAX_MEASURES_GUIDE.md`**: Tài liệu chi tiết công thức 12 DAX Measures trong bảng `_Measures`.

> **Quy tắc phối hợp cho Thanh & Dương để ghép file `.pbix` không bị lỗi:**
> - Mở trực tiếp file `powerbi/Hotel_BI_Dashboard.pbix` này để vẽ biểu đồ trên trang được phân công.
> - **Không đổi tên bảng** và **không đổi tên 12 DAX Measures** có sẵn trong `_Measures`.
> - Khi vẽ xong, chỉ cần chọn toàn bộ biểu đồ trên trang (`Ctrl + A` -> `Ctrl + C`) và dán (`Ctrl + V`) sang file tổng hợp.

---

## 2. Bộ Số Liệu Chuẩn (Ground-Truth) trên `dds` để Đối Soát Biểu Đồ

Toàn bộ con số hiển thị trên KPI Cards và biểu đồ Power BI của **Thanh**, **Dương** và **Ý** bắt buộc phải khớp 100% với kết quả truy vấn trực tiếp từ `dds.fact_bookings` dưới đây:

### 2.1. Bảng 10 Chỉ Số Tổng Quan (Toàn giai đoạn 2015–2017, không bật bộ lọc)

| Chỉ số (DAX Measure trong `_Measures`) | Giá trị chuẩn trên `dds` (2015–2017) |
| :--- | :--- |
| **Total Bookings** | `119,209` đơn |
| **Canceled Bookings** | `44,336` đơn |
| **Completed Bookings** | `74,873` đơn |
| **Cancellation Rate %** | **`37.19%`** |
| **Total Room Nights** | `408,433` đêm |
| **ADR (Giá phòng TB/đêm)** | **`$101.97`** |
| **Actual Revenue (Thực thu)** | **`$25,938,319.77`** (~`$25.94M`) |
| **Revenue Loss (Mất do hủy)** | **`$16,775,893.38`** (~`$16.78M`) |
| **Gross Potential Revenue** | **`$42,714,213.15`** (~`$42.71M`) |
| **Avg Lead Time (Days)** | `104.1` ngày |

### 2.2. Đối soát theo Năm (`dim_date[year]`) – Dùng cho Dashboard 1 (Overview)

| Năm (`year`) | Total Bookings | Cancellation Rate % | Actual Revenue ($) | Revenue Loss ($) |
| :---: | :---: | :---: | :---: | :---: |
| **2015** | `21,967` | `37.06%` | `$4,511,541.11` | `$2,306,557.45` |
| **2016** | `56,623` | `35.89%` | `$11,666,705.28` | `$7,197,099.77` |
| **2017** | `40,619` | `39.07%` | `$9,760,073.38` | `$7,272,236.16` |

### 2.3. Đối soát theo Nhóm Lead Time (`fact_bookings[lead_time_group]`) – Dùng cho Dashboard 2 (Diagnostic)

| Nhóm đặt trước (`lead_time_group`) | Total Bookings | Cancellation Rate % | Revenue Loss ($) |
| :--- | :---: | :---: | :---: |
| **1. Short (0-7 days)** | `19,635` | **`9.80%`** | `$455,287.17` |
| **2. Medium (8-30 days)** | `18,945` | `28.05%` | `$2,055,095.33` |
| **3. Long (31-90 days)** | `29,529` | `37.84%` | `$4,337,210.37` |
| **4. Very Long (91-180 days)** | `26,420` | `44.82%` | `$5,142,823.39` |
| **5. Extreme (>180 days)** | `24,680` | **`57.06%`** | `$4,785,477.12` |

---

## 3. Câu Lệnh SQL Đối Soát Nhanh (Dành cho QA – Thạch Ý)

Chạy lệnh sau trên Terminal để kiểm tra đối chiếu trực tiếp với PostgreSQL container `lab-postgres`:

```bash
docker exec lab-postgres psql -U postgres -d dw_lab -c "
SELECT 
    COUNT(*) AS total_bookings,
    SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) AS canceled_bookings,
    SUM(CASE WHEN is_canceled = 0 THEN 1 ELSE 0 END) AS completed_bookings,
    ROUND(100.0 * SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS cancellation_rate_pct,
    SUM(total_nights) AS total_room_nights,
    ROUND(AVG(adr), 2) AS avg_adr,
    SUM(actual_revenue) AS actual_revenue,
    SUM(revenue_loss) AS revenue_loss,
    SUM(gross_revenue) AS gross_potential_revenue,
    ROUND(AVG(lead_time), 1) AS avg_lead_time_days
FROM dds.fact_bookings;
"
```
