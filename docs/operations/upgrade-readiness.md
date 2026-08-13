# Upgrade readiness

Call `GET /api/v1/platform/upgrade-readiness?target=<SemVer>` with `platform_operations:read`, or run `bin/dataobs upgrade check --target <SemVer>`. `ready` requires every check and retained certification evidence; missing state yields `unknown` or `blocked`. Stable reason codes are suitable for automation. The returned plan is advisory and never executes an upgrade.
