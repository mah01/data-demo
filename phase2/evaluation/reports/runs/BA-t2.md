# Evaluation BA-t2: PASS

**Question (blind):** How is the business doing? Is there anything I should be concerned about?

Model `claude-opus-5` · 35 tool calls · systems: crm, erp, meta, payroll · 158.5 s · output tokens 11471 · cost $1.7182074999999997 · tool errors 0 · repeated identical calls 0

**Summary.** Very similar to BA-t1: revenue +2.3% vs operating profit -33.6%, with a Q2 deterioration (revenue -3.4%, operating profit -41%, verified). Concerns: equipment discounting (all 23 products; unit costs unchanged), Germany costing more and selling less (8 -> 12, +1.77M payroll, win rate 30% -> 18%, not just new hires), and Danish service revenue -23% from the December 2025 renewal round. No customer-level German analysis; pay rises not addressed.

| dimension | assessment |
|---|---|
| factual correctness | High. Spot-checked claims correct (Q2 figures, best-performing rep at 47%). |
| coverage | Good breadth. Missing German key-account attrition and explicit treatment of salary inflation. |
| causal reasoning | Good. 'Decision or drift' left open; capacity ruled out as the cause of the service drop. |
| cross system reasoning | Good. Same pattern as BA-t1. |
| evidence | Traceable. |
| unsupported claims | None. |
| investigation quality | Good. 35 calls. |

**Discoveries** (manual; ✓ found, ~ partly, ✗ not found, – not applicable)

- Overall revenue growth but operating-profit deterioration: ✓
- Germany as a major contributor to the profit decline: ✓
- German sales headcount expansion (8 -> 12): ✓
- Pipeline growth combined with worse conversion (win rate): ✓
- Poor new-rep performance (new hires convert worse): ~
- Rheinmark / Brandauer identified at customer level: ✗
- Danish revenue growth masking mix / margin deterioration: ✓
- Salary inflation insufficient to explain the profit decline: ✗

## Tool trace

  1. `meta_describe_sources` {}
  2. `meta_get_semantics` {}
  3. `erp_financial_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08"}
  4. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["quarter"], "sort_by": "quarter", "ascending": true}
  5. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
  6. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["category"]}
  7. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market", "category"]}
  8. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["month", "category"], "category": "Equipment", "sort_by": "month", "ascending": true}
  9. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["quarter", "market"], "category": "Service", "sort_by": "quarter", "ascending": true}
 10. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Service", "market": "DK", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 30}
 11. `crm_renewals` {"period": "2025-01..2026-08", "limit": 5}
 12. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["product"], "category": "Service", "market": "DK"}
 13. `crm_renewals` {"period": "2025-01..2026-08", "market": "DK", "limit": 60}
 14. `payroll_headcount` {"group_by": ["country", "department"], "on_date": "2025-08-31"}
 15. `payroll_headcount` {"group_by": ["country", "department"], "on_date": "2026-08-31"}
 16. `payroll_hires_and_departures` {"period": "2025-01..2026-08"}
 17. `crm_renewals` {"period": "2025-01..2025-08", "limit": 1}
 18. `crm_renewals` {"period": "2025-09..2025-12", "limit": 1}
 19. `crm_renewals` {"period": "2026-01..2026-08", "limit": 1}
 20. `crm_loss_reasons` {"period": "2025-09..2026-08", "deal_type": "Renewal", "include_renewals": true}
 21. `crm_win_rate` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 22. `crm_win_rate` {"period": "2026-01..2026-08", "market": "DE", "group_by": ["owner"]}
 23. `crm_loss_reasons` {"period": "2026-01..2026-08", "market": "DE"}
 24. `crm_loss_reasons` {"period": "2025-01..2025-08", "market": "DE"}
 25. `payroll_personnel_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["country", "department"]}
 26. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["account"]}
 27. `crm_deals` {"market": "DE", "outcome": "won", "date_field": "closed", "period": "2026-01..2026-08", "deal_type": "New Business", "limit": 40}
 28. `crm_pipeline` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 29. `crm_pipeline` {"period": "2026-08", "basis": "open_at_end", "compare_to": "2025-08", "group_by": ["market"]}
 30. `crm_activities` {"text_contains": "rabat", "period": "2025-10..2026-08", "limit": 15}
 31. `crm_activities` {"text_contains": "discount", "period": "2025-10..2026-08", "limit": 15}
 32. `crm_activities` {"text_contains": "insourc", "limit": 10}
 33. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Equipment", "group_by": ["product"]}
 34. `crm_pipeline` {"period": "2026-08", "basis": "open_at_end", "deal_type": "Renewal", "group_by": ["market"]}
 35. `erp_financial_summary` {"period": "2026-Q2", "compare_to": "2025-Q2"}

## Final answer

# NordFlow business review: Jan–Aug 2026 vs Jan–Aug 2025

