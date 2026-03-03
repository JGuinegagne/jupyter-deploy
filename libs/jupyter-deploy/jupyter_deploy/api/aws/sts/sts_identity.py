from __future__ import annotations

from mypy_boto3_sts.client import STSClient

from jupyter_deploy.exceptions import UnsupportedProviderRegionError
from jupyter_deploy.provider.aws.store.constants import PARTITION_LEAD_REGIONS


def get_partition(sts_client: STSClient) -> str:
    """Return the AWS partition of the caller's identity.

    Calls STS:GetCallerIdentity and extracts the partition from the ARN.
    """
    identity = sts_client.get_caller_identity()
    return identity["Arn"].split(":")[1]


def get_partition_lead_region(sts_client: STSClient) -> str:
    """Return the lead region for the caller's AWS partition.

    Raises:
        UnsupportedProviderRegionError: If the partition is not recognized.
    """
    partition = get_partition(sts_client)
    if partition not in PARTITION_LEAD_REGIONS:
        supported = ", ".join(PARTITION_LEAD_REGIONS.keys())
        raise UnsupportedProviderRegionError(
            partition,
            hint=f"Use credentials from one of the supported AWS partitions: {supported}",
        )
    return PARTITION_LEAD_REGIONS[partition]
