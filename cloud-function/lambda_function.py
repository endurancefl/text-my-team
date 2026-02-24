"""AWS Lambda handler for PDF generation.

Receives multipart/form-data via API Gateway, parses the request,
generates PDFs, and returns base64-encoded PDF.

Supports dual rendering engines during migration:
  - "reportlab" (default fallback) — original main.py engine
  - "weasyprint" — new HTML/CSS template engine (pdf_generator.py)

Set "renderer": "weasyprint" in the metadata JSON to use the new engine.
"""
import base64
import io
import json
import re

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
except ImportError:
    WEASYPRINT_AVAILABLE = False

# Default renderer — flip to "weasyprint" once all types are validated
DEFAULT_RENDERER = "weasyprint"


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

    try:
        # Get the raw body
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)
        if is_base64:
            raw_body = base64.b64decode(body)
        else:
            raw_body = body.encode("utf-8") if isinstance(body, str) else body

        # Get content type to find multipart boundary
        content_type = headers.get("content-type", headers.get("Content-Type", ""))
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
            # Invoice PDF — WeasyPrint only (no ReportLab fallback)
            if not WEASYPRINT_AVAILABLE:
                return _error_response("WeasyPrint not available for invoice PDF", 500, allowed)
            pdf_bytes, filename = wp_generate_invoice_pdf(metadata)

        elif report_type == "contract":
            # Parse optional service map photo (commercial only)
            service_map_files = parts.get("files", {}).get("service_map", [])
            service_map_buffer = None
            if service_map_files:
                buffers = parse_photo_buffers(service_map_files)
                if buffers:
                    service_map_buffer = buffers[0]

            gen = wp_generate_contract_pdf if use_wp else rl_generate_contract_pdf
            pdf_bytes, filename = gen(metadata, service_map_buffer)

        elif report_type == "before_after":
            # Parse before and after photo files
            before_files = parts.get("files", {}).get("before_photos", [])
            after_files = parts.get("files", {}).get("after_photos", [])

            before_buffers = parse_photo_buffers(before_files)
            after_buffers = parse_photo_buffers(after_files)

            gen = wp_generate_before_after_report if use_wp else rl_generate_before_after_report
            pdf_bytes, filename = gen(metadata, before_buffers, after_buffers)
        else:
            # Parse photo files
            photo_files = parts.get("files", {}).get("photos", [])
            photo_buffers = parse_photo_buffers(photo_files)

            gen = wp_generate_standard_report if use_wp else rl_generate_standard_report
            pdf_bytes, filename = gen(metadata, photo_buffers)

        # Return base64-encoded PDF
        response_headers = cors_headers(allowed)
        response_headers["Content-Type"] = "application/pdf"
        response_headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return {
            "statusCode": 200,
            "headers": response_headers,
            "body": base64.b64encode(pdf_bytes).decode("utf-8"),
            "isBase64Encoded": True,
        }

    except json.JSONDecodeError as e:
        return _error_response(f"Invalid metadata JSON: {e}", 400, allowed)
    except Exception as e:
        return _error_response(f"Internal error: {e}", 500, allowed)


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
