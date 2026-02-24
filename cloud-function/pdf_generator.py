"""WeasyPrint-based PDF generation engine.

Renders Jinja2 HTML/CSS templates into PDFs using WeasyPrint.
All images are embedded as base64 data URIs for Lambda compatibility.
"""
import base64
import io
import os
from collections import OrderedDict
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# Re-export CORS helpers from main.py so lambda_function.py can import from either module
from main import (
    ALLOWED_ORIGINS,
    allowed_origin_from_header,
    cors_headers,
    parse_photo_buffers,
    RESIDENTIAL_SERVICE_DESCRIPTIONS,
    _get_terms_clauses,
    _escape,
)

# ── Template Setup ────────────────────────────────────
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
STYLES_DIR = os.path.join(TEMPLATE_DIR, "styles")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

FOOTER_TEXT = "(407) 579-4403  |  endurancefl.com  |  Orlando, FL"

_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def _css_url(filename):
    """Return a file:// URL for a CSS file in the styles directory."""
    path = os.path.join(STYLES_DIR, filename)
    return f"file://{path}"


def _logo_data_uri():
    """Load logo.png as a base64 data URI."""
    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{data}"
    return ""


def _buffer_to_data_uri(buf, fmt="jpeg"):
    """Convert a BytesIO image buffer to a base64 data URI."""
    if not buf:
        return ""
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode("utf-8")
    mime = "image/jpeg" if fmt == "jpeg" else f"image/{fmt}"
    return f"data:{mime};base64,{data}"


def _render_pdf(template_name, context):
    """Render a Jinja2 template to PDF bytes via WeasyPrint."""
    # Add global template helpers
    context["footer_text"] = FOOTER_TEXT
    context["css_url"] = _css_url

    template = _env.get_template(template_name)
    html_string = template.render(**context)

    # Use base_url so relative CSS file:// URLs resolve correctly
    html = HTML(string=html_string, base_url=TEMPLATE_DIR)
    pdf_bytes = html.write_pdf()
    return pdf_bytes


def render_html(template_name, context):
    """Render a Jinja2 template to an HTML string (for browser preview)."""
    context["footer_text"] = FOOTER_TEXT
    context["css_url"] = _css_url

    template = _env.get_template(template_name)
    return template.render(**context)


def _resolve_template_vars(html, metadata):
    """Replace {placeholder} tokens in T&C HTML with actual values."""
    if not html:
        return html
    replacements = {
        "{duration}": str(metadata.get("duration", 12)),
        "{startDate}": str(metadata.get("startDate", "___")),
        "{endDate}": str(metadata.get("endDate", "___")),
        "{paymentTerms}": str(metadata.get("paymentTerms", "Net 30")),
        "{priceIncrease}": str(metadata.get("priceIncrease", 0)),
    }
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html


def _build_description_html(services):
    """Build rich text HTML for Description of Services from per-service descriptions."""
    parts = []
    for svc in services:
        name = svc.get("name", "Service")
        desc = svc.get("description", "")
        if desc and desc not in ("<p><br></p>", "<p></p>", ""):
            parts.append(f'<div class="svc-desc-block"><h3>{name}</h3>{desc}</div>')
        else:
            parts.append(f'<div class="svc-desc-block"><h3>{name}</h3><p>Service included as specified in the agreement.</p></div>')
    return "\n".join(parts)


# ── Public API (same signatures as main.py) ───────────

def generate_standard_report(metadata, photo_buffers):
    """Generate standard site recommendation report via WeasyPrint.

    Args:
        metadata: dict with address, inspector, date, photos (list of {category, note})
        photo_buffers: list of BytesIO buffers (JPEG images)

    Returns:
        tuple: (pdf_bytes, filename)
    """
    address = metadata.get("address", "Unknown Property")
    inspector = metadata.get("inspector", "")
    report_date = metadata.get("date", "")
    photo_metas = metadata.get("photos", [])

    # Group photos by category (preserve order of first appearance)
    categories = OrderedDict()
    photo_num = 1
    for i, pmeta in enumerate(photo_metas):
        cat = pmeta.get("category") or "Uncategorized"
        if cat not in categories:
            categories[cat] = []
        buf = photo_buffers[i] if i < len(photo_buffers) else None
        categories[cat].append({
            "num": photo_num,
            "note": (pmeta.get("note", "") or "")[:150],
            "data_uri": _buffer_to_data_uri(buf),
        })
        photo_num += 1

    context = {
        "address": address,
        "inspector": inspector,
        "date": report_date,
        "logo_uri": _logo_data_uri(),
        "categories": categories,
    }

    pdf_bytes = _render_pdf("site_report.html", context)
    return (pdf_bytes, "site-report.pdf")


