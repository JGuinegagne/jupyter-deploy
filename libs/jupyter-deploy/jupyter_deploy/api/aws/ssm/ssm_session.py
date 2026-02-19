from mypy_boto3_ssm import SSMClient
from mypy_boto3_ssm.type_defs import DescribeInstanceInformationRequestTypeDef, InstanceInformationTypeDef

from jupyter_deploy.exceptions import UnreachableHostError


def describe_instance_information(ssm_client: SSMClient, instance_id: str) -> InstanceInformationTypeDef:
    """Call SSM:DescribeInstanceInformation, return the result.

    Raises:
        UnreachableHostError: If the instance information is not available (instance stopped or SSM agent not running)
    """

    request: DescribeInstanceInformationRequestTypeDef = {"Filters": [{"Key": "InstanceIds", "Values": [instance_id]}]}
    response = ssm_client.describe_instance_information(**request)
    information_list = response["InstanceInformationList"]

    if not information_list:
        # NOTE: pytest-jupyter-deploy depends on this error message for retry logic
        raise UnreachableHostError(f"Instance '{instance_id}' is not reporting to SSM")

    return information_list[0]
