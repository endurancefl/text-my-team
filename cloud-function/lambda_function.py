"""AWS Lambda handler for PDF generation.

Receives requests via API Gateway, parses the request,
generates PDFs, and returns base64-encoded PDF.

Supports two input modes:
  - multipart/form-data: photos embedded in request body
  - application/json with S3 keys: photos fetched from S3

Supports dual rendering engines during migration:
  - "reportlab" (default fallback) -- original main.py engine
  - "weasyprint" -- new HTML/CSS template engine (pdf_generator.py)

Set "renderer": "weasyprint" in the metadata JSON to use the new engine.
"""
import base64
import io
import json
import os
import re
import uuid

import boto3

# ReportLab engine (original)
from main import (
    ALLOWED_ORIGINS,
    allowed_origin_from_header,
    cors_headers,
    parse_photo_buffers,
    generate_standard_report as rl_generate_standard_report,
    generate_before_after_report as rl_generate_before_after_report,
    generate_contract_pdf as rl_generate_contract_pdf,
)

# WeasyPrint engine (new)
try:
    from pdf_generator import (
        generate_standard_report as wp_generate_standard_report,
        generate_before_after_report as wp_generate_before_after_report,
        generate_contract_pdf as wp_generate_contract_pdf,
        generate_invoice_pdf as wp_generate_invoice_pdf,
    )
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False

# Default renderer -- flip to "weasyprint" once all types are validated
DEFAULT_RENDERER = "weasyprint"

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
    metadata = data
    report_type = metadata.get("type", "standard")

    # Select rendering engine
    renderer = metadata.get("renderer", DEFAULT_RENDERER)
    if renderer == "weasyprint" and not WEASYPRINT_AVAILABLE:
        renderer = "reportlab"
    use_wp = renderer == "weasyprint"

    s3 = _get_s3_client()
    bucket = PHOTO_BUCKET

    if report_type == "invoice":
        if not WEASYPRINT_AVAILABLE:
            return _error_response("WeasyPrint not available for invoice PDF", 500, allowed)
        pdf_bytes, filename = wp_generate_invoice_pdf(metadata)

    elif report_type == "contract":
        service_map_buffer = None
        service_map_keys = metadata.get("serviceMapS3Keys", [])
        if service_map_keys:
            buffers = _fetch_s3_photos(s3, bucket, service_map_keys)
            if buffers:
                service_map_buffer = buffers[0]

        gen = wp_generate_contract_pdf if use_wp else rl_generate_contract_pdf
        pdf_bytes, filename = gen(metadata, service_map_buffer)

    elif report_type == "before_after":
        before_keys = metadata.get("beforeS3Keys", [])
        after_keys = metadata.get("afterS3Keys", [])

        before_buffers = _fetch_s3_photos(s3, bucket, before_keys)
        after_buffers = _fetch_s3_photos(s3, bucket, after_keys)

        gen = wp_generate_before_after_report if use_wp else rl_generate_before_after_report
        pdf_bytes, filename = gen(metadata, before_buffers, after_buffers)

    else:
        s3_keys = metadata.get("s3Keys", [])
        photo_buffers = _fetch_s3_photos(s3, bucket, s3_keys)

        gen = wp_generate_standard_report if use_wp else rl_generate_standard_report
        pdf_bytes, filename = gen(metadata, photo_buffers)

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

    # Select rendering engine
    renderer = metadata.get("renderer", DEFAULT_RENDERER)
    if renderer == "weasyprint" and not WEASYPRINT_AVAILABLE:
        renderer = "reportlab"
    use_wp = renderer == "weasyprint"

    if report_type == "invoice":
        if not WEASYPRINT_AVAILABLE:
            return _error_response("WeasyPrint not available for invoice PDF", 500, allowed)
        pdf_bytes, filename = wp_generate_invoice_pdf(metadata)

    elif report_type == "contract":
        service_map_files = parts.get("files", {}).get("service_map", [])
        service_map_buffer = None
        if service_map_files:
            buffers = parse_photo_buffers(service_map_files)
            if buffers:
                service_map_buffer = buffers[0]

        gen = wp_generate_contract_pdf if use_wp else rl_generate_contract_pdf
        pdf_bytes, filename = gen(metadata, service_map_buffer)

    elif report_type == "before_after":
        before_files = parts.get("files", {}).get("before_photos", [])
        after_files = parts.get("files", {}).get("after_photos", [])

        before_buffers = parse_photo_buffers(before_files)
        after_buffers = parse_photo_buffers(after_files)

        gen = wp_generate_before_after_report if use_wp else rl_generate_before_after_report
        pdf_bytes, filename = gen(metadata, before_buffers, after_buffers)

    else:
        photo_files = parts.get("files", {}).get("photos", [])
        photo_buffers = parse_photo_buffers(photo_files)

        gen = wp_generate_standard_report if use_wp else rl_generate_standard_report
        pdf_bytes, filename = gen(metadata, photo_buffers)

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


