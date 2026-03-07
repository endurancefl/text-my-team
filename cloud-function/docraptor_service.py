"""DocRaptor PDF generation service.

Renders Jinja2 HTML/CSS templates and sends them to DocRaptor (PrinceXML)
for PDF generation. Replaces WeasyPrint (pdf_generator.py) and
ReportLab (main.py).

All CSS is inlined into <style> tags (DocRaptor can't access file:// URLs).
All fonts are embedded as base64 data URIs.
All images are embedded as base64 data URIs.
"""
import base64
import io
import os
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

import docraptor
from jinja2 import Environment, FileSystemLoader


# ── Paths ────────────────────────────────────────────────────────────────────

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
STYLES_DIR = os.path.join(TEMPLATE_DIR, "styles")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

FOOTER_TEXT = "(407) 579-4403  |  endurancefl.com  |  Orlando, FL"


# ── DocRaptor Client ─────────────────────────────────────────────────────────

_doc_api = docraptor.DocApi()
_doc_api.api_client.configuration.username = os.environ.get("DOCRAPTOR_API_KEY", "YOUR_API_KEY_HERE")


# ── CORS & Utilities (previously in main.py) ─────────────────────────────────

ALLOWED_ORIGINS = [
    "https://endurancefl.github.io",
    "https://enduranceservices.github.io",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


def cors_headers(origin="*"):
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "3600",
    }


def allowed_origin_from_header(origin_header):
    """Check if origin is allowed. Returns the origin or the default."""
    if origin_header in ALLOWED_ORIGINS:
        return origin_header
    if not origin_header or origin_header == "null":
        return "*"
    return ALLOWED_ORIGINS[0]


def parse_photo_buffers(raw_files):
    """Convert a list of raw file bytes into JPEG BytesIO buffers."""
    from PIL import Image

    buffers = []
    for file_bytes in raw_files:
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        buffers.append(buf)
    return buffers


# ── Formatting Helpers ───────────────────────────────────────────────────────

