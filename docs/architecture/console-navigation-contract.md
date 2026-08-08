# Console navigation contract

The authoritative `consoleRoutes` registry owns URL, loader, permission, team owner, capability, workspace, section, priority, navigation level, parent, availability, configuration, Quick Find, and search metadata. Consumers must filter it; they must not create parallel capability menus.

Validation rejects unknown workspaces/owners/capabilities, duplicate priorities, orphan contextual routes, top-level entity details, parent/workspace conflicts, and breadcrumb cycles. Breadcrumb traversal is loop-protected and capped at twelve route ancestors. Context changes return entity routes to their nearest static authoritative parent.
