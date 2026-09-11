# Worksheet BC-t3

**Question (blind):** Where would you investigate first if you were the CEO?

Status: completed | model claude-opus-5 | 31 tool calls | systems crm, erp, identity, meta, payroll | 160.3 s | cost $1.6554160000000002 | isolation ok: True

## Tool trace

  1. `meta_describe_sources` {}
  2. `meta_get_semantics` {}
  3. `erp_financial_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08"}
  4. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["quarter", "market"]}
  5. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market", "category"]}
  6. `payroll_personnel_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["country", "department"]}
  7. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["account"]}
  8. `erp_sales_summary` {"period": "2025-01..2026-08", "market": "DK", "category": "Service", "group_by": ["month"], "sort_by": "month", "ascending": true}
  9. `crm_renewals` {"period": "2025-01..2026-08", "limit": 5}
 10. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "category": "Service", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 20}
 11. `crm_renewals` {"period": "2025-10..2026-01", "market": "DK", "outcome": "lost", "limit": 30}
 12. `crm_win_rate` {"period": "2025-01..2026-08", "deal_type": "Renewal", "group_by": ["market", "half"]}
 13. `crm_loss_reasons` {"period": "2025-07..2026-08", "deal_type": "Renewal", "market": "DK"}
 14. `identity_find_person` {"query": "Line Østergaard"}
 15. `crm_owner_history` {"owner_id": "usr_313798", "limit": 100}
 16. `crm_win_rate` {"period": "2025-01..2026-08", "deal_type": "Renewal", "group_by": ["owner", "half"]}
 17. `payroll_hires_and_departures` {"period": "2025-01..2026-08"}
 18. `crm_win_rate` {"period": "2025-01..2026-08", "group_by": ["market", "half"]}
 19. `crm_pipeline` {"period": "2025-01..2026-08", "group_by": ["market", "half"]}
 20. `crm_win_rate` {"period": "2026-01..2026-08", "market": "DE", "group_by": ["owner"], "compare_to": "2025-01..2025-08"}
 21. `crm_loss_reasons` {"period": "2026-01..2026-08", "market": "DE"}
 22. `erp_sales_summary` {"period": "2025-01..2026-08", "category": "Equipment", "group_by": ["market", "quarter"], "sort_by": "quarter", "ascending": true}
 23. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "category": "Equipment", "group_by": ["customer"], "limit": 15}
 24. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "category": "Equipment", "group_by": ["product"], "limit": 20}
 25. `crm_activities` {"text_contains": "rabat", "period": "2025-10..2026-08", "limit": 15}
 26. `crm_activities` {"text_contains": "discount", "period": "2025-10..2026-08", "limit": 15}
 27. `crm_activities` {"text_contains": "insourc", "limit": 10}
 28. `crm_activity_summary` {"period": "2025-01..2026-08", "owner_ids": ["usr_313798"], "group_by": ["quarter", "type"]}
 29. `crm_activities` {"deal_id": "9349783739", "limit": 10}
 30. `crm_activities` {"deal_id": "9343725155", "limit": 10}
 31. `crm_deals` {"deal_type": "Renewal", "outcome": "open", "limit": 50}

## Final answer

I'd start with **Germany**, but set up a parallel check on **Danish service-contract renewals** straight away, because the next renewal round is only weeks away. Year-to-date (Jan–Aug), revenue is up 2.3% but operating profit fell from 16.0m to 10.6m DKK (−34%). Germany accounts for about two-thirds of that drop.

**Where the 5.4m DKK operating-profit drop came from** (ERP and payroll, Jan–Aug 2026 vs. Jan–Aug 2025)

| Driver | Impact (m DKK) |
|---|---|
| Germany: lower gross profit (Equipment −1.11, Components −0.54, Service −0.14) | −1.79 |
| Germany: higher sales payroll | −1.77 |
| Denmark: lower Service gross profit | −2.55 |
| Denmark: higher Equipment gross profit (more volume, lower margin) | +1.25 |
| Sweden and DK Components | +0.69 |
| Other payroll (mostly normal ~3% raises) and other operating costs | −1.22 |

## 1. Germany: bigger sales team, lower win rate, bigger discounts

