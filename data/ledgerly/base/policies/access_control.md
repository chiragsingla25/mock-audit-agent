# Ledgerly Access Control Policy
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
