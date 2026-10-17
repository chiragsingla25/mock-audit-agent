# Ledgerly SOC 2 readiness report — audit-base-20261017T024416974-r1

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

- **Condition:** Employee E1070 (hr_roster) was terminated but has no corresponding suspend or deactivate event in okta_events. The associated okta_users record 00u27ba276404 shows status ACTIVE.
- **Criteria:** Policy section 4.3: 'IT Operations must suspend or deactivate their Okta account within 24 clock hours of the termination time recorded in the HR system.'
- **Cause:** No deprovisioning event was generated for this terminated user.
- **Effect:** User retained access to Okta beyond the required 24-hour window post-termination.
- **Recommendation:** Implement controls to ensure all terminated users have corresponding deprovisioning events within 24 hours, and add monitoring to detect missing events.
- **Evidence:** hr_roster/E1070, okta_users/00u27ba276404

### C2-timeliness · high · 2 of 18

- **Condition:** E1055 had first suspend event 219.0 hours after termination (okta_events OK-000099); E1109 had first suspend event 63.0 hours after termination (okta_events OK-000261). Both exceed the 24-hour limit.
- **Criteria:** Policy section 4.3: 'IT Operations must suspend or deactivate their Okta account within 24 clock hours of the termination time recorded in the HR system.'
- **Cause:** Deprovisioning events were delayed beyond the 24-hour window without documented exceptions or approvals.
- **Effect:** Users E1055 and E1109 retained access to Okta beyond the allowed 24-hour period post-termination.
- **Recommendation:** Review and improve the deprovisioning workflow to ensure events occur within 24 hours of termination. Consider automated triggers tied to HR termination events.
- **Evidence:** hr_roster/E1055, okta_events/OK-000099, hr_roster/E1109, okta_events/OK-000261

### C3-signoff · high · 1 of 4

- **Condition:** UAR-2026Q3 was not signed by the reviewer within 10 business days of quarter end; record shows 'Signed: (not signed)' with deadline 2026-10-14 already passed
- **Criteria:** Policy section 4.6 Access reviews: 'Each review is signed and dated by the reviewer no later than 10 business days (Mon-Fri) after quarter end'
- **Cause:** Reviewer Dana Whitfield did not sign the Q3 2026 access review before the 10-business-day deadline
- **Effect:** Lack of documented reviewer sign-off means we cannot verify that the quarterly access review was properly completed and approved, creating risk of unauthorized or inappropriate access remaining undetected
- **Recommendation:** Ensure all quarterly access reviews are signed by the designated reviewer within 10 business days of quarter end; implement automated tracking and reminders for pending signatures; consider escalation procedures for overdue reviews
- **Evidence:** user_access_reviews/UAR-2026Q3

### C5-completeness · high · 1 of 30

- **Condition:** 1 of 30 items failed: AIDAFCB2757B1F7F@PAR-2026Q3. AIDAFCB2757B1F7F existed on 2026-10-07 but is not in PAR-2026Q3.
- **Criteria:** Every AWS admin that existed at the review date is on that quarter's reviewed list
- **Cause:** not determined
- **Effect:** The control 'Privileged access is reviewed quarterly' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** aws_iam_admins/AIDAFCB2757B1F7F, privileged_access_reviews/PAR-2026Q3

### C6-segregation · high · 4 of 320

- **Condition:** Four PRs (PR-1230, PR-1018, PR-1300, PR-1265) were merged to main with only the author as the sole approver, providing no independent review.
- **Criteria:** Policy Section 3.1: 'At least one approver other than the author must approve the pull request before it is merged.'
- **Cause:** Pull requests were merged without enforcing the segregation of duties requirement; either the merge was allowed despite lacking proper approval or approvals were not properly recorded.
- **Effect:** Production changes were deployed without independent verification, increasing the risk of unreviewed code entering production and potential quality/security issues going undetected.
- **Recommendation:** Enforce branch protection rules to require at least one approver other than the author before allowing merges to main. Implement automated checks to block merges that do not meet this requirement. Review existing PRs to identify and remediate similar exceptions.
- **Evidence:** github_prs/PR-1230, github_prs/PR-1018, github_prs/PR-1300, github_prs/PR-1265

### C10-new_hire · moderate · 3 of 30

- **Condition:** Three employees completed new-hire security training beyond the 30-day limit: E1136 (58 days late), E1138 (31 days late), E1141 (44 days late)
- **Criteria:** Policy section 2.1: New employees must complete 'Security Awareness - New Hire' within 30 calendar days of their hire date
- **Cause:** Operating gap - training completions were delayed beyond the required timeframe without documented exceptions
- **Effect:** Employees were non-compliant with security training requirements during the observation period, creating potential security awareness gaps
- **Recommendation:** Implement automated tracking and reminder systems for new hire training, establish manager accountability for timely completion, and review hiring/onboarding processes to prevent future delays
- **Evidence:** hr_roster/E1136, lms_completions/LMS-00109, hr_roster/E1138, lms_completions/LMS-00073, hr_roster/E1141, lms_completions/LMS-00142

