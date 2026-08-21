# fast-brain Hermes plugin

Install this directory into each Hermes profile:

```bash
mkdir -p ~/.hermes/plugins
cp -R plugins/fast-brain ~/.hermes/plugins/fast-brain
```

Configure the profile `.env`:

```env
FAST_BRAIN_URL=https://fb-memory.osviel.duckdns.org
FAST_BRAIN_API_KEY=change-me
FAST_BRAIN_AGENT_ID=hermes
FAST_BRAIN_DEVICE_ID=macbook
FAST_BRAIN_CONTEXT_MAX_CHARS=6000
```

Enable the provider:

```bash
hermes config set memory.provider fast-brain
```

For multiple Hermes instances, reuse `FAST_BRAIN_AGENT_ID=hermes` to share memory. Use different `FAST_BRAIN_DEVICE_ID` values to identify each instance.

`prefetch` uses `/v1/context` and falls back to `/v1/search` if needed. After changing files in this plugin directory, copy the plugin update to every Hermes host/profile that uses fast-brain.

The plugin stores only small runtime metadata fields for full-message sync: `name`, `tool_name`, `tool_call_id`, `finish_reason`, `timestamp`, and `turn_index`. It intentionally skips bulky prompt/reasoning fields such as `api_content` and empty assistant messages.
