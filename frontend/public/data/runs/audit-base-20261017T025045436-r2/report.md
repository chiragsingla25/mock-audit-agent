# Ledgerly SOC 2 readiness report — audit-base-20261017T025045436-r2

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

_Not reviewed by a person: these are the findings this run kept, before any human review._

### C2-completeness · high · 1 of 20

- **Condition:** HR record E1070 shows employee Anderson, Ivy terminated on 2026-04-25, but okta_users record 00u27ba276404 shows status ACTIVE; okta_events records OK-000059 and OK-000162 show only session.start events with no suspend/deactivate event
- **Criteria:** Policy Section 4.3: When a workforce member's engagement ends, IT Operations must suspend or deactivate their Okta account within 24 clock hours of the termination time recorded in the HR system
- **Cause:** No deprovisioning action was taken for terminated employee; the Okta account was not suspended or deactivated after termination
- **Effect:** Employee retained active Okta access beyond the 24-hour window, creating unauthorized access risk and violating access control policy
- **Recommendation:** Implement automated deprovisioning workflow triggered by HR termination events to ensure all terminated employees' Okta accounts are suspended or deactivated within 24 hours as required by Section 4.3
- **Evidence:** hr_roster/E1070, okta_users/00u27ba276404, okta_events/OK-000059, okta_events/OK-000162

### C2-timeliness · high · 2 of 18

- **Condition:** E1055 had first suspend event 219 hours after termination (OK-000099); E1109 had first suspend event 63 hours after termination (OK-000261)
- **Criteria:** Section 4.3: 'IT Operations must suspend or deactivate their Okta account within 24 clock hours of the termination time recorded in the HR system'
- **Cause:** Delays in executing deprovisioning workflows
- **Effect:** Users retained access beyond the 24-hour compliance window
- **Recommendation:** Review and remediate deprovisioning processes to meet 24-hour requirement
- **Evidence:** hr_roster/E1055, okta_events/OK-000099, hr_roster/E1109, okta_events/OK-000261

### C3-signoff · high · 1 of 4

- **Condition:** UAR-2026Q3 review for quarter ending 2026-09-30 was performed on 2026-10-07 but remains unsigned as of evidence collection date 2026-10-30; the 10 business day deadline of 2026-10-14 has passed without signature
- **Criteria:** Section 4.6: Each review is signed and dated by the reviewer no later than 10 business days (Mon-Fri) after quarter end
- **Cause:** Reviewer Dana Whitfield did not sign the UAR-2026Q3 review within the required timeframe
- **Effect:** The Q3 2026 user access review lacks required reviewer sign-off, creating an unverified access review state
- **Recommendation:** Obtain immediate sign-off from Dana Whitfield on UAR-2026Q3 or document approved exception; implement reminder process to ensure timely quarterly review completion
- **Evidence:** user_access_reviews/UAR-2026Q3

### C5-completeness · high · 1 of 30

- **Condition:** 1 of 30 items failed: AIDAFCB2757B1F7F@PAR-2026Q3. AIDAFCB2757B1F7F existed on 2026-10-07 but is not in PAR-2026Q3.
- **Criteria:** Every AWS admin that existed at the review date is on that quarter's reviewed list
- **Cause:** not determined
- **Effect:** The control 'Privileged access is reviewed quarterly' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** aws_iam_admins/AIDAFCB2757B1F7F, privileged_access_reviews/PAR-2026Q3

### C6-segregation · high · 4 of 320

- **Condition:** Four PRs (PR-1230, PR-1018, PR-1300, PR-1265) were merged to main with only the author serving as the sole approver, providing no independent review.
- **Criteria:** Policy Section 3.1: 'At least one approver other than the author must approve the pull request before it is merged.'
- **Cause:** Pull requests were merged without enforcing the segregation of duties requirement; authors were able to self-approve their own changes.
- **Effect:** Production changes were deployed without independent verification, increasing the risk of unreviewed code defects, security vulnerabilities, or non-compliant changes reaching production.
- **Recommendation:** Enforce branch protection rules to require at least one approver distinct from the author before allowing merges to main. Implement automated checks to block self-approvals and ensure proper segregation of duties for all production changes.
- **Evidence:** github_prs/PR-1230, github_prs/PR-1018, github_prs/PR-1300, github_prs/PR-1265

### C10-new_hire · moderate · 3 of 30

- **Condition:** Three employees (E1136, E1138, E1141) completed new-hire security training 58, 31, and 44 days respectively after their hire dates, exceeding the 30-day deadline specified in the policy.
- **Criteria:** Section 2.1: New employees must complete 'Security Awareness - New Hire' within 30 calendar days of their hire date.
- **Cause:** Training completions were delayed beyond the required timeframe without any documented approval or exception.
- **Effect:** Employees were not compliant with security training requirements during the observation period, creating potential security awareness gaps.
- **Recommendation:** Implement automated reminders for managers and employees when training deadlines approach, and establish a process for documenting and approving any legitimate delays.
- **Evidence:** hr_roster/E1136, lms_completions/LMS-00109, hr_roster/E1138, lms_completions/LMS-00073, hr_roster/E1141, lms_completions/LMS-00142

