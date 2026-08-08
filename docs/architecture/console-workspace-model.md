# Console workspace model

`ConsoleWorkspace` is a closed typed union. Each entry declares label, description, icon, default registered route, optional safe keyboard shortcut, and Quick Find keywords. Workspaces are navigation concepts, not security boundaries; visibility is derived from permission-filtered routes. Exact workspace matches rank before route results.

Defaults are Home `/`, Observe `/flow`, Investigate `/investigate`, Respond `/incidents`, Integrate `/integrations`, and Admin `/administration`. If a default is restricted, the UI exposes a workspace only when at least one authorized non-system route exists.
