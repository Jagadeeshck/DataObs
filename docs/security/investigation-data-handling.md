# Investigation data handling

Evidence and pins stay in React memory. Session/local storage never receives evidence, identifiers, labels, tenant, environment, incident bodies, queries, tokens or error payloads. Telemetry accepts only an allowlisted event, anchor type, bounded provider outcome/count, evidence-count bucket and handoff capability. Routes are same-origin and manifest-validated; return URLs lose their query. The browser calls capability APIs only and never queries Elasticsearch.
