# Ledgerly SOC 2 readiness report — audit-base-20261017T025347678-r3

_Readiness forecast from synthetic evidence. Not an audit opinion._ Mode: agent, review: skip.

## Coverage

| Control | Status | Steps tested | Not tested | Notes |
|---|---|---|---|---|
| C1 | no exceptions found | approval | — | — |
| C2 | exceptions | completeness, timeliness | — | X3001: no okta_users record, so nothing to check (not an exception). |
| C3 | exceptions | occurrence, signoff | — | — |
| C4 | no exceptions found | coverage | — | — |
| C5 | exceptions | occurrence, completeness, signoff | — | — |
| C6 | exceptions | segregation | — | — |
| C7 | exceptions | ticketed, retro_approval | — | — |
| C8 | exceptions | weekly_scan, critical_sla | — | — |
| C9 | no exceptions found | pir | — | — |
| C10 | exceptions | new_hire, annual | — | — |
| C11 | no exceptions found | review_in_period | — | — |
| C12 | exceptions | restore_test | — | — |

## Findings (10)

_Not reviewed by a person: these are the findings the agent kept (evaluation run)._

### C2-completeness · high · 1 of 20

- **Condition:** HR record E1070 shows terminated user Anderson, Ivy with Okta account 00u27ba276404 remaining ACTIVE, but no suspend/deactivate event exists in okta_events
- **Criteria:** Policy section 4.3: 'IT Operations must suspend or deactivate their Okta account within 24 clock hours of the termination time'
- **Cause:** Deprovisioning event was not generated for this terminated user; owner confirmed it was missed
- **Effect:** User retained access to Okta beyond the 24-hour requirement
- **Recommendation:** Implement controls to ensure all terminated users are deprovisioned within 24 hours and investigate why E1070 was missed
- **Evidence:** hr_roster/E1070, okta_users/00u27ba276404

### C2-timeliness · high · 2 of 18

- **Condition:** Users E1055 (Young, Evie) and E1109 (Ryan, Harper) had first suspend/deactivate events occurring 219.0 hours and 63.0 hours respectively after termination, exceeding the 24-hour limit
- **Criteria:** Policy section 4.3: 'IT Operations must suspend or deactivate their Okta account within 24 clock hours of the termination time'
- **Cause:** Deprovisioning workflows failed to execute within the required 24-hour window
- **Effect:** Users retained access to Okta systems beyond the allowed 24-hour period post-termination
- **Recommendation:** Review and remediate deprovisioning processes to ensure compliance with the 24-hour requirement; investigate root causes of delays
- **Evidence:** hr_roster/E1055, okta_events/OK-000099, hr_roster/E1109, okta_events/OK-000261

### C3-signoff · high · 1 of 4

- **Condition:** Review UAR-2026Q3 for quarter ending 2026-09-30 was performed on 2026-10-07 but was not signed by reviewer Dana Whitfield as of evidence collection date 2026-10-30; the 10 business day deadline of 2026-10-14 had passed
- **Criteria:** Section 4.6 of access_control policy: 'Each review is signed and dated by the reviewer no later than 10 business days (Mon-Fri) after quarter end'
- **Cause:** Reviewer did not complete the required sign-off within the mandated timeframe; no documented exception or approval for delay exists
- **Effect:** Control C3 failed for Q3 2026 - user access review was not properly completed with required reviewer sign-off, leaving potential unauthorized access unverified
- **Recommendation:** Obtain immediate sign-off from Dana Whitfield for UAR-2026Q3 if still valid, implement reminder process to ensure timely sign-offs, and document any exceptions with proper approval
- **Evidence:** user_access_reviews/UAR-2026Q3

### C5-completeness · high · 1 of 30

- **Condition:** 1 of 30 items failed: AIDAFCB2757B1F7F@PAR-2026Q3. AIDAFCB2757B1F7F existed on 2026-10-07 but is not in PAR-2026Q3.
- **Criteria:** Every AWS admin that existed at the review date is on that quarter's reviewed list
- **Cause:** not determined
- **Effect:** The control 'Privileged access is reviewed quarterly' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** aws_iam_admins/AIDAFCB2757B1F7F, privileged_access_reviews/PAR-2026Q3

### C6-segregation · high · 4 of 320

- **Condition:** Four PRs (PR-1230, PR-1018, PR-1300, PR-1265) were merged to main with only the author as the sole approver, violating segregation of duties requirements.
- **Criteria:** Policy Section 3.1: 'At least one approver other than the author must approve the pull request before it is merged.'
- **Cause:** Pull requests were merged without independent review/approval from someone other than the author.
- **Effect:** Production changes were deployed without proper segregation of duties, increasing risk of unauthorized or unreviewed code entering production.
- **Recommendation:** Enforce branch protection rules to require at least one approver other than the author before allowing merges to main. Implement automated checks to prevent self-approval.
- **Evidence:** github_prs/PR-1230, github_prs/PR-1018, github_prs/PR-1300, github_prs/PR-1265

### C10-new_hire · moderate · 3 of 30

