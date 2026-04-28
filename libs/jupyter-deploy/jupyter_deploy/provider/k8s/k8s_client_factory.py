from kubernetes import client, config


class K8sClientFactory:
    """Build Kubernetes API clients from kubeconfig."""

    @staticmethod
    def from_kubeconfig(kubeconfig_path: str | None = None) -> client.ApiClient:
        api_client: client.ApiClient = config.new_client_from_config(config_file=kubeconfig_path)
        return api_client
