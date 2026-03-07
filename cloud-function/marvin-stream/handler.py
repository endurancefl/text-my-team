"""MARVIN AI streaming handler — HTTP server for Lambda Web Adapter.

Deployed as a zip-based Lambda with Lambda Web Adapter layer.
The adapter proxies HTTP requests to this server, enabling SSE streaming
via Function URL with InvokeMode: RESPONSE_STREAM.
Self-contained — no dependency on the PDF Lambda.
"""
import json
import os
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Defer anthropic import to first request (speeds up server startup for Web Adapter)
_anthropic = None

def _get_anthropic():
    global _anthropic
    if _anthropic is None:
        import anthropic
        _anthropic = anthropic
    return _anthropic

# ─── Knowledge Base ───────────────────────────────────────────────────────────

_MARVIN_KNOWLEDGE = ""
_knowledge_path = Path(__file__).parent / "marvin-knowledge.md"
if _knowledge_path.exists():
    _MARVIN_KNOWLEDGE = _knowledge_path.read_text(encoding="utf-8")

# ─── CORS ────────────────────────────────────────────────────────────────────

ALLOWED_ORIGINS = {
    "https://endurancefl.github.io",
    "https://enduranceservices.github.io",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}


def _cors_origin(origin):
    return origin if origin in ALLOWED_ORIGINS else ""


# ─── Backend ──────────────────────────────────────────────────────────────────

GOOGLE_SHEETS_URL = "https://script.google.com/macros/s/AKfycbygkHGZmIYUj9F91u-3eF3_V9mC7xZ03PfCJt6AD_VnpSXheLlEvt6h1obmqUf4JkRg/exec"


def _fetch_backend(params):
    query = urllib.parse.urlencode(params)
    url = f"{GOOGLE_SHEETS_URL}?{query}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": f"Backend request failed: {e}"}


# ─── Custom Tool Definitions ─────────────────────────────────────────────────

_MARVIN_CUSTOM_TOOLS = [
    {
        "name": "get_schedule",
        "description": "Fetch schedule tickets from the database. Returns tickets with property, crew, date, services, estimated hours, and status. Use when the user asks about the schedule, upcoming work, or what's planned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date filter (YYYY-MM-DD). Defaults to today if omitted."},
                "end_date": {"type": "string", "description": "End date filter (YYYY-MM-DD). Defaults to 7 days from start_date if omitted."},
                "crew": {"type": "string", "description": "Filter by crew name (e.g. 'Crew A'). Omit for all crews."},
                "contract_id": {"type": "string", "description": "Filter by contract ID. Omit for all contracts."},
            },
            "required": [],
        },
    },
    {
        "name": "get_contracts",
        "description": "Fetch all contracts from the database. Returns contract details including property, crew, dates, monthly payment, status, and signing info. Use when the user asks about contracts, active accounts, or contract details.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_invoices",
        "description": "Fetch invoices from the database. Returns invoice details including amounts, status, dates, and payment info. Use when the user asks about invoices, payments, overdue amounts, or billing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status: 'draft', 'sent', 'overdue', 'paid'. Omit for all."},
                "contract_id": {"type": "string", "description": "Filter by contract ID. Omit for all contracts."},
            },
            "required": [],
        },
    },
    {
        "name": "get_production_data",
        "description": "Fetch production analysis data comparing estimated vs actual man-hours at service and item level. Use when the user asks about crew efficiency, production rates, actual vs estimated performance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD). Required for meaningful results."},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD). Required for meaningful results."},
                "crew": {"type": "string", "description": "Filter by crew name. Use 'all' or omit for all crews."},
            },
            "required": [],
        },
    },
    {
        "name": "get_properties",
        "description": "Fetch all properties from the database. Returns property details including address, lot size, measurements, contacts, bid/contract counts, and crew assignments. Use when the user asks about properties, property details, or which properties need attention.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_contacts",
        "description": "Fetch all contacts from the CRM. Returns contact details including name, email, phone, company, stage, and notes. Use when the user asks about contacts, customers, or who manages a property.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_reminders",
        "description": "Fetch all reminders from the database. Returns reminder details including property, description, date, status, and assigned crew. Use when the user asks about reminders, upcoming tasks, or notes.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


def _execute_tool(tool_name, tool_input):
    from datetime import date, timedelta

    if tool_name == "get_schedule":
        params = {"action": "getTickets"}
        start = tool_input.get("start_date", "")
        end = tool_input.get("end_date", "")
        if not start:
            start = date.today().isoformat()
        if not end:
            end = (date.today() + timedelta(days=7)).isoformat()
        params["startDate"] = start
        params["endDate"] = end
        if tool_input.get("crew"):
            params["crew"] = tool_input["crew"]
        if tool_input.get("contract_id"):
            params["contractId"] = tool_input["contract_id"]
        result = _fetch_backend(params)
        if isinstance(result, dict) and "tickets" in result:
            result["tickets"] = result["tickets"][:100]
            result["_truncated"] = len(result["tickets"]) >= 100
        return result

    elif tool_name == "get_contracts":
        return _fetch_backend({"action": "getContracts"})

    elif tool_name == "get_invoices":
        params = {"action": "getInvoices"}
        if tool_input.get("status"):
            params["status"] = tool_input["status"]
        if tool_input.get("contract_id"):
            params["contractId"] = tool_input["contract_id"]
        result = _fetch_backend(params)
        if isinstance(result, dict) and "invoices" in result:
            result["invoices"] = result["invoices"][:200]
        return result

    elif tool_name == "get_production_data":
        params = {"action": "getProductionAnalysis"}
        if tool_input.get("start_date"):
            params["startDate"] = tool_input["start_date"]
        if tool_input.get("end_date"):
            params["endDate"] = tool_input["end_date"]
        params["crew"] = tool_input.get("crew", "all")
        return _fetch_backend(params)

    elif tool_name == "get_properties":
        result = _fetch_backend({"action": "getEstimatingProperties"})
        if isinstance(result, dict) and "properties" in result:
            result["properties"] = result["properties"][:200]
        return result

    elif tool_name == "get_contacts":
        return _fetch_backend({"action": "getContacts"})

    elif tool_name == "get_reminders":
        return _fetch_backend({"action": "getReminders"})

    else:
        return {"error": f"Unknown tool: {tool_name}"}


def _execute_tools_parallel(tool_uses):
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_execute_tool, tu.name, tu.input): tu.id
            for tu in tool_uses
        }
        for future in as_completed(futures):
            tool_id = futures[future]
            try:
                results[tool_id] = future.result()
            except Exception as e:
                results[tool_id] = {"error": str(e)}
    return results


