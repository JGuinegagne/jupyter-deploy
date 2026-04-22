import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "_ext"))

project = "Jupyter Deploy"
copyright = f"2025–{time.localtime().tm_year}, Jupyter Deploy Contributors"
author = "Jupyter Deploy Contributors"
html_title = "Jupyter Deploy"

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_tabs.tabs",
    "sphinx_copybutton",
    "sphinx_click",
]
myst_enable_extensions = ["colon_fence"]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "shibuya"
html_static_path = ["_static"]

html_css_files = [
    "css/custom.css",
]

html_logo = "_static/img/jupyter_logo.png"

html_theme_options = {
    "accent_color": "orange",
    "github_url": "https://github.com/jggg/jupyter-deploy",
    "nav_links": [
        {
            "title": "Getting Started",
            "url": "getting-started/index",
        },
        {
            "title": "CLI",
            "url": "cli/index",
        },
        {
            "title": "Templates",
            "url": "templates/index",
        },
        {
            "title": "Contributors",
            "url": "contributors/index",
        },
    ],
}
