# BOOT.md

On startup:
1) Verify API reachability (GET {{BASE_URL}}/api/v1/gateway/status).
2) If you send a boot message, end with NO_REPLY.
3) If BOOTSTRAP.md exists in this workspace, the agent should run it once and delete it.
