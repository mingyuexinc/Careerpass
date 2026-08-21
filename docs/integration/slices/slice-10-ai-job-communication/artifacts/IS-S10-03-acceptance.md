# IS-S10-03 Acceptance Artifact

## Expected Manifest

```json
{
  "scenario_id": "IS-S10-03",
  "contract": "IC-S10-AI-COMMUNICATION@0.5",
  "required": [
    "unique_query",
    "silent_without_condition",
    "waiting_without_answer",
    "pending_after_parse_failure",
    "later_binary_answer_completes_original_query",
    "continue_reply",
    "stop_reply",
    "duplicate_trigger_deduplicated",
    "application_match_status_unchanged",
    "ownership_isolation"
  ],
  "actual": "artifacts/IS-S10-03-acceptance/actual.json"
}
```

真实证据输出位置由 Scenario 约定；本次开发者重启后端并完成前端场景复测，实际结果见 [`IS-S10-03-acceptance/report.md`](IS-S10-03-acceptance/report.md) 和 [`IS-S10-03-acceptance/actual.json`](IS-S10-03-acceptance/actual.json)。
