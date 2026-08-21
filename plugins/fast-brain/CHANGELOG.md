# fast-brain Hermes Plugin Changelog

## 0.2.0

- Use `/v1/context` for automatic prefetch.
- Fall back to `/v1/search` when `/v1/context` has no memories or fails.
- Add `FAST_BRAIN_CONTEXT_MAX_CHARS` for context prefetch budget.
- Capture full runtime messages when Hermes provides them.
- Avoid duplicate storage when Hermes passes cumulative message history.
- Store minimal message metadata only: `name`, `tool_name`, `tool_call_id`, `finish_reason`, `timestamp`, `turn_index`.
- Skip empty assistant messages during sync.

## 0.1.0

- Initial Hermes semantic memory provider.
- Automatic memory prefetch through `/v1/search`.
- Store completed user/assistant turns through `/v1/messages`.
- Expose tools: `fb_search_memory`, `fb_remember`, `fb_forget`.
