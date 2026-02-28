import unittest
from unittest.mock import Mock, patch

from jupyter_deploy.api.aws.dynamodb.dynamodb_table import (
    create_lock_table,
    delete_table,
    get_table_by_name,
    wait_for_table_active,
)


class TestGetTableByName(unittest.TestCase):
    def test_returns_response_when_table_exists(self) -> None:
        mock_ddb = Mock()
        describe_response = {"Table": {"TableStatus": "ACTIVE"}, "ResponseMetadata": {}}
        mock_ddb.describe_table.return_value = describe_response

        result = get_table_by_name(mock_ddb, "my-table")

        self.assertEqual(result, describe_response)
        mock_ddb.describe_table.assert_called_once_with(TableName="my-table")

    def test_raises_when_table_not_found(self) -> None:
        mock_ddb = Mock()
        not_found = type("ResourceNotFoundException", (Exception,), {})
        mock_ddb.describe_table.side_effect = not_found()

        with self.assertRaises(not_found):
            get_table_by_name(mock_ddb, "missing-table")


class TestCreateLockTable(unittest.TestCase):
    def test_creates_table_with_correct_schema(self) -> None:
        mock_ddb = Mock()
        tags = {"Source": "jupyter-deploy-cli"}

        create_lock_table(mock_ddb, "my-table", tags)

        mock_ddb.create_table.assert_called_once_with(
            TableName="my-table",
            KeySchema=[{"AttributeName": "LockID", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "LockID", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
            Tags=[{"Key": "Source", "Value": "jupyter-deploy-cli"}],
        )

    def test_passes_multiple_tags(self) -> None:
        mock_ddb = Mock()
        tags = {"Source": "jupyter-deploy-cli", "Version": "1"}

        create_lock_table(mock_ddb, "my-table", tags)

        call_args = mock_ddb.create_table.call_args
        tag_list = call_args[1]["Tags"]
        tag_dict = {t["Key"]: t["Value"] for t in tag_list}
        self.assertEqual(tag_dict, {"Source": "jupyter-deploy-cli", "Version": "1"})


class TestWaitForTableActive(unittest.TestCase):
    def test_returns_immediately_when_active(self) -> None:
        mock_ddb = Mock()
        mock_ddb.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}

        wait_for_table_active(mock_ddb, "my-table")

        mock_ddb.describe_table.assert_called_once_with(TableName="my-table")

    @patch("time.sleep")
    @patch("time.time")
    def test_polls_until_active(self, mock_time: Mock, mock_sleep: Mock) -> None:
        mock_ddb = Mock()
        mock_ddb.describe_table.side_effect = [
            {"Table": {"TableStatus": "CREATING"}},
            {"Table": {"TableStatus": "ACTIVE"}},
        ]
        mock_time.side_effect = [0, 5, 10]

        wait_for_table_active(mock_ddb, "my-table", timeout_seconds=60)

        self.assertEqual(mock_ddb.describe_table.call_count, 2)
        mock_sleep.assert_called_once_with(2)

    @patch("time.sleep")
    @patch("time.time")
    def test_raises_timeout_error(self, mock_time: Mock, mock_sleep: Mock) -> None:
        mock_ddb = Mock()
        mock_ddb.describe_table.return_value = {"Table": {"TableStatus": "CREATING"}}
        mock_time.side_effect = [0, 100]

        with self.assertRaises(TimeoutError) as ctx:
            wait_for_table_active(mock_ddb, "my-table", timeout_seconds=10)

        self.assertIn("Timed out", str(ctx.exception))


class TestDeleteTable(unittest.TestCase):
    def test_calls_delete_table(self) -> None:
        mock_ddb = Mock()

        delete_table(mock_ddb, "my-table")

        mock_ddb.delete_table.assert_called_once_with(TableName="my-table")
