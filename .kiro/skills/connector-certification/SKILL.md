---
name: connector-certification
description: Certify actual packaged connector runtimes and distinguish registered, tested and supported providers.
---
# Connector Certification

1. Read provider registry, Integration SDK contract and Helm deployment list.
2. A Collection Manager-only provider is not supported unless the production runtime is shipped and certified.
3. Validate capability declaration, bounded retry, cancellation, redaction, checkpoint/lease safety, malformed response handling.
4. Real tests require real provider credentials supplied securely and recorded as permitted evidence; fixture pass is not live certification.
5. Record supported / experimental / not-run / excluded per capability, not generic yes/no provider label.
6. Preserve existing passing SDK and avoid release-week provider expansion.
**Output:** provider-support matrix, packaged runtime proof and limitations.

**Always:** respect `.kiro/steering/safety-and-evidence.md` and the canonical team ownership map. Use real source, current main and exact-SHA proof.