def generate_before_after_report(metadata, before_buffers, after_buffers):
    """Generate before/after comparison report via WeasyPrint.

    Args:
        metadata: dict with address, inspector, date, originalReport, photos
        before_buffers: list of BytesIO buffers (before photos)
        after_buffers: list of BytesIO buffers (after photos)

    Returns:
        tuple: (pdf_bytes, filename)
    """
    address = metadata.get("address", "Unknown Property")
    inspector = metadata.get("inspector", "")
    report_date = metadata.get("date", "")
    photo_metas = metadata.get("photos", [])

    # Group by category
    categories = OrderedDict()
    for i, pmeta in enumerate(photo_metas):
        cat = pmeta.get("beforeCategory", "") or "Uncategorized"
        if cat not in categories:
            categories[cat] = []

        before_buf = before_buffers[i] if i < len(before_buffers) else None
        after_buf = after_buffers[i] if i < len(after_buffers) else None

        categories[cat].append({
            "num": len(categories[cat]) + 1,
            "before_uri": _buffer_to_data_uri(before_buf),
            "after_uri": _buffer_to_data_uri(after_buf),
            "before_note": (pmeta.get("beforeNote", "") or "")[:150],
            "after_note": (pmeta.get("afterNote", "") or "")[:150],
        })

    context = {
        "address": address,
        "inspector": inspector,
        "date": report_date,
        "logo_uri": _logo_data_uri(),
        "categories": categories,
    }

    pdf_bytes = _render_pdf("before_after.html", context)
    return (pdf_bytes, "before-after-report.pdf")


def generate_contract_pdf(metadata, service_map_buffer=None):
    """Generate a contract PDF — residential or commercial.

    Args:
        metadata: dict with contract details, services, customer info, etc.
        service_map_buffer: optional BytesIO buffer of service map image (commercial only)

    Returns:
        tuple: (pdf_bytes, filename)
    """
    prop_type = metadata.get("propertyType", "residential").lower()
    if prop_type == "commercial":
        return _generate_commercial_contract(metadata, service_map_buffer)
    else:
        return _generate_residential_contract(metadata)


def _generate_residential_contract(metadata):
    """Generate a 3-page residential contract PDF."""
    services = metadata.get("services", [])
    annual_total = sum(s.get("annualTotal", 0) for s in services)

    # Get primary service name and descriptions
    primary_svc = services[0].get("name", "Landscape Maintenance") if services else "Landscape Maintenance"

    # Build rich text description HTML from per-service descriptions
    description_html = _build_description_html(services)

    # Fallback to hardcoded descriptions if no per-service descriptions exist
    has_rich_desc = any(
        s.get("description", "") not in ("", "<p><br></p>", "<p></p>")
        for s in services
    )
    desc_items = []
    if not has_rich_desc:
        desc_items = RESIDENTIAL_SERVICE_DESCRIPTIONS.get(primary_svc, [])
        if not desc_items:
            desc_items = [
                (svc.get("name", ""), [svc.get("description", "Service included as specified.")])
                for svc in services
            ]

    # Handle custom Terms & Conditions HTML
    custom_terms_raw = metadata.get("termsAndConditionsHtml")
    custom_terms_html = None
    if custom_terms_raw:
        custom_terms_html = _resolve_template_vars(custom_terms_raw, metadata)

    # Fallback clause list for non-custom T&C
    clauses = _get_terms_clauses(metadata)
    clause_list = []
    for title, text in clauses:
        if isinstance(text, list):
            clause_list.append({"title": title, "text": None, "sub_items": text})
        else:
            clause_list.append({"title": title, "text": text, "sub_items": None})

    context = {
        "company_name": metadata.get("companyName", "Endurance Services"),
        "contract_id": metadata.get("contractId", ""),
        "generated_date": metadata.get("generatedDate", ""),
        "monthly_payment": metadata.get("monthlyPayment", 0),
        "contract_value": metadata.get("contractValue", 0),
        "customer_name": metadata.get("customerName", ""),
        "customer_company": metadata.get("customerCompany", ""),
        "billing_address": metadata.get("billingAddress", ""),
        "property_address": metadata.get("propertyAddress", ""),
        "services": services,
        "annual_total": annual_total,
        "primary_service_name": primary_svc,
        "description_html": description_html,
        "has_rich_desc": has_rich_desc,
        "service_descriptions": desc_items,
        "effective_date": metadata.get("effectiveDate", metadata.get("startDate", "")),
        "custom_terms_html": custom_terms_html,
        "clauses": clause_list,
    }

    pdf_bytes = _render_pdf("contract_residential.html", context)
    contract_id_clean = metadata.get("contractId", "contract").replace(" ", "-")
    return (pdf_bytes, f"{contract_id_clean}-contract.pdf")


