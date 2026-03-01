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
    """Handle MARVIN AI section generation requests."""
    try:
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)
        if is_base64:
            body = base64.b64decode(body).decode("utf-8")

        data = json.loads(body)
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return _error_response("Missing 'prompt' in request body", 400, allowed)

        # Get API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return _error_response("ANTHROPIC_API_KEY not configured", 500, allowed)

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = """You are MARVIN, a takeoff section generator for a landscape maintenance estimating tool.

Given a user description, generate a section configuration as JSON. There are 3 section types:

1. "split" — divides a total into sub-rows by percentage. Example: lawn split by mower type.
   Config: { "type": "split", "label": "Section Name", "unit": "SF", "rows": ["Row 1", "Row 2", "Row 3"] }

2. "value" — a single input value. Example: number of palm trees.
   Config: { "type": "value", "label": "Section Name", "unit": "EA" }

3. "calc" — input × constant = output. Example: flowers ÷ 18 = flats.
   Config: { "type": "calc", "label": "Section Name", "inputLabel": "Input Name", "inputUnit": "EA", "constant": 18, "constantLabel": "per flat", "outputLabel": "Output Name", "outputUnit": "flats" }

Available units: SF, LF, CY, EA, bags, flats, gallons, hours, lbs, tons, pallets

Return ONLY a JSON object with a "sections" array containing one or more section configs. No markdown, no explanation."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = message.content[0].text.strip()

        # Try to parse as JSON
        try:
            result_json = json.loads(result_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                result_json = json.loads(json_match.group())
            else:
                result_json = {"error": "Could not parse AI response", "raw": result_text}

        resp_headers = cors_headers(allowed)
        resp_headers["Content-Type"] = "application/json"
        return {
            "statusCode": 200,
            "headers": resp_headers,
            "body": json.dumps({"success": True, "result": result_json}),
        }

    except Exception as e:
        return _error_response(f"MARVIN error: {e}", 500, allowed)
