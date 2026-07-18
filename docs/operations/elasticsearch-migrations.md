# Elasticsearch migrations

Run:

```bash
dataobs elastic plan
dataobs elastic apply
dataobs elastic status
```

Rollback removes the migration record and leaves indices/templates for human snapshot validation.
