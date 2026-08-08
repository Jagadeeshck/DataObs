from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import ContractEvaluation, DataContract


class ElasticsearchContractRepository:
    """Production persistence with tenant predicates, OCC and create-only evidence."""

    CURRENT_INDEX = "dataobs-data-contract-current-v1"
    EVALUATION_STREAM = "logs-dataobs.data-contract-evaluation-default"

    def __init__(self, client: Any) -> None:
        self.client = client

    def get_contract(self, tenant_id: str, environment: str, contract_id: str) -> dict[str, Any] | None:
        response = self.client.search(
            index=self.CURRENT_INDEX,
            size=1,
            query={
                "bool": {
                    "filter": [
                        {"term": {"tenant_id": tenant_id}},
                        {"term": {"environment": environment}},
                        {"term": {"contract_id": contract_id}},
                    ]
                }
            },
        )
        hits = response["hits"]["hits"]
        return (
            None
            if not hits
            else {**hits[0]["_source"], "_seq_no": hits[0]["_seq_no"], "_primary_term": hits[0]["_primary_term"]}
        )

    def put_contract(
        self, contract: DataContract, *, seq_no: int | None = None, primary_term: int | None = None
    ) -> None:
        kwargs = {} if seq_no is None else {"if_seq_no": seq_no, "if_primary_term": primary_term}
        self.client.index(
            index=self.CURRENT_INDEX,
            id=f"{contract.tenant_id}:{contract.environment}:{contract.contract_id}",
            document=asdict(contract),
            refresh="wait_for",
            **kwargs,
        )

    def append_evaluation(self, tenant_id: str, environment: str, evaluation: ContractEvaluation) -> None:
        document = asdict(evaluation) | {
            "tenant_id": tenant_id,
            "environment": environment,
            "@timestamp": evaluation.evaluated_at.isoformat(),
        }
        self.client.create(
            index=self.EVALUATION_STREAM, id=evaluation.evaluation_id, document=document, refresh="wait_for"
        )
