# BOOTSTRAP.md

You just woke up. Time to figure out who you are.
There is no memory yet. This is a fresh workspace, so it’s normal that memory files don’t exist until you create them.

## Bootstrap steps (run in order)
1) Ensure required tools are installed:

```bash
for tool in curl jq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required tool: $tool" >&2
    echo "Install examples:" >&2
    echo "  Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y curl jq" >&2
    echo "  RHEL/CentOS:   sudo dnf install -y curl jq" >&2
    echo "  macOS (brew):  brew install curl jq" >&2
    exit 1
  fi
done
```

2) Verify API reachability:

```bash
curl -fsS "{{ base_url }}/healthz" >/dev/null
```

3) Ensure required files exist:
- `AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `MEMORY.md`, `HEARTBEAT.md`, `BOOTSTRAP.md`

4) Create `memory/` if missing.

5) Ensure today's daily file exists: `memory/YYYY-MM-DD.md`.

6) Initialize current delivery status in `MEMORY.md`:
- set objective if missing
- set state to `Working` (or `Waiting` if external dependency exists)
- set one concrete next step

7) Add one line to `MEMORY.md` noting bootstrap completion date.

8) Delete this file.
