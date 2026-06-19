# Quarto deployment & cutover runbook

This Quarto site (`quarto-docs/`) is the **live documentation**, published to GitHub Pages from the
`gh-pages` branch by `.github/workflows/quarto-pages.yml`. The workflow runs on every push to `main`
that touches `quarto-docs/**` (and is also available as a manual `workflow_dispatch`).

The previous MkDocs Material site (`docs/` + `mkdocs.yml` + `.github/workflows/pages.yml`) was removed
during the cutover. The two could not deploy at the same time because they used **mutually exclusive
GitHub Pages source modes**:

| Pipeline               | Pages source mode               | Workflow                         |
|------------------------|---------------------------------|----------------------------------|
| ~~MkDocs~~ (removed)   | GitHub Actions artifact upload  | ~~`.github/workflows/pages.yml`~~ |
| **Quarto** (live)      | `gh-pages` branch (push)        | `.github/workflows/quarto-pages.yml` |

GitHub Pages has one repo-wide source setting; only one of these modes can be active at a time.

## Current state

- `quarto-docs/` renders cleanly: `quarto render quarto-docs/` → `quarto-docs/_site/`.
- `.github/workflows/quarto-pages.yml` is enabled and runs on push to `main`. It renders the site
  and force-pushes the output to the `gh-pages` branch via `peaceiris/actions-gh-pages`.
- `docs/`, `mkdocs.yml`, and `pages.yml` have been deleted from the repo.
- GitHub Pages source must point at the **`gh-pages` branch / `/ (root)`** folder (see "Required
  GitHub Pages settings" below).

## Local preview

```bash
quarto preview quarto-docs/
```

Opens a local server (default <http://localhost:4599>). Check the light/dark toggle, the per-section
sidebars (Data, References, root), the JSON-LD block on the landing page, the `::: {.panel-tabset}`
download tabs on every data page, and the Mermaid pipeline diagrams on the architecture page.

## Required GitHub Pages settings (repo owner action)

The Pages source is a repo-wide setting that cannot be changed from code. It must be set to the
`gh-pages` branch once, after which the Quarto workflow keeps it current:

1. **Settings → Pages → Build and deployment → Source** = **Deploy from a branch**.
2. **Branch** = `gh-pages`, **folder** = `/ (root)`.

If the setting is still on "GitHub Actions" (the old MkDocs mode), the `gh-pages` branch pushed by
the workflow will not be served until it is switched. The workflow does not create the branch until
its first successful run.

## Triggering a deployment

- **Automatic** — any push to `main` that changes `quarto-docs/**` or the workflow file triggers a
  rebuild and republish.
- **Manual** — *Actions → Quarto Pages → Run workflow* (uses the `workflow_dispatch` trigger).

## Verification checklist

Once the workflow succeeds and the Pages source points at `gh-pages`, open the published Pages URL
and check:

- Landing page renders with JSON-LD (`view-source:` for `application/ld+json`).
- `/llms.txt` and `/robots.txt` are served at the site root.
- Navbar and per-section sidebars navigate correctly.
- Mermaid diagrams on `/references/architecture.html` render.

## Redirect considerations (from the MkDocs site)

The old MkDocs URL scheme and the new Quarto URL scheme match at the section level except for the
references, which moved under `/references/`:

- `/psgc/` → `/references/psgc/`
- `/huc-mapping/` → `/references/huc-mapping/`
- `/citation/` → `/references/citation/`
- `/data/` → `/boundaries/`
- The architecture page is new (`/references/architecture/`).

The repo's `README.md` and `quarto-docs/llms.txt` already point to the new paths.

## Rollback (Quarto → back to MkDocs)

The MkDocs sources are recoverable from git history (the cutover commit removed `docs/`,
`mkdocs.yml`, and `.github/workflows/pages.yml`). To roll back:

1. Restore the MkDocs files from the commit before the cutover:
   ```bash
   git checkout <pre-cutover-sha> -- docs/ mkdocs.yml .github/workflows/pages.yml
   ```
2. Re-enable `.github/workflows/pages.yml` in *Actions* (it is inactive once restored until its next
   push trigger).
3. Switch the Pages source back to **GitHub Actions**.
4. Disable `.github/workflows/quarto-pages.yml` in *Actions* (or comment out the `push:` trigger).
5. Optionally delete the `gh-pages` branch.
