# Publishing the NHANES Assistant plugin

This plugin can be distributed two ways. Route 1 (your own marketplace) is live the
moment you push `.claude-plugin/marketplace.json`. Route 2 (official directory) is a
review-gated submission.

---

## Route 1 — Self-hosted marketplace (in your control)

`.claude-plugin/marketplace.json` is committed at the repo root. Once pushed, anyone runs:

```bash
claude plugin marketplace add douglasm-2025/nhanes-assistant-plugin
claude plugin install nhanes-assistant@nhanes-marketplace
cd ~/.claude/plugins/cache/nhanes-marketplace/nhanes-assistant/*/ && bash setup.sh
```

The marketplace entry uses `"source": "./"` — the plugin lives in the same repo as the
marketplace, so there is no second clone (and no SSH host-key issue for installers).

### Optional: pin for reproducibility
The entry currently tracks the default branch. To pin installers to a fixed release,
tag the release and reference it, or swap the source to a pinned commit:

```jsonc
"source": {
  "source": "url",
  "url": "https://github.com/douglasm-2025/nhanes-assistant-plugin.git",
  "commit": "<RELEASE_SHA>",
  "sha": "<RELEASE_SHA>"
}
```

`claude plugin tag` creates a `nhanes-assistant--v2.0.0` git tag and checks that
`plugin.json` and the marketplace entry agree — useful before announcing a version.

---

## Route 2 — Official Anthropic plugin directory (review-gated)

The official marketplace (`anthropics/claude-plugins-official`) does **not** accept
third-party pull requests. External plugins are submitted via a form and reviewed
against quality and security standards:

**Submission form:** https://clau.de/plugin-directory-submission

### Info to have ready for the form
- **Plugin name:** nhanes-assistant
- **Version:** 2.0.0
- **Repository:** https://github.com/douglasm-2025/nhanes-assistant-plugin
- **Description:** Expert NHANES research engine: statistical analysis and
  manuscript-ready output for peer-reviewed nutrition epidemiology.
- **Category:** data / science (research tooling)
- **Author / owner:** douglasm-2025
- **License:** present in repo (`LICENSE`)
- **Marketplace manifest:** `.claude-plugin/marketplace.json` at repo root

### Likely review friction to pre-empt
This is **not** a self-contained plugin, which directory reviewers tend to scrutinize:
1. **Heavy external toolchain.** Requires a working R installation plus ~17 R packages
   and a Python venv, built by `setup.sh` (5–10 min). The MCP server cannot start until
   setup runs. Make this unmistakable in the README (done) and in the form notes.
2. **Network at runtime.** Downloads NHANES tables from CDC/NCHS via `nhanesA` on demand.
3. **Local code execution.** The server executes R scripts the agent writes — disclose
   this plainly; it is the core design, but reviewers will want it stated.
4. **Platform setup.** macOS needs Homebrew font libraries; document Linux/Windows R setup.

If the directory requires a one-step install, this plugin may not qualify as-is without a
bundled/containerized runtime. Route 1 works regardless and needs no approval.