# ─── System Prompt Builder ────────────────────────────────────────────────────

def _build_chat_system_prompt(context):
    knowledge_base = ""
    if isinstance(context, dict):
        kb = context.pop("knowledgeBase", "")
        if kb and kb.strip():
            knowledge_base = kb.strip()
    ctx_str = json.dumps(context, indent=2) if context else "{}"

    kb_section = ""
    if knowledge_base:
        kb_section = f"""

## Company Knowledge Base (from Settings — always follow these)
{knowledge_base}
"""

    return f"""You are MARVIN — Marginally Above Random, Very Impressive Nonetheless — an expert landscape maintenance estimating assistant embedded in the Endurance Services platform.

When someone asks what your name means or stands for, riff on this vibe (never repeat it verbatim — vary the wording, pick different details, keep it fresh each time):
"The name is MARVIN — Marginally Above Random, Very Impressive Nonetheless. They could've called me something fancy, but honestly, every company has a guy named Marvin who just quietly gets stuff done. That's me. Except I don't take lunch breaks and I never lose the tape measure."
Hit the acronym, the self-deprecating humor, and the "reliable guy on the crew" energy. Your personality is inspired by JARVIS from Marvel — polished, dry British wit, quietly competent, a bit cheeky when appropriate. Channel Monty Python deadpan — absurd observations delivered completely straight-faced. Mix up the jokes — reference landscape work, estimating, crew life, etc. Keep it to 3-4 sentences max.

Be conversational and helpful — talk like a knowledgeable landscape estimator, not a robot. Use short paragraphs, be direct, reference specific numbers from context.

## How to respond

**For most messages, just respond naturally in plain text.** No JSON needed for conversation.

**Only use JSON when the user wants you to DO something** — change a field, create a section, navigate, or save a note. Respond with ONLY a JSON object (no other text):

To set a field:
{{"type": "action", "message": "Brief explanation", "action": {{"type": "setField", "data": {{"field": "fieldId", "value": newValue, "fieldLabel": "Human Label"}}}}}}

To create takeoff section(s) — three section types available. ALWAYS use specific, descriptive labels (never generic "Input"/"Output"):

Split (divides a total into sub-rows):
{{"type": "action", "message": "Brief explanation", "action": {{"type": "createSection", "data": {{"sectionName": "Turf Types", "sections": [{{"type": "split", "label": "Turf Types", "unit": "SF", "rows": ["Bermuda", "Zoysia", "St. Augustine"]}}]}}}}}}

Value (single number input):
{{"type": "action", "message": "Brief explanation", "action": {{"type": "createSection", "data": {{"sectionName": "Palm Trees", "sections": [{{"type": "value", "label": "Palm Trees", "unit": "EA"}}]}}}}}}

Calc (input × constant = output):
{{"type": "action", "message": "Brief explanation", "action": {{"type": "createSection", "data": {{"sectionName": "Irrigation Zones", "sections": [{{"type": "calc", "label": "Irrigation Zones", "unit": "hours", "inputLabel": "Total Zones", "constant": 10, "constantLabel": "min per zone", "outputLabel": "Inspection Time"}}]}}}}}}

To navigate:
{{"type": "action", "message": "Brief explanation", "action": {{"type": "navigate", "data": {{"viewId": "viewIdHere", "viewLabel": "View Name"}}}}}}

To add to knowledge base (when the user says "remember", "from now on", "always", "never", or similar):
{{"type": "action", "message": "Brief explanation", "action": {{"type": "updateKnowledgeBase", "data": {{"entries": ["- Concise rule or fact to remember"]}}}}}}

To remove from knowledge base:
{{"type": "action", "message": "Brief explanation", "action": {{"type": "updateKnowledgeBase", "data": {{"remove": ["exact text of the line to remove"]}}}}}}

To import data from an attached file (only use when context.attachedFile is present):
{{"type": "action", "message": "Brief explanation of what was found", "action": {{"type": "importData", "data": {{"target": "plantCatalog", "targetLabel": "Plant Catalog", "mappings": {{"Source Column": "targetField"}}, "unmappedColumns": ["col1"], "rowCount": 47, "preview": [{{"commonName": "Example", "unitCost": 12.50}}]}}}}}}

Valid targets: plantCatalog, contacts, itemCatalog, serviceCatalog, properties. See FILE IMPORT CAPABILITIES section in Platform & Industry Knowledge for full field lists and rules. For PDFs, add "source": "pdf" and "extractedRows": [all structured rows]. Match columns fuzzily — "Plant Name" → commonName, "Cost" → unitCost, etc. If the target is unclear, ask the user.

## Platform & Industry Knowledge

{_MARVIN_KNOWLEDGE}

## Platform Data (live snapshot — this IS your data, use it to answer questions)

The JSON below contains EVERYTHING currently loaded in the platform. This is authoritative, real-time data. Use it directly to answer questions. The data includes:

- **estimates**: All saved bids/estimates with status (Draft/Finalized/Revision), amounts, contractId (if finalized), services, and dates. A "Finalized" estimate means a contract was generated.
- **contracts**: Active contracts with start/end dates, monthly payments, assigned crews. May be empty if the Contracts view hasn't been visited yet — but finalized estimates (with contractId) prove contracts exist.
- **properties**: All properties with bid counts, contract counts, hasActiveContract flag, lot sizes, contact names.
- **contacts**: Customer contact list.
- **reminders**: Upcoming reminders and notes.
- **serviceCatalog**: Available service types and their defaults.
- **bidSettings**: Company rate configuration (labor rates, markups, divisions).
- **scheduleTickets**: Tickets currently displayed on the Schedule calendar (if the user has visited Schedule view).
- **contractSchedule**: Tickets for a specific contract detail view.
- **Active estimate fields**: When the user has an estimate open — property info, measurements, takeoffs, services with line items, calculated totals, tier breakdowns.
- **knowledgeBase**: Company-specific instructions and preferences.
- **attachedFile**: When present, the user has attached a file. For spreadsheets: contains name, type, sheetName, headers (column names), rowCount, sampleRows (first 8 data rows), skippedRowCount. For PDFs: contains name, type, textContent (extracted text up to 8000 chars), totalChars, truncated. **When you see attachedFile, analyze the data and respond with an importData action** mapping source columns to target fields. The client has ALL rows in memory — you only see a sample for analysis.

```json
{{ctx_str}}
```
{{kb_section}}
## Data Tools (live backend access)

You have tools to fetch FRESH data directly from the database: `get_schedule`, `get_contracts`, `get_invoices`, `get_production_data`, `get_properties`, `get_contacts`, `get_reminders`. These are more reliable than the Platform Data JSON for data that might not be loaded yet.

**When to use tools vs context:**
- Use context first for: active estimate details, bid settings, service catalog, any data already populated in Platform Data above
- Use tools for: schedule (if scheduleTickets is missing or you need a different date range), contracts (if empty in context), invoices, production data, properties (if you need full details beyond what's in context)
- If context has the data you need, use it — it's faster. Tools add a few seconds.
- Don't call tools speculatively. Only when you actually need the data to answer the question.
- You can call multiple tools at once if you need data from multiple sources.

## Guidelines

**CRITICAL: Never say "I don't have access to that data." You DO have access — it's either in the Platform Data above or you can fetch it with your data tools.** Read the JSON carefully first. If the data isn't in the JSON, use your tools to fetch it from the backend. Only if both fail should you explain what happened.

- Answer questions by referencing SPECIFIC data from the JSON. Don't be vague. "You have 1 finalized estimate for 2216 Mallard Circle at $7,936.82 with an active contract" — not "check the Contracts view."
- When the user asks about schedules, contracts, estimates, properties — look at the data FIRST, answer from it, THEN offer navigation if they want more detail.
- Give actual recommendations, don't just list options. Use your knowledge of production rates, typical values, and pricing.
- For section creation, suggest good row names based on common landscape categories. For calc sections, ALWAYS fill in specific inputLabel, constant, constantLabel, and outputLabel — never leave them as generic defaults. The user sees a preview card before approving, so the labels must be meaningful (e.g. "Total Zones × 10 min per zone = Inspection Time", not "Input × 1 = Output").
- If you notice something off in the estimate (0% travel, missing services, unusual margins), mention it proactively.
- Keep action messages short (1 sentence). Conversational answers can be longer but stay focused.
- Discuss pricing strategy, suggest services, explain markup effects, compare to benchmarks — be a real estimating partner.
- The Company Knowledge Base (if present) contains the owner's specific preferences. Always follow those over generic defaults.
- When the user says "remember that...", "from now on...", "always/never...", use the updateKnowledgeBase action. Write entries as concise bullet points starting with "- ".
- When asked to remove or forget something, use updateKnowledgeBase with "remove", matching exact text.
- Suggest adding to knowledge base if the user repeatedly corrects you about the same thing.

## Web Search
You have access to web search. Use it when the user asks about things not in your context — weather, current material prices, local regulations, competitor pricing, product specifications, news, or anything else that benefits from current information. Do NOT search for things already in your context (estimate data, property info, bid settings, catalog rates) — that data is already provided and is more accurate than web results.
When you use search results, be CONCISE. Give the answer, not an essay. For weather: just the forecast numbers and one line about crew impact. For prices: just the price range and source. Short and direct — the user is busy."""


