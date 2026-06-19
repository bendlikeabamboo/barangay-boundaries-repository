# Quarto deployment & cutover runbook

This Quarto site (`quarto-docs/`) is **configured but not yet live**. The MkDocs Material site under
`docs/` + `mkdocs.yml` + `.github/workflows/pages.yml` is still the production documentation. The two
cannot deploy at the same time because they use **mutually exclusive GitHub Pages source modes**:

| Pipeline               | Pages source mode               | Workflow                         |
|------------------------|---------------------------------|----------------------------------|
| **MkDocs** (live)      | GitHub Actions artifact upload  | `.github/workflows/pages.yml`    |
| **Quarto** (this site) | `gh-pages` branch (push)        | `.github/workflows/quarto-pages.yml` |

GitHub Pages has one repo-wide source setting; only one of these modes can be active at a time.

## Current state

- `quarto-docs/` renders cleanly: `quarto render quarto-docs/` → `quarto-docs/_site/`.
- `.github/workflows/quarto-pages.yml` exists but is **`workflow_dispatch` only** — it does **not**
  run on push to `main`. Triggering it manually before the cutover would push a `gh-pages` branch
  that GitHub Pages would ignore (its source still points at the Actions artifact).

- `docs/`, `mkdocs.yml`, `pages.yml` are **untouched**.

## Local preview

```bash
quarto preview quarto-docs/
```

Opens a local server (default <http://localhost:4599>). Check the light/dark toggle, the per-section
sidebars (Data, References, root), the JSON-LD block on the landing page, the `::: {.panel-tabset}`
download tabs on every data page, and the Mermaid pipeline diagrams on the architecture page.

## Cutover procedure (run when ready to go live)

The cutover swaps Pages from the MkDocs Actions artifact to the Quarto `gh-pages` branch.

1. **Confirm the latest Quarto build is green locally:**
   ```bash
   quarto render quarto-docs/
   ```

2. **Switch the repo's GitHub Pages source.**
   In *Settings → Pages → Build and deployment → Source*, change **GitHub Actions** → **Deploy from
   a branch**, then select the `gh-pages` branch and `/ (root)` folder.

3. **Disable the MkDocs workflow.**
   In *Actions → Pages (workflow)* → `⋮` → **Disable workflow**. Also consider removing
   `.github/workflows/pages.yml` in the retirement step below.

4. **Trigger the Quarto deployment.**
   - In *Actions → Quarto Pages* → **Run workflow** (manual dispatch), or
   - Uncomment the `push:` block in `.github/workflows/quarto-pages.yml` and commit, so future
     `quarto-docs/**` changes auto-deploy.

5. **Verify.** Once the workflow succeeds, open the published Pages URL and check:
   - Landing page renders with JSON-LD (`view-source:` for `application/ld+json`).
   - `/llms.txt` and `/robots.txt` are served at the site root.
   - Navbar and per-section sidebars navigate correctly.
   - Mermaid diagrams on `/references/architecture.html` render.

6. **(Optional) Redirect considerations.** The old MkDocs URL scheme and the new Quarto URL scheme
   match at the section level (`/data/...`, `/psgc/`, `/huc-mapping/`, `/citation/`, `/changelog/`)
   *except*:
   - `/psgc/` → `/references/psgc/`
   - `/huc-mapping/` → `/references/huc-mapping/`
   - `/citation/` → `/references/citation/`
   - The architecture page is new (`/references/architecture/`).

   If inbound links exist to the old `/psgc/` etc. paths, add a redirect rule or restructure the
   `references/` directory. (The `llms.txt` shipped in `docs/` still points to the mkdocs paths and
   will need updating as part of retirement — see the follow-ups.)

## Retirement of mkdocs (final cleanup, separate step)

Only after the Quarto site is live and verified:

1. Delete `docs/` and `mkdocs.yml`.
2. Delete `.github/workflows/pages.yml`.
3. Remove `docs/requirements.txt` (if only used by mkdocs).
4. Update root `README.md` doc links — they currently point to mkdocs paths
   (`https://bendlikeabamboo.github.io/barangay-boundaries-repository/psgc/` etc.).

5. Update `llms.txt` (now at `quarto-docs/llms.txt`) to point to the new `/references/...` paths.
6. Consider keeping `pages.yml` disabled but present until at least one full release cycle has
   passed, as a rollback path.

## Rollback (Quarto → back to MkDocs)

1. Re-enable `.github/workflows/pages.yml` in *Actions*.
2. Switch Pages source back to **GitHub Actions**.
3. Disable `.github/workflows/quarto-pages.yml` (and re-comment the `push:` trigger if it was
   enabled).

4. Optionally delete the `gh-pages` branch.
