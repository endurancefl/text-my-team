"""AWS Lambda handler for PDF generation and MARVIN AI chat.

Receives requests via API Gateway, parses the request,
generates PDFs via DocRaptor, and returns base64-encoded PDF.

Supports two input modes:
  - multipart/form-data: photos embedded in request body
  - application/json with S3 keys: photos fetched from S3
"""
import base64
import io
import json
import os
import re
import uuid
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from pathlib import Path

from docraptor_service import (
    ALLOWED_ORIGINS,
    allowed_origin_from_header,
    cors_headers,
    parse_photo_buffers,
    generate_standard_report,
    generate_before_after_report,
    generate_contract_pdf,
    generate_invoice_pdf,
)

DOCRAPTOR_TEST_MODE = os.environ.get("DOCRAPTOR_TEST_MODE", "false").lower() == "true"

# Load MARVIN knowledge file (bundled in Docker image, read once at cold start)
_MARVIN_KNOWLEDGE = ""
_knowledge_path = Path(__file__).parent / "marvin-knowledge.md"
if _knowledge_path.exists():
    _MARVIN_KNOWLEDGE = _knowledge_path.read_text(encoding="utf-8")

# Google Sheets backend URL (same endpoint used by all frontend apps)
GOOGLE_SHEETS_URL = "https://script.google.com/macros/s/AKfycbygkHGZmIYUj9F91u-3eF3_V9mC7xZ03PfCJt6AD_VnpSXheLlEvt6h1obmqUf4JkRg/exec"

# S3 client (reused across invocations)
_s3_client = None
PHOTO_BUCKET = os.environ.get("PHOTO_BUCKET", "")