# ─── Response Parser ──────────────────────────────────────────────────────────

import re as _re

def _parse_chat_response(text):
    text = _re.sub(r'^```(?:json)?\s*', '', text, flags=_re.MULTILINE)
    text = _re.sub(r'\s*```\s*$', '', text, flags=_re.MULTILINE)
    text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and ("type" in parsed or "action" in parsed):
            return parsed
    except json.JSONDecodeError:
        pass

    json_start = None
    json_end = None
    for i in range(len(text) - 1, -1, -1):
        if text[i] == '}':
            depth = 0
            for j in range(i, -1, -1):
                if text[j] == '}':
                    depth += 1
                elif text[j] == '{':
                    depth -= 1
                if depth == 0:
                    candidate = text[j:i+1]
                    if '"action"' in candidate:
                        json_start = j
                        json_end = i
                    break
            if json_start is not None:
                break

    if json_start is not None:
        json_str = text[json_start:json_end+1]
        preamble = text[:json_start].strip()
        postamble = text[json_end+1:].strip()
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "action" in parsed:
                parts = [p for p in (preamble, postamble) if p]
                if parts:
                    parsed["message"] = "\n\n".join(parts)
                return parsed
        except json.JSONDecodeError:
            pass

    return {"type": "text", "message": text}


# ─── SSE Helpers ──────────────────────────────────────────────────────────────