def _generate_commercial_contract(metadata, service_map_buffer=None):
    """Generate a 5-6 page commercial contract PDF."""
    services = metadata.get("services", [])
    start_date = metadata.get("startDate", "")
    end_date = metadata.get("endDate", "")
    prop_addr = metadata.get("propertyAddress", "")
    contract_id = metadata.get("contractId", "")
    customer = metadata.get("customerName", "")
    customer_company = metadata.get("customerCompany", "")
    billing_addr = metadata.get("billingAddress", "")
    generated_date = metadata.get("generatedDate", "")

    # Parse dates for title
    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d")
        ed = datetime.strptime(end_date, "%Y-%m-%d")
        start_month = sd.strftime("%B")
        start_year = sd.strftime("%Y")
        end_month = ed.strftime("%B")
        end_year = ed.strftime("%Y")
        fy_year = sd.strftime("%Y")
    except Exception:
        start_month = start_year = end_month = end_year = fy_year = ""

    prop_name = prop_addr.split(",")[0] if prop_addr else "Property"

    # Split services by billing tier
    fixed_services = [s for s in services if s.get("billingTier", "fixed") == "fixed"]
    billed_services = [s for s in services if s.get("billingTier") == "billed"]
    recommended_services = [s for s in services if s.get("billingTier") == "recommended"]

    fixed_total = sum(s.get("annualTotal", 0) for s in fixed_services)
    billed_total = sum(s.get("annualTotal", 0) for s in billed_services)
    recommended_total = sum(s.get("annualTotal", 0) for s in recommended_services)

    # Info box items
    info_items = [
        ("Date:", generated_date),
        ("Proposal #:", contract_id),
        ("Property:", prop_addr[:35] if prop_addr else ""),
        ("", prop_addr[35:70] if len(prop_addr) > 35 else ""),
        ("Billing Contact:", customer),
        ("Company:", customer_company),
        ("Billing Address:", billing_addr[:35] if billing_addr else ""),
    ]

    # Build rich text description HTML from per-service descriptions
    description_html = _build_description_html(services)
    has_rich_desc = any(
        s.get("description", "") not in ("", "<p><br></p>", "<p></p>")
        for s in services
    )

    # Handle custom Terms & Conditions HTML
    custom_terms_raw = metadata.get("termsAndConditionsHtml")
    custom_terms_html = None
    if custom_terms_raw:
        custom_terms_html = _resolve_template_vars(custom_terms_raw, metadata)

    clauses = _get_terms_clauses(metadata)
    clause_list = []
    for title, text in clauses:
        if isinstance(text, list):
            clause_list.append({"title": title, "text": None, "sub_items": text})
        else:
            clause_list.append({"title": title, "text": text, "sub_items": None})

    tier_groups = [
        ("Fixed Payment Services", fixed_services),
        ("Services Billed Separately", billed_services),
        ("Recommended Services", recommended_services),
    ]

    context = {
        "company_name": metadata.get("companyName", "Endurance Services"),
        "logo_uri": _logo_data_uri(),
        "info_items": info_items,
        "title_text": f"FY{fy_year} Landscape Maintenance Agreement",
        "subtitle_text": f"{prop_name} ({start_month} {start_year} - {end_month} {end_year})",
        "service_map_uri": _buffer_to_data_uri(service_map_buffer) if service_map_buffer else "",
        "fixed_services": fixed_services,
        "billed_services": billed_services,
        "recommended_services": recommended_services,
        "fixed_total": fixed_total,
        "billed_total": billed_total,
        "recommended_total": recommended_total,
        "payment_schedule": metadata.get("paymentSchedule", []),
        "tier_groups": tier_groups,
        "description_html": description_html,
        "has_rich_desc": has_rich_desc,
        "effective_date": metadata.get("effectiveDate", start_date),
        "custom_terms_html": custom_terms_html,
        "clauses": clause_list,
        "customer_name": customer,
        "customer_company": customer_company,
        "generated_date": generated_date,
        "contract_id": contract_id,
    }

    pdf_bytes = _render_pdf("contract_commercial.html", context)
    contract_id_clean = contract_id.replace(" ", "-") if contract_id else "contract"
    return (pdf_bytes, f"{contract_id_clean}-contract.pdf")
