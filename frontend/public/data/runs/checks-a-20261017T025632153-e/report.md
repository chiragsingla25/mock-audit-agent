# Ledgerly SOC 2 readiness report — checks-a-20261017T025632153-e

_Readiness forecast from synthetic evidence. Not an audit opinion._ Mode: checks_only, review: skip.

## Coverage

| Control | Status | Steps tested | Not tested | Notes |
|---|---|---|---|---|
| C1 | exceptions | approval | — | — |
| C2 | exceptions | completeness, timeliness | — | X3001: no okta_users record, so nothing to check (not an exception). |
| C3 | no exceptions found | occurrence | signoff (judgment-only step (checks-only mode)) | — |
| C4 | no exceptions found | coverage | — | — |
| C5 | exceptions | occurrence, completeness | signoff (judgment-only step (checks-only mode)) | — |
| C6 | exceptions | segregation | — | — |
| C7 | no exceptions found | ticketed, retro_approval | — | — |
| C8 | exceptions | weekly_scan, critical_sla | — | — |
| C9 | exceptions | pir | — | — |
| C10 | exceptions | new_hire, annual | — | — |
| C11 | no exceptions found | review_in_period | — | — |
| C12 | not tested | — | restore_test (judgment-only step (checks-only mode)) | — |

## Findings (8)

_Not reviewed by a person: these are the findings the agent kept (evaluation run)._

### C2-timeliness · high · 3 of 19

- **Condition:** 3 of 19 items failed: E1004, E1006, E1038. First suspend/deactivate 1586.0 h after termination (limit 24 h). First suspend/deactivate 77.0 h after termination (limit 24 h). First suspend/deactivate 89.0 h after termination (limit 24 h).
- **Criteria:** First suspend or deactivate event within 24 clock hours of termination
- **Cause:** not determined
- **Effect:** The control 'Terminated users lose access within 24 hours' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** hr_roster/E1004, okta_events/OK-000062, hr_roster/E1006, okta_events/OK-000037, hr_roster/E1038, okta_events/OK-000153

### C5-completeness · high · 1 of 30

- **Condition:** 1 of 30 items failed: AIDA0DAED3206F81@PAR-2025Q4. AIDA0DAED3206F81 existed on 2026-01-06 but is not in PAR-2025Q4.
- **Criteria:** Every AWS admin that existed at the review date is on that quarter's reviewed list
- **Cause:** not determined
- **Effect:** The control 'Privileged access is reviewed quarterly' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** aws_iam_admins/AIDA0DAED3206F81, privileged_access_reviews/PAR-2025Q4

### C6-segregation · high · 3 of 320

- **Condition:** 3 of 320 items failed: PR-1316, PR-1229, PR-1017. Merged with no approver other than the author (isla.murphy). Merged with no approver other than the author (olivia.anderson). Merged with no approver other than the author (william.sato).
- **Criteria:** Every PR merged to main has at least one approver who is not the author
- **Cause:** not determined
- **Effect:** The control 'Production changes are approved by someone other than the author' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** github_prs/PR-1316, github_prs/PR-1229, github_prs/PR-1017

### C1-approval · moderate · 1 of 57

- **Condition:** 1 of 57 items failed: AR-0038. Granted 49.0 h before it was approved.
- **Criteria:** Each access grant has an approval timestamp at or before the grant
- **Cause:** not determined
- **Effect:** The control 'New access is approved before it is granted' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** access_requests/AR-0038

### C10-new_hire · moderate · 2 of 30

- **Condition:** 2 of 30 items failed: E1131, E1139. Completed 44 days after the event (limit 30). Completed 49 days after the event (limit 30).
- **Criteria:** New hires complete new-hire security training within 30 days of their hire date
- **Cause:** not determined
- **Effect:** The control 'Security training is completed within 30 days of hire and annually' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** hr_roster/E1131, lms_completions/LMS-00015, hr_roster/E1139, lms_completions/LMS-00143

### C8-critical_sla · moderate · 2 of 9

- **Condition:** 2 of 9 items failed: VULN-0009, VULN-0029. 60 days (limit 30). 49 days (limit 30).
- **Criteria:** Critical vulnerabilities are closed within 30 calendar days of being opened
- **Cause:** not determined
- **Effect:** The control 'Vulnerability scans run weekly and critical findings are fixed within 30 days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** vulnerabilities/VULN-0009, vulnerabilities/VULN-0029

### C8-weekly_scan · moderate · 3 of 53

- **Condition:** 3 of 53 items failed: 2026-W05, 2026-W06, 2026-W07. No scanner_runs occurrence for 2026-W05. No scanner_runs occurrence for 2026-W06. No scanner_runs occurrence for 2026-W07.
- **Criteria:** Each ISO week in the period has at least one completed scan
- **Cause:** not determined
- **Effect:** The control 'Vulnerability scans run weekly and critical findings are fixed within 30 days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** scanner_runs/SCAN-2026-W04, scanner_runs/SCAN-2026-W08

### C9-pir · moderate · 1 of 7

- **Condition:** 1 of 7 items failed: INC-21. No linked post_incident_reviews document.
- **Criteria:** Every Incident ticket links a post-incident review document
- **Cause:** not determined
- **Effect:** The control 'Security incidents are logged and get a post-incident review' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** jira_tickets/INC-21

## Remediation tasks

- [high] C2-timeliness: Investigate each exception with the control owner and remediate.
- [high] C5-completeness: Investigate each exception with the control owner and remediate.
- [high] C6-segregation: Investigate each exception with the control owner and remediate.
- [moderate] C1-approval: Investigate each exception with the control owner and remediate.
- [moderate] C10-new_hire: Investigate each exception with the control owner and remediate.
- [moderate] C8-critical_sla: Investigate each exception with the control owner and remediate.
- [moderate] C8-weekly_scan: Investigate each exception with the control owner and remediate.
- [moderate] C9-pir: Investigate each exception with the control owner and remediate.

Cost: US$0.0000 · 0 tokens · 0 LLM calls
