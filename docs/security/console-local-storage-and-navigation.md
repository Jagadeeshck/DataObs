# Console local storage and safe navigation

Console local storage is limited to bounded onboarding preferences and Quick Find recent metadata. Recent records contain entity type, display label, canonical route, timestamp, tenant, and environment and are filtered to the active trusted context. Never store tokens, authorization headers, evidence, incident comments, personal data, provider settings, or credentials.

Investigation return locations are parsed against the current origin and accepted only when their pathname is registered. Protocol-relative, cross-origin, malformed, and unknown paths are discarded. Entity path parameters always use the registry encoder. Tenant/environment authority comes only from authenticated context.