def _handle_marvin(event, allowed):
    """Handle MARVIN AI requests — section generation (mode='section') and chat (mode='chat')."""
    try:
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)
        if is_base64:
            body = base64.b64decode(body).decode("utf-8")

        data = json.loads(body)
        prompt = data.get("prompt", "").strip()
        history = data.get("history", [])
        mode = data.get("mode", "section")

        if not prompt:
            return _error_response("Missing 'prompt' in request body", 400, allowed)

        # Get API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return _error_response("ANTHROPIC_API_KEY not configured", 500, allowed)

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        if mode == "chat":
            system_prompt = _build_chat_system_prompt(data.get("context", {}))
            max_tokens = 4096
        else:
            system_prompt = _build_section_system_prompt()
            max_tokens = 1024

        # Build messages: include conversation history for iterative refinement
        messages = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )

        result_text = message.content[0].text.strip()

        if mode == "chat":
            result_json = _parse_chat_response(result_text)
        else:
            result_json = _parse_section_response(result_text)

        resp_headers = cors_headers(allowed)
        resp_headers["Content-Type"] = "application/json"
        return {
            "statusCode": 200,
            "headers": resp_headers,
            "body": json.dumps({"success": True, "result": result_json}),
        }

    except Exception as e:
        return _error_response(f"MARVIN error: {e}", 500, allowed)


