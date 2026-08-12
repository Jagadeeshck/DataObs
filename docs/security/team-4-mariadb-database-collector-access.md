# Team 4 MariaDB collector access

Production configuration requires TLS, CA verification, and server identity verification. Connector/Python 1.1.14 exposes `ssl_verify_cert`; it delegates certificate-chain and hostname verification to MariaDB Connector/C. There is no separate Python `ssl_verify_identity` connection option. Certification must be blocked as `hostname_verification_unavailable` if the deployed Connector/C cannot demonstrate identity validation.

The provider fixes all SQL statements. It exposes no DSN, init SQL, client flags, session variables, authentication plugin paths, connection attributes, or multi-statements. `local_infile=False`; `LOAD DATA LOCAL INFILE`, mutations, administration, raw view/CHECK/default/generated/partition expressions, query text, row samples, and sequence/history values are forbidden.
