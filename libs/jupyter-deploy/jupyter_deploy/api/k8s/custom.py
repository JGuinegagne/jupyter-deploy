from dataclasses import dataclass
from typing import Any

from kubernetes.client import CustomObjectsApi


@dataclass(frozen=True)
class CustomResourceRef:
    group: str
    version: str
    plural: str


@dataclass(frozen=True)
class CustomObjectResult:
    name: str
    resource: dict[str, Any]


def list_namespaced(
    api: CustomObjectsApi,
    ref: CustomResourceRef,
    namespace: str,
    limit: int | None = None,
    _continue: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    kwargs: dict[str, Any] = {
        "group": ref.group,
        "version": ref.version,
        "namespace": namespace,
        "plural": ref.plural,
    }
    if limit:
        kwargs["limit"] = limit
    if _continue:
        kwargs["_continue"] = _continue

    result = api.list_namespaced_custom_object(**kwargs)
    items: list[dict[str, Any]] = result.get("items", [])
    next_token: str | None = result.get("metadata", {}).get("continue") or None
    return items, next_token


def list_cluster(
    api: CustomObjectsApi,
    ref: CustomResourceRef,
    limit: int | None = None,
    _continue: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    kwargs: dict[str, Any] = {
        "group": ref.group,
        "version": ref.version,
        "plural": ref.plural,
    }
    if limit:
        kwargs["limit"] = limit
    if _continue:
        kwargs["_continue"] = _continue

    result = api.list_cluster_custom_object(**kwargs)
    items: list[dict[str, Any]] = result.get("items", [])
    next_token: str | None = result.get("metadata", {}).get("continue") or None
    return items, next_token


def get_namespaced(api: CustomObjectsApi, ref: CustomResourceRef, namespace: str, name: str) -> CustomObjectResult:
    result: dict[str, Any] = api.get_namespaced_custom_object(
        group=ref.group,
        version=ref.version,
        namespace=namespace,
        plural=ref.plural,
        name=name,
    )
    obj_name: str = result.get("metadata", {}).get("name", "")
    return CustomObjectResult(name=obj_name, resource=result)


def patch_namespaced(
    api: CustomObjectsApi, ref: CustomResourceRef, namespace: str, name: str, body: dict[str, Any]
) -> CustomObjectResult:
    result: dict[str, Any] = api.patch_namespaced_custom_object(
        group=ref.group,
        version=ref.version,
        namespace=namespace,
        plural=ref.plural,
        name=name,
        body=body,
    )
    obj_name: str = result.get("metadata", {}).get("name", "")
    return CustomObjectResult(name=obj_name, resource=result)
