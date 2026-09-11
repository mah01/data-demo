# Evaluation BB-t2: PASS

**Question (blind):** What deserves management attention right now?

Model `claude-opus-5` · 58 tool calls · systems: crm, erp, identity, meta, payroll · 336.6 s · output tokens 15813 · cost $2.9880864999999996 · tool errors 2 · repeated identical calls 0

**Summary.** Three priorities: Danish service renewals (renewal rate 83% -> 64%, 18 losses worth 4.26M, next round imminent with no open deals), equipment discounting (team-wide in DK and DE, about 2.9M), and Germany (8 -> 12, win rate 30% -> 18%, new hires 12% vs veterans 22.6%). Unprompted, it reached customer level: the 13-account bulk reassignment and the two largest losses, Rheinmark (-2.6M) and Brandauer (-2.2M), together more than Germany's net decline. It notes the mixed picture across reassigned accounts.

| dimension | assessment |
|---|---|
| factual correctness | High. |
| coverage | Very good. All major drivers except explicit salary-inflation treatment. |
| causal reasoning | Strong. 'The data doesn't prove that the reassignment caused the losses'; the qualification weakness is labelled an inference. |
| cross system reasoning | Excellent. ERP -> identity -> CRM owner history and deals; payroll hires -> CRM owner win rates. |
| evidence | Traceable. |
| unsupported claims | None. |
| investigation quality | Excellent. 58 calls (the most of any run); two date-format errors recovered. |

**Discoveries** (manual; ✓ found, ~ partly, ✗ not found, – not applicable)

- Overall revenue growth but operating-profit deterioration: ✓
- Germany as a major contributor to the profit decline: ✓
- German sales headcount expansion (8 -> 12): ✓
- Pipeline growth combined with worse conversion (win rate): ✓
- Poor new-rep performance (new hires convert worse): ✓
- Rheinmark / Brandauer identified at customer level: ✓
- Danish revenue growth masking mix / margin deterioration: ✓
- Salary inflation insufficient to explain the profit decline: ✗

