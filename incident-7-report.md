# Incident Investigation Report: High security incident for alex.morgan

**Generated:** 2026-07-15 04:51:35 UTC
**Incident ID:** 7

## Incident Overview

Correlated 2 alerts involving alex.morgan and CLOUD-IAM.

- **Severity:** high
- **Status:** open
- **Affected user:** alex.morgan
- **Affected assets:** CLOUD-IAM
- **First seen:** 2026-06-16 08:42:11 UTC
- **Last seen:** 2026-06-16 08:49:05 UTC
- **Suspected attack path:** Brute force followed by successful login -> Successful login from unusual IP

## Executive Summary

Incident 7 is a high severity investigation involving alex.morgan and CLOUD-IAM. The suspected attack path is: Brute force followed by successful login -> Successful login from unusual IP.

## Technical Summary

Correlated 2 alerts and 5 normalized events. Alert rules observed: Brute force followed by successful login, Successful login from unusual IP. Evidence event IDs: 92, 93, 94, 95, 97.

## Attack Timeline

- **2026-06-16 08:42:11 UTC** - Event 92: CLOUD-IAM / interactive_login
- **2026-06-16 08:43:02 UTC** - Event 93: CLOUD-IAM / interactive_login
- **2026-06-16 08:44:19 UTC** - Event 94: CLOUD-IAM / interactive_login
- **2026-06-16 08:45:51 UTC** - Event 95: CLOUD-IAM / interactive_login
- **2026-06-16 08:49:05 UTC** - Event 97: CLOUD-IAM / interactive_login

## Triggered Alerts

| Rule | Severity | User | Asset | Description |
| --- | --- | --- | --- | --- |
| Brute force followed by successful login | high | alex.morgan | CLOUD-IAM | alex.morgan had 4 failed logins followed by a successful login from 203.0.113.77. |
| Successful login from unusual IP | medium | alex.morgan | CLOUD-IAM | alex.morgan successfully logged in from unusual IP 203.0.113.77. |

## Evidence Event IDs

92, 93, 94, 95, 97

## Recommended Containment Steps

- Preserve incident evidence and keep original normalized event IDs attached to the case.
- Review and validate each alert before taking irreversible remediation action.
- Disable or reset sessions for affected user accounts: alex.morgan.
- Isolate or increase monitoring on affected assets: CLOUD-IAM.
- Revoke suspicious access keys, tokens, and VPN sessions tied to the incident.
- Review API export activity and confirm whether data left the environment.

## Analyst Notes

_Add analyst observations, validation results, decisions, and follow-up actions here._

## Limitations

- This report is generated from incident, alert, event, and summary data currently stored in the platform.
- Missing or incomplete source telemetry may affect the investigation narrative.
- AI-assisted content should be validated by a qualified analyst before operational or legal use.
- This Markdown export is intended for investigation support and is not a formal forensic report.
