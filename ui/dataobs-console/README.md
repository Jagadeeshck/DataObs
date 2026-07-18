# DataObs Console

The strict TypeScript React/Vite application is DataObs' guided product surface. Kibana remains the deep investigation and administration surface.

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm api:generate
pnpm dev
```

The browser calls only the DataObs API. Local authentication uses secure same-origin development sessions; bearer test tokens, when needed, are held in memory and are never persisted in browser storage. The production adapter is designed for a future secure-cookie OIDC/session exchange.

## Performance budgets

The current-view contract is capped at 1,000 nodes and 2,500 edges. Total uncompressed JavaScript must remain below 2 MB; production source maps are disabled.
