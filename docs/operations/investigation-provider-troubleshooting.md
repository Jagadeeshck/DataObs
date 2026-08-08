# Investigation provider troubleshooting

`permission denied` means the identity lacks the provider read permission. `not configured` corresponds to a bounded endpoint returning not found. `timed out` means the two-second budget elapsed. `unavailable` covers an isolated request failure. `unsupported` means the provider does not support the anchor. Retry once with Refresh, confirm tenant/environment and capability configuration, then follow the capability-owned request ID. Never treat an empty response as healthy.
