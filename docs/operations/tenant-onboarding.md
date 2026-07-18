# Tenant onboarding

Create a tenant with `POST /api/v1/tenants` using `tenant_id`, `display_name`, and `namespace`. Pass `X-DataObs-Tenant` on subsequent requests to enforce tenant isolation.