- **Condition:** Three employees (E1136, E1138, E1141) completed Security Awareness - New Hire training 58, 31, and 44 days respectively after their hire dates, exceeding the 30-day requirement
- **Criteria:** Section 2.1: New employees must complete 'Security Awareness - New Hire' within 30 calendar days of their hire date
- **Cause:** Training completion was delayed beyond the 30-day window; no approved exceptions were documented for these delays
- **Effect:** Employees worked for extended periods without completing mandatory security training, creating exposure to security risks
- **Recommendation:** Implement automated tracking and reminder systems to ensure new hires complete security training within 30 days; establish escalation procedures for managers when training is overdue; review whether any delays had legitimate business reasons requiring formal exception approval
- **Evidence:** hr_roster/E1136, lms_completions/LMS-00109, hr_roster/E1138, lms_completions/LMS-00073, hr_roster/E1141, lms_completions/LMS-00142

### C12-restore_test · moderate · 1 of 1

- **Condition:** The only restore test record (RST-2025-09) has test date 2025-09-12, which is before the observation period start date of 2025-10-01
- **Criteria:** Policy section 4.1: 'A restore of the production database from backup is tested at least once in every observation period'
- **Cause:** No restore test was performed within the observation period 2025-10-01 to 2026-09-30
- **Effect:** Control C12 'Backup restore is tested annually' is not satisfied for this observation period
- **Recommendation:** Perform and document a restore test within the observation period 2025-10-01 to 2026-09-30
- **Evidence:** restore_tests/RST-2025-09

### C7-ticketed · moderate · 2 of 8

- **Condition:** Two emergency deploys (D-00389, D-00851) have no linked change ticket (ticket field is empty)
- **Criteria:** Policy section 3.2: 'An emergency change may be deployed before approval to restore service. It must be recorded in an Emergency Change ticket linked from the deploy'
- **Cause:** Emergency deploys were executed without creating or linking an Emergency Change ticket
- **Effect:** Cannot verify retroactive approval was obtained; control objective for emergency change tracking not met
- **Recommendation:** Implement process controls to ensure all emergency deploys are linked to an Emergency Change ticket before or immediately after deployment
- **Evidence:** deploys/D-00389, deploys/D-00851

### C8-critical_sla · moderate · 1 of 9

- **Condition:** Critical vulnerability VULN-0003 (CVE-2026-29275) was opened on 2025-11-01 and closed on 2025-12-18, taking 47 days to remediate. The vulnerability record shows no risk acceptance was documented.
- **Criteria:** Section 2.2 of vulnerability_management policy: 'Critical vulnerabilities are remediated within 30 calendar days of being opened.' Section 2.3 states exceptions require an approved, unexpired risk acceptance ticket.
- **Cause:** No risk acceptance was obtained for this critical vulnerability, and remediation exceeded the 30-day SLA without documented approval.
- **Effect:** The organization failed to meet its vulnerability management SLA for critical vulnerabilities, potentially leaving systems exposed to known security risks beyond acceptable thresholds.
- **Recommendation:** Implement processes to ensure all critical vulnerabilities are either remediated within 30 days or have approved risk acceptances in place before the deadline. Review VULN-0003 to understand why no risk acceptance was obtained and prevent similar SLA breaches.
- **Evidence:** vulnerabilities/VULN-0003

### C8-weekly_scan · moderate · 3 of 53

- **Condition:** 3 of 53 items failed: 2026-W32, 2026-W33, 2026-W34. No scanner_runs occurrence for 2026-W32. No scanner_runs occurrence for 2026-W33. No scanner_runs occurrence for 2026-W34.
- **Criteria:** Each ISO week in the period has at least one completed scan
- **Cause:** not determined
- **Effect:** The control 'Vulnerability scans run weekly and critical findings are fixed within 30 days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** scanner_runs/SCAN-2026-W31, scanner_runs/SCAN-2026-W35

## Remediation tasks

- [high] C2-completeness: Implement controls to ensure all terminated users are deprovisioned within 24 hours and investigate why E1070 was missed
- [high] C2-timeliness: Review and remediate deprovisioning processes to ensure compliance with the 24-hour requirement; investigate root causes of delays
- [high] C3-signoff: Obtain immediate sign-off from Dana Whitfield for UAR-2026Q3 if still valid, implement reminder process to ensure timely sign-offs, and document any exceptions with proper approval
- [high] C5-completeness: Investigate each exception with the control owner and remediate.
- [high] C6-segregation: Enforce branch protection rules to require at least one approver other than the author before allowing merges to main. Implement automated checks to prevent self-approval.
- [moderate] C10-new_hire: Implement automated tracking and reminder systems to ensure new hires complete security training within 30 days; establish escalation procedures for managers when training is overdue; review whether any delays had legitimate business reasons requiring formal exception approval
- [moderate] C12-restore_test: Perform and document a restore test within the observation period 2025-10-01 to 2026-09-30
- [moderate] C7-ticketed: Implement process controls to ensure all emergency deploys are linked to an Emergency Change ticket before or immediately after deployment
- [moderate] C8-critical_sla: Implement processes to ensure all critical vulnerabilities are either remediated within 30 days or have approved risk acceptances in place before the deadline. Review VULN-0003 to understand why no risk acceptance was obtained and prevent similar SLA breaches.
- [moderate] C8-weekly_scan: Investigate each exception with the control owner and remediate.

Cost: US$0.0147 · 120,319 tokens · 33 LLM calls
