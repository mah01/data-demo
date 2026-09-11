# Evaluation BB-t3: PASS

**Question (blind):** What deserves management attention right now?

Model `claude-opus-5` · 51 tool calls · systems: crm, erp, identity, meta, payroll · 344.0 s · output tokens 19098 · cost $2.4825329999999997 · tool errors 0 · repeated identical calls 0

**Summary.** Four issues: the renewal season (64% vs 85%, 16 of 39 Danish contracts lost, time-critical), equipment discounting (quarterly table; about 2.9M upper bound), the German expansion (8 -> 12, +1.77M, win rate 29.9% -> 18.1%, new hires 8 of 69) including the account handovers with Rheinmark and Brandauer documented from CRM notes, and normal cost growth ('outside German Sales, payroll grew about 3-4%, in line with salary increases'). One overgeneralisation: 'experienced reps are also winning only 13-14%' describes some veterans; their average is about 23%.

| dimension | assessment |
|---|---|
| factual correctness | High, with one overgeneralisation about veteran win rates. |
| coverage | Very good. Includes key accounts and places pay rises as normal growth. |
| causal reasoning | Strong. Handover causation 'not proven, but well documented' for Rheinmark. |
| cross system reasoning | Excellent. |
| evidence | Traceable. |
| unsupported claims | None beyond the overgeneralisation. |
| investigation quality | Very good. 51 calls. |

**Discoveries** (manual; ✓ found, ~ partly, ✗ not found, – not applicable)

- Overall revenue growth but operating-profit deterioration: ✓
- Germany as a major contributor to the profit decline: ✓
- German sales headcount expansion (8 -> 12): ✓
- Pipeline growth combined with worse conversion (win rate): ✓
- Poor new-rep performance (new hires convert worse): ✓
- Rheinmark / Brandauer identified at customer level: ✓
- Danish revenue growth masking mix / margin deterioration: ✓
- Salary inflation insufficient to explain the profit decline: ~

## Tool trace

  1. `meta_describe_sources` {}
  2. `meta_get_semantics` {}
  3. `erp_financial_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08"}
  4. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["month"], "sort_by": "month", "ascending": true}
  5. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market", "category"]}
  6. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "category": "Service", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 25}
  7. `crm_renewals` {"period": "2025-09..2026-08", "limit": 100}
  8. `erp_sales_summary` {"period": "2025-01..2026-08", "category": "Equipment", "group_by": ["market", "quarter"], "sort_by": "quarter", "ascending": true}
  9. `crm_renewals` {"period": "2025-01..2025-08", "limit": 1}
 10. `crm_renewals` {"period": "2026-01..2026-08", "limit": 1}
 11. `crm_renewals` {"period": "2026-01..2026-08", "market": "DK", "outcome": "lost", "limit": 60}
 12. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Service", "market": "DK", "group_by": ["product"]}
 13. `erp_sales_summary` {"period": "2025-01..2026-08", "category": "Service", "group_by": ["market", "quarter"], "sort_by": "quarter", "ascending": true}
 14. `payroll_headcount` {"basis": "average_monthly", "period": "2026-01..2026-08", "group_by": ["country", "department"]}
 15. `payroll_headcount` {"basis": "average_monthly", "period": "2025-01..2025-08", "group_by": ["country", "department"]}
 16. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "category": "Service", "sort_by": "revenue_dkk_change", "ascending": false, "limit": 15}
 17. `payroll_hires_and_departures` {"period": "2025-01..2026-08"}
 18. `crm_owner_history` {"period": "2025-06..2026-08", "limit": 120}
 19. `crm_win_rate` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 20. `crm_win_rate` {"period": "2025-09..2026-08", "market": "DE", "group_by": ["owner"]}
 21. `crm_pipeline` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market"]}
 22. `crm_loss_reasons` {"period": "2026-01..2026-08"}
 23. `payroll_personnel_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["country", "department"]}
 24. `identity_find_company` {"query": "Køge Bygningsservice"}
 25. `crm_activities` {"period": "2025-10..2026-08", "text_contains": "service", "limit": 40}
 26. `crm_renewals` {"period": "2025-09..2025-12", "market": "DK", "outcome": "lost", "limit": 40}
 27. `crm_renewals` {"period": "2024-09..2024-12", "limit": 1}
 28. `crm_renewals` {"period": "2025-09..2025-12", "limit": 1}
 29. `crm_deals` {"deal_type": "Renewal", "outcome": "open", "limit": 80, "sort_by": "value_dkk"}
 30. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "account_type": "opex", "group_by": ["account"]}
 31. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DE", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 12}
 32. `identity_crm_companies_to_erp` {"company_ids": ["cmp_95298", "cmp_60635", "cmp_38410", "cmp_71526", "cmp_63758", "cmp_67619", "cmp_78239", "cmp_92184", "cmp_82561", "cmp_52669", "cmp_52777", "cmp_15266", "cmp_31816"]}
 33. `crm_users` {"team": "DACH"}
 34. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DE", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 100}
 35. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "39862"}
 36. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "65426"}
 37. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "31957"}
 38. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "44987"}
 39. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "53068"}
 40. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "18406"}
 41. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "44592"}
 42. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "19734"}
 43. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "21231"}
 44. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "customer_number": "33570"}
 45. `crm_deals` {"market": "DE", "outcome": "won", "date_field": "closed", "period": "2026-01..2026-08", "limit": 40}
 46. `crm_activities` {"company_id": "cmp_82561", "limit": 15}
 47. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "market": "DK", "category": "Equipment", "limit": 12}
 48. `crm_win_rate` {"period": "2026-01..2026-08", "market": "DK", "group_by": ["owner"]}
 49. `crm_deals` {"market": "DK", "outcome": "won", "date_field": "closed", "period": "2026-01..2026-08", "product_category": "Equipment", "limit": 25}
 50. `crm_pipeline` {"period": "2026-08", "basis": "open_at_end", "group_by": ["market", "stage"]}
 51. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "account_type": "opex", "group_by": ["department"]}

