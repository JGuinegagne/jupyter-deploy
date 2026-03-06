import unittest
from unittest.mock import Mock

from jupyter_deploy.api.aws.sts.sts_identity import get_caller_arn, get_partition, get_partition_lead_region
from jupyter_deploy.exceptions import UnsupportedProviderRegionError


class TestGetCallerArn(unittest.TestCase):
    def test_returns_full_arn(self) -> None:
        sts_client = Mock()
        sts_client.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:user/jeff"}

        self.assertEqual(get_caller_arn(sts_client), "arn:aws:iam::123456789012:user/jeff")


class TestGetPartition(unittest.TestCase):
    def test_extracts_aws_commercial_partition(self) -> None:
        sts_client = Mock()
        sts_client.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:user/test"}

        self.assertEqual(get_partition(sts_client), "aws")

    def test_extracts_aws_china_partition(self) -> None:
        sts_client = Mock()
        sts_client.get_caller_identity.return_value = {"Arn": "arn:aws-cn:iam::123456789012:user/test"}

        self.assertEqual(get_partition(sts_client), "aws-cn")

    def test_extracts_aws_govcloud_partition(self) -> None:
        sts_client = Mock()
        sts_client.get_caller_identity.return_value = {"Arn": "arn:aws-us-gov:iam::123456789012:user/test"}

        self.assertEqual(get_partition(sts_client), "aws-us-gov")


class TestGetPartitionLeadRegion(unittest.TestCase):
    def test_returns_us_east_1_for_commercial(self) -> None:
        sts_client = Mock()
        sts_client.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:user/test"}

        self.assertEqual(get_partition_lead_region(sts_client), "us-east-1")

    def test_returns_cn_north_1_for_china(self) -> None:
        sts_client = Mock()
        sts_client.get_caller_identity.return_value = {"Arn": "arn:aws-cn:iam::123456789012:user/test"}

        self.assertEqual(get_partition_lead_region(sts_client), "cn-north-1")

    def test_returns_us_gov_west_1_for_govcloud(self) -> None:
        sts_client = Mock()
        sts_client.get_caller_identity.return_value = {"Arn": "arn:aws-us-gov:iam::123456789012:user/test"}

        self.assertEqual(get_partition_lead_region(sts_client), "us-gov-west-1")

    def test_raises_for_unknown_partition(self) -> None:
        sts_client = Mock()
        sts_client.get_caller_identity.return_value = {"Arn": "arn:aws-iso:iam::123456789012:user/test"}

        with self.assertRaises(UnsupportedProviderRegionError) as ctx:
            get_partition_lead_region(sts_client)

        self.assertEqual(ctx.exception.region_or_location, "aws-iso")
        self.assertIsNotNone(ctx.exception.hint)
        hint: str = ctx.exception.hint  # type: ignore[assignment]
        self.assertIn("aws", hint)
        self.assertIn("aws-cn", hint)
        self.assertIn("aws-us-gov", hint)
