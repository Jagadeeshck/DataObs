# DataObs version and API policy

The machine authority is `version-policy.yaml`. Patch releases preserve public API and configuration contracts and prohibit destructive required migrations. Minor releases may add APIs and deprecate contracts. Breaking stable contracts require a major version, an appropriate API version (not an incidental `/api/v2` in this work), a deprecation window, and an operator migration guide. Structural checks do not prove semantic compatibility.