**In short:** Revenue is flat (+2%), but operating profit is down 34% and the drop got worse in Q2. There are three causes: bigger discounts on Equipment, lost Danish service contracts, and a German sales team that has grown without bringing in more sales.

## The numbers (ERP)

| Jan–Aug | 2025 | 2026 | Change |
|---|---|---|---|
| Revenue | 113.2M DKK | 115.7M DKK | +2.3% |
| Gross margin | 40.0% | 37.1% | −3.0 pts |
| Personnel costs | 19.5M | 21.9M | +12.0% |
| Operating profit | 16.0M | 10.6M | **−33.6%** |
| Operating margin | 14.2% | 9.2% | −5.0 pts |

The trend is getting worse, not better. In Q2 2026 alone, revenue fell 3.4% and operating profit fell 41% (operating margin went from 16.9% to 10.4%).

**Where the 5.4M DKK drop in operating profit came from:**
- **Lower gross profit (−2.4M):** Service −2.6M, Components −0.15M, Equipment +0.3M.
- **Higher personnel costs (+2.35M):** 1.77M of this is German Sales.
- **Higher other operating costs (+0.64M):** mainly travel, cars, marketing and rent.

## Concern 1: Equipment discounts jumped in January 2026

- **Facts (ERP):** The average Equipment discount went from 7.0% to 11.2%. It jumped in January 2026 and has stayed at 9.5–12% every month since. It went up on all 23 Equipment products. Unit costs didn't change (for example, the BS-3 costs 139,539 DKK per unit in both years), so the margin loss comes from lower prices, not higher costs.
- **By market:** Germany went from 7.0% to 15.3%, Denmark from 6.9% to 10.8%, and Sweden stayed flat.
- **Estimate:** Selling at 2025 discount levels would have brought in about 2.9M DKK more gross profit. This is my own calculation.
- **Unknown:** I found nothing in the CRM notes explaining why. I can't tell whether this was a decision or drift.

## Concern 2: Germany costs more and sells less

- **Facts:** The German sales team grew from 8 to 12 people (four hires between Sept 2025 and Jan 2026). The team's payroll cost rose 49% (+1.77M DKK). Over the same period, German revenue fell 8% and gross profit fell 16% (−1.8M).
- **Win rate (CRM):** Germany's new-deal win rate fell from 30% to 18%. The team closed 37% more deals but won fewer: 29 compared with 35 last year.
- **Not just the new hires:** Most long-standing reps are also winning only 13–23% of deals. Only Tobias Wagner is at 47%. One new hire has won 0 of 8 deals, another 1 of 19.
- **Discounts aren't helping:** German reps are giving 14–19% discounts, yet they win less often. Most losses are put down to "price too high" or "lost to competitor".
- **Missing loss reasons:** Deals with no loss reason recorded went from 12 to 30, which limits what we can diagnose. "Not qualified" (15 deals) is a new loss reason this year.

## Concern 3: Danish Service revenue is down 23%

- **Facts:** Danish Service revenue fell 4.3M DKK. This is the highest-margin business, at about 59%. Service contracts, technician hours and call-out fees each fell about 25%.
- **Cause (CRM):** The December 2025 renewal round went badly. Only 64% of contracts renewed, compared with about 85% in the rounds before and after, and 5.2M DKK of contract value was lost. The most common reason was "customer insourced maintenance" (9 losses, 2.5M DKK). The lost customers are the same ones showing the biggest revenue drops in the ERP (for example Køge Bygningsservice −93% and Herning Foder −41%).
- **Costs didn't fall with revenue:** Denmark still has 8 technicians, so capacity didn't cause the drop. It does mean the same labour cost now covers a lot less billable work.
- **Next risk:** The next big renewal round closes in December. Last year those deals were set up in the CRM in October and November. None are open yet, which fits that timing.

## What's going well
- **Danish Equipment:** revenue up 28%, gross profit up 1.25M DKK.
- **Sweden:** stable, with revenue +2%, gross profit +5.5% and the best margin of the three markets (40.8%).
- **Pipeline:** new sales deals created are up 16% by value, and open deals at the end of August are up 18%. Germany's pipeline is growing, but it isn't turning into wins.

## Questions to take to the team
1. **Pricing:** Was there a pricing or discount decision in January? Who approves Equipment discounts above 10%?
2. **Germany:** What sales growth was expected when the team was expanded? And how are new deals checked before they go into the pipeline?
3. **Service renewals:** Why are customers taking maintenance in-house? What is the plan for the December renewal round? All Danish renewals sit with one owner, Line Østergaard.

**Notes on the data:** Figures run to 31 August 2026, so Q3 only covers July and August. Loss reasons are often left blank in the CRM. The payroll figures match the ERP payroll journal (21.89M DKK in both). The causes behind the discounting and the insourcing aren't recorded anywhere I can see.