# Marvel Powers — Power Grid Explorer

A static, responsive website for browsing the `sanand0/marvel-powers` dataset.

## Features
- Search and browse character profiles
- Six attribute ratings with minimum/maximum ranges preserved
- Head-to-head character comparison
- Rankings by maximum total or individual attribute
- Links to each source character page
- Mobile-friendly dark interface with red accents

## Data
The site fetches `marvel-powers-summary.json` from the upstream repository when it loads:
https://raw.githubusercontent.com/sanand0/marvel-powers/master/marvel-powers-summary.json

Dataset last updated by the source project on February 27, 2023. Ratings may be incomplete or outdated. This is an independent fan-made explorer, not affiliated with Marvel.

## Run locally
Because the app fetches data from a remote JSON file, serve the folder over HTTP rather than opening `index.html` as a `file://` URL. For example, with Python installed:

```bash
python -m http.server 8000
```

Then open http://localhost:8000.

## Publish with GitHub Pages
1. Create a new public repository, e.g. `marvel-powers-explorer`.
2. Upload `index.html` and `README.md` to the repository root.
3. In repository Settings → Pages, set the source to deploy from the `main` branch and `/ (root)`.
4. Save. GitHub will provide the published URL after the deployment finishes.

This is a static site; no server or build step is required.
