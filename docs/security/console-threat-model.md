# Console threat model

Primary threats are cross-tenant projection reads, credential leakage, unsafe external links, stored-view injection and overly broad topology responses. Controls include mandatory server predicates, no browser-to-Elasticsearch access, no persistent tokens, normalized fields, bounded graph responses, CSP and same-origin API routing. Destructive and autonomous remediation are out of scope.
