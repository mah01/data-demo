# Evaluation BC-t2: PASS

**Question (blind):** Where would you investigate first if you were the CEO?

Model `claude-opus-5` · 26 tool calls · systems: crm, erp, meta, payroll · 134.0 s · output tokens 9964 · cost $1.5723260000000001 · tool errors 0 · repeated identical calls 0

**Summary.** Prioritises Germany (about two-thirds of the profit decline: -1.8M gross profit plus +1.77M sales payroll; win rate 31% -> 26% -> 19% -> 17%; discounts doubled; best rep 47% worth studying), then Danish renewals (16 of 39 lost, confirmed in both CRM and ERP; imminent round). It explicitly did not investigate German spare parts -16%, which is where the key-account attrition is.

| dimension | assessment |
|---|---|
| factual correctness | High. |
| coverage | Good for the question. Missing key accounts (flagged as not investigated) and salary inflation. |
| causal reasoning | Good. Lists possible explanations without choosing one. |
| cross system reasoning | Good. ERP + CRM + payroll. |
| evidence | Traceable. |
| unsupported claims | None. |
| investigation quality | Good but shallow (26 calls). |

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
  5. `erp_sales_summary` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["market", "category"]}
  6. `erp_operating_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["account"]}
  7. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["month", "market"], "category": "Equipment", "sort_by": "month", "ascending": true}
  8. `erp_sales_summary` {"period": "2025-01..2026-08", "group_by": ["month"], "category": "Service", "market": "DK", "sort_by": "month", "ascending": true}
  9. `crm_renewals` {"period": "2025-01..2026-08", "limit": 5}
 10. `erp_customer_revenue` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "category": "Service", "market": "DK", "sort_by": "revenue_dkk_change", "ascending": true, "limit": 15}
 11. `crm_renewals` {"period": "2025-09..2026-01", "outcome": "lost", "limit": 40}
 12. `crm_loss_reasons` {"period": "2025-01..2026-08", "deal_type": "Renewal"}
 13. `crm_win_rate` {"period": "2025-01..2026-08", "deal_type": "Renewal", "group_by": ["half", "market"], "sort_by": "half", "ascending": true}
 14. `crm_win_rate` {"period": "2025-01..2026-08", "deal_type": "Renewal", "group_by": ["half", "owner"], "sort_by": "half", "ascending": true}
 15. `crm_owner_history` {"period": "2025-01..2026-09"}
 16. `crm_deals` {"deal_type": "Renewal", "outcome": "open", "limit": 60}
 17. `crm_users` {}
 18. `crm_deals` {"market": "DE", "outcome": "won", "date_field": "closed", "period": "2025-01..2026-08", "product_category": "Equipment", "limit": 150, "sort_by": "closed_at"}
 19. `crm_win_rate` {"period": "2025-01..2026-08", "group_by": ["half", "market"], "sort_by": "half", "ascending": true}
 20. `crm_win_rate` {"period": "2026-01..2026-08", "market": "DK", "product_category": "Equipment", "group_by": ["owner"], "compare_to": "2025-01..2025-08"}
 21. `payroll_personnel_costs` {"period": "2026-01..2026-08", "compare_to": "2025-01..2025-08", "group_by": ["country", "department"]}
 22. `payroll_hires_and_departures` {"period": "2025-01..2026-08"}
 23. `crm_pipeline` {"period": "2025-01..2026-08", "group_by": ["half", "market"], "sort_by": "half", "ascending": true}
 24. `crm_loss_reasons` {"period": "2026-01..2026-08", "market": "DE"}
 25. `crm_loss_reasons` {"period": "2025-01..2025-08", "market": "DE"}
 26. `crm_win_rate` {"period": "2026-01..2026-08", "market": "DE", "group_by": ["owner"]}

## Final answer

I'd start with **Germany**. It explains about two-thirds of this year's drop in operating profit, and the trend is still getting worse. In parallel I'd look at **Danish service-contract renewals**, because there's a deadline: the next renewal round starts in about a month.

## The overall picture (ERP, Jan–Aug 2026 vs Jan–Aug 2025)

| | 2025 YTD | 2026 YTD | Change |
|---|---|---|---|
| Revenue | 113.2m DKK | 115.7m DKK | +2.3% |
| Gross margin | 40.0% | 37.1% | −3.0 pts |
| Personnel costs | 19.5m DKK | 21.9m DKK | +12.0% |
| **Operating profit** | **16.0m DKK** | **10.6m DKK** | **−34%** (margin 14.2% → 9.2%) |

Revenue is growing, but profit is not. The 5.4m DKK drop in operating profit comes from 2.4m less gross profit, 2.35m more personnel costs and 0.6m more other operating costs.

## Priority 1: Germany – more salespeople and bigger discounts, but fewer wins

What the data shows:
- **Gross profit in Germany is down 1.8m DKK** (ERP). Equipment gross profit fell 27% as its margin dropped from 28.4% to 21.7%. Spare-parts revenue fell 16%.
- **Discounts have roughly doubled.** The average equipment discount went from 6–7% (H1 2025) to 8–10% (H2 2025) and 15–17% every month since February 2026 (ERP). CRM deal records show the same shift for nearly every German rep, long-standing ones included (typically 5–9% in early 2025, 15–20% in 2026). So it's team-wide, not a problem with one person.
- **Winning less despite the discounts.** The German win rate went from 31% (H1 2025) to 26% (H2 2025), 19% (H1 2026) and 17% so far in H2 2026 (CRM). "Price too high" is still one of the top two loss reasons.
- **Sales costs up sharply.** German sales headcount went from 8 to 12 with four hires between Sep 2025 and Jan 2026. German sales payroll rose 1.77m DKK (+49%) (payroll). That's about 75% of the company's entire personnel cost increase.
- The new hires are adding pipeline: new German opportunities were worth 35.1m DKK in H1 2026, up from 26.4m. But it isn't converting. Deals won were worth 7.6m DKK, down from 10.1m in H1 2025.

**Bottom line:** lower German gross profit plus the extra sales payroll comes to about 3.6m DKK, roughly two-thirds of the profit decline.

**My reading (not proven by the data):** Deeper discounts haven't bought more volume. The data can't tell me why. Possible explanations include a tougher German market, a new competitor, loose discount approval, or new reps still ramping up (two new reps have won 1 of 19 and 0 of 8 deals). One rep, Tobias Wagner, wins 47%, so it's worth finding out what he does differently. Also, 23% of German losses have no reason recorded, up from 15%, which makes diagnosis harder.

## Priority 2: Danish service contracts – lost renewals, with the next round starting soon

- **Danish service revenue is down 22.6% (−4.3m DKK), costing 2.55m DKK in gross profit.** That's the biggest single loss in any market and product line (ERP). The quarterly contract billing peaks dropped from about 4.0–4.5m to about 3.1–3.3m DKK.
- **Cause (confirmed in both CRM and ERP):** the December 2025 renewal round lost 16 of 39 Danish contracts (3.7m DKK of contract value), compared with 2 of 9 in H1 2025. The lost accounts in the CRM (Køge Bygningsservice, Herning Foder, Lolland Emballage, Fjord Energi and others) are the same customers whose service revenue fell in the ERP.
- **The top loss reason is "customer insourced maintenance"**: 10 of 25 lost renewals across all markets since Jan 2025. That points to customers doing maintenance in-house rather than simply pricing.
- **Why it's urgent:** last year's renewal deals were created in October–November and closed in December. Right now there are no open renewal deals in the CRM. The next round is about to start, and nothing I can see in the data shows it's being prepared.

## Lower priority: Danish equipment discounts

Danish equipment discounts also rose, from 6.9% to 10.8%. Unlike Germany, volume grew: revenue is up 28% and gross profit up 1.25m DKK. It's worth checking whether the discount was necessary, but it isn't hurting profit the way Germany is.

## Questions I'd put to management
1. **DACH sales lead:** Who approves discounts over about 10%, and what changed around January 2026? Were the four hires backed by a plan, and when were they expected to pay off?
2. **Service sales:** Why are customers taking maintenance in-house? Is there a plan for the Q4 2026 renewal round, and which contracts are at risk?
3. **Finance:** What's the full-year outlook if German win rates stay around 17%?

**Caveats:** H2 2026 covers only July–August. CRM and ERP convert currencies with different rates, so their DKK figures differ slightly. I didn't investigate why German spare-parts sales fell 16%. All renewals losses in Denmark sit with one owner (Line Østergaard), but she handles essentially all Danish renewals, so that alone doesn't suggest a personal performance issue.