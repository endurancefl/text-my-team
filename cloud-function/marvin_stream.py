"""marvin_stream.py — SSE streaming server for MARVIN AI chat.

Runs as a standalone HTTP server inside the Lambda container via Lambda Web Adapter.
Streams Anthropic API responses as Server-Sent Events (SSE) to the frontend.
"""
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

import anthropic

# Import shared logic from the existing Lambda module
from lambda_function import (
    _build_chat_system_prompt,
    _execute_tools_parallel,
    _MARVIN_CUSTOM_TOOLS,
    _parse_chat_response,
    allowed_origin_from_header,
    cors_headers,
)


class MarvinStreamHandler(BaseHTTPRequestHandler):
    """Handle POST requests with SSE streaming responses."""

    # Suppress default stderr logging for each request
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        allowed = allowed_origin_from_header(origin)
        self.send_response(204)
        for k, v in cors_headers(allowed).items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        allowed = allowed_origin_from_header(origin)
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len))

        # SSE response headers
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        for k, v in cors_headers(allowed).items():
            self.send_header(k, v)
        self.end_headers()

        try:
            self._stream_marvin(body)
        except Exception as e:
            self._write_sse("error", {"error": str(e)})

    def _stream_marvin(self, data):
        prompt = data.get("prompt", "").strip()
        history = data.get("history", [])
        context = data.get("context", {})
        files = data.get("files", [])

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            self._write_sse("error", {"error": "ANTHROPIC_API_KEY not configured"})
            return

        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = _build_chat_system_prompt(context)
        messages = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # Build user content (text + optional file attachments)
        user_content = self._build_user_content(prompt, files)
        messages.append({"role": "user", "content": user_content})

        # API kwargs — web_search + custom tools + thinking + cache
        api_kwargs = {
            "model": "claude-opus-4-5-20251101",
            "max_tokens": 8192,
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": messages,
            "thinking": {"type": "enabled", "budget_tokens": 4096},
            "tools": [
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
                    "user_location": {
                        "type": "approximate",
                        "city": "Orlando",
                        "region": "Florida",
                        "country": "US",
                    },
                }
            ]
            + _MARVIN_CUSTOM_TOOLS,
        }

        full_text = ""
        tool_use_count = 0
        total_iterations = 0

        while total_iterations < 5:
            total_iterations += 1

            with client.messages.stream(**api_kwargs) as stream:
                for event in stream:
                    # Handle text deltas — stream to client in real-time
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            full_text += event.delta.text
                            self._write_sse("text", {"delta": event.delta.text})
                        elif hasattr(event.delta, "thinking"):
                            self._write_sse("thinking", {"status": "reasoning"})

                # Get the final assembled message
                final_message = stream.get_final_message()

            # Check stop reason
            if final_message.stop_reason == "end_turn":
                break

            if final_message.stop_reason == "pause_turn":
                # Web search continuation
                messages.append(
                    {"role": "assistant", "content": final_message.content}
                )
                messages.append({"role": "user", "content": "Continue."})
                api_kwargs["messages"] = messages
                continue

            if final_message.stop_reason == "tool_use":
                if tool_use_count >= 5:
                    break
                tool_use_count += 1

                tool_use_blocks = [
                    b for b in final_message.content if b.type == "tool_use"
                ]
                self._write_sse(
                    "tool_start",
                    {
                        "tools": [
                            {"name": tu.name, "id": tu.id} for tu in tool_use_blocks
                        ]
                    },
                )

                results = _execute_tools_parallel(tool_use_blocks)

                tool_results = []
                for tu in tool_use_blocks:
                    result_data = results.get(tu.id, {"error": "No result"})
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tu.id,
                            "content": json.dumps(result_data, default=str),
                        }
                    )

                self._write_sse(
                    "tool_result", {"tools": [tu.name for tu in tool_use_blocks]}
                )

                messages.append(
                    {"role": "assistant", "content": final_message.content}
                )
                messages.append({"role": "user", "content": tool_results})
                api_kwargs["messages"] = messages
                continue

            break  # Unknown stop_reason

        # Parse full text for action JSON
        parsed = _parse_chat_response(full_text)
        action = parsed.get("action", None)
        message = parsed.get("message", full_text)

        self._write_sse("done", {"message": message, "action": action})

    def _build_user_content(self, prompt, files):
        """Build user content blocks. Supports text + file attachments."""
        if not files:
            return prompt
        blocks = [{"type": "text", "text": prompt}]
        for f in files:
            if f.get("type") == "image" and f.get("data"):
                blocks.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": f.get("media_type", "image/jpeg"),
                            "data": f["data"],
                        },
                    }
                )
            elif f.get("type") == "text" and f.get("content"):
                blocks.append({"type": "text", "text": f["content"]})
        return blocks

    def _write_sse(self, event_type, data):
        """Write a single SSE event to the response stream."""
        line = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        self.wfile.write(line.encode("utf-8"))
        self.wfile.flush()


PORT = int(os.environ.get("PORT", 8080))

if __name__ == "__main__":
    server = HTTPServer(("", PORT), MarvinStreamHandler)
    print(f"MARVIN streaming server listening on port {PORT}")
    server.serve_forever()
