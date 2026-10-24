# altmedbase-website

Deployment repo for the Natural Remedies Directory (altmedbase.com).

## How the site is published

This repo's `website/dist/` directory is served by GitHub Pages. Pushing to
`main` triggers `.github/workflows/deploy-website.yml`, which publishes the
contents of `website/dist/` to **https://altmedbase.com/**.

## How to update the live site

The source code lives in a **separate** repo: `systemnotes/altmedbase`
(`/home/scottm/projects/altmedbase`). To go live:

1. Edit source in the `altmedbase` repo (JSON data, Jinja2 templates, or the
   site generator).
2. Build the site:
   ```bash
   cd /home/scottm/projects/altmedbase
   python3 website/scripts/generate_site.py
   ```
   (Requires `jinja2` — `pip install jinja2`.)
3. Copy the generated output into this repo:
   ```bash
   cp -r /home/scottm/projects/altmedbase/website/dist/* website/dist/
   ```
4. Commit and push:
   ```bash
   git add website/dist/
   git commit -m "describe your changes"
   git push origin main
   ```

## Custom domain

`altmedbase.com` is configured via the `CNAME` file in `website/dist/`
(auto-written by the generator on every build) and in GitHub Settings → Pages.

## Release tags

Tag known-good baselines in the **source** repo (`systemnotes/altmedbase`),
e.g. `git tag -a v1.0.0 -m "Stable baseline"`.