**What the data shows:**
- **More staff, less revenue:** Germany hired 4 salespeople between Sep 2025 and Jan 2026, taking the team from 8 to 12. Sales payroll rose from 3.64m to 5.41m DKK (+49%), while German revenue fell about 8% (payroll, ERP).
- **More pipeline, fewer wins:** New pipeline in H1 2026 was 35% higher than a year earlier. But the win rate fell from 30% to 18%, excluding renewals (CRM).
- **The new hires closed 8 of 67 deals (12%).** Win rates for experienced reps dropped too: Stefan Brenner 47%→23%, Julia Fischer-Lang 38%→15%, Florian Braun 30%→13%. Only Tobias Wagner improved (32%→47%).
- **Discounts on German equipment doubled,** from 7.0% to 15.3%, and gross margin fell from 28.4% to 21.7% (ERP).

**My read (interpretation, not proven):** Adding people generated more pipeline, but not more wins, and the deals that did close needed deeper discounts. The data can't tell whether that's competitors, pricing or sales execution. 23% of German losses have no reason recorded, and "price too high" and "lost to a competitor" are each about 20%.

## 2. Denmark: service contracts lost in the December renewal round (time-critical)

- **Service revenue down 23%:** Danish service billing peaks every quarter, which looks like contract invoicing. Those peaks fell 22–25% from January 2026 (e.g. April: 4.48m → 3.34m DKK). Service is the highest-margin category at about 59%.
- **The December 2025 round lost 16 of 39 contracts,** worth 3.7m DKK a year. Other rounds renew about 80%.
- **One person owns every Danish renewal (Line Østergaard).** The accounts weren't reassigned, and she logged far more activity in Q4 2025 than in other quarters. So this doesn't look like neglect, but it is a key-person risk.
- **The next round is about to open.** Last year's renewal deals were created in Oct–early Nov, and none exist in the CRM yet.
- **Some of these relationships are still active.** Several lost service customers still buy equipment, at higher discounts (e.g. Lolland Emballage). They may be winnable back.

**Don't rely on the recorded loss reasons.** Herning Foder is coded "customer insourced maintenance", but the rep's own note says "found cheaper service partner."

## 3. Equipment discounting in Denmark (and Germany)

- **Denmark jumped in one step:** the equipment discount went from 7.0% in Q4 2025 to 10.5% in Q1 2026. It rose across all 20 main products and nearly every major customer, which points to a policy or pricing change rather than one big deal.
- **Sweden is the useful comparison:** its discounts stayed flat (~6.9%) and its equipment margin rose.
- **Cost:** the lower equipment margins in Denmark and Germany together cost about 2.0m DKK in gross profit year-to-date.
- **No explanation found:** there are no CRM notes about pricing or discounts.

## Lower priority
- Other operating costs rose 0.6m DKK, mainly travel, cars and trade fairs.
- Swedish results are stable or improving.
- Staff outside sales got roughly 3% raises.

## Questions I'd ask first
1. **Germany:** What was the business case for the four hires, and when were they expected to pay off? Who approves discounts above 10%? Why did experienced reps' win rates fall as well?
2. **Denmark pricing:** What changed on 1 January? For example a new price list, more discount authority for reps, or a change to sales pay. Commission is up 17% and bonuses are down 17% year-to-date, which could fit a pay-plan change, but I haven't checked that.
3. **Service renewals:** What's the plan for the next round, and does it go beyond one account owner? Should we try to win back the lost customers who still buy equipment from us?

Two things to keep in mind: Q3 2026 only includes July and August so far, which is why I compared January–August for both years. And the CRM, ERP and payroll each convert currencies at their own rates, so figures from different systems can differ slightly.

## Automatic discovery signals

| item | stated | investigated | snippet |
|---|---|---|---|
| revenue_up_profit_down | True | True | Year-to-date (Jan–Aug), revenue is up 2.3% but operating profit fell from 16.0m to 10.6m DKK (−34%). |
| germany_major_contributor | True | True | / Germany: lower gross profit (Equipment −1.11, Components −0.54, Service −0.14) / −1.79 / |
| german_sales_headcount_expansion | True | True | - **More staff, less revenue:** Germany hired 4 salespeople between Sep 2025 and Jan 2026, taking the team from 8 to 12. |
| pipeline_up_conversion_down | True | True | Germany: bigger sales team, lower win rate, bigger discounts |
| new_rep_underperformance | True | True | - **The new hires closed 8 of 67 deals (12%).** Win rates for experienced reps dropped too: Stefan Brenner 47%→23%, Julia Fischer-Lang 38%→15%, Florian Braun 30 |
| key_accounts_named | False | True |  |
| denmark_mix_margin | True | True | I'd start with **Germany**, but set up a parallel check on **Danish service-contract renewals** straight away, because the next renewal round is only weeks away |
| salary_inflation_insufficient | True | False | / Other payroll (mostly normal ~3% raises) and other operating costs / −1.22 / |

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
