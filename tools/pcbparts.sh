#!/bin/sh
# Call a pcbparts.dev MCP tool: pcbparts.sh <tool> '<json args>'
curl -s -m 60 https://pcbparts.dev/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$1\",\"arguments\":$2}}" \
  | sed -n 's/^data: //p' | python3 -I -c 'import json,sys; r=json.load(sys.stdin); print("\n".join(c.get("text","") for c in r.get("result",{}).get("content",[])) or r)'