def _get_s3_client():
    """Lazy-init S3 client for connection reuse."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def lambda_handler(event, context):
    """AWS Lambda entry point for API Gateway HTTP API."""
    # Handle CORS preflight
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    if not method:
        method = event.get("httpMethod", "GET")

    headers = event.get("headers", {})
    # API Gateway lowercases header names for HTTP API
    origin = headers.get("origin", headers.get("Origin", ""))
    allowed = allowed_origin_from_header(origin)

    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": cors_headers(allowed),
            "body": "",
        }

    # Route by path
    path = event.get("requestContext", {}).get("http", {}).get("path", "")
    if not path:
        path = event.get("path", "")

    if "/upload-urls" in path:
        return _handle_upload_urls(event, allowed)

    if "/marvin" in path:
        return _handle_marvin(event, allowed)

    # Default: PDF generation
    return _handle_generate_pdf(event, allowed, headers)


def _handle_upload_urls(event, allowed):
    """Generate pre-signed S3 PUT URLs for photo uploads."""
    try:
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)
        if is_base64:
            body = base64.b64decode(body).decode("utf-8")

        data = json.loads(body)
        session_id = str(uuid.uuid4())
        s3 = _get_s3_client()

        report_type = data.get("reportType", "standard")

        if report_type == "before_after":
            before_count = int(data.get("beforeCount", 0))
            after_count = int(data.get("afterCount", 0))

            before_urls, before_keys = _generate_presigned_urls(
                s3, session_id, "before", before_count
            )
            after_urls, after_keys = _generate_presigned_urls(
                s3, session_id, "after", after_count
            )

            response_body = {
                "sessionId": session_id,
                "beforeUrls": before_urls,
                "beforeKeys": before_keys,
                "afterUrls": after_urls,
                "afterKeys": after_keys,
            }
        else:
            count = int(data.get("count", 0))
            urls, keys = _generate_presigned_urls(s3, session_id, "photo", count)

            response_body = {
                "sessionId": session_id,
                "urls": urls,
                "keys": keys,
            }

        resp_headers = cors_headers(allowed)
        resp_headers["Content-Type"] = "application/json"
        return {
            "statusCode": 200,
            "headers": resp_headers,
            "body": json.dumps(response_body),
        }

    except Exception as e:
        return _error_response(f"Upload URL error: {e}", 500, allowed)


def _generate_presigned_urls(s3, session_id, prefix, count):
    """Generate pre-signed PUT URLs and corresponding S3 keys."""
    urls = []
    keys = []
    for i in range(count):
        key = f"uploads/{session_id}/{prefix}_{i}.jpg"
        url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": PHOTO_BUCKET,
                "Key": key,
                "ContentType": "image/jpeg",
            },
            ExpiresIn=900,  # 15 minutes
        )
        urls.append(url)
        keys.append(key)
    return urls, keys


def _fetch_s3_photos(s3, bucket, keys):
    """Fetch photos from S3 and return BytesIO buffers."""
    raw_files = []
    for key in keys:
        resp = s3.get_object(Bucket=bucket, Key=key)
        raw_files.append(resp["Body"].read())
    return parse_photo_buffers(raw_files)


# API Gateway payload limit is 10MB (base64 adds ~33% overhead)
# So ~7MB raw PDF is the safe threshold before base64 pushes it over 10MB
_PDF_SIZE_THRESHOLD = 7 * 1024 * 1024


def _pdf_response(pdf_bytes, filename, allowed):
    """Return PDF either inline (base64) or via S3 pre-signed URL if too large."""
    if len(pdf_bytes) < _PDF_SIZE_THRESHOLD:
        # Small enough — return inline
        response_headers = cors_headers(allowed)
        response_headers["Content-Type"] = "application/pdf"
        response_headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return {
            "statusCode": 200,
            "headers": response_headers,
            "body": base64.b64encode(pdf_bytes).decode("utf-8"),
            "isBase64Encoded": True,
        }

    # Too large for API Gateway — write to S3 and return download URL
    s3 = _get_s3_client()
    key = f"pdfs/{uuid.uuid4()}/{filename}"
    s3.put_object(
        Bucket=PHOTO_BUCKET,
        Key=key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )
    download_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": PHOTO_BUCKET, "Key": key},
        ExpiresIn=3600,  # 1 hour
    )
    response_headers = cors_headers(allowed)
    response_headers["Content-Type"] = "application/json"
    return {
        "statusCode": 200,
        "headers": response_headers,
        "body": json.dumps({"downloadUrl": download_url, "filename": filename}),
    }


def _handle_generate_pdf(event, allowed, headers):
    """Handle PDF generation — supports both multipart and JSON+S3 flows."""
    try:
        # Get the raw body
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)
        if is_base64:
            raw_body = base64.b64decode(body)
        else:
            raw_body = body.encode("utf-8") if isinstance(body, str) else body

        # Determine content type to choose parsing strategy
        content_type = headers.get("content-type", headers.get("Content-Type", ""))

        if "application/json" in content_type:
            return _handle_json_request(raw_body, allowed)
        else:
            return _handle_multipart_request(raw_body, content_type, allowed)

    except json.JSONDecodeError as e:
        return _error_response(f"Invalid metadata JSON: {e}", 400, allowed)
    except Exception as e:
        return _error_response(f"Internal error: {e}", 500, allowed)


def _handle_json_request(raw_body, allowed):
    """Handle JSON request with S3 keys for photos."""
    data = json.loads(raw_body)
    # Support nested metadata string (Apps Script sends { metadata: JSON.stringify(...) })
    if "metadata" in data and isinstance(data["metadata"], str):
        metadata = json.loads(data["metadata"])
    else:
        metadata = data
    report_type = metadata.get("type", "standard")

    s3 = _get_s3_client()
    bucket = PHOTO_BUCKET
    test = DOCRAPTOR_TEST_MODE

    if report_type == "invoice":
        pdf_bytes, filename = generate_invoice_pdf(metadata, test=test)

    elif report_type == "contract":
        service_map_buffer = None
        service_map_keys = metadata.get("serviceMapS3Keys", [])
        if service_map_keys:
            buffers = _fetch_s3_photos(s3, bucket, service_map_keys)
            if buffers:
                service_map_buffer = buffers[0]

        pdf_bytes, filename = generate_contract_pdf(metadata, service_map_buffer, test=test)

    elif report_type == "before_after":
        before_keys = metadata.get("beforeS3Keys", [])
        after_keys = metadata.get("afterS3Keys", [])

        before_buffers = _fetch_s3_photos(s3, bucket, before_keys)
        after_buffers = _fetch_s3_photos(s3, bucket, after_keys)

        pdf_bytes, filename = generate_before_after_report(metadata, before_buffers, after_buffers, test=test)

    else:
        s3_keys = metadata.get("s3Keys", [])
        photo_buffers = _fetch_s3_photos(s3, bucket, s3_keys)

        pdf_bytes, filename = generate_standard_report(metadata, photo_buffers, test=test)

    return _pdf_response(pdf_bytes, filename, allowed)


def _handle_multipart_request(raw_body, content_type, allowed):
    """Handle multipart/form-data request with embedded photos (legacy flow)."""
    boundary = _extract_boundary(content_type)
    if not boundary:
        return _error_response("Missing multipart boundary", 400, allowed)

    # Parse multipart form data
    parts = _parse_multipart(raw_body, boundary)

    # Extract metadata
    metadata_raw = parts.get("fields", {}).get("metadata")
    if not metadata_raw:
        return _error_response("Missing metadata field", 400, allowed)

    metadata = json.loads(metadata_raw)
    report_type = metadata.get("type", "standard")
    test = DOCRAPTOR_TEST_MODE

    if report_type == "invoice":
        pdf_bytes, filename = generate_invoice_pdf(metadata, test=test)

    elif report_type == "contract":
        service_map_files = parts.get("files", {}).get("service_map", [])
        service_map_buffer = None
        if service_map_files:
            buffers = parse_photo_buffers(service_map_files)
            if buffers:
                service_map_buffer = buffers[0]

        pdf_bytes, filename = generate_contract_pdf(metadata, service_map_buffer, test=test)

    elif report_type == "before_after":
        before_files = parts.get("files", {}).get("before_photos", [])
        after_files = parts.get("files", {}).get("after_photos", [])

        before_buffers = parse_photo_buffers(before_files)
        after_buffers = parse_photo_buffers(after_files)

        pdf_bytes, filename = generate_before_after_report(metadata, before_buffers, after_buffers, test=test)

    else:
        photo_files = parts.get("files", {}).get("photos", [])
        photo_buffers = parse_photo_buffers(photo_files)

        pdf_bytes, filename = generate_standard_report(metadata, photo_buffers, test=test)

    return _pdf_response(pdf_bytes, filename, allowed)


def _error_response(message, status_code, origin):
    """Build an error response with CORS headers."""
    response_headers = cors_headers(origin)
    response_headers["Content-Type"] = "application/json"
    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": json.dumps({"error": message}),
    }


def _extract_boundary(content_type):
    """Extract the multipart boundary from Content-Type header."""
    match = re.search(r'boundary=([^\s;]+)', content_type)
    if match:
        boundary = match.group(1)
        # Remove surrounding quotes if present
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]
        return boundary
    return None


def _parse_multipart(body, boundary):
    """Parse multipart/form-data body into fields and files.

    Returns:
        dict with 'fields' (name -> string value) and 'files' (name -> [bytes, ...])
    """
    result = {"fields": {}, "files": {}}

    # The boundary in the body is prefixed with --
    delimiter = b"--" + boundary.encode("utf-8")
    end_delimiter = delimiter + b"--"

    # Split body by delimiter
    parts = body.split(delimiter)

    for part in parts:
        # Skip empty parts and end delimiter
        if not part or part.strip() == b"--" or part.strip() == b"":
            continue
        if part.startswith(b"--"):
            continue

        # Strip leading \r\n
        if part.startswith(b"\r\n"):
            part = part[2:]

        # Split headers from body at double CRLF
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue

        header_data = part[:header_end].decode("utf-8", errors="replace")
        body_data = part[header_end + 4:]

        # Remove trailing \r\n from body
        if body_data.endswith(b"\r\n"):
            body_data = body_data[:-2]

        # Parse Content-Disposition header
        name = None
        filename = None
        is_file = False

        for line in header_data.split("\r\n"):
            if line.lower().startswith("content-disposition"):
                name_match = re.search(r'name="([^"]*)"', line)
                if name_match:
                    name = name_match.group(1)
                filename_match = re.search(r'filename="([^"]*)"', line)
                if filename_match:
                    filename = filename_match.group(1)
                    is_file = True

        if not name:
            continue

        if is_file:
            if name not in result["files"]:
                result["files"][name] = []
            result["files"][name].append(body_data)
        else:
            result["fields"][name] = body_data.decode("utf-8", errors="replace")

    return result


# ─── MARVIN Custom Tool Definitions ───────────────────────────────────────────

_MARVIN_CUSTOM_TOOLS = [
    {
        "name": "get_schedule",
        "description": "Fetch schedule tickets from the database. Returns tickets with property, crew, date, services, estimated hours, and status. Use when the user asks about the schedule, upcoming work, or what's planned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date filter (YYYY-MM-DD). Defaults to today if omitted."
                },
                "end_date": {
                    "type": "string",
                    "description": "End date filter (YYYY-MM-DD). Defaults to 7 days from start_date if omitted."
                },
                "crew": {
                    "type": "string",
                    "description": "Filter by crew name (e.g. 'Crew A'). Omit for all crews."
                },
                "contract_id": {
                    "type": "string",
                    "description": "Filter by contract ID. Omit for all contracts."
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_contracts",
        "description": "Fetch all contracts from the database. Returns contract details including property, crew, dates, monthly payment, status, and signing info. Use when the user asks about contracts, active accounts, or contract details.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_invoices",
        "description": "Fetch invoices from the database. Returns invoice details including amounts, status, dates, and payment info. Use when the user asks about invoices, payments, overdue amounts, or billing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'draft', 'sent', 'overdue', 'paid'. Omit for all."
                },
                "contract_id": {
                    "type": "string",
                    "description": "Filter by contract ID. Omit for all contracts."
                },
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
                "start_date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD). Required for meaningful results."
                },
                "end_date": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD). Required for meaningful results."
                },
                "crew": {
                    "type": "string",
                    "description": "Filter by crew name. Use 'all' or omit for all crews."
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_properties",
        "description": "Fetch all properties from the database. Returns property details including address, lot size, measurements, contacts, bid/contract counts, and crew assignments. Use when the user asks about properties, property details, or which properties need attention.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_contacts",
        "description": "Fetch all contacts from the CRM. Returns contact details including name, email, phone, company, stage, and notes. Use when the user asks about contacts, customers, or who manages a property.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_reminders",
        "description": "Fetch all reminders from the database. Returns reminder details including property, description, date, status, and assigned crew. Use when the user asks about reminders, upcoming tasks, or notes.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def _fetch_backend(params):
    """HTTP GET to the Google Sheets backend with query parameters. Returns parsed JSON."""
    query = urllib.parse.urlencode(params)
    url = f"{GOOGLE_SHEETS_URL}?{query}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except Exception as e:
        return {"error": f"Backend request failed: {e}"}


def _execute_tool(tool_name, tool_input):
    """Dispatch a MARVIN tool call to the appropriate backend endpoint."""
    from datetime import date, timedelta

    if tool_name == "get_schedule":
        params = {"action": "getTickets"}
        start = tool_input.get("start_date", "")
        end = tool_input.get("end_date", "")
        # Default to today + 7 days if no dates provided
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
        # Truncate to 100 tickets max
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
        # Truncate to 200 invoices max
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
        # Truncate to 200 properties max
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
    """Execute multiple tool calls in parallel. Returns dict of tool_id -> result."""
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


def _handle_marvin(event, allowed):
    """Handle MARVIN AI chat requests."""
    try:
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)
        if is_base64:
            body = base64.b64decode(body).decode("utf-8")

        data = json.loads(body)
        prompt = data.get("prompt", "").strip()
        history = data.get("history", [])

        if not prompt:
            return _error_response("Missing 'prompt' in request body", 400, allowed)

        # Get API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return _error_response("ANTHROPIC_API_KEY not configured", 500, allowed)

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = _build_chat_system_prompt(data.get("context", {}))
        max_tokens = 8192

        # Build messages: include conversation history for iterative refinement
        messages = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        # Build API call kwargs with web search and custom data tools
        api_kwargs = {
            "model": "claude-opus-4-5-20251101",
            "max_tokens": max_tokens,
            "system": [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
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

        message = client.messages.create(**api_kwargs)

        # Continuation loop: handles web search (pause_turn) and custom tools (tool_use)
        tool_use_count = 0
        total_iterations = 0

        while total_iterations < 5:
            if message.stop_reason == "end_turn":
                break

            if message.stop_reason == "pause_turn":
                # Web search continuation
                total_iterations += 1
                messages.append({"role": "assistant", "content": message.content})
                messages.append({"role": "user", "content": "Continue."})
                message = client.messages.create(**api_kwargs)
                continue

            if message.stop_reason == "tool_use":
                if tool_use_count >= 5:
                    break  # Safety cap: prevent runaway tool loops
                tool_use_count += 1
                total_iterations += 1

                # Extract tool_use blocks and execute in parallel
                tool_uses = [b for b in message.content if b.type == "tool_use"]
                results = _execute_tools_parallel(tool_uses)

                # Build tool_result messages
                tool_results = []
                for tu in tool_uses:
                    result_data = results.get(tu.id, {"error": "No result"})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": json.dumps(result_data, default=str),
                    })

                messages.append({"role": "assistant", "content": message.content})
                messages.append({"role": "user", "content": tool_results})
                message = client.messages.create(**api_kwargs)
                continue

            break  # Unknown stop_reason

        # Extract text from response — may contain multiple blocks when web search is used
        text_parts = []
        for block in message.content:
            if block.type == "text":
                text_parts.append(block.text)
        result_text = "\n".join(text_parts).strip()

        result_json = _parse_chat_response(result_text)

        resp_headers = cors_headers(allowed)
        resp_headers["Content-Type"] = "application/json"
        return {
            "statusCode": 200,
            "headers": resp_headers,
            "body": json.dumps({"success": True, "result": result_json}),
        }

    except Exception as e:
        return _error_response(f"MARVIN error: {e}", 500, allowed)


def _build_chat_system_prompt(context):
    """Build the conversational system prompt with injected context."""
    # Extract knowledge base before serializing context (keep context JSON clean)
    knowledge_base = ""
    if isinstance(context, dict):
        kb = context.pop("knowledgeBase", "")
        if kb and kb.strip():
            knowledge_base = kb.strip()
    ctx_str = json.dumps(context, indent=2) if context else "{}"

    # Build the knowledge base section
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

To bulk-update existing catalog entries (when the user asks to change a field on multiple items — e.g., "set supplier to X on all plants", "change category to Tree for all oaks"):
{{"type": "action", "message": "Brief explanation", "action": {{"type": "bulkUpdate", "data": {{"target": "plantCatalog", "targetLabel": "Plant Catalog", "updates": {{"supplier": "County Line"}}, "filter": {{}}, "affectedCount": 10}}}}}}

Supported targets: plantCatalog. The updates object is a field→value map.
plantCatalog updatable fields: supplier (applied to every size entry on each plant), category, notes.
filter narrows scope; empty object {{}} = all items. Examples:
  {{"category": "Shrub"}} — only plants with category Shrub
  {{"supplier": ""}} — only plants where ALL sizes have a blank/empty supplier
  {{"supplier": "County Line"}} — only plants where ALL sizes have supplier "County Line"
Use "" (empty string) in filter to match blank/missing values.
affectedCount MUST equal the number of items from context.plantCatalog that match the filter — count them carefully from the data. For supplier filters, check each plant's sizes array.
Use bulkUpdate when the user wants to MODIFY EXISTING data in bulk, not import new data.
IMPORTANT: In your text message for bulkUpdate, do NOT list specific plant names — the client computes the real count and shows details on the action card. Keep your message brief, e.g., "Setting supplier to County Line for plants with blank suppliers." Never enumerate or guess which plants match.

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

```json
{ctx_str}
```
{kb_section}
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


def _parse_chat_response(text):
    """Parse a chat-mode response. Could be plain text, JSON action, or mixed."""
    import re
    # Strip markdown fences if present
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()

    # Case 1: Pure JSON response (action only)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and ("type" in parsed or "action" in parsed):
            return parsed
    except json.JSONDecodeError:
        pass

    # Case 2: Mixed response — natural text with a JSON action block anywhere.
    # Find the last top-level JSON object in the text that contains "action".
    # Track both start (j) and end (i) positions so text before AND after
    # the JSON block is captured as the message.
    json_start = None
    json_end = None
    for i in range(len(text) - 1, -1, -1):
        if text[i] == '}':
            # Walk backwards to find the matching opening brace
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
                # Combine text before and after JSON as the message
                parts = [p for p in (preamble, postamble) if p]
                if parts:
                    parsed["message"] = "\n\n".join(parts)
                return parsed
        except json.JSONDecodeError:
            pass

    # Case 3: Plain text response — the normal conversational case
    return {"type": "text", "message": text}
