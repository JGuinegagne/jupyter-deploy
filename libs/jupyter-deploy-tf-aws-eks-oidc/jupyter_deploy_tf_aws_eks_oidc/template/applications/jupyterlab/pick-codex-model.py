"""Print the model Codex recommends for an inference profile prefix, read from its own catalog.

Usage: codex debug models | python3 pick-codex-model.py <prefix>
Prints nothing when the catalog has no model for the prefix.
"""

import json
import sys

prefix = f"{sys.argv[1]}."
models = json.load(sys.stdin)["models"]
ranked = sorted((m for m in models if m["slug"].startswith(prefix)), key=lambda m: m.get("priority", 0))
if ranked:
    print(ranked[0]["slug"])
