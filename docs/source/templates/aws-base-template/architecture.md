# Architecture

## Containers

The application runs as a set of containerized services orchestrated by Docker Compose. [Traefik](https://doc.traefik.io/traefik/) acts as the reverse proxy — it handles TLS termination, routes incoming HTTPS requests, and delegates authentication decisions to [OAuth2 Proxy](https://oauth2-proxy.github.io/oauth2-proxy/) via the [ForwardAuth](https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/forwardauth/) middleware. OAuth2 Proxy manages the full [OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749) flow with [GitHub as the identity provider](https://oauth2-proxy.github.io/oauth2-proxy/configuration/providers/github), handling redirects, token validation, and session cookies. Authenticated requests are forwarded to the **JupyterLab** container. A Fluent Bit sidecar collects service logs and a logrotate container manages log retention on disk.

![Containers](diagrams/containers.svg)

## Authentication flow

On first visit, Traefik forwards the request to OAuth2 Proxy, which redirects the browser to GitHub for authentication. GitHub prompts the user to authorize the OAuth App, then redirects back to OAuth2 Proxy with an authorization code. OAuth2 Proxy exchanges the code for an access token, verifies the user's identity against the configured allowlist, sets a session cookie, and lets the request through to **JupyterLab**. Subsequent requests are authenticated via the session cookie without repeating the OAuth dance. See the [OAuth2 Proxy GitHub provider documentation](https://oauth2-proxy.github.io/oauth2-proxy/configuration/providers/github) for details.

![Authentication flow](diagrams/auth-flow.svg)