### C12-restore_test · moderate · 1 of 1

- **Condition:** The only restore test record RST-2025-09 shows a test date of 2025-09-12, which is before the observation period start date of 2025-10-01. No restore test was evidenced within the observation period 2025-10-01 to 2026-09-30.
- **Criteria:** Policy Section 4.1: 'A restore of the production database from backup is tested at least once in every observation period and evidenced in a signed restore test report.'
- **Cause:** The restore test RST-2025-09 was performed on 2025-09-12, prior to the observation period beginning on 2025-10-01.
- **Effect:** Control C12 cannot be considered satisfied for the observation period 2025-10-01 to 2026-09-30 as there is no documented restore test within this period.
- **Recommendation:** Perform and document a restore test within the observation period (2025-10-01 to 2026-09-30) to satisfy the annual testing requirement.
- **Evidence:** restore_tests/RST-2025-09

### C7-ticketed · moderate · 2 of 8

- **Condition:** Two emergency deploys (D-00389 deployed 2026-02-23, D-00851 deployed 2026-09-11) have empty ticket fields with no linked change tickets
- **Criteria:** Policy section 3.2: 'An emergency change may be deployed before approval to restore service. It must be recorded in an Emergency Change ticket linked from the deploy'
- **Cause:** Owner confirmed that 'nobody raised the change ticket afterwards' for these hotfixes
- **Effect:** Emergency changes were deployed without required documentation, violating change management controls and preventing proper audit trail and retroactive approval process
- **Recommendation:** Implement automated enforcement requiring ticket linkage before emergency deploy completion; provide training to deployment personnel on change management policy requirements; establish monitoring to detect unticketed emergency deploys
- **Evidence:** deploys/D-00389, deploys/D-00851

### C8-critical_sla · moderate · 1 of 9

- **Condition:** Critical vulnerability VULN-0003 (CVE-2026-29275) remained open for 47 days from 2025-11-01 to 2025-12-18, exceeding the 30-day remediation requirement.
- **Criteria:** Section 2.2 of the vulnerability management policy: 'Critical vulnerabilities are remediated within 30 calendar days of being opened.'
- **Cause:** No risk acceptance was documented for this vulnerability, and it was not remediated within the required timeframe.
- **Effect:** The organization failed to meet its vulnerability management SLA for critical vulnerabilities, potentially leaving systems exposed to known security risks beyond acceptable thresholds.
- **Recommendation:** Implement stricter monitoring and escalation processes for critical vulnerabilities approaching the 30-day deadline, and ensure all risk acceptances are properly documented and tracked.
- **Evidence:** vulnerabilities/VULN-0003

### C8-weekly_scan · moderate · 3 of 53

- **Condition:** 3 of 53 items failed: 2026-W32, 2026-W33, 2026-W34. No scanner_runs occurrence for 2026-W32. No scanner_runs occurrence for 2026-W33. No scanner_runs occurrence for 2026-W34.
- **Criteria:** Each ISO week in the period has at least one completed scan
- **Cause:** not determined
- **Effect:** The control 'Vulnerability scans run weekly and critical findings are fixed within 30 days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** scanner_runs/SCAN-2026-W31, scanner_runs/SCAN-2026-W35

## Remediation tasks

- [high] C2-completeness: Implement automated deprovisioning workflow triggered by HR termination events to ensure all terminated employees' Okta accounts are suspended or deactivated within 24 hours as required by Section 4.3
- [high] C2-timeliness: Review and remediate deprovisioning processes to meet 24-hour requirement
- [high] C3-signoff: Obtain immediate sign-off from Dana Whitfield on UAR-2026Q3 or document approved exception; implement reminder process to ensure timely quarterly review completion
- [high] C5-completeness: Investigate each exception with the control owner and remediate.
- [high] C6-segregation: Enforce branch protection rules to require at least one approver distinct from the author before allowing merges to main. Implement automated checks to block self-approvals and ensure proper segregation of duties for all production changes.
- [moderate] C10-new_hire: Implement automated reminders for managers and employees when training deadlines approach, and establish a process for documenting and approving any legitimate delays.
- [moderate] C12-restore_test: Perform and document a restore test within the observation period (2025-10-01 to 2026-09-30) to satisfy the annual testing requirement.
- [moderate] C7-ticketed: Implement automated enforcement requiring ticket linkage before emergency deploy completion; provide training to deployment personnel on change management policy requirements; establish monitoring to detect unticketed emergency deploys
- [moderate] C8-critical_sla: Implement stricter monitoring and escalation processes for critical vulnerabilities approaching the 30-day deadline, and ensure all risk acceptances are properly documented and tracked.
- [moderate] C8-weekly_scan: Investigate each exception with the control owner and remediate.

Cost: US$0.0170 · 143,842 tokens · 40 LLM calls
