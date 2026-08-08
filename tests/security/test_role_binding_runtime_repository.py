from concurrent.futures import ThreadPoolExecutor

from services.security.memory_role_binding_repository import InMemoryRoleBindingRepository
from services.security.role_binding_repository import LastAdministratorError, RoleBinding


def test_development_repository_final_admin_check_is_atomic():
    repository = InMemoryRoleBindingRepository()
    binding = repository.create(
        RoleBinding.new(
            issuer="issuer",
            principal_type="user",
            principal_id="admin",
            tenant_id="platform",
            environments=["prod"],
            roles=["platform_admin"],
            actor="bootstrap",
        )
    )

    def disable():
        try:
            repository.disable(binding.binding_id, "platform", if_match=binding.etag, actor="operator")
            return "disabled"
        except LastAdministratorError:
            return "protected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert [future.result() for future in [pool.submit(disable), pool.submit(disable)]] == [
            "protected",
            "protected",
        ]


def test_development_repository_idempotent_create_and_payload_conflict():
    repository = InMemoryRoleBindingRepository()
    binding = RoleBinding.new(
        issuer="issuer",
        principal_type="user",
        principal_id="reader",
        tenant_id="t1",
        environments=["prod"],
        roles=["viewer"],
        actor="admin",
    )
    assert repository.create(binding) == repository.create(binding)
