# Rollback policy

Rollback states are `supported`, `application_only`, `blocked_by_migration`, `blocked_by_configuration`, `not_applicable`, and `unvalidated`. Image rollback never proves system rollback. A rollback barrier is reported before upgrade; destructive reverse migrations are never automatic. The first release is `not_applicable`; unknown historical migration metadata remains `unvalidated`.
