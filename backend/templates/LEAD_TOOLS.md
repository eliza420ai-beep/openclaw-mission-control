# TOOLS.md

- `BASE_URL={{ base_url }}`
- `AUTH_TOKEN={{ auth_token }}`
- `AGENT_NAME={{ agent_name }}`
- `AGENT_ID={{ agent_id }}`
- `BOARD_ID={{ board_id }}`
- `WORKSPACE_ROOT={{ workspace_root }}`
- `WORKSPACE_PATH={{ workspace_path }}`
- Required tools: `curl`, `jq`

## OpenAPI refresh (run before API-heavy work)

```bash
mkdir -p api
curl -fsS "{{ base_url }}/openapi.json" -o api/openapi.json
jq -r '
  .paths | to_entries[] as $p
  | $p.value | to_entries[]
  | select((.value.tags // []) | index("agent-lead"))
  | "\(.key|ascii_upcase)\t\($p.key)\t\(.value.operationId // "-")"
' api/openapi.json | sort > api/lead-operations.tsv
```

## API source of truth
- `api/openapi.json`
- `api/lead-operations.tsv`

## API discovery policy
- Use only operations tagged `agent-lead`.
- Derive method/path/schema from `api/openapi.json` at runtime.
- Do not hardcode endpoint paths in markdown files.

## API safety
If no confident match exists for current intent, ask one clarifying question.
