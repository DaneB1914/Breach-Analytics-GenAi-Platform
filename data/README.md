# Sample Security Logs

These files contain realistic but fake security data for the Breach Analytics GenAI Platform. They are safe for a portfolio project and do not contain real personal data, real credentials, or real customer information.

The data is intentionally small enough to inspect by hand, but varied enough to support future ETL testing. Field names are mostly consistent, but not identical across sources. For example, user identity appears as `username`, `user`, `actor`, and `user_name`; event time appears as `timestamp`, `time`, `event_time`, and `observed_at`. Phase 5 ETL can normalize those differences.

## Files

### `auth_logs.json`

Fake identity-provider authentication events from `CLOUD-IAM`.

Represents:

- Normal login activity for `jamie.lee`
- Normal service-account token refresh for `svc-reporting`
- Repeated failed logins for `alex.morgan`
- A later successful login for `alex.morgan` from unusual public IP `203.0.113.77`
- A privileged console session started after the successful login

Useful future normalized fields include `timestamp`, `source_system`, `event_type`, `username`, `source_ip`, `asset`, `action`, `outcome`, and `reason`.

### `vpn_logs.csv`

Fake VPN session telemetry.

Represents:

- Normal VPN activity for `jamie.lee`
- A service tunnel for `svc-reporting`
- A suspicious VPN session for `alex.morgan` from `203.0.113.77`
- A large outbound data transfer during Alex's VPN session

Useful future normalized fields include `time`, `user`, `client_ip`, `assigned_private_ip`, `device_name`, `action`, `result`, `session_id`, `bytes_in`, and `bytes_out`.

### `cloud_audit_logs.json`

Fake cloud control-plane audit events.

Represents:

- Normal cloud object access by `jamie.lee`
- Normal scheduled reporting activity by `svc-reporting`
- Suspicious identity and admin actions by `alex.morgan`
- Access-key creation, admin policy attachment, security group change, MFA disablement, and file archive listing

Useful future normalized fields include `event_time`, `actor`, `actor_type`, `source_ip`, `service`, `asset`, `operation`, `outcome`, `target_resource`, and `details`.

### `api_access_logs.csv`

Fake API gateway access logs from `API-GATEWAY-01`.

Represents:

- Normal profile and report access by `jamie.lee`
- Normal scheduled report access by `svc-reporting`
- Abnormal admin queries, bulk exports, service-token creation, and large file downloads by `alex.morgan`

Useful future normalized fields include `timestamp`, `user`, `source_ip`, `asset`, `http_method`, `path`, `status_code`, `response_bytes`, `records_returned`, `user_agent`, and `request_category`.

### `endpoint_alerts.json`

Fake endpoint detection and response events.

Represents:

- Normal workstation and service activity for `jamie.lee` and `svc-reporting`
- Suspicious PowerShell activity on `LAPTOP-ALEX-01`
- Attempted LSASS credential access
- Download of a suspicious script from `192.0.2.44`
- Access to `FILE-SERVER-02`
- Archive creation and possible exfiltration behavior

Useful future normalized fields include `observed_at`, `host`, `user_name`, `source_system`, `event_type`, `process_name`, `command_line`, `destination_ip`, `action`, `outcome`, `severity`, `mitre_technique_id`, and `message`.

## Breach Story Timeline

All timestamps are fake and use UTC.

| Time | Source | Event |
| --- | --- | --- |
| 2026-06-16T08:10:12Z | Auth | `jamie.lee` has a normal successful login from `198.51.100.24`. |
| 2026-06-16T08:12:04Z | Auth | `svc-reporting` refreshes its service token from private IP `10.20.5.15`. |
| 2026-06-16T08:42:11Z - 08:45:51Z | Auth | `alex.morgan` has four failed login attempts from `203.0.113.77`. |
| 2026-06-16T08:49:05Z | Auth | `alex.morgan` successfully logs in from the same unusual IP. |
| 2026-06-16T08:53:22Z | VPN | `alex.morgan` starts a VPN session from `203.0.113.77` and receives private IP `10.8.14.23`. |
| 2026-06-16T09:05:38Z - 09:14:49Z | Cloud audit | `alex.morgan` creates an access key, attaches `AdministratorAccess`, changes network access, and disables MFA. |
| 2026-06-16T09:12:44Z | Endpoint | `LAPTOP-ALEX-01` shows an attempted LSASS credential dump mapped to MITRE `T1003.001`. |
| 2026-06-16T09:17:32Z - 09:24:08Z | Cloud/API/Endpoint | `alex.morgan` lists finance archives, accesses `FILE-SERVER-02`, creates an archive, and downloads a large file through `API-GATEWAY-01`. |
| 2026-06-16T09:28:09Z - 09:31:36Z | API | `alex.morgan` creates a service token and performs another bulk customer export. |
| 2026-06-16T09:34:18Z | Endpoint | `LAPTOP-ALEX-01` connects to `192.0.2.44`, suggesting possible exfiltration. |
| 2026-06-16T09:42:12Z - 09:44:12Z | Cloud/API/Endpoint | `svc-reporting` continues expected reporting activity, useful as normal service-account comparison data. |

## Correlation Hints for Future ETL

- `alex.morgan` is the suspicious human user.
- `jamie.lee` is the normal human comparison user.
- `svc-reporting` is the normal service-account comparison identity.
- `203.0.113.77` is the unusual public source IP for suspicious activity.
- `10.8.14.23` is Alex's assigned VPN private IP.
- `LAPTOP-ALEX-01`, `API-GATEWAY-01`, `FILE-SERVER-02`, and `CLOUD-IAM` connect the story across sources.
- Event IDs such as `auth-1008`, `vpn-2003`, `audit-3005`, `req-4005`, and `end-5004` are useful evidence examples for future incident summaries.
