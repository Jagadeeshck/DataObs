/** Presentation reference to Team 0's built-in role identifiers; this grants no authority. */
export const canonicalRoles = [
  "platform_admin",
  "tenant_admin",
  "operator",
  "investigator",
  "monitor_editor",
  "workflow_approver",
  "viewer",
  "collector",
] as const;
export type CanonicalRole = (typeof canonicalRoles)[number];
