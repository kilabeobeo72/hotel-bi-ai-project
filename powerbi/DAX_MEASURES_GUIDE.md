# 12 DAX MEASURES CHUẨN

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
