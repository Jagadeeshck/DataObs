# DataObs — Alloy Config Generator

Generates per-tenant Grafana Alloy config overlays from a central base config.

## Usage

```bash
# Install dependencies
pip install pyyaml

# Add a tenant
cp tools/alloy-config-gen/tenants/tenant.example.yaml \
   tools/alloy-config-gen/tenants/my-tenant.yaml
# Edit my-tenant.yaml with real values

# Generate configs
python tools/alloy-config-gen/generate.py \
  --tenants tools/alloy-config-gen/tenants/ \
  --base integrations/grafana-alloy/alloy/config.alloy \
  --output output/alloy-configs/
```

## Credential Injection

Credentials are **never** written to config files. Each tenant's auth
values are read from environment variables named:
- `DATAOBS_{TENANT_ID}_PROM_USER`
- `DATAOBS_{TENANT_ID}_PROM_PASS`

Resolves: [#31](https://github.com/Jagadeeshck/DataObs/issues/31)