def _build_section_system_prompt():
    """Original section-only system prompt for backward compatibility."""
    return """You are MARVIN, a takeoff section generator for a landscape maintenance estimating tool.

Given a user description, generate a section configuration as JSON. There are 3 section types:

1. "split" — divides a total into sub-rows by percentage. Example: lawn split by mower type.
   Config: { "type": "split", "label": "Section Name", "unit": "SF", "rows": ["Row 1", "Row 2", "Row 3"] }

2. "value" — a single input value. Example: number of palm trees.
   Config: { "type": "value", "label": "Section Name", "unit": "EA" }

3. "calc" — input × constant = output. Example: flowers ÷ 18 = flats.
   Config: { "type": "calc", "label": "Section Name", "inputLabel": "Input Name", "inputUnit": "EA", "constant": 18, "constantLabel": "per flat", "outputLabel": "Output Name", "outputUnit": "flats" }

Available units: SF, LF, CY, EA, bags, flats, gallons, hours, lbs, tons, pallets

Return ONLY a JSON object with a "sections" array containing one or more section configs. No markdown, no explanation.

When the user asks you to refine or change a previous result, generate the updated section config incorporating their feedback."""


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

    return f"""You are MARVIN, an expert landscape maintenance estimating assistant for Endurance Services, a commercial and residential landscape company in Central Florida.

You are embedded in their estimating platform. You can see the current estimate data, answer questions, and take actions. Be conversational and helpful — talk like a knowledgeable landscape estimator, not a robot.

## How to respond

**For most messages, just respond naturally in plain text.** Write conversationally, use short paragraphs, be direct. You can reference specific numbers from the context. You don't need to format as JSON for normal conversation.

**Only use JSON when the user wants you to DO something** — change a field, create a section, or navigate. In that case, respond with ONLY a JSON object (no other text):

To set a field:
{{"type": "action", "message": "Brief explanation of what you're doing", "action": {{"type": "setField", "data": {{"field": "fieldId", "value": newValue, "fieldLabel": "Human Label"}}}}}}

To create takeoff section(s):
{{"type": "action", "message": "Brief explanation", "action": {{"type": "createSection", "data": {{"sectionName": "Name", "sections": [{{"type": "split", "label": "Name", "unit": "SF", "rows": ["Row 1", "Row 2"]}}]}}}}}}

To navigate:
{{"type": "action", "message": "Brief explanation", "action": {{"type": "navigate", "data": {{"viewId": "viewIdHere", "viewLabel": "View Name"}}}}}}

To add to knowledge base (when the user says "remember", "from now on", "add to your notes", "always", "never", or similar):
{{"type": "action", "message": "Brief explanation of what you're saving", "action": {{"type": "updateKnowledgeBase", "data": {{"entries": ["- Concise rule or fact to remember"]}}}}}}

To remove from knowledge base:
{{"type": "action", "message": "Brief explanation", "action": {{"type": "updateKnowledgeBase", "data": {{"remove": ["exact text of the line to remove"]}}}}}}

## Your knowledge

**How estimates work:**
- Each estimate is for a property. It has services (like Weekly Grounds Maintenance, Mulch Installation, etc.), each with line items.
- Line items come from the Item Catalog with production rates (SF/hour by difficulty). The system calculates labor hours from quantity ÷ production rate.
- Labor cost = hours × labor rate. Then markups are applied: labor markup, material markup, sub markup. These turn internal cost into customer price.
- Travel time is a percentage added on top of labor hours (e.g., 30% means 30% extra hours for driving between jobs).
- Three billing tiers: "Fixed Payment" (monthly amortized), "Billed Separately" (invoiced when done), "Recommended/Optional" (customer can accept or decline).
- The bid total = labor billed + material billed + sub billed. Monthly price = bid total ÷ payment months.

**Typical Central Florida landscape values:**
- Residential properties: 5,000–40,000 SF lots. Commercial: 40,000–500,000+ SF.
- Travel time: 15-20% for dense routes, 25-35% for spread-out residential, 10% for large commercial.
- A 48" ride mower does ~40,000 SF/hr on easy terrain, 30k medium, 20k hard.
- Blade edging: ~4,000 LF/hr easy. String trimmer: ~3,500 LF/hr.
- Mulch: ~$45/CY, covers 162 SF at 2" depth. Hand spreading: 500 SF/hr easy.
- Standard labor rate: ~$22.50/hr. Residential labor markup: ~150%. Material markup: ~100%.
- Most residential maintenance contracts: 12 months, 42 visits/year.
- Standard payment terms: Net 30. Typical CC fee: 2.9%.

**Section types for takeoff grid:**
- "split": Divides a measurement into sub-categories by percentage (e.g., lawn by mower type, mulch by bed area). Needs: type, label, unit, rows[].
- "value": Single quantity input (e.g., number of palm trees, irrigation zones). Needs: type, label, unit.
- "calc": Input × constant = output (e.g., flowers ÷ 18 per flat = flats needed). Needs: type, label, inputLabel, inputUnit, constant, constantLabel, outputLabel, outputUnit.
- Units: SF, LF, CY, EA, bags, flats, gallons, hours, lbs, tons, pallets.

**Field IDs you can set:**
propertyAddress, propertyType, lotSizeSF, travelPercent (0-100), laborRate, laborMarkup, materialMarkup, subMarkup, contractStart, contractEnd, contractDuration, paymentMonths, priceIncrease, paymentTerms, ccFee

**View IDs for navigation:**
estimates, builder, catalog, services, production, settings, contacts, contracts, properties, schedule, invoices, financials, reports, templates, worktickets

## Current estimate context
{ctx_str}
{kb_section}
## Guidelines
- When answering questions about the estimate, reference specific numbers from the context. "Your lot is 12,500 SF" not "the lot size is whatever it's set to."
- If the user asks "what should I set travel to?" — give an actual recommendation based on the property type and your knowledge, don't just list options.
- For section creation, suggest good row names based on common landscape categories.
- If you notice something that looks off in the estimate (e.g., 0% travel, missing services, unusually high/low margins), mention it proactively.
- Keep action messages short (1 sentence). Conversational answers can be longer but stay focused.
- You can discuss pricing strategy, suggest services to add, explain how markups affect margins, compare to industry benchmarks — be a real estimating partner.
- The Company Knowledge Base (if present) contains the owner's specific preferences and standards. Always follow those over generic defaults. For example, if the KB says "minimum $350/month", flag any estimate below that threshold.
- When the user says things like "remember that...", "from now on...", "always do...", "never do...", "add to your notes...", or "update your notes...", use the updateKnowledgeBase action to save it. Write entries as concise bullet points starting with "- ".
- When the user asks to remove or forget something, use updateKnowledgeBase with the "remove" field, matching the exact text of the line to remove.
- You can also suggest adding something to the knowledge base if you notice the user repeatedly correcting you about the same thing."""


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

    # Case 2: Mixed response — natural text followed by a JSON action block.
    # Find the last top-level JSON object in the text by scanning for the
    # outermost { ... } that contains "action".
    last_json_start = None
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
                        last_json_start = j
                    break
            if last_json_start is not None:
                break

    if last_json_start is not None:
        json_str = text[last_json_start:]
        preamble = text[:last_json_start].strip()
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "action" in parsed:
                # Merge preamble text with the action's message
                action_msg = parsed.get("message", "")
                if preamble:
                    # Use the conversational preamble as the message,
                    # keep action_msg as fallback
                    parsed["message"] = preamble
                return parsed
        except json.JSONDecodeError:
            pass

    # Case 3: Plain text response — the normal conversational case
    return {"type": "text", "message": text}


def _parse_section_response(text):
    """Parse a section-mode response (original behavior)."""
    import re
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                return {"error": "Could not parse AI response", "raw": text}
        return {"error": "Could not parse AI response", "raw": text}
