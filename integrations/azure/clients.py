from importlib.metadata import PackageNotFoundError, version

from .authentication import create_credential
from .errors import safe_error
from .identifiers import datalake_endpoint

ALLOWED_OPERATIONS = frozenset(
    {
        "subscription_get",
        "factory_get",
        "pipeline_list",
        "trigger_list",
        "adf_pipeline_runs_query",
        "adf_activity_runs_query",
        "workspace_get",
        "sql_pool_list",
        "spark_pool_list",
        "synapse_pipeline_list",
        "synapse_pipeline_runs_query",
        "synapse_activity_runs_query",
        "storage_account_get",
        "filesystem_list",
        "path_list",
    }
)
PROHIBITED_OPERATION_FRAGMENTS = frozenset(
    {
        "create",
        "update",
        "delete",
        "start",
        "stop",
        "pause",
        "resume",
        "cancel",
        "trigger_run",
        "execute",
        "upload",
        "download",
        "append",
        "flush",
        "rename",
        "acl",
        "key",
        "sas",
    }
)


class ReadOnlyAzureClients:
    def __init__(self, operations):
        self._operations = operations

    def invoke(self, operation, *args, **kwargs):
        if operation not in ALLOWED_OPERATIONS:
            raise safe_error("unsupported_feature")
        return self._operations[operation](*args, **kwargs)


class AzureClientFactory:
    def create(self, cfg):
        try:
            from azure.mgmt.datafactory import DataFactoryManagementClient
            from azure.mgmt.resource import SubscriptionClient
            from azure.mgmt.storage import StorageManagementClient
            from azure.mgmt.synapse import SynapseManagementClient
            from azure.storage.filedatalake import DataLakeServiceClient
        except ImportError as exc:
            raise safe_error("dependency_unavailable") from exc
        credential = create_credential(cfg.authentication)
        sub = cfg.subscription_id
        subscriptions = SubscriptionClient(credential).subscriptions
        adf = DataFactoryManagementClient(credential, sub)
        syn = SynapseManagementClient(credential, sub)
        storage = StorageManagementClient(credential, sub)
        lakes = {
            x["storage_account"]: DataLakeServiceClient(datalake_endpoint(x["storage_account"]), credential=credential)
            for x in cfg.adls_gen2
        }
        return ReadOnlyAzureClients(
            {
                "subscription_get": lambda: subscriptions.get(sub),
                "factory_get": adf.factories.get,
                "pipeline_list": adf.pipelines.list_by_factory,
                "trigger_list": adf.triggers.list_by_factory,
                "adf_pipeline_runs_query": adf.pipeline_runs.query_by_factory,
                "adf_activity_runs_query": adf.activity_runs.query_by_pipeline_run,
                "workspace_get": syn.workspaces.get,
                "sql_pool_list": syn.sql_pools.list_by_workspace,
                "spark_pool_list": syn.big_data_pools.list_by_workspace,
                "synapse_pipeline_list": lambda rg, n: (),
                "synapse_pipeline_runs_query": lambda *a, **k: (),
                "synapse_activity_runs_query": lambda *a, **k: (),
                "storage_account_get": storage.storage_accounts.get_properties,
                "filesystem_list": lambda account: lakes[account].list_file_systems(),
                "path_list": lambda account, fs, path: lakes[account]
                .get_file_system_client(fs)
                .get_paths(path=path, recursive=True),
            }
        )

    def versions(self):
        out = {}
        for p in (
            "azure-identity",
            "azure-mgmt-resource",
            "azure-mgmt-datafactory",
            "azure-mgmt-synapse",
            "azure-mgmt-storage",
            "azure-storage-file-datalake",
            "azure-core",
        ):
            try:
                out[p] = version(p)
            except PackageNotFoundError:
                out[p] = "unavailable"
        return out

    def close(self, client):
        close = getattr(client, "close", None)
        if close:
            close()
