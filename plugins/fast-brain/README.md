# fast-brain Hermes plugin

Install this directory into each Hermes profile:

```bash
mkdir -p ~/.hermes/plugins
cp -R plugins/fast-brain ~/.hermes/plugins/fast-brain
```

Configure the profile `.env`:

```env
FAST_BRAIN_URL=http://192.168.31.144:4668
FAST_BRAIN_API_KEY=change-me
FAST_BRAIN_AGENT_ID=hermes
FAST_BRAIN_DEVICE_ID=macbook
```

Enable the provider:

```bash
hermes config set memory.provider fast-brain
```

For multiple Hermes instances, reuse `FAST_BRAIN_AGENT_ID=hermes` to share memory. Use different `FAST_BRAIN_DEVICE_ID` values to identify each instance.
