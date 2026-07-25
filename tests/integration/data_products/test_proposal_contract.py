from packages.domain_model.data_product import DataProductMembershipProposal


def test_proposal_schema_keeps_revision_and_source_distinct():
    schema = DataProductMembershipProposal.model_json_schema()
    assert "proposal_revision" in schema["required"]
    assert set(schema["properties"]["source"]["enum"]) >= {"lineage", "dependency"}
