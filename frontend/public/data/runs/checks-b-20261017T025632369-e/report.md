# Ledgerly SOC 2 readiness report — checks-b-20261017T025632369-e

_Readiness forecast from synthetic evidence. Not an audit opinion._ Mode: checks_only, review: skip.

## Coverage

| Control | Status | Steps tested | Not tested | Notes |
|---|---|---|---|---|
| C1 | exceptions | approval | — | — |
| C2 | exceptions | completeness, timeliness | — | X3001: no okta_users record, so nothing to check (not an exception). |
| C3 | no exceptions found | occurrence | signoff (judgment-only step (checks-only mode)) | — |
| C4 | no exceptions found | coverage | — | — |
| C5 | exceptions | occurrence, completeness | signoff (judgment-only step (checks-only mode)) | — |
| C6 | no exceptions found | segregation | — | — |
| C7 | exceptions | ticketed, retro_approval | — | — |
| C8 | exceptions | weekly_scan, critical_sla | — | — |
| C9 | exceptions | pir | — | — |
| C10 | exceptions | new_hire, annual | — | — |
| C11 | no exceptions found | review_in_period | — | — |
| C12 | not tested | — | restore_test (judgment-only step (checks-only mode)) | — |

## Findings (9)

_Not reviewed by a person: these are the findings this run kept, before any human review._

### C2-completeness · high · 1 of 20

- **Condition:** 1 of 20 items failed: E1028. E1028 is missing from okta_events.
- **Criteria:** Every HR termination with an Okta account appears in the deprovisioning population
- **Cause:** not determined
- **Effect:** The control 'Terminated users lose access within 24 hours' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** hr_roster/E1028, okta_users/00u5e7b85b559

### C5-completeness · high · 1 of 30

- **Condition:** 1 of 30 items failed: AIDAB886960EB41A@PAR-2026Q1. AIDAB886960EB41A existed on 2026-04-01 but is not in PAR-2026Q1.
- **Criteria:** Every AWS admin that existed at the review date is on that quarter's reviewed list
- **Cause:** not determined
- **Effect:** The control 'Privileged access is reviewed quarterly' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** aws_iam_admins/AIDAB886960EB41A, privileged_access_reviews/PAR-2026Q1

### C1-approval · moderate · 1 of 63

- **Condition:** 1 of 63 items failed: AR-0003. Granted 49.0 h before it was approved.
- **Criteria:** Each access grant has an approval timestamp at or before the grant
- **Cause:** not determined
- **Effect:** The control 'New access is approved before it is granted' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** access_requests/AR-0003

### C10-new_hire · moderate · 3 of 30

- **Condition:** 3 of 30 items failed: E1125, E1140, E1145. Completed 49 days after the event (limit 30). Completed 52 days after the event (limit 30). Completed 56 days after the event (limit 30).
- **Criteria:** New hires complete new-hire security training within 30 days of their hire date
- **Cause:** not determined
- **Effect:** The control 'Security training is completed within 30 days of hire and annually' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** hr_roster/E1125, lms_completions/LMS-00010, hr_roster/E1140, lms_completions/LMS-00109, hr_roster/E1145, lms_completions/LMS-00149

### C2-timeliness · moderate · 1 of 18

- **Condition:** 1 of 18 items failed: E1010. First suspend/deactivate 1658.0 h after termination (limit 24 h).
- **Criteria:** First suspend or deactivate event within 24 clock hours of termination
- **Cause:** not determined
- **Effect:** The control 'Terminated users lose access within 24 hours' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** hr_roster/E1010, okta_events/OK-000085

### C7-ticketed · moderate · 1 of 8

- **Condition:** 1 of 8 items failed: D-00875. Emergency deploy has no linked change ticket.
- **Criteria:** Every emergency deploy links an emergency change ticket
- **Cause:** not determined
- **Effect:** The control 'Emergency changes are approved retroactively within 2 business days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** deploys/D-00875

### C8-critical_sla · moderate · 2 of 9

- **Condition:** 2 of 9 items failed: VULN-0031, VULN-0037. 60 days (limit 30). 50 days (limit 30).
- **Criteria:** Critical vulnerabilities are closed within 30 calendar days of being opened
- **Cause:** not determined
- **Effect:** The control 'Vulnerability scans run weekly and critical findings are fixed within 30 days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** vulnerabilities/VULN-0031, vulnerabilities/VULN-0037

### C8-weekly_scan · moderate · 3 of 53

- **Condition:** 3 of 53 items failed: 2026-W30, 2026-W31, 2026-W32. No scanner_runs occurrence for 2026-W30. No scanner_runs occurrence for 2026-W31. No scanner_runs occurrence for 2026-W32.
- **Criteria:** Each ISO week in the period has at least one completed scan
- **Cause:** not determined
- **Effect:** The control 'Vulnerability scans run weekly and critical findings are fixed within 30 days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** scanner_runs/SCAN-2026-W29, scanner_runs/SCAN-2026-W33

### C9-pir · moderate · 1 of 7

- **Condition:** 1 of 7 items failed: INC-23. No linked post_incident_reviews document.
- **Criteria:** Every Incident ticket links a post-incident review document
- **Cause:** not determined
- **Effect:** The control 'Security incidents are logged and get a post-incident review' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** jira_tickets/INC-23

## Remediation tasks

- [high] C2-completeness: Investigate each exception with the control owner and remediate.
- [high] C5-completeness: Investigate each exception with the control owner and remediate.
- [moderate] C1-approval: Investigate each exception with the control owner and remediate.
- [moderate] C10-new_hire: Investigate each exception with the control owner and remediate.
- [moderate] C2-timeliness: Investigate each exception with the control owner and remediate.
- [moderate] C7-ticketed: Investigate each exception with the control owner and remediate.
- [moderate] C8-critical_sla: Investigate each exception with the control owner and remediate.
- [moderate] C8-weekly_scan: Investigate each exception with the control owner and remediate.
- [moderate] C9-pir: Investigate each exception with the control owner and remediate.

Cost: US$0.0000 · 0 tokens · 0 LLM calls
