# DAX MEASURES CHUẨN (12 measure gốc + 5 measure trang 2)

```dax
Total Bookings = COUNTROWS(fact_bookings)

Canceled Bookings = CALCULATE([Total Bookings], fact_bookings[is_canceled] = 1)

Completed Bookings = CALCULATE([Total Bookings], fact_bookings[is_canceled] = 0)

Cancellation Rate % = DIVIDE([Canceled Bookings], [Total Bookings], 0)

Total Room Nights = SUM(fact_bookings[total_nights])

ADR = AVERAGE(fact_bookings[adr])

Actual Revenue = SUM(fact_bookings[actual_revenue])

Revenue Loss (Canceled) = SUM(fact_bookings[revenue_loss])

Gross Potential Revenue = [Actual Revenue] + [Revenue Loss (Canceled)]

Revenue YoY Growth % = 
VAR CurrentRev = [Actual Revenue]
VAR PrevYearRev = CALCULATE([Actual Revenue], SAMEPERIODLASTYEAR(dim_date[full_date]))
RETURN DIVIDE(CurrentRev - PrevYearRev, PrevYearRev, BLANK())

Avg Lead Time (Days) = AVERAGE(fact_bookings[lead_time])

Room Upgrade Rate % = 
DIVIDE(
    CALCULATE([Total Bookings], dim_room_policy[is_room_upgraded] = TRUE()),
    [Total Bookings],
    0
)
```

## Measures bổ sung cho trang "2. Cancellation Diagnostic"

Tất cả tạo trong bảng `_Measures`. Không đổi tên bảng hay 12 measure ở trên.

```dax
Revenue Loss % = DIVIDE([Revenue Loss (Canceled)], [Gross Potential Revenue], 0)

Avg Lead Time Canceled (Days) = CALCULATE([Avg Lead Time (Days)], fact_bookings[is_canceled] = 1)

Overall Cancellation Rate % = CALCULATE([Cancellation Rate %], ALLSELECTED())

Revenue Loss (triệu USD) = DIVIDE([Revenue Loss (Canceled)], 1000000)
```

Measure chữ chỉ dùng cho thẻ KPI (thẻ mới tự rút gọn số thành "nghìn"/"triệu" và bỏ qua định dạng số):

```dax
Canceled Bookings (Text) = FORMAT([Canceled Bookings], "#,0")

Revenue Loss (Text) = FORMAT([Revenue Loss (Canceled)] / 1000000, "$#,0.00") & "M"
```

| Measure | Dùng ở | Định dạng |
|---|---|---|
| Revenue Loss % | Thẻ K4 | Phần trăm, 1 chữ số thập phân |
| Avg Lead Time Canceled (Days) | Thẻ K5 | Số thập phân, 2 chữ số |
| Overall Cancellation Rate % | Đường tham chiếu ở C1 | Phần trăm |
| Revenue Loss (triệu USD) | C6 (Top 10 quốc gia) | Số thập phân, 1 chữ số (không dùng Tiền tệ để tránh ký hiệu ₫) |
| Canceled Bookings (Text) | Thẻ K2 | Văn bản |
| Revenue Loss (Text) | Thẻ K3 | Văn bản |

### Số đối chiếu khi chưa lọc

| Chỉ số | Giá trị |
|---|---|
| Cancellation Rate % | 37,19% |
| Canceled Bookings | 44.336 |
| Revenue Loss (Canceled) | $16.775.893,38 |
| Revenue Loss % | 39,3% |
| Avg Lead Time Canceled (Days) | 144,62 |
| year = 2016 | 35,89% |
| year = 2017 | 39,07%, Revenue Loss $7.272.236,16 |
