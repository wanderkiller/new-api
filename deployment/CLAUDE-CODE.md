# Claude Code through New API

Use your New API server URL and New API API key. For this configuration, use
the server root URL without `/v1` or `/v1/anthropic` appended.

```sh
export ANTHROPIC_BASE_URL="https://YOUR-NEW-API-HOST"
export ANTHROPIC_AUTH_TOKEN="YOUR-NEW-API-KEY"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_DEFAULT_SONNET_MODEL="claude-sonnet"
export ANTHROPIC_DEFAULT_OPUS_MODEL="claude-opus"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="claude-sonnet"
claude --model claude-sonnet
```

Switch to Opus with `claude --model claude-opus` or `/model claude-opus`.
The Haiku tier is mapped to Sonnet here because no Haiku model was added;
background tasks therefore use Sonnet and incur Sonnet's price.
If previously signed into Anthropic, `/logout` and relaunch; confirm the
configured URL and model with `/status`. Model-restricted New API keys must
allow both aliases. Claude Code does not automatically load `.env` files.

New API forwards the Messages protocol to Merge's native Anthropic endpoint
with the full mapped model ID. Channels 1 and 5 are enabled; channel 7 awaits
Anthropic access. Four production Claude Code coding workflows passed.
