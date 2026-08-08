# dbt change analysis

The bounded parser accepts model metadata from a manifest, caps artifact/model/column sizes, and rejects raw/compiled SQL, credentials, tokens, secrets and environment payloads. It retains identifiers, relation metadata, dependencies, bounded column definitions, materialization, tags, allowlisted ownership metadata, path, and fingerprints. A stable canonical JSON fingerprint classifies added, modified, removed, unchanged, and fingerprint-supported rename candidates.
