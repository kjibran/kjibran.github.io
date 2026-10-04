# kjibran.github.io

Source of my portfolio site: **[kjibran.github.io](https://kjibran.github.io)**

A single static page, generated with Python and published by GitHub Actions on every push.

## How it works

- `content.yaml` holds all text, links and projects. This is the only file to edit for content changes.
- `templates/index.html.j2` is the page layout, with all styling inline.
- `images/source/` holds the original images. The build resizes and compresses them.
- `build.py` renders everything into `site/`, including the sitemap, robots.txt and link preview image.

## Build locally

```bash
uv sync
uv run python build.py
uv run python -m http.server 8765 -d site   # preview at http://localhost:8765
```

Pushing to `main` builds and publishes the site automatically.
