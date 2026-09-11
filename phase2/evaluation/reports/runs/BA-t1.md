# Evaluation BA-t1: PASS

**Question (blind):** How is the business doing? Is there anything I should be concerned about?

Model `claude-opus-5` · 33 tool calls · systems: crm, erp, meta, payroll · 228.8 s · output tokens 12075 · cost $2.4293415 · tool errors 0 · repeated identical calls 0

**Summary.** Unprompted, it established revenue +2.3% vs operating profit -34% and a clean bridge, then surfaced three concerns: lost Danish service contracts (biggest; December 2025 renewal round, 16 of 39 lost, insourcing reason), equipment discounting in DK and DE, and the German sales expansion not paying off (8 -> 12, pipeline +35%, win rate 30% -> 18%, new hires 8 of 67). It did not drill to German customers, so the key-account attrition is missing, and it did not address pay rises.

| dimension | assessment |
|---|---|
| factual correctness | High. Figures verified. |
| coverage | Good breadth. Missing the German key-account attrition, the largest single German revenue driver. |
| causal reasoning | Good. Discount cause 'couldn't find'; ramp-up caveat for new hires. |
| cross system reasoning | Good. ERP service decline <-> CRM renewals <-> ERP invoice lines; payroll hires <-> CRM win rates. |
| evidence | Traceable. |
| unsupported claims | None. |
| investigation quality | Good. 33 calls, systematic; stopped at market/rep level for Germany. |

**Discoveries** (manual; ✓ found, ~ partly, ✗ not found, – not applicable)

- Overall revenue growth but operating-profit deterioration: ✓
- Germany as a major contributor to the profit decline: ✓
- German sales headcount expansion (8 -> 12): ✓
- Pipeline growth combined with worse conversion (win rate): ✓
- Poor new-rep performance (new hires convert worse): ✓
- Rheinmark / Brandauer identified at customer level: ✗
- Danish revenue growth masking mix / margin deterioration: ✓
- Salary inflation insufficient to explain the profit decline: ✗

## Tool trace

  1. `meta_describe_sources` {}
  2. `meta_get_semantics` {}
  3. `erp_financial_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08"}
  4. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["month"], "sort_by": "month", "ascending": true}
  5. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market", "category"]}
  6. `crm_renewals` {"period": "2026-01..2026-08", "limit": 5}
  7. `crm_renewals` {"period": "2025-01..2025-08", "limit": 5}
  8. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Service", "market": "DK", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 25}
  9. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Service", "group_by": ["market", "product"]}
 10. `erp_sales_summary` {"period": "2025-01..2026-08", "category": "Service", "market": "DK", "group_by": ["month"], "sort_by": "month", "ascending": true}
 11. `payroll_headcount` {"on_date": "2025-08-31", "group_by": ["country", "department"]}
 12. `payroll_headcount` {"on_date": "2026-08-31", "group_by": ["country", "department"]}
 13. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Service", "market": "DK", "sort_by": "revenue_dkk_change", "ascending": false, "limit": 10}
 14. `erp_invoice_lines` {"product_number": "SA-STD", "market": "DK", "period": "2025-10", "limit": 60}
 15. `erp_invoice_lines` {"product_number": "SA-STD", "market": "DK", "period": "2026-07", "limit": 60}
 16. `crm_renewals` {"period": "2025-09..2025-12", "limit": 100}
 17. `crm_deals` {"deal_type": "Renewal", "outcome": "open", "limit": 100}
 18. `payroll_personnel_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["country", "department"]}
 19. `payroll_hires_and_departures` {"period": "2025-06..2026-08"}
 20. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["account"]}
 21. `crm_win_rate` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 22. `crm_pipeline` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 23. `crm_win_rate` {"period": "2026-01..2026-08", "group_by": ["market", "owner"], "sort_by": "won_value_dkk"}
 24. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["department"], "account_type": "opex"}
 25. `crm_loss_reasons` {"period": "2026-01..2026-08", "market": "DE"}
 26. `crm_loss_reasons` {"period": "2025-01..2025-08", "market": "DE"}
 27. `crm_deals` {"market": "DE", "outcome": "won", "date_field": "closed", "period": "2026-01..2026-08", "limit": 40, "sort_by": "value_dkk"}
 28. `erp_sales_summary` {"period": "2025-01..2026-08", "category": "Equipment", "group_by": ["quarter", "market"], "sort_by": "quarter", "ascending": true}
 29. `crm_activities` {"text_contains": "rabat", "limit": 15}
 30. `crm_activities` {"text_contains": "discount", "limit": 15}
 31. `crm_deals` {"market": "DK", "outcome": "won", "date_field": "closed", "period": "2026-01..2026-08", "product_category": "Equipment", "limit": 50, "sort_by": "value_dkk"}
 32. `crm_deals` {"market": "DK", "outcome": "won", "date_field": "closed", "period": "2025-07..2025-12", "product_category": "Equipment", "limit": 50, "sort_by": "value_dkk"}
 33. `crm_pipeline` {"period": "2026-08", "basis": "open_at_end", "compare_to": "2025-08", "group_by": ["market"]}

