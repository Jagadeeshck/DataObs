import os,pytest
@pytest.mark.skipif(os.getenv("RUN_BIGQUERY_INTEGRATION_TESTS")!="1",reason="requires RUN_BIGQUERY_INTEGRATION_TESTS=1 and approved synthetic project credentials")
def test_live_bigquery_metadata_only():
 pytest.skip("live certification requires an explicitly approved synthetic project and locations")
