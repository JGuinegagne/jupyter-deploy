from jupyter_deploy.enum import StoreType
from jupyter_deploy.provider.store.store_manager import StoreManager


class StoreManagerFactory:
    """Factory class to handle lower level imports of cloud provider specific store dependencies.

    This ensures that the base jupyter-deploy does not depend on any cloud provider SDK.
    """

    @staticmethod
    def get_manager(store_type: StoreType, store_id: str | None = None) -> StoreManager:
        """Return a StoreManager for the given store type.

        Args:
            store_type: The type of store.
            store_id: Optional store identifier (e.g., bucket name).

        Raises:
            NotImplementedError if the store type is not recognized.
        """
        if store_type == StoreType.S3_ONLY:
            # do NOT move imports to top level
            from jupyter_deploy.provider.aws.store.s3_store import S3StoreManager

            partition_lead_region = S3StoreManager.resolve_lead_region()
            return S3StoreManager(region=partition_lead_region, bucket_name=store_id)

        if store_type == StoreType.S3_DDB:
            # do NOT move imports to top level
            from jupyter_deploy.provider.aws.store.s3_dynamodb_store import S3DynamoDbTableStoreManager

            partition_lead_region = S3DynamoDbTableStoreManager.resolve_lead_region()
            return S3DynamoDbTableStoreManager(region=partition_lead_region, bucket_name=store_id)

        raise NotImplementedError(f"No store manager for store type: {store_type}")
