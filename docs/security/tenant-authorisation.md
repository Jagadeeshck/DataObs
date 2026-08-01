# Tenant authorisation
`X-DataObs-Tenant` and `X-DataObs-Environment` select, but never grant, context. Bindings and roles are evaluated only for the selected tenant/environment. `claims`, `bindings`, and `intersection` modes exist; production permits only the latter two. Ambiguous selection is rejected and tenant A authority cannot apply to tenant B.