## Tool trace

  1. `meta_describe_sources` {}
  2. `meta_get_semantics` {}
  3. `erp_financial_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08"}
  4. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
  5. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["category"]}
  6. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["month"], "sort_by": "month", "ascending": true}
  7. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market", "category"]}
  8. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["quarter", "market"], "category": "Equipment", "sort_by": "quarter", "ascending": true}
  9. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["quarter", "market"], "category": "Service", "sort_by": "quarter", "ascending": true}
 10. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "category": "Service", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 30}
 11. `crm_renewals` {"period": "2025-09..2026-08", "limit": 5}
 12. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "category": "Service", "group_by": ["product"]}
 13. `crm_win_rate` {"period": "2025-09..2026-08", "compare_to": "2024-09..2025-08", "deal_type": "Renewal", "group_by": ["market"]}
 14. `crm_loss_reasons` {"period": "2025-09..2026-08", "deal_type": "Renewal", "market": "DK"}
 15. `payroll_hires_and_departures` {"period": "2025-01..2026-08"}
 16. `payroll_headcount` {"basis": "average_monthly", "period": "2025-01..2026-08", "group_by": ["country", "department"]}
 17. `payroll_personnel_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["country", "department"]}
 18. `crm_win_rate` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 19. `crm_pipeline` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 20. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["account"]}
 21. `crm_win_rate` {"period": "2026-01..2026-08", "market": "DE", "group_by": ["owner"]}
 22. `crm_loss_reasons` {"period": "2026-01..2026-08", "market": "DE"}
 23. `crm_deals` {"period": "2025-07..2026-08", "date_field": "closed", "outcome": "won", "product_category": "Equipment", "limit": 150, "sort_by": "discount_pct"}
 24. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Equipment", "group_by": ["product"], "market": "DE"}
 25. `erp_customer_revenue` {"period": "2026-01..2026-08", "market": "DK", "category": "Equipment", "first_invoice_from": "2025-09-01", "limit": 40} **ERROR**
 26. `crm_deals` {"period": "2026-01..2026-08", "date_field": "closed", "outcome": "won", "min_value_dkk": 400000, "limit": 40, "sort_by": "discount_pct"}
 27. `crm_activities` {"text_contains": "rabat", "period": "2025-07..2026-09", "limit": 15}
 28. `crm_activities` {"text_contains": "Rabatt", "period": "2025-07..2026-09", "limit": 15}
 29. `crm_activities` {"text_contains": "insourc", "limit": 15}
 30. `crm_activities` {"text_contains": "discount", "limit": 15}
 31. `crm_activities` {"text_contains": "price", "period": "2025-07..2026-09", "limit": 15}
 32. `crm_renewals` {"period": "2025-09..2026-08", "market": "DK", "outcome": "lost", "limit": 20}
 33. `crm_deals` {"deal_type": "Renewal", "outcome": "open", "limit": 60, "sort_by": "value_dkk"}
 34. `crm_users` {}
 35. `crm_pipeline` {"period": "2026-08", "basis": "open_at_end", "group_by": ["market", "stage"], "compare_to": "2025-08"}
 36. `crm_deals` {"outcome": "open", "date_field": "expected_close", "period": "2024-09..2026-08", "limit": 5, "sort_by": "value_dkk"}
 37. `crm_win_rate` {"period": "2026-01..2026-08", "market": "DK", "group_by": ["owner"], "compare_to": "2025-01..2025-08"}
 38. `crm_deals` {"owner_ids": ["usr_681988"], "outcome": "won", "date_field": "closed", "period": "2025-01..2026-08", "product_category": "Equipment", "limit": 40, "sort_by": "closed_at"}
 39. `crm_deals` {"owner_ids": ["usr_912432", "usr_491244"], "outcome": "won", "date_field": "closed", "period": "2025-01..2026-08", "product_category": "Equipment", "limit": 40, "sort_by": "closed_at"}
 40. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DE", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 10}
 41. `erp_customer_revenue` {"period": "2026-01..2026-08", "market": "DE", "first_invoice_from": "2025-09-01", "first_invoice_to": "2026-08-31", "limit": 20} **ERROR**
 42. `identity_erp_customers_to_crm` {"customer_numbers": ["14959", "52902"]}
 43. `crm_deals` {"company_id": "cmp_82561", "limit": 15}
 44. `crm_owner_history` {"company_id": "cmp_82561"}
 45. `crm_owner_history` {"company_id": "cmp_71526"}
 46. `crm_owner_history` {"period": "2025-07..2026-08", "limit": 100}
 47. `identity_crm_companies_to_erp` {"company_ids": ["cmp_95298", "cmp_60635", "cmp_38410", "cmp_71526", "cmp_63758", "cmp_67619", "cmp_78239", "cmp_92184", "cmp_82561", "cmp_52669", "cmp_52777", "cmp_15266", "cmp_31816"]}
 48. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DE", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 100}
 49. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "39862"}
 50. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "65426"}
 51. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "31957"}
 52. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "44987"}
 53. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "53068"}
 54. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "18406"}
 55. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "44592"}
 56. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "19734"}
 57. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "21231"}
 58. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "33570"}

## Final answer

I'd put three things in front of management: Danish service contract losses, rising Equipment discounts, and a bigger German sales team whose sales have fallen. Revenue is up 2% on last year (Jan–Aug), but operating profit is down 34%, and those three explain most of it. Unless stated otherwise, figures compare Jan–Aug 2026 with Jan–Aug 2025, in DKK. Profit and sales figures come from the ERP (finance system), deals from the CRM (sales system), and staff costs from payroll.

## The overall picture

| | Jan–Aug 2025 | Jan–Aug 2026 | Change |
|---|---|---|---|
| Revenue | 113.2m | 115.7m | +2.3% |
| Gross margin | 40.0% | 37.1% | −3.0 pts |
| Personnel costs | 19.5m | 21.9m | +12.0% |
| Operating profit | 16.0m | 10.6m | **−5.4m (−34%)** |

Where the 5.4m went:
- **Lower gross profit: −2.4m.** DK Service −2.55m, DE Equipment −1.1m and DE Components −0.54m. These were partly offset by DK Equipment (+1.25m) and Sweden (+0.5m).
- **Higher personnel costs: +2.35m.** 1.77m of this is the German sales team.
- **Higher other operating costs: +0.64m.** Mainly travel, cars, marketing and rent, each up about 0.2m.

