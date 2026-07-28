# Role-permission matrix

The executable registry is `src/security/roles.py`. `viewer` receives domain reads; `operator` adds operational mutations and execution but not approval/IAM; `investigator` adds incident annotation; `monitor_editor` manages quality and monitors; `workflow_approver` adds workflow approval; `tenant_admin` receives tenant permissions but not `platform:admin`; `platform_admin` receives all registered permissions; `collector` receives only self-inspection and `collection:ingest`.

Unknown roles and unmapped groups grant nothing. Tenant administrators cannot grant platform administration or operate outside their active authorised tenant.
