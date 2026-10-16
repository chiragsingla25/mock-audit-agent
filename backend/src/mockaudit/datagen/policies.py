"""Ledgerly policy texts. The tester quotes these as criteria; trap explanations are grounded here."""

POLICIES = {
    "access_control.md": """# Ledgerly Access Control Policy
Version 3.2 · approved 2025-09-12 by the CTO · owner: IT Operations Manager

## 4.1 Access requests
Access to company systems is requested in the access request tool and approved by the system owner
before it is granted.

## 4.2 Birthright access
The roles `Employee-Base` (Okta, Slack, Google Workspace) are birthright roles. They are provisioned
automatically from the HR hire record and are pre-approved by HR as part of onboarding. A request
record created for a birthright role is for tracking only; its approval time may be after the grant.

## 4.3 Deprovisioning
When a workforce member's engagement ends, IT Operations must suspend or deactivate their Okta
account within 24 clock hours of the termination time recorded in the HR system. Weekends and public
holidays are not excluded. Suspension removes access; later deletion is housekeeping.

## 4.4 Change of worker type
When an employee converts to a contractor with no break in engagement, HR records a termination of
the employee record and a new contractor record linked by `prior_employee_id`. The existing account is
retained and its profile updated. Section 4.3 applies when the contractor engagement ends.

## 4.5 MFA
Multi-factor authentication is required for every Okta user through an active Okta sign-on policy
rule that covers every group.

## 4.6 Access reviews
User access (Okta) and privileged access (AWS administrators) are reviewed every calendar quarter.
Each review is signed and dated by the reviewer no later than 10 business days (Mon-Fri) after
quarter end. A review of the final quarter of the observation period may be signed after the period
ends, within that window.
""",
    "change_management.md": """# Ledgerly Change Management Policy
Version 2.1 · approved 2025-08-30 by the Head of Engineering

## 3.1 Standard changes
All production changes go through a pull request to `main`. At least one approver other than the
author must approve the pull request before it is merged.

## 3.2 Emergency changes
An emergency change may be deployed before approval to restore service. It must be recorded in an
Emergency Change ticket linked from the deploy, and approved retroactively by the Head of
Engineering or delegate within 2 business days (Mon-Fri, UTC dates) of the deploy.
""",
    "vulnerability_management.md": """# Ledgerly Vulnerability Management Policy
Version 1.6 · approved 2025-09-01 by the Security Lead

## 2.1 Scanning
Production assets are scanned at least once in every ISO calendar week.

## 2.2 Remediation
Critical vulnerabilities are remediated within 30 calendar days of being opened.

## 2.3 Risk acceptance
Where a critical vulnerability cannot be remediated in time, the Security Lead and the CTO may accept
the risk in a signed RISK ticket that names compensating controls and an expiry date. A critical
covered by an approved, unexpired risk acceptance is not a remediation exception.
""",
    "incident_response.md": """# Ledgerly Incident Response Policy
Version 2.0 · approved 2025-09-20 by the Security Lead

## 5.1 Logging
Security alerts and incidents are logged as Jira tickets of type Incident.

## 5.2 Post-incident review
Every confirmed security incident gets a post-incident review (PIR) document within 15 business days
of resolution, linked from the ticket. Tickets resolved as "Not an incident" (for example false
positives) are closed with a triage note and do not need a PIR.
""",
    "security_training.md": """# Ledgerly Security Training Policy
Version 1.4 · approved 2025-09-05 by the People Operations Lead

## 2.1 New hires
New employees (worker type "employee" in the HR roster) complete "Security Awareness - New Hire" within
30 calendar days of their hire date. Contractors are bound by the security terms of their contract
and are out of scope for this section.

## 2.2 Annual
All employees employed throughout the annual campaign (1 March to 31 May) complete
"Security Awareness - Annual 2026" during the campaign.
""",
    "vendor_management.md": """# Ledgerly Vendor Management Policy
Version 1.2 · approved 2025-07-14 by the Security Lead

## 3.1 Critical vendors
Vendors rated critical are risk-reviewed at least annually. The review date is recorded in the
vendor register.
""",
    "backup_recovery.md": """# Ledgerly Backup and Recovery Policy
Version 1.3 · approved 2025-06-02 by the Head of Platform

## 4.1 Restore testing
A restore of the production database from backup is tested at least once in every observation period
and evidenced in a signed restore test report.
""",
}