### C12-restore_test · moderate · 1 of 1

- **Condition:** The only restore test record (RST-2025-09) has test date 2025-09-12, which is before the observation period start date of 2025-10-01. No restore test was evidenced within the observation period 2025-10-01 to 2026-09-30.
- **Criteria:** Policy section 4.1: 'A restore of the production database from backup is tested at least once in every observation period and evidenced in a signed restore test report.'
- **Cause:** No restore test was performed or documented during the observation period; the existing test predates the period by approximately 19 days.
- **Effect:** Control C12 'Backup restore is tested annually' cannot be considered effective for observation period 2025-10-01 to 2026-09-30 due to lack of annual restore testing evidence.
- **Recommendation:** Perform and document a restore test within the current observation period, ensuring the test report is signed and dated within 2025-10-01 to 2026-09-30.
- **Evidence:** restore_tests/RST-2025-09

### C7-ticketed · moderate · 2 of 8

- **Condition:** Two emergency deploys (D-00389 and D-00851) were identified with no linked emergency change ticket (ticket field empty in both records).
- **Criteria:** Policy Section 3.2: 'An emergency change may be deployed before approval to restore service. It must be recorded in an Emergency Change ticket linked from the deploy'
- **Cause:** Emergency changes were deployed without creating required change tickets; no documented exception or approval for this omission.
- **Effect:** Lack of audit trail for emergency changes; unable to verify retroactive approval within 2 business days; control objective not met.
- **Recommendation:** Implement system controls to prevent emergency deploys without a linked change ticket, and establish a remediation process to document and approve retroactively for existing gaps.
- **Evidence:** deploys/D-00389, deploys/D-00851

### C8-critical_sla · moderate · 1 of 9

- **Condition:** Critical vulnerability VULN-0003 (CVE-2026-29275) required 47 days to remediate from opening (2025-11-01) to closing (2025-12-18), exceeding the 30-day SLA limit. No risk acceptance ticket was associated with this vulnerability.
- **Criteria:** Policy section 2.2: 'Critical vulnerabilities are remediated within 30 calendar days of being opened.' Section 2.3: Exceptions require an approved, unexpired risk acceptance ticket signed by Security Lead and CTO.
- **Cause:** The vulnerability remained open beyond the 30-day window without obtaining an approved risk acceptance before the deadline.
- **Effect:** The organization failed to meet its documented vulnerability management SLA for critical vulnerabilities, potentially leaving production assets exposed to known security risks for an extended period.
- **Recommendation:** Implement automated tracking and alerts for critical vulnerabilities approaching the 30-day threshold. Establish a process to obtain risk acceptance approvals before SLA expiration when remediation cannot be completed in time.
- **Evidence:** vulnerabilities/VULN-0003

### C8-weekly_scan · moderate · 3 of 53

- **Condition:** 3 of 53 items failed: 2026-W32, 2026-W33, 2026-W34. No scanner_runs occurrence for 2026-W32. No scanner_runs occurrence for 2026-W33. No scanner_runs occurrence for 2026-W34.
- **Criteria:** Each ISO week in the period has at least one completed scan
- **Cause:** not determined
- **Effect:** The control 'Vulnerability scans run weekly and critical findings are fixed within 30 days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** scanner_runs/SCAN-2026-W31, scanner_runs/SCAN-2026-W35

## Remediation tasks

- [high] C2-completeness: Implement controls to ensure all terminated users have corresponding deprovisioning events within 24 hours, and add monitoring to detect missing events.
- [high] C2-timeliness: Review and improve the deprovisioning workflow to ensure events occur within 24 hours of termination. Consider automated triggers tied to HR termination events.
- [high] C3-signoff: Ensure all quarterly access reviews are signed by the designated reviewer within 10 business days of quarter end; implement automated tracking and reminders for pending signatures; consider escalation procedures for overdue reviews
- [high] C5-completeness: Investigate each exception with the control owner and remediate.
- [high] C6-segregation: Enforce branch protection rules to require at least one approver other than the author before allowing merges to main. Implement automated checks to block merges that do not meet this requirement. Review existing PRs to identify and remediate similar exceptions.
- [moderate] C10-new_hire: Implement automated tracking and reminder systems for new hire training, establish manager accountability for timely completion, and review hiring/onboarding processes to prevent future delays
- [moderate] C12-restore_test: Perform and document a restore test within the current observation period, ensuring the test report is signed and dated within 2025-10-01 to 2026-09-30.
- [moderate] C7-ticketed: Implement system controls to prevent emergency deploys without a linked change ticket, and establish a remediation process to document and approve retroactively for existing gaps.
- [moderate] C8-critical_sla: Implement automated tracking and alerts for critical vulnerabilities approaching the 30-day threshold. Establish a process to obtain risk acceptance approvals before SLA expiration when remediation cannot be completed in time.
- [moderate] C8-weekly_scan: Investigate each exception with the control owner and remediate.

Cost: US$0.0147 · 110,399 tokens · 32 LLM calls
