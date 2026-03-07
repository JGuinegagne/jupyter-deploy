from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from jupyter_deploy.enum import StoreType
from jupyter_deploy.exceptions import InvalidStoreTypeError

STORE_CONFIG_V1_KEYS_ORDER = [
    "store-type",
    "store-id",
    "project-id",
]


class JupyterDeployStoreConfigV1(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    store_type: str | None = Field(alias="store-type", default=None)
    store_id: str | None = Field(alias="store-id", default=None)
    project_id: str | None = Field(alias="project-id", default=None)

    def get_store_type(self) -> StoreType:
        """Return the store type as an enum.

        Raises:
            InvalidStoreTypeError: If the store type is not recognized.
            ValueError: If store_type is None.
        """
        if self.store_type is None:
            raise ValueError("store-type is not set")
        try:
            return StoreType.from_string(self.store_type)
        except ValueError:
            raise InvalidStoreTypeError(self.store_type, [t.value for t in StoreType]) from None


# Combined type using discriminated union
JupyterDeployStoreConfig = Annotated[JupyterDeployStoreConfigV1, "store-type"]
