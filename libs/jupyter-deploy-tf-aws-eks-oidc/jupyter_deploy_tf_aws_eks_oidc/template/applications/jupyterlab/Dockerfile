ARG CLAUDE_CODE_VERSION
ARG CODEX_VERSION

# Coding agent CLIs. The npm packages wrap native binaries but need a newer node
# than trixie ships, so install them here and copy the prefix (plus node, for the
# codex launcher) into the final image.
FROM node:22-trixie-slim AS ai-clis
ARG CLAUDE_CODE_VERSION
ARG CODEX_VERSION
RUN test -n "$CLAUDE_CODE_VERSION" && test -n "$CODEX_VERSION" && \
    npm install -g --prefix /opt/ai-clis \
      "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
      "@openai/codex@${CODEX_VERSION}" && \
    npm cache clean --force

FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim
ARG CODEX_MODEL

USER root

# git for the coding agents' repo awareness; procps (ps) for the Codex TUI,
# which tracks its background app-server by pid.
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends git procps && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash jovyan

RUN mkdir -p /etc/jupyter
COPY jupyter_server_config.py /etc/jupyter/

RUN mkdir -p /opt/uv/jupyter
COPY pyproject.toml /opt/uv/jupyter/pyproject.toml
RUN uv sync --directory /opt/uv/jupyter

# Installed outside /home/jovyan, which the data volume mounts over. Both CLIs
# reach Bedrock with the workspace's EKS Pod Identity credentials; the region and
# inference profile prefix come from the WorkspaceTemplate env.
COPY --from=ai-clis /usr/local/bin/node /usr/local/bin/node
COPY --from=ai-clis /opt/ai-clis /opt/ai-clis
RUN ln -s /opt/ai-clis/bin/claude /usr/local/bin/claude && \
    ln -s /opt/ai-clis/bin/codex /usr/local/bin/codex
COPY claude-managed-settings.json /etc/claude-code/managed-settings.json
COPY codex-config.toml /etc/codex/config.toml
RUN test -n "$CODEX_MODEL" && sed -i "s|@CODEX_MODEL@|${CODEX_MODEL}|" /etc/codex/config.toml

COPY jupyter-start.sh /usr/local/bin/
COPY jupyter-reset.sh /usr/local/bin/

RUN chmod -R a+r /opt/uv
RUN chmod -R a+r /etc/jupyter /etc/claude-code /etc/codex
RUN chmod +x /usr/local/bin/jupyter-start.sh
RUN chmod +x /usr/local/bin/jupyter-reset.sh
RUN chown -R jovyan:jovyan /home/jovyan

WORKDIR /home/jovyan
USER jovyan

ENTRYPOINT ["/usr/local/bin/jupyter-start.sh"]