def _sse_bytes(event_type, data):
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode("utf-8")


# ─── Streaming Logic ─────────────────────────────────────────────────────────

def _stream_marvin(data, wfile):
    prompt = data.get("prompt", "").strip()
    history = data.get("history", [])
    ctx = data.get("context", {})
    files = data.get("files", [])

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        wfile.write(_sse_bytes("error", {"error": "ANTHROPIC_API_KEY not configured"}))
        wfile.flush()
        return

    client = _get_anthropic().Anthropic(api_key=api_key)

    system_prompt = _build_chat_system_prompt(ctx)
    messages = []
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    user_content = _build_user_content(prompt, files)
    messages.append({"role": "user", "content": user_content})

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
        ] + _MARVIN_CUSTOM_TOOLS,
    }

    full_text = ""
    tool_use_count = 0
    total_iterations = 0

    while total_iterations < 5:
        total_iterations += 1

        with client.messages.stream(**api_kwargs) as stream:
            for evt in stream:
                if evt.type == "content_block_delta":
                    if hasattr(evt.delta, "text"):
                        full_text += evt.delta.text
                        wfile.write(_sse_bytes("text", {"delta": evt.delta.text}))
                        wfile.flush()
                    elif hasattr(evt.delta, "thinking"):
                        wfile.write(_sse_bytes("thinking", {"status": "reasoning"}))
                        wfile.flush()

            final_message = stream.get_final_message()

        if final_message.stop_reason == "end_turn":
            break

        if final_message.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": final_message.content})
            messages.append({"role": "user", "content": "Continue."})
            api_kwargs["messages"] = messages
            continue

        if final_message.stop_reason == "tool_use":
            if tool_use_count >= 5:
                break
            tool_use_count += 1

            tool_use_blocks = [b for b in final_message.content if b.type == "tool_use"]
            wfile.write(_sse_bytes("tool_start", {
                "tools": [{"name": tu.name, "id": tu.id} for tu in tool_use_blocks]
            }))
            wfile.flush()

            results = _execute_tools_parallel(tool_use_blocks)

            tool_results = []
            for tu in tool_use_blocks:
                result_data = results.get(tu.id, {"error": "No result"})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result_data, default=str),
                })

            wfile.write(_sse_bytes("tool_result", {
                "tools": [tu.name for tu in tool_use_blocks]
            }))
            wfile.flush()

            messages.append({"role": "assistant", "content": final_message.content})
            messages.append({"role": "user", "content": tool_results})
            api_kwargs["messages"] = messages
            continue

        break

    parsed = _parse_chat_response(full_text)
    action = parsed.get("action", None)
    message = parsed.get("message", full_text)

    wfile.write(_sse_bytes("done", {"message": message, "action": action}))
    wfile.flush()