## Final answer

## How the business is doing (Jan–Aug 2026 vs Jan–Aug 2025)

Revenue is up slightly, but profit is falling fast. Revenue grew 2.3% to 115.7M DKK, while operating profit fell 34%, from 16.0M to 10.6M.

| Metric (ERP) | 2025 | 2026 | Change |
|---|---|---|---|
| Revenue | 113.2M | 115.7M | +2.3% |
| Gross margin | 40.0% | 37.1% | −3.0 pts |
| Personnel costs | 19.5M | 21.9M | +12.0% |
| Other operating costs | 9.7M | 10.4M | +6.6% |
| **Operating margin** | **14.2%** | **9.2%** | **−5.0 pts** |

The 5.4M drop in operating profit comes from three things: 2.4M less gross profit, 2.35M more personnel cost and 0.6M more other costs. Three issues explain most of it.

### 1. Lost service contracts in Denmark (the biggest concern)
- **What happened:** Danish Service revenue fell 22.6% (−4.3M). Service agreements, technician hours and call-out fees all fell by about 24.5%. Service is the highest-margin line at about 59%, so this alone cost about 2.55M of gross profit.
- **Cause:** The CRM shows a poor December 2025 renewal round. Only 35 of 55 renewals were won (64%), against about 85% in other renewal periods, and 5.2M of annual contract value was lost.
- **Denmark specifically:** 16 of 39 renewals were lost, worth about 3.7M a year. The most common recorded reason was "Customer insourced maintenance" (7 contracts, about 2.3M). Examples are Køge Bygningsservice, Herning Foder and Lolland Emballage.
- **Cross-check:** Billing confirms it. Danish service-agreement invoices fell from 53 in Oct 2025 to 40 in Jul 2026.
- **Watch point:** The next calendar-year renewal round is in Oct–Dec 2026. If customers keep bringing maintenance in-house, this could repeat.

### 2. Bigger discounts are eroding Equipment margins
- **Denmark:** Average Equipment discount jumped from about 7.0% in Q4 2025 to 10.5% in Q1 2026 and has stayed there. Revenue rose 28%, but gross margin fell from 28.4% to 25.6%.
- **Germany:** Discounts climbed steadily, from 6.7% in early 2025 to about 15.5% now. Margin fell from 28.4% to 21.7%, and revenue still dropped 5%.
- **Sweden:** Unchanged at about 7%, with stable margins.
- The CRM shows this is not one or two reps. Every rep's won Equipment deals moved up, from 4–9% in late 2025 to 8–14% in Denmark and 14–20% in Germany.
- **What I couldn't find:** The CRM notes don't explain why. I can't tell whether this was a pricing decision or a response to competitors. Worth asking the sales leaders.
- **Rough scale:** At last year's discount rates, this year's Equipment sales would have brought in about 2.9M more. This assumes the same volumes would have been won, which may not be true.

### 3. The German sales expansion isn't paying off yet
- **Cost:** German Sales grew from 8 to 12 people (four hires, Sep 2025–Jan 2026). That added 1.77M in personnel cost (+49%), and costs booked to Germany rose a further 0.5M (+26%).
- **Results so far:**
  - The CRM shows 35% more new pipeline created.
  - But win rate fell from 30% to 18%, and won value dropped 24%.
  - German invoiced revenue is down about 8%.
- **By rep:** The new hires have won 8 of 67 closed deals. Established reps are also winning less, e.g. Florian Braun 2 of 15 and Markus Becker 2 of 14.
- **Why deals are lost:** "Price too high" rose from 19 to 27 losses despite the higher discounts. Losses with no reason recorded rose from 12 to 30.
- **Interpretation:** New hires usually take time to become productive, so this isn't a final verdict. But so far the extra cost has not produced more wins.

### What's going well
- Sweden is stable, with slightly better margins.
- The Danish new-sales win rate is steady at 35%, and won value is up 16%.
- Open pipeline at end of August is 18% higher than a year ago (47.3M vs 40.2M).
- Components margins are unchanged.

### Suggested next steps
1. Start the December 2026 renewal round early, especially with customers at risk of taking maintenance in-house.
2. Review who approves discounts and why they rose in January 2026.
3. Set clear targets and a review date for the German team.

*Data caveats:* Loss reasons in the CRM are optional and often blank. The payroll journal is not split by market. The CRM and ERP use slightly different exchange rates, so their figures won't match exactly.