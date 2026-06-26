# Claude Code MCP Setup

Connect the NHANES Plugin v2 MCP server to Claude Code.

## Prerequisites

Run `setup.sh` from the `nhanes-assistant-plugin/` directory first:
```bash
cd /path/to/NHANES-plugin/nhanes-assistant-plugin
./setup.sh
```

## Add Server to Claude Code

Edit your Claude Code MCP settings file:
- **macOS:** `~/.claude/claude_desktop_config.json`

Add the `nhanes-assistant` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "nhanes-assistant": {
      "command": "/path/to/NHANES-plugin/nhanes-assistant-plugin/nhanes_server/venv/bin/python",
      "args": [
        "/path/to/NHANES-plugin/nhanes-assistant-plugin/nhanes_server/server.py"
      ]
    }
  }
}
```

Replace `/path/to/NHANES-plugin` with the actual absolute path on your machine.

## Install the Skill

Copy the skill file to your Claude Code skills directory:
```bash
mkdir -p ~/.claude/skills/nhanes-assistant
cp nhanes-assistant-plugin/skills/nhanes-assistant/SKILL.md ~/.claude/skills/nhanes-assistant/
```

Or add to your project's `.claude/skills/` directory for project-scoped use.

## Verify

Start Claude Code and run:
```
/nhanes-assistant does NHANES have data on snacking frequency in children?
```

Expected: Quick path announcement, then variable lookup results.

## Troubleshooting

- **Server won't start:** Check that `Rscript` is in PATH and `setup.sh` completed without errors
- **STROBE-nut empty:** Ensure `STROBE-nut_checklist.docx` is present in `nhanes-assistant-plugin/`
- **R packages missing:** Re-run `setup.sh`
