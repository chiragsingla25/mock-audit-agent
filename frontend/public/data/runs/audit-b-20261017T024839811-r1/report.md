# Ledgerly SOC 2 readiness report — audit-b-20261017T024839811-r1

_Readiness forecast from synthetic evidence. Not an audit opinion._ Mode: agent, review: skip.

## Coverage

| Control | Status | Steps tested | Not tested | Notes |
|---|---|---|---|---|
| C1 | no exceptions found | approval | — | — |
| C2 | exceptions | completeness, timeliness | — | X3001: no okta_users record, so nothing to check (not an exception). |
| C3 | exceptions | occurrence, signoff | — | — |
| C4 | no exceptions found | coverage | — | — |
| C5 | exceptions | occurrence, completeness, signoff | — | — |
| C6 | no exceptions found | segregation | — | — |
| C7 | exceptions | ticketed, retro_approval | — | — |
| C8 | exceptions | weekly_scan, critical_sla | — | — |
| C9 | no exceptions found | pir | — | — |
| C10 | exceptions | new_hire, annual | — | — |
| C11 | no exceptions found | review_in_period | — | — |
| C12 | no exceptions found | restore_test | — | — |

## Findings (7)

_Not reviewed by a person: these are the findings the agent kept (evaluation run)._

### C2-completeness · high · 1 of 20

- **Condition:** HR record E1028 shows employee Charlotte Ryan terminated on 2025-12-21 17:30, but Okta user 00u5e7b85b559 remains ACTIVE with no suspend or deactivate event in okta_events
- **Criteria:** Policy section 4.3: 'When a workforce member's engagement ends, IT Operations must suspend or deactivate their Okta account within 24 clock hours of the termination time recorded in the HR system.'
- **Cause:** No deprovisioning action was taken for this terminated employee
- **Effect:** User retained access to Okta beyond the 24-hour window after termination, creating unauthorized access risk
- **Recommendation:** Implement automated deprovisioning workflow triggered by HR terminations and add monitoring to ensure all terminated users are suspended/deactivated within 24 hours
- **Evidence:** hr_roster/E1028, okta_users/00u5e7b85b559

### C3-signoff · high · 1 of 4

- **Condition:** UAR-2026Q2 shows 'Signed: (not signed)' - the review was performed but never signed by the reviewer Dana Whitfield
- **Criteria:** Policy section 4.6: 'Each review is signed and dated by the reviewer no later than 10 business days (Mon-Fri) after quarter end'
- **Cause:** No approved exception documented; the reviewer failed to sign the Q2 2026 review within the required timeframe
- **Effect:** Control C3 cannot be validated for Q2 2026 as the mandatory reviewer sign-off is missing
- **Recommendation:** Obtain the missing signature from the reviewer or document an approved exception. If no valid exception exists, this represents a control deficiency that must be remediated.
- **Evidence:** user_access_reviews/UAR-2026Q2

### C5-completeness · high · 1 of 30

- **Condition:** 1 of 30 items failed: AIDAB886960EB41A@PAR-2026Q1. AIDAB886960EB41A existed on 2026-04-01 but is not in PAR-2026Q1.
- **Criteria:** Every AWS admin that existed at the review date is on that quarter's reviewed list
- **Cause:** not determined
- **Effect:** The control 'Privileged access is reviewed quarterly' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** aws_iam_admins/AIDAB886960EB41A, privileged_access_reviews/PAR-2026Q1

### C10-new_hire · moderate · 3 of 30

- **Condition:** Three employees (E1125, E1140, E1145) completed new-hire security training 49, 52, and 56 days respectively after their hire dates, exceeding the 30-day limit specified in the policy.
- **Criteria:** Section 2.1: New employees complete 'Security Awareness - New Hire' within 30 calendar days of their hire date.
- **Cause:** Training completions were delayed beyond the required timeframe without documented approval or exception.
- **Effect:** Employees were not protected by security awareness training during the initial period of employment, creating exposure to security risks.
- **Recommendation:** Implement automated reminders for managers and new hires to ensure training is completed within 30 days. Establish an exception process requiring documented approval for any delays, and enforce timely completion through follow-up procedures.
- **Evidence:** hr_roster/E1125, lms_completions/LMS-00010, hr_roster/E1140, lms_completions/LMS-00109, hr_roster/E1145, lms_completions/LMS-00149

### C7-ticketed · moderate · 1 of 8

- **Condition:** Emergency deploy D-00875 (deployed 2026-09-16) has no linked change ticket (ticket field is empty)
- **Criteria:** Policy section 3.2: 'It must be recorded in an Emergency Change ticket linked from the deploy'
- **Cause:** No Emergency Change ticket was created or linked for this emergency deploy
- **Effect:** Unable to verify retroactive approval within 2 business days; control objective not met
- **Recommendation:** Ensure all emergency deploys are linked to an Emergency Change ticket and obtain retroactive approval from Head of Engineering or delegate within 2 business days
- **Evidence:** deploys/D-00875

### C8-critical_sla · moderate · 1 of 9

- **Condition:** VULN-0037 (CVE-2026-16362) was open for 50 calendar days before closure, exceeding the 30-day remediation SLA. The vulnerability has no associated risk acceptance ticket.
- **Criteria:** Policy section 2.2: 'Critical vulnerabilities are remediated within 30 calendar days of being opened.'
- **Cause:** No approved risk acceptance was obtained for this critical vulnerability despite the extended remediation timeline.
- **Effect:** A critical vulnerability remained unremediated beyond the required 30-day window without documented exception approval, creating exposure to potential exploitation.
- **Recommendation:** Ensure all critical vulnerabilities are either remediated within 30 days or have an approved risk acceptance ticket (signed by Security Lead and CTO) before the 30-day deadline expires. Implement monitoring alerts for vulnerabilities approaching the 30-day threshold.
- **Evidence:** vulnerabilities/VULN-0037

### C8-weekly_scan · moderate · 3 of 53

- **Condition:** 3 of 53 items failed: 2026-W30, 2026-W31, 2026-W32. No scanner_runs occurrence for 2026-W30. No scanner_runs occurrence for 2026-W31. No scanner_runs occurrence for 2026-W32.
- **Criteria:** Each ISO week in the period has at least one completed scan
- **Cause:** not determined
- **Effect:** The control 'Vulnerability scans run weekly and critical findings are fixed within 30 days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** scanner_runs/SCAN-2026-W29, scanner_runs/SCAN-2026-W33

## Remediation tasks

- [high] C2-completeness: Implement automated deprovisioning workflow triggered by HR terminations and add monitoring to ensure all terminated users are suspended/deactivated within 24 hours
- [high] C3-signoff: Obtain the missing signature from the reviewer or document an approved exception. If no valid exception exists, this represents a control deficiency that must be remediated.
- [high] C5-completeness: Investigate each exception with the control owner and remediate.
- [moderate] C10-new_hire: Implement automated reminders for managers and new hires to ensure training is completed within 30 days. Establish an exception process requiring documented approval for any delays, and enforce timely completion through follow-up procedures.
- [moderate] C7-ticketed: Ensure all emergency deploys are linked to an Emergency Change ticket and obtain retroactive approval from Head of Engineering or delegate within 2 business days
- [moderate] C8-critical_sla: Ensure all critical vulnerabilities are either remediated within 30 days or have an approved risk acceptance ticket (signed by Security Lead and CTO) before the 30-day deadline expires. Implement monitoring alerts for vulnerabilities approaching the 30-day threshold.
- [moderate] C8-weekly_scan: Investigate each exception with the control owner and remediate.

Cost: US$0.0107 · 82,648 tokens · 26 LLM calls
