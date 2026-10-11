# Phase 6 - Scenario stress tests

Same 8-week replay, 5,748 series. Base = Phase 5 plan.

| scenario              |   fill_rate |   lost_sales_units |   lost_sales_value |   avg_on_hand_value |   holding_cost_8wk |   share_series_stockout |   safety_stock_value |   d_fill_pts |   d_lost_sales_value |   d_on_hand_value |
|:----------------------|------------:|-------------------:|-------------------:|--------------------:|-------------------:|------------------------:|---------------------:|-------------:|---------------------:|------------------:|
| base                  |      0.9931 |               4572 |              12351 |              564374 |              21707 |                   0.11  |               348715 |         0    |                    0 |                 0 |
| bias_corrected        |      0.9937 |               4178 |              11303 |              595113 |              22889 |                   0.1   |               379685 |         0.06 |                -1048 |             30740 |
| lower_A_target_95     |      0.9915 |               5633 |              15688 |              515844 |              19840 |                   0.12  |               299438 |        -0.16 |                 3337 |            -48529 |
| delay_1x2wk           |      0.9855 |               9629 |              26979 |              510465 |              19633 |                   0.221 |               348715 |        -0.76 |                14629 |            -53909 |
| lead_time_4wk         |      0.8923 |              71639 |             191475 |              324588 |              12484 |                   0.625 |               -61276 |       -10.08 |               179124 |           -239786 |
| lead_time_4wk_resized |      0.9852 |               9859 |              27217 |              776293 |              29857 |                   0.152 |               450189 |        -0.79 |                14866 |            211919 |
| demand_+30pct_wk3-6   |      0.9862 |              10577 |              29367 |              501652 |              19294 |                   0.218 |               348715 |        -0.7  |                17017 |            -62721 |
| demand_-30pct_wk3-6   |      0.9949 |               2901 |               7910 |              630196 |              24238 |                   0.076 |               348715 |         0.18 |                -4441 |             65822 |
| combined_lt4_+30pct   |      0.8142 |             141945 |             382035 |              283680 |              10911 |                   0.794 |               -61276 |       -17.89 |               369684 |           -280694 |

## How to read this

- `delay_1x2wk` vs `lead_time_4wk`: a one-off late shipment is survivable on safety stock; a structural lead-time change is not, unless the plan is re-sized (`_resized`).
- `bias_corrected`: if lost sales fall and on-hand barely moves, the under-forecasting found in Phase 5 was real and fixing it is cheaper than holding stock against it.
- `lower_A_target_95`: what the 98% A target was actually buying.
- `demand_-30pct`: the overstock side - inventory cost of a demand drop with no response.
- `combined`: the stress case to size an emergency buffer or dual-sourcing decision against.