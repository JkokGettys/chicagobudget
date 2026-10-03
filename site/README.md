# Chicago budget explorer site

Static Astro site for the exported budget data in `public/data/`. Build the data with `python3 build/export_site.py` from the repository root, then in this directory run `npm ci`, `npm run check`, and `npm run build`. Astro's current checker needs Node 20.19+ or 22.12+; the project includes a local Node 22 dev dependency for machines with older system Node.

The build writes `dist/` only. It does not deploy. Important box pages are pre-rendered; unrendered deep links use the static `/box-shell` and Cloudflare Pages `_redirects` rewrites. Keep those rewrites if changing hosts.

Optional build-time environment variables:

- `PUBLIC_REPO_URL`: an HTTPS GitHub repository URL, such as `https://github.com/owner/repo`. When set, exported, tracked `repo_path` sources without an official URL link to `blob/main/<path>`. Do not configure an unverified repository URL.
- `PUBLIC_CF_ANALYTICS_TOKEN`: Cloudflare Web Analytics site token. The beacon script is emitted only when this is set. It is not configured for local builds.

No per-box JSON download files are created. Box pages show citations and optional repository source links instead.
