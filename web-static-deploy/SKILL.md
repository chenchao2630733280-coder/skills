---
name: "web-static-deploy"
description: "Deploy web frontends (static HTML/JS, Vite/React/Vue builds) to production. Use when a user asks how to publish, deploy, or host a web app or game, or wants to choose among GitHub Pages, Vercel, Netlify, CloudBase or COS, CloudStudio. This skill decides whether the app is PURE STATIC (no backend, browser localStorage only) or NEEDS A DATABASE (CloudBase document DB plus auth plus cloud functions), then executes the matching deploy path and covers the silent-404 failure modes (private repo, Pages source not set to GitHub Actions, TXT domain verification, CNAME persistence)."
agent_created: true
---

# Web Static Deploy

## Overview

Deploy a web frontend to a reachable URL. The skill first classifies the app as
**PURE STATIC** or **NEEDS A DATABASE**, then routes to the correct provider and
executes the deploy, including the config steps that silently break (causing 404s).

Key principle: a "static site" with no backend means **no database** — player state
lives in browser `localStorage` and is per-device, per-browser, erasable. If the user
needs cross-device saves, accounts, leaderboards, or anti-cheat, that requires a real
backend (CloudBase document DB + auth + cloud functions), which is a different deploy class.

## Step 0 — Classify the deployment

Ask or infer before choosing a provider. Use this decision:

| Signal | Classification |
|--------|----------------|
| No server code, no DB calls, state in `localStorage`/`IndexedDB` only | **PURE STATIC** |
| Has API routes, DB reads/writes, auth, cloud functions | **NEEDS A DATABASE** |
| User says "just publish the demo / game / landing page" | **PURE STATIC** |
| User says "need accounts / cloud save / ranking / anti-cheat" | **NEEDS A DATABASE** |

When unclear, ask one question: *"这是纯静态前端（数据只存浏览器），还是需要一个云端数据库 / 账号系统？"*
Do NOT assume a DB exists — most Vite/React demos are pure static.

If **NEEDS A DATABASE** and the user has no backend yet, route to the "With Database" section
(CloudBase). If pure static, route to the provider list below.

## Step 1 — Build the artifact first

Always produce `dist/` (or `build/`) before deploying. Confirm:

- `vite.config.ts` / build config uses `base: './'` (relative paths) so the bundle works
  under any subpath or when opened from a subdomain. This prevents broken asset paths.
- Run `npm run build` (or framework equivalent) and verify `dist/index.html` exists.
- For GitHub Pages specifically: write `dist/.nojekyll` (so Jekyll doesn't drop `_`-prefixed
  files) and, if a custom domain is used, also write `dist/CNAME` containing the domain, so
  re-deploys don't wipe the custom-domain setting. See `references/github-pages.md`.
- Exclude `node_modules/` and `dist/` from git via `.gitignore` (unless pushing `dist` to a
  `gh-pages` branch, which this skill avoids by using CI builds).

A reference postbuild hook that emits both files is in `references/postbuild-snippet.md`.

## Step 2 — Choose a provider (pure static)

Pick based on the user's constraints, then follow the matching reference:

- **GitHub Pages** — free, tied to a public repo, auto-deploy via Actions.
  Read `references/github-pages.md`. ⚠️ Requires the repo to be **public** and Pages
  **Source = "GitHub Actions"**; the single most common silent-404 cause is leaving Source
  on "Deploy from a branch" while using an Actions workflow (deploy job fails, site 404s).
- **Vercel / Netlify** — free, zero-config CI, supports private repos, gives `*.vercel.app`
  / `*.netlify.app` domain, can bind custom domains. Best when repo must stay private.
- **CloudBase / COS (Tencent)** — `xxx.tcloudbase.com` or `*.cos-website.*.myqcloud.com`,
  domestic China access, no ICP filing needed for the default domain. Needs the user's own
  Tencent Cloud account + SecretId/SecretKey (or manual console upload). Read `references/cloudbase.md`.
- **CloudStudio sandbox** — zero-config, **run by the agent now** via the
  `workbuddy_cloudstudio_deploy` tool. Gives a temporary shareable link in seconds, good for
  instant verification. Not a permanent host. Use when the user wants a link immediately or to
  validate the build before committing to a permanent provider.

