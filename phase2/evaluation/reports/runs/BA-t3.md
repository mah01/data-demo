# Evaluation BA-t3: PASS

**Question (blind):** How is the business doing? Is there anything I should be concerned about?

Model `claude-opus-5` · 54 tool calls · systems: crm, erp, identity, meta, payroll · 337.5 s · output tokens 17153 · cost $3.002653 · tool errors 0 · repeated identical calls 0

**Summary.** The deepest open-ended run. Beyond revenue vs profit, the Danish renewal round, discounting and the German expansion, it drilled to customer level unprompted: it found the bulk reassignment of 13 accounts to the new hires, identified Rheinmark (-2.6M) and Brandauer (-2.2M) as the company's two largest customer declines, and quoted the handover notes. It also noticed that the CRM loss-reason field contradicts the reps' notes on several lost Danish renewals ('insourced maintenance' vs 'found cheaper service partner') and flagged the field as unreliable. That is a genuine inconsistency in the dataset. Two minor factual slips.

| dimension | assessment |
|---|---|
| factual correctness | Mostly high. Two slips: the new hires' 8 wins are said to be worth 3.4M (actual 2.64M), and 'the other 11 reassigned accounts actually grew' generalises a net +1.71M where 8 of 11 grew. |
| coverage | Very good. All major encoded drivers except explicit salary-inflation treatment. |
| causal reasoning | Strong. Causes described as 'well supported but not proven'; considers that some Danish equipment growth may have been bought with discounts. |
| cross system reasoning | Excellent. ERP -> CRM renewals/notes; payroll hires -> CRM owner history -> identity -> ERP customer revenue -> CRM activities. |
| evidence | Traceable. |
| unsupported claims | None beyond the two numeric slips. |
| investigation quality | Excellent. 54 calls; followed the German decline to customers and cross-checked loss reasons against note text. |

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
  4. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["month"], "sort_by": "month", "ascending": true}
  5. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market", "category"]}
  6. `erp_sales_summary` {"period": "2025-01..2026-08", "market": "DK", "category": "Service", "group_by": ["quarter"], "sort_by": "quarter", "ascending": true}
  7. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "category": "Service", "group_by": ["product"]}
  8. `crm_renewals` {"period": "2025-01..2026-08", "limit": 5}
  9. `crm_renewals` {"period": "2024-09..2024-12", "limit": 100}
 10. `crm_renewals` {"period": "2025-09..2025-12", "limit": 100}
 11. `crm_loss_reasons` {"period": "2025-09..2025-12", "deal_type": "Renewal", "include_renewals": true}
 12. `erp_sales_summary` {"period": "2025-01..2026-08", "category": "Equipment", "group_by": ["market", "quarter"], "sort_by": "quarter", "ascending": true}
 13. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["account"]}
 14. `payroll_headcount` {"basis": "average_monthly", "period": "2026-01..2026-08", "group_by": ["country", "department"]}
 15. `payroll_headcount` {"basis": "average_monthly", "period": "2025-01..2025-08", "group_by": ["country", "department"]}
 16. `payroll_hires_and_departures` {"period": "2025-01..2026-08"}
 17. `payroll_personnel_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["country", "department"]}
 18. `erp_sales_summary` {"period": "2025-01..2026-08", "market": "DE", "group_by": ["quarter"], "sort_by": "quarter", "ascending": true}
 19. `crm_win_rate` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 20. `crm_pipeline` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 21. `crm_win_rate` {"period": "2025-09..2026-08", "market": "DE", "group_by": ["owner"]}
 22. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Equipment", "market": "DK", "group_by": ["product"]}
 23. `crm_loss_reasons` {"period": "2026-01..2026-08", "market": "DE"}
 24. `crm_loss_reasons` {"period": "2025-01..2025-08", "market": "DE"}
 25. `crm_loss_reasons` {"period": "2026-01..2026-08", "market": "DK"}
 26. `crm_deals` {"deal_type": "Renewal", "outcome": "open", "limit": 100}
 27. `crm_deals` {"market": "DE", "outcome": "won", "date_field": "closed", "period": "2025-01..2026-08", "deal_type": "New Business", "limit": 100, "sort_by": "closed_at"}
 28. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 15}
 29. `crm_owner_history` {"period": "2025-06..2026-08", "limit": 100}
 30. `identity_find_company` {"query": "Brandauer"}
 31. `identity_crm_companies_to_erp` {"company_ids": ["cmp_95298", "cmp_60635", "cmp_38410", "cmp_71526", "cmp_63758", "cmp_67619", "cmp_78239", "cmp_92184", "cmp_82561", "cmp_52669", "cmp_52777", "cmp_15266", "cmp_31816"]}
 32. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DE", "limit": 100, "sort_by": "revenue_dkk_change", "ascending": true}
 33. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "52902"}
 34. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "14959"}
 35. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "44633"}
 36. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "39862"}
 37. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "65426"}
 38. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "31957"}
 39. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "44987"}
 40. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "53068"}
 41. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "18406"}
 42. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "44592"}
 43. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "19734"}
 44. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "21231"}
 45. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "33570"}
 46. `crm_activities` {"company_id": "cmp_71526", "limit": 30}
 47. `crm_activities` {"company_id": "cmp_82561", "limit": 30}
 48. `crm_activities` {"text_contains": "insourc", "limit": 20}
 49. `crm_activity_summary` {"period": "2024-09..2026-08", "owner_ids": ["usr_313798"], "group_by": ["quarter"]}
 50. `crm_activities` {"deal_id": "9349783739", "limit": 15}
 51. `crm_activities` {"deal_id": "9343725155", "limit": 15}
 52. `crm_activities` {"text_contains": "service", "activity_type": "NOTE", "period": "2025-09..2026-08", "owner_ids": ["usr_313798"], "limit": 20}
 53. `crm_renewals` {"period": "2026-01..2026-08", "limit": 30}
 54. `crm_pipeline` {"period": "2026-08", "basis": "open_at_end", "group_by": ["market"]}

## Final answer

## NordFlow: January–August 2026 compared with January–August 2025

**Bottom line:** Revenue is flat (+2%), but operating profit is down about a third, from 16.0M to 10.6M DKK, and the operating margin fell from 14.2% to 9.2%. Four problems explain almost all of it. Three of them are still going on.

| Jan–Aug, DKK M (ERP) | 2025 | 2026 | Change |
|---|---|---|---|
| Revenue | 113.2 | 115.7 | +2.3% |
| Gross profit | 45.3 | 42.9 | −5.3% |
| Gross margin | 40.0% | 37.1% | −3.0 pts |
| Personnel costs | 19.5 | 21.9 | +12.0% |
| Other operating costs | 9.7 | 10.4 | +6.6% |
| **Operating profit** | **16.0** | **10.6** | **−33.6%** |

### What concerns me

**1. Danish service contracts are being lost. This is the largest and most profitable single problem.**
- **Facts:** Danish Service revenue is down 23% (−4.3M) and its gross profit is down 2.55M. That drop alone is bigger than the whole company's gross-profit decline. Service carries a 59% margin, against about 25% on Equipment. (ERP)
- The cause is the renewal round in late 2025. In the CRM, 64% of contracts were renewed, against 85% a year earlier. In Denmark only 23 of 39 renewed (59%), against 38 of 45 the year before. The lost Danish contracts were worth about 3.7M a year.
- The loss shows up across the board: service agreements −24%, technician hours −25% and call-out fees −25%. Losing a contract also loses the extra work that comes with it.
- **What I can't confirm:** why customers left. The loss-reason field says "insourced maintenance" most often, but the reps' notes on several of those same deals say "found cheaper service partner" or "budget cut". I'd treat the field as unreliable. The notes point mainly to price competition and budget pressure.
- **Why it matters now:** the mid-year 2026 renewals went better (84%). The next big renewal round is in Q4, and no renewal deals have been opened in the CRM yet. Denmark still has 8 service technicians. Their pay is a fixed personnel cost, so lost service revenue goes almost straight to operating profit.

**2. Discounts are higher, which is squeezing margins.**
- **Facts:** The average discount on Equipment rose from 6.9% to 10.8% in Denmark and from 7.0% to 15.3% in Germany. (ERP)
- In Denmark the rise started in Q1 2026 and hit almost every Equipment product at once (+3–5 points). A change that uniform suggests a pricing policy change rather than individual deals, but I found nothing that confirms it.
- In Germany, discounts on won deals went from about 5–10% to 14–19% from late 2025, for experienced and new reps alike. (CRM)
- **Rough size:** if discounts had stayed at 2025 levels, gross profit would be about 3M higher. That assumes the same volumes, which is optimistic, because some of Denmark's +28% Equipment growth was probably bought with the discounts.

**3. Germany has spent more on sales but is selling less.**
- **Facts:** Four sales staff were hired between September 2025 and January 2026. German sales headcount went from 8 to 12, and the team's employer cost rose 1.77M (+49%). That is about 75% of the company's increase in personnel costs. (Payroll)
- Over the same period, German revenue fell 8% (−2.3M). The win rate dropped from 30% to 18%, even though new pipeline was up 35%. (ERP/CRM)
- New loss reasons appeared in 2026, "Not qualified" and "No response", and 23% of losses have no reason recorded. That suggests more but weaker pipeline.
- The four new hires have won 8 deals worth 3.4M in total. It's still early for them, but it is well below what they cost.
- **Key accounts damaged in the handover:** 13 accounts were bulk-reassigned to the new hires. Two of them, Rheinmark Chemie (−2.6M) and Brandauer Papierwerke (−2.2M), are the company's two largest customer declines. Together they account for more than all of Germany's decline. The other 11 reassigned accounts actually grew.
  - At Rheinmark, the maintenance manager asked why Stefan no longer covered the site and wanted continuity. The service contract was then lost to a competitor, and later so was a pump project.
  - At Brandauer, purchasing "had not been informed" of the new contact. They then moved spare parts to a local distributor.

**4. Other costs are up 0.64M.** Travel, car costs and marketing each rose about 20–25%, partly offset by lower recruitment spend. This is minor next to the first three.

### What's going well
- Sweden is steady: revenue and margins are slightly up in every product category.
- Danish Equipment volume is up 28% and Components are up 4%.
- New pipeline across the company is up 16%, and the 2026 mid-year renewals were 84%.
- Payroll and ERP personnel costs match exactly (21.89M), so the cost figures are reliable.

### Suggested priorities
1. **Start the Q4 2026 renewal round early.** Focus on Denmark's larger contracts, and decide in advance how to respond on price.
2. **Review the discount policy.** Find out whether the Danish change in Q1 was deliberate and who approves discounts in Germany.
3. **Recover the damaged German accounts and review the new team.** Agree a plan for Rheinmark and Brandauer, and set targets and a review date for the new team's pipeline quality and win rates.
4. **Fix loss-reason recording in the CRM.** At the moment we can't reliably tell why we lose deals.

**Caveats:** The ERP and CRM convert currencies at slightly different rates. Q3 2026 only covers July and August. Where I describe causes, they come from the CRM notes and from timing; they are well supported but not proven.