# Evaluation BB-t1: PASS

**Question (blind):** What deserves management attention right now?

Model `claude-opus-5` · 33 tool calls · systems: crm, erp, identity, meta, payroll · 291.7 s · output tokens 12610 · cost $2.0033515 · tool errors 1 · repeated identical calls 0

**Summary.** Revenue +2% vs operating profit -34% (continuing in Jul-Aug). Three priorities: lost Danish service contracts (16 lost in H2 2025, all with one owner, zero open renewal deals ahead of the next round), equipment discounting (about 2.9M gross profit), and the German expansion (8 -> 12, about 75% of the personnel increase, win rate 31% -> 19%, new hires 12%, veterans 23%). It noticed German Components -16% but explicitly did not investigate it: that is where the key-account attrition sits. It admits matching lost renewals to ERP by name rather than via the identity mapping.

| dimension | assessment |
|---|---|
| factual correctness | High. |
| coverage | Good. Missing the German key-account attrition (flagged as uninvestigated) and salary inflation. |
| causal reasoning | Good. Pipeline-quality hypothesis labelled 'isn't proven'. |
| cross system reasoning | Good, with one self-reported shortcut (name matching instead of identity tools). |
| evidence | Traceable. |
| unsupported claims | None. |
| investigation quality | Good. 33 calls; stopped before customer-level analysis of Germany. |

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
  4. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["quarter", "market"]}
  5. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market", "category"]}
  6. `erp_sales_summary` {"period": "2025-01..2026-08", "category": "Equipment", "group_by": ["month", "market"], "sort_by": "month", "ascending": true}
  7. `erp_sales_summary` {"period": "2025-01..2026-08", "category": "Service", "group_by": ["month", "market"], "sort_by": "month", "ascending": true}
  8. `crm_renewals` {"period": "2025-01..2026-08", "outcome": "lost"}
  9. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Service", "market": "DK", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 30}
 10. `crm_renewals` {"period": "2025-01..2025-10", "limit": 1}
 11. `crm_renewals` {"period": "2025-11..2025-12", "limit": 1}
 12. `crm_renewals` {"period": "2026-01..2026-08", "limit": 1}
 13. `crm_win_rate` {"period": "2025-01..2026-08", "deal_type": "Renewal", "group_by": ["market", "half"]}
 14. `crm_deals` {"deal_type": "Renewal", "outcome": "open", "limit": 100, "sort_by": "value_dkk"}
 15. `crm_users` {}
 16. `identity_find_person` {"query": "Østergaard"}
 17. `crm_activities` {"text_contains": "insourc", "limit": 15}
 18. `crm_win_rate` {"period": "2025-01..2026-08", "market": "DE", "group_by": ["owner", "half"]}
 19. `payroll_personnel_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["country", "department"]}
 20. `payroll_hires_and_departures` {"period": "2025-01..2026-08"}
 21. `crm_win_rate` {"period": "2025-01..2026-08", "group_by": ["market", "half"]}
 22. `crm_pipeline` {"period": "2025-01..2026-08", "group_by": ["market", "half"]}
 23. `crm_loss_reasons` {"period": "2026-01..2026-08", "market": "DE"}
 24. `crm_loss_reasons` {"period": "2025-01..2025-08", "market": "DE"}
 25. `crm_deals` {"market": "DK", "outcome": "won", "date_field": "closed", "period": "2025-07..2026-08", "limit": 100, "sort_by": "closed_at"}
 26. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Equipment", "market": "DK", "group_by": ["product"]}
 27. `crm_deals` {"market": "DK", "outcome": "won", "date_field": "closed", "period": "2026-01..2026-08", "product_category": "Equipment", "limit": 40, "sort_by": "value_dkk"}
 28. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "account_type": "opex", "group_by": ["account"]}
 29. `erp_financial_summary` {"period": "2026-07..2026-08", "compare_to": "2025-07..2025-08"}
 30. `crm_pipeline` {"period": "2026-08-31", "basis": "open_at_end", "group_by": ["market", "stage"]} **ERROR**
 31. `crm_deals` {"outcome": "open", "date_field": "expected_close", "period": "2024-01-01..2026-08-31", "limit": 5, "sort_by": "value_dkk"}
 32. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "account_type": "opex", "group_by": ["department"]}
 33. `crm_pipeline` {"period": "2026-01-01..2026-08-31", "basis": "open_at_end", "group_by": ["market"], "compare_to": "2025-01-01..2025-08-31"}

## Final answer

# What needs management attention (data through August 2026)

Revenue is up 2% on last year, but operating profit is down 34%. Three things drive it: service contracts lost in Denmark, heavier Equipment discounting, and a bigger German sales team that isn't bringing in more business yet. July–August show the same pattern (operating profit −35% on last year), so it is still going on.

**Year to date, Jan–Aug 2026 vs Jan–Aug 2025 (ERP)**

| | 2025 | 2026 | Change |
|---|---|---|---|
| Revenue | 113.2M | 115.7M | +2.6M (+2%) |
| Gross margin | 40.0% | 37.1% | −3.0pp |
| Gross profit | 45.3M | 42.9M | −2.4M |
| Personnel costs | 19.5M | 21.9M | −2.4M (+12%) |
| Other operating costs | 9.7M | 10.4M | −0.6M (+7%) |
| **Operating profit** | **16.0M** | **10.6M** | **−5.4M (−34%)** |

All amounts are DKK.

## 1. Lost Danish service contracts: the biggest single hit, and the next renewal round starts soon
- **Facts:** Danish Service revenue is down 4.3M (−23%) and its gross profit down 2.6M. That's more than the whole company's gross-profit decline. Service carries a 59% margin, so every lost contract hurts. The quarterly service billing in Denmark dropped from 4.0–4.5M to 3.1–3.3M per quarter from January 2026 (ERP).
- **Cause in the CRM:** 16 Danish renewals were lost in the second half of 2025, worth 3.7M, nearly all in December. The Danish renewal rate fell to 59%, against 78–82% in the periods before and after. All 16 belong to one person, Line Østergaard. The recorded reasons:
  - customer took maintenance in-house: 7
  - lost to a competitor: 4
  - price: 2
  - budget: 1
  - no reason recorded: 2
- **Why now:** There are **zero open renewal deals** in the CRM today. Last year's renewal round (55 deals, 5.2M lost) started being created on 1 October.
- **Opportunity:** Several of the lost service customers still bought equipment in 2026, e.g. Herning Foder, Lolland Emballage and Bornholms Energi. The relationships look intact, so these are candidates for winning the contracts back.
- **Suggested action:** Start the 2027 renewal round now. Review the biggest contracts with management before year-end, and decide how to answer customers who want to do maintenance themselves.

## 2. Equipment discounts jumped in January–February 2026
- **Facts (ERP):**
  - Denmark: average Equipment discount went from about 7% to 11% in January.
  - Germany: from about 7% to 15–16% in February.
  - Sweden: unchanged at about 7%.
  - In Denmark the increase shows up on almost every product and every sales rep (8–14% per deal in the CRM), so it isn't a handful of one-off deals.
- **Cost:** At last year's discount levels, gross profit would have been roughly **2.9M higher** (1.6M in Denmark, 1.3M in Germany). This is my estimate and assumes the same volumes.
- **Interpretation:** The extra discount hasn't won more deals. Denmark's win rate is flat at about 35%, and Germany's fell. Danish volume grew (Equipment revenue +28%), but I can't show the discount caused that. I found nothing in the data explaining why discounts stepped up. Worth asking whether this was a decision, and who approves discounts.

## 3. The German sales expansion isn't paying off yet
- **Cost (payroll, ERP):** German sales headcount grew from 8 to 12 between September 2025 and January 2026. Their cost is up 1.8M (+49%), about 75% of the whole personnel-cost increase. German operating costs are also up 0.5M (+27%).
- **Results:**
  - German revenue is down 2.3M (−8%) and gross profit down 1.8M (ERP).
  - The Germans are creating 35% more pipeline, but the win rate fell from 31% (first half 2025) to 19% (first half 2026) and 17% so far in the second half (CRM, excluding renewals).
  - The four new hires have won 8 of 67 closed deals (12%). The existing reps are also down, at 23%.
- **Interpretation:** More deals are being lost as "not qualified" or with no reason recorded. That suggests pipeline quality and discount discipline issues, not a lack of activity, but it isn't proven. Together, Germany is about 4M worse off than last year.

## 4. Smaller items to watch
- **Components in Germany** are down 16% (−1.3M). I haven't looked into why yet.
- **Travel (+26%), marketing (+23%) and car costs (+19%)** are rising, partly in the German department.
- **24 open deals** have an expected close date that has already passed. It's a CRM clean-up issue, but it makes the forecast less reliable.
- **Positive:** Sweden is steady, with margins improving slightly. Open pipeline is 18% higher than a year ago.

## Caveats
- Loss reasons are typed in by sales and are often blank.
- I matched lost CRM renewals to ERP customers by name, not through the formal ID mapping between the systems.
- The discount effect is an estimate. Nothing in the data shows whether the discount increases or the German hiring were planned decisions.