# Ledgerly SOC 2 readiness report — audit-a-20261017T024647072-r1

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
| C7 | no exceptions found | ticketed, retro_approval | — | — |
| C8 | exceptions | weekly_scan, critical_sla | — | — |
| C9 | no exceptions found | pir | — | — |
| C10 | exceptions | new_hire, annual | — | — |
| C11 | no exceptions found | review_in_period | — | — |
| C12 | no exceptions found | restore_test | — | — |

## Findings (7)

_Not reviewed by a person: these are the findings this run kept, before any human review._

### C2-timeliness · high · 2 of 19

- **Condition:** Two terminated users had their Okta accounts suspended/deactivated more than 24 hours after termination: E1006 (Rossi, Kenji) had first suspend event 77 hours after termination (OK-000037), and E1038 (Lee, Ivy) had first deactivate event 89 hours after termination (OK-000153). Owner confirmed both offboarding tickets were actioned late with no approved exceptions.
- **Criteria:** Policy section 4.3: 'When a workforce member's engagement ends, IT Operations must suspend or deactivate their Okta account within 24 clock hours of the termination time recorded in the HR system. Weekends and public holidays are not excluded.'
- **Cause:** Offboarding tickets were actioned late without approved exceptions
- **Effect:** Terminated users retained access to Okta for up to 89 hours beyond the allowed 24-hour window, creating unauthorized access risk
- **Recommendation:** Implement automated monitoring and alerts for termination-to-deprovisioning delays, establish escalation procedures for late tickets, and ensure all exceptions are formally documented and approved before implementation
- **Evidence:** hr_roster/E1006, okta_events/OK-000037, hr_roster/E1038, okta_events/OK-000153

### C3-signoff · high · 1 of 4

- **Condition:** Review UAR-2026Q2 (quarter ending 2026-06-30) shows 'Signed: (not signed)' - the reviewer Dana Whitfield did not sign this quarterly access review
- **Criteria:** Policy section 4.6: 'Each review is signed and dated by the reviewer no later than 10 business days (Mon-Fri) after quarter end'
- **Cause:** The review was performed on 2026-07-02 but was never signed by the reviewer
- **Effect:** The quarterly user access review control was not properly completed for Q2 2026, leaving a gap in access certification oversight
- **Recommendation:** Obtain retroactive sign-off from the reviewer Dana Whitfield for UAR-2026Q2, or conduct a new review with proper documentation and sign-off within the required timeframe
- **Evidence:** user_access_reviews/UAR-2026Q2

### C5-completeness · high · 1 of 30

- **Condition:** AWS admin AIDA0DAED3206F81 existed on 2026-01-06 but was not listed in the PAR-2025Q4 privileged access review
- **Criteria:** Policy section 4.6: 'privileged access (AWS administrators) are reviewed every calendar quarter'
- **Cause:** The quarterly review process did not capture all existing AWS admins
- **Effect:** Privileged access for AIDA0DAED3206F81 was not reviewed in Q4 2025, leaving a gap in access oversight
- **Recommendation:** Implement automated checks to ensure all AWS admins existing during each quarter are included in that quarter's review
- **Evidence:** aws_iam_admins/AIDA0DAED3206F81, privileged_access_reviews/PAR-2025Q4

### C6-segregation · high · 3 of 320

- **Condition:** Three pull requests (PR-1316, PR-1229, PR-1017) were merged to main with only the author serving as approver, violating segregation of duties requirements.
- **Criteria:** Policy section 3.1: 'At least one approver other than the author must approve the pull request before it is merged.'
- **Cause:** Pull request merge controls did not enforce that an approver different from the author must approve before merge.
- **Effect:** Production changes were deployed without independent review, increasing risk of unvalidated code entering production.
- **Recommendation:** Configure branch protection rules to require at least one approval from a user other than the PR author before allowing merges to main. Implement automated enforcement to prevent self-approval.
- **Evidence:** github_prs/PR-1316, github_prs/PR-1229, github_prs/PR-1017

