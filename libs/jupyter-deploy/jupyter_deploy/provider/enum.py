from enum import Enum


class ProviderType(str, Enum):
    """Enum to list the types of cloud providers."""

    AWS = "aws"
