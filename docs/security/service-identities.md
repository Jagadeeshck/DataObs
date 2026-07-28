# Service identities

Non-interactive collectors use OIDC client credentials. The provider must emit an explicit configured collector group and tenant/environment access. Collector permission is limited to ingestion and authentication self-inspection; it cannot browse product data, manage IAM, approve workflows, or use Console login. Rotate provider credentials and keep tokens short-lived.
