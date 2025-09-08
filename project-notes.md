# 📘 Project Notes: Zotero → WordPress Bibliography Worker

This file documents the intent, architecture, and implementation strategy for the Zotero PDF Worker.  
It is written primarily for future maintainers and coding assistants (e.g. LLMs inside Cursor) to quickly  
understand the project structure and goals.

---

## 1. Purpose

- Generate per-author bibliography PDFs from a Zotero group library collection.  
- Output PDFs directly into a WordPress multisite uploads directory, bypassing WP’s date-based folders.  
- Provide:  
  - Permalink PDFs → one stable file per author, always current.  
  - History PDFs → optional timestamped versions for archival.

---

## 2. Architecture

- Runs as a standalone Docker container alongside WordPress.  
- Shares the wp-content/uploads volume with WordPress.  
- Driven by two configs:  
  - .env → environment/deployment settings (paths, site ID).  
  - config.json → domain logic (authors, identifiers, citation style).  
- Outputs static files only (no WP DB integration).

---

## 3. Features

- Zotero integration:  
  - Fetches all items from one group collection in a single request.  
  - Uses Zotero API with include=bib to get CSL-formatted citations.  
  - Citation style configurable (chicago-author-date by default).

- Author filtering:  
  - Each author has a slug and a set of identifiers.  
  - Zotero creators with creatorType=author matched against identifiers.  
  - Items may appear in multiple bibliographies (for co-authors).

- Rendering:  
  - Jinja2 templates produce bibliography HTML.  
  - WeasyPrint converts HTML+CSS → DIN A4 PDFs.  
  - Montserrat font installed system-wide (/usr/share/fonts/truetype/montserrat/).  
  - Text selectable and copyable.

- Output structure:  
  - Deterministic paths:  
    {WP_UPLOADS_PATH}/sites/{SITE_ID}/{BIB_ROOT}/{permalink|history}/{author_slug}/...  
  - Permalink folder contains one stable {slug}.pdf  
  - History folder contains optional timestamped versions.

---

## 4. File Structure

Root of the repo contains:

- Dockerfile (Python + WeasyPrint + fonts)  
- compose.yaml (local dev compose config)  
- .env (deployment config: paths, site ID, dirs)  
- config.json (domain config: authors, citation style, options)  
- requirements.txt (Python dependencies)  
- src/ (Python source code)  
  - main.py (orchestration entrypoint)  
  - zotero_client.py  
  - authors.py  
  - renderer.py  
  - paths.py  
  - logging_util.py  
- output/ (local dev mount simulating wp-content/uploads)

---

## 5. Path Resolution

At runtime, paths are built from env + config:

BASE = {WP_UPLOADS_PATH}/sites/{SITE_ID}/{BIB_ROOT}  
PERMALINK_PATH = BASE/{PERMALINK_DIR}/{author.slug}/{filename_template}  
HISTORY_PATH   = BASE/{HISTORY_DIR}/{author.slug}/{history_filename_template}  

Example in dev:  

/app/output/sites/30/bibliographies/permalink/anna-mueller/anna-mueller.pdf  
/app/output/sites/30/bibliographies/history/anna-mueller/anna-mueller-20250908-143012.pdf  

Example in production URL:  

/wp-content/uploads/sites/30/bibliographies/permalink/anna-mueller/anna-mueller.pdf

---

## 6. Implementation Strategy

- Docker  
  - Base: python:3.12-slim  
  - Install WeasyPrint system deps (libcairo2, libpango-1.0-0).  
  - Install Montserrat font in /usr/share/fonts/truetype/montserrat/.  
  - Refresh font cache (fc-cache).  
  - Copy configs + source into /app.

- Python app  
  - zotero_client.py → fetch API items.  
  - authors.py → match items per author.  
  - renderer.py → Jinja2 → HTML → WeasyPrint PDF.  
  - paths.py → resolve absolute output paths.  
  - main.py → tie everything together.

- Dev workflow  
  - Mount ./output → /app/output to simulate uploads.  
  - Run via docker compose up --build.  
  - Inspect PDFs in ./output.

- Prod workflow  
  - Mount the real WP uploads volume into /app/output.  
  - Container writes to stable and history directories.  
  - WordPress serves the files directly.

---

## 7. Design Principles

- Separation of concerns  
  - .env → deployment specifics (paths, IDs).  
  - config.json → application logic (authors, styles).  

- Deterministic outputs  
  - Stable permalinks always available.  
  - Optional history for archival.  

- Minimalism  
  - Single Zotero request (no pagination).  
  - No cache/CDN logic initially.  
  - No WP plugin or DB involvement.  

- Future-proof  
  - Identifiers allow multiple name variants.  
  - CSL style configurable.  
  - History archiving optional.

---

## 8. Deliverables

- Dockerized worker image.  
- .env and config.json templates.  
- Jinja2 template + CSS for styling.  
- Python source modules.  
- Documentation (this file).

---

✅ Summary:  
The Zotero PDF Worker is a containerized Python app that fetches a group library, splits works per author, generates styled bibliography PDFs, and writes them into predictable WordPress uploads subdirectories for serving as static files.  
Environment config defines where to write; domain config defines what to generate.  
Outputs are permalinks and optional histories, using system-installed fonts and DIN A4 PDFs.