def _format_signed_at(iso_str):
    """Convert ISO timestamp to 'Feb 26, 2026 at 9:35 PM Eastern'."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        eastern = timezone(timedelta(hours=-5))
        dt_eastern = dt.astimezone(eastern)
        return dt_eastern.strftime("%b %-d, %Y at %-I:%M %p") + " Eastern"
    except Exception:
        return iso_str


def _format_date(iso_str):
    """Convert ISO date string (2026-04-01) to '1 APR 2026'."""
    if not iso_str:
        return ""
    try:
        dt = datetime.strptime(str(iso_str).strip(), "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%b').upper()} {dt.year}"
    except Exception:
        return str(iso_str)


def _format_month(iso_str):
    """Convert ISO date string (2026-02-01) to 'FEB 2026'."""
    if not iso_str:
        return ""
    try:
        dt = datetime.strptime(str(iso_str).strip(), "%Y-%m-%d")
        return f"{dt.strftime('%b').upper()} {dt.year}"
    except Exception:
        return str(iso_str)


# ── Template Setup ───────────────────────────────────────────────────────────

_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
_env.filters["format_date"] = _format_date
_env.filters["format_month"] = _format_month


# Cache for CSS file contents and font base64 (read once per cold start)
_css_cache = {}
_font_b64_cache = None


def _css_content(filename):
    """Read a CSS file from the styles directory and return its content.

    Used by templates: {{ css_content('common.css') }}
    Results are cached per Lambda cold start.
    """
    if filename not in _css_cache:
        path = os.path.join(STYLES_DIR, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                _css_cache[filename] = f.read()
        else:
            _css_cache[filename] = ""
    return _css_cache[filename]


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


def _get_font_b64():
    """Load Dancing Script font as base64 (cached)."""
    global _font_b64_cache
    if _font_b64_cache is None:
        font_path = os.path.join(ASSETS_DIR, "fonts", "DancingScript-Bold.ttf")
        if os.path.exists(font_path):
            with open(font_path, "rb") as f:
                _font_b64_cache = base64.b64encode(f.read()).decode("utf-8")
        else:
            _font_b64_cache = ""
    return _font_b64_cache


def _embed_fonts(html):
    """Replace file:// font URLs with base64 data URIs.

    DocRaptor/PrinceXML can't access local file paths — fonts must be
    embedded as base64 data URIs in the CSS.
    """
    font_b64 = _get_font_b64()
    if not font_b64:
        return html
    data_uri = f"url('data:font/ttf;base64,{font_b64}')"
    # Replace the file:// path used in contract.css
    html = html.replace(
        "url('file:///var/task/assets/fonts/DancingScript-Bold.ttf')",
        data_uri,
    )
    # Also handle double-quote variant
    html = html.replace(
        'url("file:///var/task/assets/fonts/DancingScript-Bold.ttf")',
        data_uri,
    )
    return html


# ── PDF Rendering ────────────────────────────────────────────────────────────

def _render_html(template_name, context):
    """Render a Jinja2 template to an HTML string with all CSS inlined."""
    context["footer_text"] = FOOTER_TEXT
    context["css_content"] = _css_content
    if "logo_uri" not in context:
        context["logo_uri"] = _logo_data_uri()

    template = _env.get_template(template_name)
    html_string = template.render(**context)

    # Embed fonts as base64 data URIs
    html_string = _embed_fonts(html_string)

    return html_string


def _render_pdf(template_name, context, test=False):
    """Render a Jinja2 template and send to DocRaptor for PDF generation.

    Returns: bytes (raw PDF data)
    """
    html_content = _render_html(template_name, context)

    response = _doc_api.create_doc({
        "test": test,
        "document_type": "pdf",
        "document_content": html_content,
        "prince_options": {
            "media": "print",
        },
    })

    return bytes(response)


# ── Contract Helpers (ported from main.py) ───────────────────────────────────

RESIDENTIAL_SERVICE_DESCRIPTIONS = {
    "Weekly Grounds Maintenance": [
        ("Weekly Maintenance", [
            "Endurance Services will perform weekly maintenance visits to your property. If weather prevents a scheduled visit, the service will be rescheduled as soon as possible."
        ]),
        ("Trash and Debris Removal", [
            "Light trash and debris will be collected and removed during each visit, limited to items that can be easily picked up by hand or with small handheld tools."
        ]),
        ("Mowing", [
            "Grass areas will be mowed on a regular schedule, with frequency adjusted seasonally based on weather, ground conditions, and grass type.",
            "Mowing techniques including rotating patterns will be used to maintain a smooth, even surface and prevent damage to the lawn. All clippings and debris will be removed."
        ]),
        ("Edging", [
            "Mechanical edging will be performed along walkways, driveways, and landscape beds during each mowing visit. All debris will be removed."
        ]),
        ("String Trimming", [
            "String trimming will be performed during each mowing visit around fences, trees, and areas the mower cannot reach. All debris will be removed."
        ]),
        ("Blowing", [
            "All walkways, driveways, patios, and landscape areas will be blown clean during each visit. Leaves will be bagged and hauled away on an as needed basis."
        ]),
        ("Weeding", [
            "Routine weed control will be performed in landscape beds on an as needed basis."
        ]),
        ("Pruning and Hedge Trimming", [
            "Shrubs, hedges, and trees 10 feet or under will be pruned and shaped on a regular basis to maintain a neat appearance.",
            "Pruning of trees and hedges over 10 feet will require a separate estimate and customer approval."
        ]),
        ("Irrigation", [
            "Endurance Services will inspect your irrigation system 12 times per year and perform routine repairs on a Time and Materials basis. Client authorizes Endurance Services to complete repairs under $100. Repairs over $100 will require client approval."
        ]),
    ],
}


def _get_terms_clauses(metadata):
    """Return the 12 standard contract clauses with template variables filled in."""
    duration = metadata.get("duration", 12)
    start = metadata.get("startDate", "___")
    end = metadata.get("endDate", "___")
    terms = metadata.get("paymentTerms", "Net 30")
    increase = metadata.get("priceIncrease", 0)

    return [
        ("Term", f"The term of this Landscape Management Agreement will be {duration} months. Start Date: {start} and End Date: {end}."),
        ("Regular Monthly Maintenance Billing", "The customer will be invoiced once per month for the Weekly Property Maintenance."),
        ("Enhancement Work Billing", "Additional work not outlined in this Landscape Management Agreement will be subject to customer approval and invoiced separately."),
        ("Invoice Terms", f"Payment terms will be {terms} on all invoices."),
        ("Sales Tax", "All state and local sales tax will be applied to invoices where required by law."),
        ("Background Check", "Endurance Services will conduct background checks on all team members prior to working on the client\u2019s property."),
        ("Uniform", "Endurance Services team members will wear the company uniform: work boots, pants, and Endurance Services branded shirts and hats."),
        ("Insurance", "Endurance Services will maintain Workers Compensation and General Liability Insurance."),
        ("Termination", "Either party may terminate this contract for cause, by providing thirty (30) days\u2019 prior written notice stating the reason for termination."),
        ("Contract Renewal", "This contract will automatically renew unless either party provides written notice of non-renewal at least sixty (60) days prior to the expiration date."),
        ("Price Increase", f"Upon contract renewal, a cost-of-living adjustment will be applied to the new contract. The adjustment will be equal to the greater of {increase} percent ({increase}%) or the percentage increase in the \u201cCPI-U, US CITY AVERAGE, ALL ITEMS\u201d as measured by the U.S. Bureau of Labor Statistics (https://www.bls.gov/cpi/) for the most recent twelve-month period."),
        ("Named Tropical Event Policy", [
            "A Named Tropical Event is defined as a tropical storm or hurricane given a name by the National Hurricane Center (www.nhc.noaa.gov).",
            "Once work can be performed safely, property cleanup resulting from a Named Tropical Event will be billed on a Time and Materials basis at $65 per hour in addition to the monthly contract price.",
        ]),
    ]


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


# ── Public API ───────────────────────────────────────────────────────────────
# Same signatures as pdf_generator.py — all return (pdf_bytes, filename)

def generate_standard_report(metadata, photo_buffers, test=False):
    """Generate standard site recommendation report.

    Args:
        metadata: dict with address, inspector, date, photos
        photo_buffers: list of BytesIO buffers (JPEG images)
        test: if True, generates free watermarked PDF

    Returns:
        tuple: (pdf_bytes, filename)
    """
    address = metadata.get("address", "Unknown Property")
    inspector = metadata.get("inspector", "")
    report_date = metadata.get("date", "")
    photo_metas = metadata.get("photos", [])

    # Build flat photo list
    all_photos = []
    for i, pmeta in enumerate(photo_metas):
        buf = photo_buffers[i] if i < len(photo_buffers) else None
        all_photos.append({
            "num": i + 1,
            "note": (pmeta.get("note", "") or "")[:200],
            "category": pmeta.get("category") or "Uncategorized",
            "data_uri": _buffer_to_data_uri(buf),
        })

    # Build explicit table rows, paired into 2-column rows
    # Page 1: 4 photos (2 rows), subsequent: 6 photos (3 rows)
    FIRST_PAGE = 4
    LATER_PAGE = 6

    def make_rows(photos):
        rows = []
        for j in range(0, len(photos), 2):
            left = photos[j]
            right = photos[j + 1] if j + 1 < len(photos) else None
            rows.append({"left": left, "right": right})
        return rows

    pages = []
    if all_photos:
        pages.append({"rows": make_rows(all_photos[:FIRST_PAGE]), "first": True})
        remaining = all_photos[FIRST_PAGE:]
        while remaining:
            pages.append({"rows": make_rows(remaining[:LATER_PAGE]), "first": False})
            remaining = remaining[LATER_PAGE:]

    context = {
        "address": address,
        "inspector": inspector,
        "date": report_date,
        "logo_uri": _logo_data_uri(),
        "pages": pages,
    }

    pdf_bytes = _render_pdf("site_report.html", context, test=test)
    return (pdf_bytes, "site-report.pdf")


def generate_before_after_report(metadata, before_buffers, after_buffers, test=False):
    """Generate before/after comparison report.

    Args:
        metadata: dict with address, inspector, date, photos
        before_buffers: list of BytesIO buffers (before photos)
        after_buffers: list of BytesIO buffers (after photos)
        test: if True, generates free watermarked PDF

    Returns:
        tuple: (pdf_bytes, filename)
    """
    address = metadata.get("address", "Unknown Property")
    inspector = metadata.get("inspector", "")
    report_date = metadata.get("date", "")
    photo_metas = metadata.get("photos", [])

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

    pdf_bytes = _render_pdf("before_after.html", context, test=test)
    return (pdf_bytes, "before-after-report.pdf")


def generate_contract_pdf(metadata, service_map_buffer=None, test=False):
    """Generate a contract PDF — residential or commercial.

    Args:
        metadata: dict with contract details, services, customer info
        service_map_buffer: optional BytesIO buffer (commercial only)
        test: if True, generates free watermarked PDF

    Returns:
        tuple: (pdf_bytes, filename)
    """
    prop_type = metadata.get("propertyType", "residential").lower()
    if prop_type == "commercial":
        return _generate_commercial_contract(metadata, service_map_buffer, test=test)
    else:
        return _generate_residential_contract(metadata, test=test)


def _generate_residential_contract(metadata, test=False):
    """Generate a 3-page residential contract PDF."""
    services = metadata.get("services", [])
    annual_total = sum(s.get("annualTotal", 0) for s in services)

    primary_svc = services[0].get("name", "Landscape Maintenance") if services else "Landscape Maintenance"

    description_html = _build_description_html(services)

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

    context = {
        "company_name": metadata.get("companyName", "Endurance Services"),
        "logo_uri": _logo_data_uri(),
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
        "signed_name": metadata.get("signedName", ""),
        "signed_at": _format_signed_at(metadata.get("signedAt", "")),
        "company_signer": metadata.get("companySigner", ""),
        "company_signed_at": _format_signed_at(metadata.get("companySignedAt", "")),
    }

    pdf_bytes = _render_pdf("contract_residential.html", context, test=test)
    contract_id_clean = metadata.get("contractId", "contract").replace(" ", "-")
    suffix = "-signed" if metadata.get("signedName") else ""
    return (pdf_bytes, f"{contract_id_clean}-contract{suffix}.pdf")


def _generate_commercial_contract(metadata, service_map_buffer=None, test=False):
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

    fixed_services = [s for s in services if s.get("billingTier", "fixed") == "fixed"]
    billed_services = [s for s in services if s.get("billingTier") == "billed"]
    recommended_services = [s for s in services if s.get("billingTier") == "recommended"]

    fixed_total = sum(s.get("annualTotal", 0) for s in fixed_services)
    billed_total = sum(s.get("annualTotal", 0) for s in billed_services)
    recommended_total = sum(s.get("annualTotal", 0) for s in recommended_services)

    info_items = [
        ("Date:", generated_date),
        ("Proposal #:", contract_id),
        ("Property:", prop_addr[:35] if prop_addr else ""),
        ("", prop_addr[35:70] if len(prop_addr) > 35 else ""),
        ("Billing Contact:", customer),
        ("Company:", customer_company),
        ("Billing Address:", billing_addr[:35] if billing_addr else ""),
    ]

    description_html = _build_description_html(services)
    has_rich_desc = any(
        s.get("description", "") not in ("", "<p><br></p>", "<p></p>")
        for s in services
    )

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
        "signed_name": metadata.get("signedName", ""),
        "signed_at": _format_signed_at(metadata.get("signedAt", "")),
        "company_signer": metadata.get("companySigner", ""),
        "company_signed_at": _format_signed_at(metadata.get("companySignedAt", "")),
    }

    pdf_bytes = _render_pdf("contract_commercial.html", context, test=test)
    contract_id_clean = contract_id.replace(" ", "-") if contract_id else "contract"
    suffix = "-signed" if metadata.get("signedName") else ""
    return (pdf_bytes, f"{contract_id_clean}-contract{suffix}.pdf")


def generate_invoice_pdf(metadata, test=False):
    """Generate an invoice PDF from metadata.

    Args:
        metadata: dict with invoice details, line items, totals
        test: if True, generates free watermarked PDF

    Returns:
        tuple: (pdf_bytes, filename)
    """
    line_items = metadata.get("lineItems", [])

    context = {
        "logo_data_uri": _logo_data_uri(),
        "invoice_id": metadata.get("invoiceId", ""),
        "contact_name": metadata.get("contactName", ""),
        "contact_email": metadata.get("contactEmail", ""),
        "billing_address": metadata.get("billingAddress", ""),
        "property_address": metadata.get("propertyAddress", ""),
        "invoice_date": metadata.get("invoiceDate", ""),
        "due_date": metadata.get("dueDate", ""),
        "billing_period_start": metadata.get("billingPeriodStart", ""),
        "billing_period_end": metadata.get("billingPeriodEnd", ""),
        "payment_terms": metadata.get("paymentTerms", "Net 30"),
        "subtotal": float(metadata.get("subtotal", 0)),
        "tax_rate": float(metadata.get("taxRate", 0)),
        "tax_amount": float(metadata.get("taxAmount", 0)),
        "total": float(metadata.get("total", 0)),
        "line_items": line_items,
        "pay_url": metadata.get("payUrl", ""),
    }

    pdf_bytes = _render_pdf("invoice.html", context, test=test)
    inv_id = metadata.get("invoiceId", "invoice").replace(" ", "-")
    return (pdf_bytes, f"{inv_id}.pdf")
