from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from .models import ContractEvaluation, ContractVersion, DataContract


class NotFound(KeyError):
    pass


class StaleETag(ValueError):
    pass


class OverlappingEffectiveVersion(ValueError):
    pass


class MemoryContractRepository:
    """Test repository. Production wiring must use ElasticsearchContractRepository."""

    def __init__(self) -> None:
        self.contracts: dict[tuple[str, str, str], DataContract] = {}
        self.versions: dict[tuple[str, str, str], list[ContractVersion]] = {}
        self.evaluations: list[ContractEvaluation] = []

    def create_draft(self, contract: DataContract, version: ContractVersion) -> DataContract:
        key = (contract.tenant_id, contract.environment, contract.contract_id)
        if key in self.contracts:
            raise ValueError("contract already exists")
        self.contracts[key], self.versions[key] = deepcopy(contract), [version]
        return deepcopy(contract)

    def get_contract(self, tenant: str, environment: str, contract_id: str) -> DataContract:
        try:
            return deepcopy(self.contracts[(tenant, environment, contract_id)])
        except KeyError as exc:
            raise NotFound(contract_id) from exc

    def update_draft(self, contract: DataContract, if_match: str) -> DataContract:
        key = (contract.tenant_id, contract.environment, contract.contract_id)
        current = self.get_contract(*key)
        if current.etag != if_match:
            raise StaleETag("contract changed; reload and review before retrying")
        contract.revision = current.revision + 1
        self.contracts[key] = deepcopy(contract)
        return deepcopy(contract)

    def add_version(self, tenant: str, environment: str, version: ContractVersion) -> None:
        key = (tenant, environment, version.contract_id)
        for existing in self.versions.get(key, []):
            if existing.effective_from and version.effective_from:
                a_end, b_end = (
                    existing.effective_until or datetime.max.replace(tzinfo=version.effective_from.tzinfo),
                    version.effective_until or datetime.max.replace(tzinfo=version.effective_from.tzinfo),
                )
                if existing.effective_from < b_end and version.effective_from < a_end:
                    raise OverlappingEffectiveVersion("effective periods overlap")
        self.versions.setdefault(key, []).append(version)

    def get_version_effective_at(
        self, tenant: str, environment: str, contract_id: str, at: datetime
    ) -> ContractVersion:
        matches = [
            v
            for v in self.versions.get((tenant, environment, contract_id), [])
            if v.effective_from and v.effective_from <= at and (v.effective_until is None or at < v.effective_until)
        ]
        if len(matches) != 1:
            raise NotFound("no unique effective version")
        return matches[0]
