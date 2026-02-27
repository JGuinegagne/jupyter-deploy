import unittest
from typing import Any, cast

import botocore.exceptions

from jupyter_deploy.exceptions import InvalidProviderCredentialsError, ProviderPermissionError
from jupyter_deploy.provider.aws.aws_error_handler import aws_error_context_manager


def _client_error(code: str, message: str = "error", operation_name: str = "TestOp") -> botocore.exceptions.ClientError:
    error_response = cast(Any, {"Error": {"Code": code, "Message": message}})
    return botocore.exceptions.ClientError(error_response, operation_name)


class TestAwsErrorContextManager(unittest.TestCase):
    def test_no_credentials_raises_invalid_provider_credentials(self) -> None:
        with self.assertRaises(InvalidProviderCredentialsError), aws_error_context_manager():
            raise botocore.exceptions.NoCredentialsError()

    def test_partial_credentials_raises_invalid_provider_credentials(self) -> None:
        with self.assertRaises(InvalidProviderCredentialsError), aws_error_context_manager():
            raise botocore.exceptions.PartialCredentialsError(provider="test", cred_var="key")

    def test_access_denied_raises_provider_permission_error(self) -> None:
        with self.assertRaises(ProviderPermissionError), aws_error_context_manager():
            raise _client_error("AccessDenied")

    def test_expired_token_raises_invalid_provider_credentials(self) -> None:
        with self.assertRaises(InvalidProviderCredentialsError), aws_error_context_manager():
            raise _client_error("ExpiredToken")

    def test_other_client_error_reraises(self) -> None:
        with self.assertRaises(botocore.exceptions.ClientError), aws_error_context_manager():
            raise _client_error("ThrottlingException")

    def test_no_exception_passes_through(self) -> None:
        with aws_error_context_manager():
            result = 1 + 1

        self.assertEqual(result, 2)
