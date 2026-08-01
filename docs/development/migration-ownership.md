# Migration ownership

Team 0 owns the migration registry; feature teams propose requirements. Migrations are additive and released migrations immutable. One migration ID has one owning PR. Parallel teams reserve numbers with Team 0 before implementation and resolve conflicts before merge. Mappings must preserve tenant/environment scope. Rollback guidance and migration tests are mandatory. This foundation adds no migration.
