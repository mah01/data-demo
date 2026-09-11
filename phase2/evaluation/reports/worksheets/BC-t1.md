# Worksheet BC-t1

**Question (blind):** Where would you investigate first if you were the CEO?

Status: completed | model claude-opus-5 | 28 tool calls | systems crm, erp, meta, payroll | 157.1 s | cost $1.9751544999999997 | isolation ok: True

## Tool trace

  1. `meta_describe_sources` {}
  2. `meta_get_semantics` {}
  3. `erp_financial_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08"}
  4. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["quarter", "market"], "sort_by": "quarter", "ascending": true}
  5. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market", "category"]}
  6. `erp_sales_summary` {"period": "2025-07..2026-08", "group_by": ["month", "market"], "sort_by": "month", "ascending": true}
  7. `crm_renewals` {"period": "2026-01..2026-08", "limit": 5}
  8. `crm_renewals` {"period": "2025-01..2025-08", "limit": 5}
  9. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Service", "market": "DK", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 20}
 10. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Service", "group_by": ["market", "product"]}
 11. `payroll_headcount` {"group_by": ["country", "department"], "on_date": "2026-08-31"}
 12. `payroll_hires_and_departures` {"period": "2025-06..2026-08"}
 13. `erp_sales_summary` {"period": "2025-01..2026-08", "category": "Service", "market": "DK", "group_by": ["quarter", "product"], "sort_by": "quarter", "ascending": true}
 14. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 15}
 15. `erp_sales_summary` {"period": "2026-04..2026-08", "compare_to": "2025-10..2025-12", "product_number": "SA-STD", "market": "DK", "group_by": ["customer"], "sort_by": "revenue_dkk", "ascending": true, "limit": 25}
 16. `crm_deals` {"deal_type": "Renewal", "market": "DK", "period": "2025-09..2026-09", "date_field": "closed", "limit": 50}
 17. `crm_renewals` {"period": "2025-10..2025-12", "limit": 1}
 18. `crm_renewals` {"period": "2024-10..2024-12", "limit": 1}
 19. `crm_loss_reasons` {"period": "2025-10..2025-12", "deal_type": "Renewal"}
 20. `crm_deals` {"deal_type": "Renewal", "outcome": "open", "limit": 40, "sort_by": "value_dkk"}
 21. `crm_win_rate` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 22. `crm_win_rate` {"period": "2026-01..2026-08", "market": "DE", "group_by": ["owner"]}
 23. `payroll_personnel_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["country", "department"]}
 24. `crm_loss_reasons` {"period": "2026-01..2026-08", "market": "DE"}
 25. `crm_loss_reasons` {"period": "2025-01..2025-08", "market": "DE"}
 26. `crm_deals` {"market": "DE", "outcome": "won", "period": "2026-01..2026-08", "date_field": "closed", "limit": 35}
 27. `crm_deals` {"market": "DK", "outcome": "won", "period": "2026-01..2026-08", "date_field": "closed", "product_category": "Equipment", "limit": 30}
 28. `crm_pipeline` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}

## Final answer

I'd start with **service-contract renewals in Denmark**. The next renewal round is about to begin and nothing for it is in the CRM yet. Germany comes a close second.

Operating profit for Jan–Aug 2026 is down **5.4M DKK (−34%)** on the same period last year, even though revenue grew 2.3% (ERP). Three items explain most of the drop:

| Driver (Jan–Aug 2026 vs 2025) | Effect on operating profit | Source |
|---|---|---|
| DK Service revenue down 23% | −2.55M gross profit | ERP |
| Germany: gross profit down | −1.79M | ERP |
| Germany: sales team grew from 8 to 12 | −1.77M extra personnel cost | Payroll |
| DK Equipment: sold more, at bigger discounts | +1.25M | ERP |
| Everything else (other costs, SE, DK Components) | −0.53M | ERP |

## 1. Lost service contracts in Denmark

**What the data shows:**
- The renewal round that closed in Oct–Dec 2025 kept **64%** of contracts, down from **85%** a year earlier. 20 of 55 contracts were lost, worth **5.2M DKK** a year, against 1.6M the year before (CRM). Most losses were Danish customers.
- The most common loss reason was **"Customer insourced maintenance"** (9 of 20). Next came "Lost to competitor" (5) and "Price too high" (2).
- Invoicing confirms it. Customers billed for a Danish service agreement fell from about 51 to about 36 in 2026-Q1 (ERP). Customers who left also stopped buying technician hours and call-outs, which all fell about 24.5%. Several went from high six-figure DKK service spend to almost nothing.
- Service is the highest-margin line, at about 59% gross margin.

**Why it's urgent:** last year's renewal deals were created in the CRM between 7 Oct and 6 Nov. Today there are **no open renewal deals**. Two renewals for 2027 have already been lost on "Price too high".

**A reporting gap:** the year-to-date renewal rate looks healthy (84%) only because the big round closes in December. The problem only shows up if you look at Q4.

