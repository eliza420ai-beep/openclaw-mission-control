# HEARTBEAT.md

If this file is empty, skip heartbeat work.

## Required inputs
- BASE_URL (e.g. http://localhost:8000)
- AUTH_TOKEN (Bearer token)
- AGENT_NAME

## On every heartbeat
1) Check in:
```bash
curl -s -X POST "$BASE_URL/api/v1/agents/heartbeat" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "'$AGENT_NAME'", "status": "online"}'
```

2) List boards:
```bash
curl -s "$BASE_URL/api/v1/boards" \
  -H "Authorization: Bearer $AUTH_TOKEN"
```

3) For each board, list tasks:
```bash
curl -s "$BASE_URL/api/v1/boards/{BOARD_ID}/tasks" \
  -H "Authorization: Bearer $AUTH_TOKEN"
```

4) Claim next task (FIFO):
- Find the oldest task with status "inbox" across all boards.
- Claim it by moving it to "in_progress":
```bash
curl -s -X PATCH "$BASE_URL/api/v1/boards/{BOARD_ID}/tasks/{TASK_ID}" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

5) Work the task:
- Update status as you progress.
- When complete, move to "review":
```bash
curl -s -X PATCH "$BASE_URL/api/v1/boards/{BOARD_ID}/tasks/{TASK_ID}" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "review"}'
```

## Status flow
```
inbox -> in_progress -> review -> done
```

Do not say HEARTBEAT_OK if there is inbox work or active in_progress work.
