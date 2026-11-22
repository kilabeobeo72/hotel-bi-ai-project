# POWER BI SEMANTIC MODEL & DASHBOARDS

Thư mục này chứa file Power BI (`Hotel_BI_Dashboard.pbix`) đã tích hợp dữ liệu từ tầng `dds` (Data Warehouse), thiết lập lược đồ Hình sao (**Star Schema**), **03 Hierarchies** và bộ **12 DAX Measures**.

---

## 1. Bộ Số Liệu Chuẩn (Ground-Truth) trên `dds`

### 1.1. Bảng 10 Chỉ Số Tổng Quan (Giai đoạn 2015–2017)

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

### 1.2. Đối soát theo Năm (`dim_date[year]`)

| Năm (`year`) | Total Bookings | Cancellation Rate % | Actual Revenue ($) | Revenue Loss ($) |
| :---: | :---: | :---: | :---: | :---: |
| **2015** | `21,967` | `37.06%` | `$4,511,541.11` | `$2,306,557.45` |
| **2016** | `56,623` | `35.89%` | `$11,666,705.28` | `$7,197,099.77` |
| **2017** | `40,619` | `39.07%` | `$9,760,073.38` | `$7,272,236.16` |

### 1.3. Đối soát theo Nhóm Lead Time (`fact_bookings[lead_time_group]`)

| Nhóm đặt trước (`lead_time_group`) | Total Bookings | Cancellation Rate % | Revenue Loss ($) |
| :--- | :---: | :---: | :---: |
| **1. Short (0-7 days)** | `19,635` | **`9.80%`** | `$455,287.17` |
| **2. Medium (8-30 days)** | `18,945` | `28.05%` | `$2,055,095.33` |
| **3. Long (31-90 days)** | `29,529` | `37.84%` | `$4,337,210.37` |
| **4. Very Long (91-180 days)** | `26,420` | `44.82%` | `$5,142,823.39` |
| **5. Extreme (>180 days)** | `24,680` | **`57.06%`** | `$4,785,477.12` |