## Final answer

# NordFlow: what needs management attention now (data through August 2026)

**Operating profit is down 34% so far this year, even though revenue is up 2%.** January–August 2026 operating profit was 10.6M DKK against 16.0M in the same months of 2025. Operating margin fell from 14.2% to 9.2% (ERP).

| Driver of the change (Jan–Aug 2026 vs 2025) | Effect on profit, DKK |
|---|---|
| Lower gross profit (margin 40.0% → 37.1%) | −2.4M |
| Higher personnel costs (+12%) | −2.35M |
| Higher other operating costs (+6.6%) | −0.64M |

Four issues account for most of this. The first is urgent because of timing.

---

## 1. Last year's service renewal season went badly, and this year's is starting now

**What the data shows**
- **Renewal rate:** in the September–December 2025 renewal season, 64% of service contracts were renewed, against 85% in the same season of 2024. Lost contract value rose to 5.2M DKK (38% of the total), from 1.6M DKK (11%) (CRM).
- **Denmark:** 16 of 39 contracts were lost, worth 3.7M DKK. The recorded reasons:
  - "customer insourced maintenance" (7)
  - lost to a competitor (4)
  - price (2)
  - budget cuts (1)
  - no reason recorded (2)
  - The sales notes repeat "Customer found cheaper service partner" and "Budget cut – service reduced to ad hoc calls."
- **Revenue impact:** Danish Service revenue is down 4.3M DKK (−23%) and gross profit down 2.55M DKK (ERP). This is the **biggest single cause of the gross-profit decline**.
  - Service contract billing: −2.24M
  - Technician hours: −1.70M
  - Call-out fees: −0.42M
- **Technicians:** Denmark still has 8 service technicians, and their cost is up 2.9% (payroll).

**My interpretation:** the customers who stopped billing are largely the same ones whose renewals were lost. That suggests losing a contract also loses the technician hours and call-outs that come with it. With technician headcount flat and revenue down, technicians are likely less fully used.

**Why now:** last year the renewal deals were created in October–November. **The CRM has no open renewal deals right now**, so the 2027 renewal season has not started in the system yet.

## 2. Equipment discounts have risen sharply in Germany and Denmark