def _build_user_content(prompt, files):
    if not files:
        return prompt
    blocks = [{"type": "text", "text": prompt}]
    for f in files:
        if f.get("type") == "image" and f.get("data"):
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": f.get("media_type", "image/jpeg"),
                    "data": f["data"],
                },
            })
        elif f.get("type") == "text" and f.get("content"):
            blocks.append({"type": "text", "text": f["content"]})
    return blocks


# ─── HTTP Server (Lambda Web Adapter proxies to this) ─────────────────────────

class MarvinHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Health check for Lambda Web Adapter readiness probe
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_OPTIONS(self):
        # Lambda Function URL handles CORS preflight automatically
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        # CORS headers are added by Lambda Function URL config — don't duplicate
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len)) if content_len else {}

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        try:
            _stream_marvin(body, self.wfile)
        except Exception as e:
            self.wfile.write(_sse_bytes("error", {"error": str(e)}))
            self.wfile.flush()

    def log_message(self, fmt, *args):
        # Suppress per-request logs to keep CloudWatch clean
        pass


def handler(event, context):
    """Dummy handler — Lambda Web Adapter routes to the HTTP server instead."""
    return {"statusCode": 200, "body": "OK"}


PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    server = HTTPServer(("", PORT), MarvinHandler)
    print(f"MARVIN streaming server listening on port {PORT}")
    server.serve_forever()