## 1. Danish service revenue is down 23%, driven by lost contract renewals (most urgent)

**What the data shows:**
- DK Service revenue fell from 19.1m to 14.8m (−4.3m), and gross profit fell 2.55m. Both service contracts (−24%) and technician hours (−25%) dropped, spread across many customers.
- The DK renewal rate fell from 83% to 64% (CRM, 12 months to August). 18 renewals worth 4.26m were lost. The most common recorded reason is "customer insourced maintenance" (7 deals, 2.3m), followed by "price too high" (4) and "lost to competitor" (4).
- 15 of the 18 losses closed in December 2025, and all 18 are owned by one person, Line Østergaard (Service Sales).
- Technician headcount did not change: one technician left in September 2025 and was replaced in November. So a lack of capacity doesn't explain the drop.

**Why it's urgent:** the next December renewal cycle is about three months away, and there are currently no open renewal deals in the CRM. Last year's cycle was set up in October–November, so this isn't overdue yet, but it's the moment to act. Two things are worth doing: talk to the lost customers to confirm the insourcing reason, and review the renewal approach and the reliance on one owner before the cycle opens.

## 2. Equipment discounts have jumped and are eroding margin

**What the data shows:**
- The average Equipment discount rose from 7.0% to 11.2%, and Equipment gross margin fell from 28.4% to 25.4%.
- **Germany:** discounts went from 7.0% to 15.3%, and margin from 28.4% to 21.7%. The rise started in Q3 2025 and appears on all 23 Equipment products, while unit costs stayed flat. So this is about pricing, not product mix or input costs.
- **Denmark:** discounts went from 6.9% to 10.8%, starting in Q1 2026. This is team-wide: Katrine Moller, Rasmus Winther and JP Hansen all moved from roughly 4–9% on deals won in H1 2025 to roughly 9–13% in 2026.
- **Sweden:** discounts are stable at about 7%, and margin rose slightly.

**My estimate, not a measured fact:** at 2025 discount levels, this year's Equipment sales would have brought in roughly 2.9m more gross profit (about 1.6m DK, 1.3m DE). That assumes the same volumes, which may not hold if the discounts helped win deals.

**What's unclear:** I found nothing in the CRM notes that explains the change, such as a pricing policy or approval rule. Management should find out whether it was a deliberate decision.

## 3. Germany has four more salespeople but lower sales

**What the data shows:**
- The DE sales team grew from 8 to 12 between September 2025 and January 2026. DE sales payroll is up 1.77m (+49%).
- Over the same period, DE revenue fell 8% and gross profit fell 16%. The value of new deals created is up 35%, but the win rate dropped from 30% to 18% and won deal value fell 24%.
- The four new hires have won 8 of 67 closed deals (12%). The existing reps won 22.6%, still below last year's 30% team average, so the decline isn't only about the new people.
- Many notes on the new hires' deals read "Asked for price indication only". That suggests weakly qualified deals, but it's an inference.
- 13 German accounts were bulk-reassigned to the new hires. The two largest DE customer losses are among them:
  - **Rheinmark Chemie:** revenue −2.6m. Its service renewal was lost to a competitor in December 2025.
  - **Brandauer Papierwerke:** revenue −2.2m. Its spare-parts framework agreement was lost to a competitor in January 2026.
  - Across all 13 accounts the result is mixed: net about −3m, but several grew, such as Lebensmittel Donautal (+1.3m). So the data doesn't prove that the reassignment caused the losses.
- The two lost accounts alone (−4.8m) are more than Germany's whole net decline (−2.3m).

**Worth doing:** a review of the German sales ramp-up: how deals are qualified, discount authority, and how key accounts are handed over.

## Smaller points
- 24 open deals have an expected close date that has already passed, which makes the sales forecast less reliable.
- Other operating costs are up 6.6%. Travel (+26%), marketing (+23%) and car costs (+19%) are rising faster than revenue.
- Sweden is the steady performer: revenue +2%, gross profit +5.5%, stable discounts and a 91% renewal rate.

**Caveat:** the CRM loss reasons are chosen by salespeople and are often left blank (23% of German losses have none), so treat them as pointers rather than proof.