Average invoice discount on Equipment, by quarter (ERP; Q3 2026 is July–August only):

| Market | 2025 Q1–Q2 | 2025 Q3 | 2025 Q4 | 2026 Q1 | 2026 Q2 | 2026 Q3 |
|---|---|---|---|---|---|---|
| Germany | 6.7% | 8.3% | 9.6% | 14.5% | 15.9% | 15.5% |
| Denmark | ~7% | 7.0% | 7.1% | 10.5% | 11.1% | 10.9% |
| Sweden | 6.6–7.2% throughout | | | | | |

- **Margins:** German Equipment gross margin fell from 28.4% to 21.7%, and Danish from 28.4% to 25.5%. Sweden held at about 29–30%.
- **It is not a few salespeople.** Won deals in 2026 show 14–20% discounts across all German reps, experienced ones included, and 8–14% across all five Danish reps (CRM).
- **Rough size:** had discounts stayed at 2025 levels on the same volume, gross profit this year would be about 2.9M DKK higher. That is an upper bound, since some of the volume may depend on the discounts.
- **Denmark vs Germany:** Danish Equipment revenue grew 28%, so the discounts may be buying volume there. German Equipment revenue fell 5% despite them.
- **Open question:** Denmark's jump in January 2026 looks like a deliberate pricing decision, but nothing in the data confirms it. It's worth checking whether it was authorised.

## 3. The German sales team grew by half, but German sales fell

- **Cost:** German Sales went from 8 to 12 people (four hires between September 2025 and January 2026). Its cost rose 1.77M DKK (+49%), which is about 75% of the group's personnel cost increase. German operating costs rose a further 0.52M DKK (+27%) (payroll and ERP).
- **Results:** new German pipeline is up 35%, but the win rate fell from 29.9% to 18.1%. Won value is down 24% and German revenue is down 2.3M DKK (−8%) (CRM and ERP).
- **Not only new hires:** the four new reps have won 8 of 69 closed deals in the last 12 months. Some ramp-up time is normal. But experienced reps are also winning only 13–14% of deals; only one rep is above 40%.
- **Account handovers:** 13 accounts were bulk-moved from experienced reps to the new hires in September–November 2025. Across those accounts revenue is down a net 3.0M DKK, almost all of it at two customers:
  - **Rheinmark Chemie (−2.6M DKK):**
    - In October the customer asked why their usual rep no longer covered the site and asked for continuity.
    - In December they didn't renew the service contract, choosing a competitor that bundled service and spare parts.
    - In February a tank-farm pump project went to that same competitor.
  - **Brandauer Papier (−2.2M DKK):** in January it moved its spare-parts business to a local distributor that holds stock on site.
  - The data doesn't prove the handovers caused these losses, but the Rheinmark sequence is well documented in the notes.

## 4. Other cost growth looks normal

Outside German Sales, payroll grew about 3–4%, which is in line with salary increases. Travel (+26%), car costs (+19%) and marketing (+23%) are up, and most of the operating-cost increase is booked to Germany.

---

## What is working
- Sweden is stable in revenue, margin and win rate.
- Denmark's win rate on new sales is steady at 35%, and its Equipment volume is growing.
- Spare-parts revenue in Denmark and Sweden is stable.

## Suggested next steps
1. **Renewals:** start the 2027 renewal deals now, have a senior person own the largest contracts, and look into why Danish customers are insourcing maintenance. Several customers who dropped service still buy equipment from us (Lolland Emballage, Herning Foder, Bornholms Energi, Fjord Fødevarer), which gives an opening to win the service back.
2. **Discounts:** confirm whether the January 2026 change in Denmark was a decision, set discount approval limits, and track the prices actually achieved each month by market.
3. **Germany:** set ramp-up targets for the new reps, agree a handover procedure for accounts that change rep, and make recovery plans for Rheinmark and Brandauer.

**Caveats:**
- 19% of lost deals have no loss reason recorded.
- The CRM and ERP convert currencies at slightly different rates.
- The discount estimate is a simple calculation, not a forecast.
- Links between events, such as handovers leading to lost business, come from sales notes and timing and haven't been proven.