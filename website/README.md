# Simple Static Site Generator (MVP)

This is a minimal, Python‑only static‑site generator for the **Natural Remedies Directory**.

## How it works
1. **Data** – JSON files are stored in `data/` (e.g. `remedies.json`, `ailments.json`, `protocols.json`).
2. **Templates** – Jinja2‑style HTML templates live in `templates/`.
3. **Generator** – `scripts/generate_site.py` reads the JSON files, renders the templates, and writes the output to `dist/`.
4. **Search** – A tiny client‑side Lunr.js index (`dist/search_index.json`) is generated from every record’s `title` and `content` fields.
5. **Menu** – The generator builds a navigation menu based on the top‑level collections (Remedies, Ailments, First‑Aid, Protocols, About).

## Running the generator
```bash
cd /home/scottm/projects/altmedbase/website
python3 scripts/generate_site.py
```
The static site will be generated in `dist/` and can be served with any static file server, e.g.:
```bash
python3 -m http.server 8000 --directory dist
```

## Extending
- Add new JSON files under `data/` and reference them in `site_config.json`.
- Create new templates in `templates/` and add a mapping in the generator.
- For a full‑featured site you can later swap this for a framework like Gatsby or Hugo – the folder layout is already compatible.