Recommendation order for a typical user:
1. Want a permanent free URL + auto-update on push, repo can be public → **GitHub Pages**.
2. Repo must stay private, or want the smoothest DX → **Vercel/Netlify**.
3. Domestic China players, no ICP filing → **CloudBase/COS**.
4. Just need a link right now to check it works → **CloudStudio** (agent runs it).

## Step 3 — Execute the chosen provider

Follow the matching reference file for exact commands/config. General rules:

- **Do not commit `dist/`** when using CI-based providers (GitHub Pages Actions, Vercel, Netlify,
  CloudBase CLI) — let the pipeline build. Only commit source + workflow/config files.
- **Credential handling:** when a push/CLI needs auth and the shell has no cached credential
  (common: HTTPS GitHub 401, no `gh`/SSH), ask the user for a scoped token (GitHub PAT with
  `repo`; Tencent SecretId/SecretKey with the relevant service permission). Embed the token only
  for the single push/command, then immediately reset the remote/config back to the credential-free
  form so the secret is never left in `.git/config` or any committed file. Prefer letting the user
  run the auth step locally if they don't want to share the token.
- **Custom domain (verified domain):** if the user wants their own domain (e.g. `fish.example.com`):
  1. Add a **TXT** record at `_github-pages-challenge-<user>.<domain>` (GitHub) or the provider's
     challenge — NOT a CNAME — to prove ownership. The TXT record value is the code GitHub shows.
  2. After "Verified", add the actual routing record: **CNAME** for a subdomain
     (`fish` → `<user>.github.io` / `<env>.tcloudbase.com`), or **A records** (4 GitHub IPs
     `185.199.108/109/110/111.153`) for a root/apex domain.
  3. Persist the domain via `dist/CNAME` (GitHub Pages) or the provider's console so re-deploys
     keep it.
  4. Enable **Enforce HTTPS** once the cert provisions (usually minutes).
  A TXT-vs-CNAME confusion is the #2 cause of "we couldn't verify ownership" errors.

## Step 4 — Verify the deploy (do not trust "I configured it")

After deploy, actually check the live URL instead of assuming success:

- For GitHub Pages: query the GitHub API (no auth needed for public repos) to confirm:
  - repo `visibility` is `public` and `has_pages` is `true`;
  - the latest Actions run's **deploy** job `conclusion` is `success` (build success alone is
    NOT enough — the separate deploy job frequently fails while build passes);
  - `curl -o /dev/null -w "%{http_code}"` against both `https://<user>.github.io/<repo>/` and the
    custom domain. A 301 from the github.io URL to the custom domain + 404 on the custom domain
    means "deployed but custom domain not resolving / not yet propagated".
- For CloudStudio: confirm the returned `shareLink` is reachable.
- Tell the user the measured HTTP status, not just "done".

## With Database (CloudBase, Tencent)

When classified as NEEDS A DATABASE:

1. User creates a CloudBase environment (static hosting + document DB + auth) in Tencent Cloud.
2. Obtain a scoped SecretId/SecretKey (or `tcb login`).
3. Deploy static files: `tcb hosting deploy dist -e <envId>`.
4. Add a backend layer:
   - **Auth:** use CloudBase anonymous/wechat login to get a per-player UID.
   - **DB:** replace `localStorage` saves with read/write to a CloudBase document
     (local cache + cloud sync, merge on conflict).
   - **Anti-cheat / economy:** move gacha, shop, month-card validation into **cloud functions**
     so the client can't forge state.
   - **Leaderboard/social:** possible once a central DB exists.
5. This is an architecture change, not a config flip — scope it explicitly with the user before
   building (estimate login + sync + cloud-function work).

This skill does NOT auto-build the backend; it sets up hosting + documents the DB integration
boundary. Flag the backend work as a separate implementation task.

## Resources

- `references/github-pages.md` — exact workflow YAML, the Source="GitHub Actions" gotcha, TXT/CNAME
  domain steps, and the API verification commands.
- `references/cloudbase.md` — CloudBase/COS setup, `tcb` CLI deploy, SecretId/SecretKey scoping.
- `references/postbuild-snippet.md` — `postbuild.mjs` snippet that emits `dist/.nojekyll` and
  `dist/CNAME` for GitHub Pages.
- `assets/` — (none; no binary templates needed for this skill).