### C10-new_hire · moderate · 2 of 30

- **Condition:** Two employees (E1131, E1139) completed new-hire security training 44 and 49 days after their respective hire dates, exceeding the 30-day limit specified in policy section 2.1
- **Criteria:** Policy section 2.1: 'New employees complete Security Awareness - New Hire within 30 calendar days of their hire date'
- **Cause:** Training completions were delayed beyond the required timeframe without documented approval or exception
- **Effect:** Control failure: Employees were not trained within the required 30-day window, leaving them potentially exposed to security risks during the untrained period
- **Recommendation:** Implement automated reminders for managers when new hires approach the 30-day deadline; establish an exception request process with proper documentation; review training completion workflows to identify bottlenecks
- **Evidence:** hr_roster/E1131, lms_completions/LMS-00015, hr_roster/E1139, lms_completions/LMS-00143

### C8-critical_sla · moderate · 1 of 9

- **Condition:** Critical vulnerability VULN-0029 was open for 49 days from 2026-05-13 to 2026-07-01, exceeding the 30-day remediation SLA. No risk acceptance was documented for this vulnerability.
- **Criteria:** Policy section 2.2: 'Critical vulnerabilities are remediated within 30 calendar days of being opened.' Section 2.3 allows exceptions only with approved, unexpired risk acceptance tickets.
- **Cause:** No risk acceptance ticket was created or linked to VULN-0029 despite the 49-day delay exceeding the 30-day SLA threshold.
- **Effect:** Critical vulnerability remained unremediated beyond the acceptable timeframe without documented business justification or compensating controls approval.
- **Recommendation:** Implement enforcement to require risk acceptance documentation for any critical vulnerability approaching the 30-day SLA threshold. Review VULN-0029 to determine if compensating controls were in place and obtain retroactive approval if warranted, or document why this represents a control failure.
- **Evidence:** vulnerabilities/VULN-0029

### C8-weekly_scan · moderate · 3 of 53

- **Condition:** 3 of 53 items failed: 2026-W05, 2026-W06, 2026-W07. No scanner_runs occurrence for 2026-W05. No scanner_runs occurrence for 2026-W06. No scanner_runs occurrence for 2026-W07.
- **Criteria:** Each ISO week in the period has at least one completed scan
- **Cause:** not determined
- **Effect:** The control 'Vulnerability scans run weekly and critical findings are fixed within 30 days' did not operate as designed for these items.
- **Recommendation:** Investigate each exception with the control owner and remediate.
- **Evidence:** scanner_runs/SCAN-2026-W04, scanner_runs/SCAN-2026-W08

## Remediation tasks

- [high] C2-timeliness: Implement automated monitoring and alerts for termination-to-deprovisioning delays, establish escalation procedures for late tickets, and ensure all exceptions are formally documented and approved before implementation
- [high] C3-signoff: Obtain retroactive sign-off from the reviewer Dana Whitfield for UAR-2026Q2, or conduct a new review with proper documentation and sign-off within the required timeframe
- [high] C5-completeness: Implement automated checks to ensure all AWS admins existing during each quarter are included in that quarter's review
- [high] C6-segregation: Configure branch protection rules to require at least one approval from a user other than the PR author before allowing merges to main. Implement automated enforcement to prevent self-approval.
- [moderate] C10-new_hire: Implement automated reminders for managers when new hires approach the 30-day deadline; establish an exception request process with proper documentation; review training completion workflows to identify bottlenecks
- [moderate] C8-critical_sla: Implement enforcement to require risk acceptance documentation for any critical vulnerability approaching the 30-day SLA threshold. Review VULN-0029 to determine if compensating controls were in place and obtain retroactive approval if warranted, or document why this represents a control failure.
- [moderate] C8-weekly_scan: Investigate each exception with the control owner and remediate.

Cost: US$0.0119 · 93,817 tokens · 28 LLM calls