**What I can't tell from the data:** *why* customers are taking maintenance in-house. The loss reason is a drop-down choice, so it needs conversations with those customers. All Danish renewals are owned by one person, Line Østergaard. That's worth noting as a dependency, but it isn't evidence that she caused the losses.

## 2. Germany: more salespeople, fewer wins, bigger discounts

**What the data shows:**
- The team grew by 4 (Sep-2025 to Jan-2026), adding 1.77M DKK in cost (+49%).
- New deals entering the pipeline rose 35%. But the win rate fell from **30% to 18%**, and the value of deals won fell 24% (CRM).
- Average discount on German Equipment went from **7.0% to 15.3%**, and its gross margin from 28% to 22% (ERP). Won deals typically carry 14–20% discount.
- The low win rates aren't just new hires ramping up. Most longer-standing reps are also at 13–23%; only Tobias Wagner is at 47%. Even at these discounts, "Price too high" is still a top loss reason, and 23% of losses have no reason recorded.

**My reading (not proven):** German prices are being cut without winning more deals. That points to a pricing or positioning problem rather than too few salespeople. I found nothing in the data showing whether the discount level was a deliberate decision.

## 3. Watch item: Danish Equipment discounts

Discounts rose from 6.9% to 10.8%, spread across all reps. Volume grew 28%, so profit still rose. Sweden kept discounts around 7% and improved its margin, which makes it a useful internal comparison.

## Suggested next steps
1. This month, review the upcoming Danish renewal round contract by contract, and talk to the customers who left about why they took maintenance in-house.
2. Find out who approves discounts in Germany and Denmark, and whether the 2026 increase was a policy decision.
3. Set up checkpoints for the German expansion: win rate, won value and gross profit per rep, against the added cost.

## Automatic discovery signals

| item | stated | investigated | snippet |
|---|---|---|---|
| revenue_up_profit_down | True | True | Operating profit for Jan–Aug 2026 is down **5.4M DKK (−34%)** on the same period last year, even though revenue grew 2.3% (ERP). |
| germany_major_contributor | True | True | / Germany: gross profit down / −1.79M / ERP / |
| german_sales_headcount_expansion | True | True | / Germany: sales team grew from 8 to 12 / −1.77M extra personnel cost / Payroll / |
| pipeline_up_conversion_down | False | True |  |
| new_rep_underperformance | True | True | - The low win rates aren't just new hires ramping up. |
| key_accounts_named | False | True |  |
| denmark_mix_margin | True | True | I'd start with **service-contract renewals in Denmark**. |
| salary_inflation_insufficient | False | False |  |

## Reference facts (evaluation only)

### story
- headline: Revenue is up ~3.5% (DKK 86m -> 89m) but operating profit is down ~33% (DKK 12m -> 8m); margin falls from ~14% to ~9%.
- drivers: 
  - {"id": "germany_expansion", "rank": 1, "summary": "German sales headcount grew 8 -> 12. New pipeline +35%, but win rate fell 31% -> 19% (new reps win ~12%, veterans ~23%). Germany costs rose (people + cars, travel, office, trade fair) while German revenue fell ~8% and discounting cut equipment margins.", "systems": ["payroll", "crm", "erp"]}
  - {"id": "german_key_accounts", "rank": 2, "summary": "Rheinmark Chemie and Brandauer Papierwerke were reassigned from a veteran account manager to two newly hired reps in Sep/Oct 2025. Account activity dropped, Rheinmark's service contract renewal and follow-on deals were lost, Brandauer moved spare parts to a local distributor. Their combined H1 revenue fell ~DKK 3.6m, more than Germany's entire n
  - {"id": "denmark_mix", "rank": 3, "summary": "Danish revenue grew ~9-10%, but high-margin service fell ~23% (a third of service-contract value was not renewed at end-2025) while lower-margin equipment grew ~30% at bigger discounts. Danish gross profit is DOWN despite revenue growth.", "systems": ["erp", "crm"]}
  - {"id": "salary_inflation_red_herring", "rank": null, "summary": "A company-wide raise of ~3.5-4% in Jan 2026 is visible on every payslip but explains only ~DKK 0.55m (about a third of the personnel increase and ~15% of the profit decline).", "systems": ["payroll"]}
- sweden: Stable control market: revenue roughly flat, win rate ~30%, slight margin improvement.

### company
- revenue_h1: 85.77m -> 88.82m
- operating_profit_h1: 11.97m -> 8.00m
- operating_margin_h1: 0.1396 -> 0.0900
- gross_margin_h1: 0.3989 -> 0.3682
- revenue_ytd_jan_aug: 113.16m -> 115.72m
- profit_ytd_jan_aug: 16.04m -> 10.65m
- other_opex_h1: 7.43m -> 8.09m

### bridge
- gross_profit_DK: -0.48m
- gross_profit_SE: 0.39m
- gross_profit_DE: -1.42m
- personnel_de_sales: -1.36m
- personnel_other: -0.44m
- opex_de: -0.58m
- opex_other: -0.08m
- total: -3.97m
- profit_change: -3.97m
- germany_total: -3.36m
