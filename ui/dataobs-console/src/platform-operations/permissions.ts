export const PLATFORM_OPERATIONS_READ = "platform_operations:read" as const;
export const RESOURCE_READ_PERMISSIONS = {
  environment: "environments:read",
  installation: "installations:read",
  cluster: "clusters:read",
  tenant: "tenants:provision",
} as const;
