from collections.abc import Generator
from contextlib import contextmanager

import botocore.exceptions

from jupyter_deploy.enum import ProviderType
from jupyter_deploy.exceptions import InvalidProviderCredentialsError, ProviderPermissionError

# Permission-related error codes
# Sources:
# - UnauthorizedOperation: EC2 API
#   (docs.aws.amazon.com/AWSEC2/latest/APIReference/errors-overview.html)
# - AccessDenied, AccessDeniedException, NotAuthorized, OptInRequired: Common across AWS services
#   (observed in practice, need specific documentation)
PERMISSION_ERROR_CODES = {
    "AccessDenied",
    "AccessDeniedException",
    "NotAuthorized",
    "UnauthorizedOperation",
    "OptInRequired",
}

# Credential-related error codes
# Sources:
# - ExpiredToken, InvalidIdentityToken : STS API
#   (docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html)
#   (docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)
# - AuthFailure, IncompleteSignature, InvalidClientTokenId, MissingAuthenticationToken
#   MissingAuthenticationToken: EC2 API
#  (docs.aws.amazon.com/AWSEC2/latest/APIReference/errors-overview.html)
# - AuthorizationHeaderMalformed, AuthorizationQueryParametersError: S3 Error Responses
#   (docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html)
# - ExpiredTokenException: EKS Error Responses
#   (https://docs.aws.amazon.com/eks/latest/APIReference/CommonErrors.html)
CREDENTIAL_ERROR_CODES = {
    "ExpiredToken",
    "InvalidIdentityToken",
    "AuthFailure",
    "IncompleteSignature",
    "InvalidClientTokenId",
    "MissingAuthenticationToken",
    "AuthorizationHeaderMalformed",
    "AuthorizationQueryParametersError",
    "ExpiredTokenException",
}


@contextmanager
def aws_error_context_manager() -> Generator[None, None, None]:
    """Catch botocore exceptions and re-raise as jupyter-deploy provider errors."""
    try:
        yield
    except botocore.exceptions.NoCredentialsError as e:
        raise InvalidProviderCredentialsError(
            provider_name=ProviderType.AWS,
            original_message=str(e),
        ) from e
    except botocore.exceptions.PartialCredentialsError as e:
        raise InvalidProviderCredentialsError(
            provider_name=ProviderType.AWS,
            original_message=str(e),
        ) from e
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        if error_code in PERMISSION_ERROR_CODES:
            operation = e.operation_name if hasattr(e, "operation_name") else None
            raise ProviderPermissionError(
                provider_name=ProviderType.AWS,
                operation=operation,
                original_message=error_message,
            ) from e

        if error_code in CREDENTIAL_ERROR_CODES:
            raise InvalidProviderCredentialsError(
                provider_name=ProviderType.AWS,
                original_message=error_message,
            ) from e

        # For other ClientErrors, re-raise
        raise
