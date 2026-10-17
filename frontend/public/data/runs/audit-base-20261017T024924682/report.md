# Ledgerly SOC 2 readiness report — audit-base-20261017T024924682

_Readiness forecast from synthetic evidence. Not an audit opinion._ Mode: agent, review: human.

## Coverage

| Control | Status | Steps tested | Not tested | Notes |
|---|---|---|---|---|
| C1 | no exceptions found | approval | — | — |
| C2 | exceptions | completeness, timeliness | — | X3001: no okta_users record, so nothing to check (not an exception). |
| C3 | exceptions dismissed in review | occurrence, signoff | — | 1 finding(s) dismissed in review |
| C4 | no exceptions found | coverage | — | — |
| C5 | exceptions | occurrence, completeness, signoff | — | — |
| C6 | exceptions dismissed in review | segregation | — | 1 finding(s) dismissed in review |
| C7 | exceptions dismissed in review | ticketed, retro_approval | — | 1 finding(s) dismissed in review |
| C8 | exceptions dismissed in review | weekly_scan, critical_sla | — | 2 finding(s) dismissed in review |
| C9 | no exceptions found | pir | — | — |
| C10 | exceptions dismissed in review | new_hire, annual | — | 1 finding(s) dismissed in review |
| C11 | no exceptions found | review_in_period | — | — |
| C12 | exceptions dismissed in review | restore_test | — | 1 finding(s) dismissed in review |

## Findings (3)

### C2-completeness · high · 1 of 20

- **Condition:** E1070 (hr_roster) shows terminated user with no corresponding suspend/deactivate event in okta_events; okta_users record 00u27ba276404 shows status ACTIVE
- **Criteria:** Section 4.3 requires 'suspend or deactivate their Okta account within 24 clock hours of the termination time'
- **Cause:** No deprovisioning event was recorded for this terminated user; owner confirmed deactivation was missed
- **Effect:** User retained access without proper deprovisioning beyond observation period
- **Recommendation:** Implement controls to ensure all terminated users have corresponding suspend/deactivate events within 24 hours and verify completion
- **Evidence:** hr_roster/E1070, okta_users/00u27ba276404

### C2-timeliness · high · 2 of 18

- **Condition:** E1055 had first suspend event 219.0 hours after termination (OK-000099); E1109 had first suspend event 63.0 hours after termination (OK-000261); both exceed 24-hour limit
- **Criteria:** Section 4.3 requires 'suspend or deactivate their Okta account within 24 clock hours of the termination time'
- **Cause:** Offboarding tickets were actioned late for both users; no approved exceptions exist
- **Effect:** Users retained access beyond the allowed 24-hour period after termination
- **Recommendation:** Review and improve deprovisioning processes to meet 24-hour SLA and implement monitoring for timely completion
- **Evidence:** hr_roster/E1055, okta_events/OK-000099, hr_roster/E1109, okta_events/OK-000261

### C5-completeness · high · 1 of 30

- **Condition:** 1 of 30 items failed: AIDAFCB2757B1F7F@PAR-2026Q3. AIDAFCB2757B1F7F existed on 2026-10-07 but is not in PAR-2026Q3.
- **Criteria:** Every AWS admin that existed at the review date is on that quarter's reviewed list
- **Cause:** not determined
- **Effect:** The control 'Privileged access is reviewed quarterly' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** aws_iam_admins/AIDAFCB2757B1F7F, privileged_access_reviews/PAR-2026Q3

## Remediation tasks

- [high] C2-completeness: Implement controls to ensure all terminated users have corresponding suspend/deactivate events within 24 hours and verify completion
- [high] C2-timeliness: Review and improve deprovisioning processes to meet 24-hour SLA and implement monitoring for timely completion
- [high] C5-completeness: Investigate each exception with the control owner and remediate.

Cost: US$0.0156 · 124,350 tokens · 34 LLM calls
