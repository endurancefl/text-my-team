import io
import json
import os
from collections import OrderedDict
from datetime import datetime, timedelta, timezone


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

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, KeepTogether, Flowable, PageBreak,
)
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image

# Register Dancing Script cursive font for typed e-signatures
_DANCING_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "DancingScript-Bold.ttf")
if os.path.exists(_DANCING_SCRIPT_PATH):
    pdfmetrics.registerFont(TTFont("DancingScript", _DANCING_SCRIPT_PATH))
    _HAS_DANCING_SCRIPT = True
else:
    _HAS_DANCING_SCRIPT = False


ALLOWED_ORIGINS = [
    "https://endurancefl.github.io",
    "https://enduranceservices.github.io",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

GREEN = HexColor("#3A5F4B")
GRAY_HEADER = HexColor("#666666")
DARK = HexColor("#1A2E24")
LIGHT_GRAY = HexColor("#CCCCCC")
FOOTER_TEXT = "(407) 579-4403  |  endurancefl.com  |  Orlando, FL"


def cors_headers(origin="*"):
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "3600",
    }


def cors_preflight(origin):
    return ("", 204, cors_headers(origin))


def allowed_origin_from_header(origin_header):
    """Check if origin is allowed. Returns the origin or the default."""
    if origin_header in ALLOWED_ORIGINS:
        return origin_header
    # file:// pages send Origin: null — allow for local testing
    if not origin_header or origin_header == "null":
        return "*"
    return ALLOWED_ORIGINS[0]


# ── Constants ──────────────────────────────────────
NOTE_CHAR_LIMIT = 150  # Max characters for photo notes
NOTE_BOX_HEIGHT = 36   # Fixed height for note boxes (fits ~2-3 lines)

# ── Styles ──────────────────────────────────────────

NOTE_STYLE = ParagraphStyle(
    "NoteStyle",
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=DARK,
    leftIndent=4,
    rightIndent=4,
    bulletIndent=0,
    spaceBefore=2,
    spaceAfter=2,
)

TITLE_STYLE = ParagraphStyle(
    "TitleStyle",
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    textColor=DARK,
)

COL_HEADER_STYLE = ParagraphStyle(
    "ColHeader",
    fontName="Helvetica-Bold",
    fontSize=10,
    textColor=DARK,
)

BA_LABEL_STYLE = ParagraphStyle(
    "BALabel",
    fontName="Helvetica-Bold",
    fontSize=11,
    textColor=white,
    alignment=TA_CENTER,
)

BA_NOTE_STYLE = ParagraphStyle(
    "BANote",
    fontName="Helvetica",
    fontSize=9,
    leading=11,
    textColor=DARK,
)


# ── Custom Flowables ────────────────────────────────

class CategoryHeader(Flowable):
    """Full-width gray bar with category name."""

    def __init__(self, category, width):
        super().__init__()
        self.category = category
        self.flowable_width = width
        self.height = 22

    def wrap(self, availWidth, availHeight):
        return self.flowable_width, self.height

    def draw(self):
        c = self.canv
        w = self.flowable_width
        h = self.height

        # Gray background bar
        c.setFillColor(GRAY_HEADER)
        c.rect(0, 0, w, h, fill=True, stroke=False)

        # Category name — white bold
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(8, 6, self.category)


class HRule(Flowable):
    """Thin horizontal rule."""

    def __init__(self, width, thickness=0.5, color=LIGHT_GRAY):
        super().__init__()
        self.flowable_width = width
        self.thickness = thickness
        self.color = color
        self.height = thickness + 4

    def wrap(self, availWidth, availHeight):
        return self.flowable_width, self.height

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 2, self.flowable_width, 2)


class PhotoBox(Flowable):
    """Photo with black border and fixed-height note box below."""

    def __init__(self, img_reader, width, img_height, note="", note_num=None):
        super().__init__()
        self.img_reader = img_reader
        self.flowable_width = width
        self.img_height = img_height
        self.note = note[:NOTE_CHAR_LIMIT] if note else ""
        self.note_num = note_num
        self.height = img_height + NOTE_BOX_HEIGHT

    def wrap(self, availWidth, availHeight):
        return self.flowable_width, self.height

    def draw(self):
        c = self.canv
        w = self.flowable_width
        img_h = self.img_height
        note_h = NOTE_BOX_HEIGHT

        # Draw photo
        if self.img_reader:
            try:
                c.drawImage(
                    self.img_reader, 0, note_h, width=w, height=img_h,
                    preserveAspectRatio=True, anchor='c'
                )
            except:
                pass

        # Black border around photo
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.rect(0, note_h, w, img_h, fill=False, stroke=True)

        # Note box below (shares top border with photo)
        c.rect(0, 0, w, note_h, fill=False, stroke=True)

        # Draw note text
        if self.note:
            c.setFillColor(DARK)
            c.setFont("Helvetica", 8)
            # Add number prefix if provided
            text = f"{self.note_num}. {self.note}" if self.note_num else self.note
            # Simple text wrapping
            max_chars = int((w - 8) / 4)  # Approximate chars per line
            y = note_h - 10
            words = text.split()
            line = ""
            for word in words:
                test = f"{line} {word}".strip()
                if len(test) <= max_chars:
                    line = test
                else:
                    if line:
                        c.drawString(4, y, line)
                        y -= 10
                        if y < 4:
                            break
                    line = word
            if line and y >= 4:
                c.drawString(4, y, line)


class BAPhotoBox(Flowable):
    """Before/After photo with colored label bar, black border, and note box."""

    def __init__(self, img_reader, width, img_height, label, label_color, note=""):
        super().__init__()
        self.img_reader = img_reader
        self.flowable_width = width
        self.img_height = img_height
        self.label = label
        self.label_color = label_color
        self.note = note[:NOTE_CHAR_LIMIT] if note else ""
        self.label_h = 18
        self.height = self.label_h + img_height + NOTE_BOX_HEIGHT

    def wrap(self, availWidth, availHeight):
        return self.flowable_width, self.height

    def draw(self):
        c = self.canv
        w = self.flowable_width
        img_h = self.img_height
        note_h = NOTE_BOX_HEIGHT
        label_h = self.label_h

        # Label bar at top
        c.setFillColor(self.label_color)
        c.rect(0, note_h + img_h, w, label_h, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        text_w = c.stringWidth(self.label, "Helvetica-Bold", 10)
        c.drawString((w - text_w) / 2, note_h + img_h + 5, self.label)

        # Draw photo
        if self.img_reader:
            try:
                c.drawImage(
                    self.img_reader, 0, note_h, width=w, height=img_h,
                    preserveAspectRatio=True, anchor='c'
                )
            except:
                pass

        # Black border around photo (below label)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.rect(0, note_h, w, img_h, fill=False, stroke=True)

        # Note box below
        c.rect(0, 0, w, note_h, fill=False, stroke=True)

        # Draw note text
        if self.note:
            c.setFillColor(DARK)
            c.setFont("Helvetica", 8)
            max_chars = int((w - 8) / 4)
            y = note_h - 10
            words = self.note.split()
            line = ""
            for word in words:
                test = f"{line} {word}".strip()
                if len(test) <= max_chars:
                    line = test
                else:
                    if line:
                        c.drawString(4, y, line)
                        y -= 10
                        if y < 4:
                            break
                    line = word
            if line and y >= 4:
                c.drawString(4, y, line)


# ── Numbered canvas for footer + page count ─────────

class NumberedCanvas(pdf_canvas.Canvas):
    """Two-pass canvas: renders all pages, then stamps 'Page X of Y' footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(self.__dict__.copy())
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for idx, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self.setFont("Helvetica", 8)
            self.setFillColor(HexColor("#666666"))
            self.drawString(36, 24, FOOTER_TEXT)
            self.drawRightString(
                letter[0] - 36, 24,
                f"Page {idx + 1} of {total}",
            )
            pdf_canvas.Canvas.showPage(self)
        pdf_canvas.Canvas.save(self)


# ── Photo buffer helpers ───────────────────────────

def parse_photo_buffers(raw_files):
    """Convert a list of raw file bytes into JPEG BytesIO buffers.

    Args:
        raw_files: list of bytes objects (raw image data)

    Returns:
        list of BytesIO buffers (JPEG, seeked to 0)
    """
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


# ── PDF Generation (platform-agnostic) ─────────────

def generate_standard_report(metadata, photo_buffers):
    """Generate standard site recommendation report.

    Args:
        metadata: dict with address, inspector, date, photos (list of {category, note})
        photo_buffers: list of BytesIO buffers (JPEG images, seeked to 0)

    Returns:
        tuple: (pdf_bytes, filename) where pdf_bytes is the raw PDF content
    """
    address = metadata.get("address", "Unknown Property")
    inspector = metadata.get("inspector", "")
    report_date = metadata.get("date", "")
    photo_metas = metadata.get("photos", [])

    # Group photos by category (preserve order of first appearance)
    categories = OrderedDict()
    for i, pmeta in enumerate(photo_metas):
        cat = pmeta.get("category") or "Uncategorized"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "index": i,
            "note": pmeta.get("note", ""),
            "buffer": photo_buffers[i] if i < len(photo_buffers) else None,
        })

    # Build PDF with direct canvas control
    buffer = io.BytesIO()
    page_w, page_h = letter  # 612 x 792

    # MASTER GRID COORDINATES (from spec)
    LEFT_MARGIN = 40
    RIGHT_MARGIN = 40
    TOP_MARGIN = 40
    BOTTOM_MARGIN = 50

    CONTENT_LEFT = LEFT_MARGIN  # 40
    CONTENT_RIGHT = page_w - RIGHT_MARGIN  # 572
    CONTENT_WIDTH = CONTENT_RIGHT - CONTENT_LEFT  # 532
    CONTENT_TOP = page_h - TOP_MARGIN  # 752
    CONTENT_BOTTOM = BOTTOM_MARGIN  # 50
    USABLE_HEIGHT = CONTENT_TOP - CONTENT_BOTTOM  # 702

    # Column grid
    GUTTER = 16
    COL_WIDTH = (CONTENT_WIDTH - GUTTER) / 2  # 258
    COL1_LEFT = CONTENT_LEFT  # 40
    COL2_LEFT = COL1_LEFT + COL_WIDTH + GUTTER  # 314

    # Row grid - calculate for 3 rows on normal page
    ROW_GAP = 14
    NOTE_H = 30
    ROWS_NORMAL = 3
    TOTAL_GAP = ROW_GAP * (ROWS_NORMAL - 1)  # 28
    ROW_HEIGHT = (USABLE_HEIGHT - TOTAL_GAP) / ROWS_NORMAL  # 224.67
    PHOTO_HEIGHT = ROW_HEIGHT - NOTE_H  # 194.67

    # Category header
    CAT_HEADER_HEIGHT = 24
    CAT_PADDING = 10

    c = pdf_canvas.Canvas(buffer, pagesize=letter)

    def draw_photo(x, y_top, photo_buf, note, note_num):
        """Draw a single photo with note box below. y_top is top of the row."""
        photo_bottom = y_top - PHOTO_HEIGHT
        note_bottom = photo_bottom - NOTE_H

        # Black border around photo area (drawn first as frame)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.rect(x, photo_bottom, COL_WIDTH, PHOTO_HEIGHT, fill=False, stroke=True)

        # Draw photo inside the frame
        if photo_buf:
            photo_buf.seek(0)
            try:
                c.drawImage(
                    ImageReader(photo_buf), x, photo_bottom,
                    width=COL_WIDTH, height=PHOTO_HEIGHT,
                    preserveAspectRatio=True, anchor='c'
                )
            except:
                pass

        # Note box - SAME x and width as photo for perfect alignment
        c.rect(x, note_bottom, COL_WIDTH, NOTE_H, fill=False, stroke=True)

        # Draw note text with number
        c.setFillColor(DARK)
        c.setFont("Helvetica", 8)
        max_chars = int((COL_WIDTH - 8) / 4)

        note_text = f"{note_num}. Note: {note[:NOTE_CHAR_LIMIT]}" if note else f"{note_num}."

        y = note_bottom + NOTE_H - 10
        words = note_text.split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if len(test) <= max_chars:
                line = test
            else:
                if line:
                    c.drawString(x + 4, y, line)
                    y -= 10
                    if y < note_bottom + 4:
                        break
                line = word
        if line and y >= note_bottom + 4:
            c.drawString(x + 4, y, line)

    def draw_section_header(y_top, category):
        """Draw a category header bar. Returns y position for first row."""
        header_bottom = y_top - CAT_HEADER_HEIGHT
        c.setFillColor(GRAY_HEADER)
        c.rect(CONTENT_LEFT, header_bottom, CONTENT_WIDTH, CAT_HEADER_HEIGHT, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(CONTENT_LEFT + 8, header_bottom + 7, category)
        # Normal gap between category bar and first row
        return header_bottom - ROW_GAP

    def draw_page1_header():
        """Draw the header on page 1. Returns y position for content."""
        y = CONTENT_TOP

        # Logo
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            try:
                c.drawImage(logo_path, CONTENT_LEFT, y - 42, width=180, height=42, preserveAspectRatio=True)
            except:
                pass

        # Info box on right - extra height for longer addresses
        info_x = CONTENT_RIGHT - 160
        info_y = y - 10
        box_h = 105  # Increased from 90 to fit longer addresses
        info_box_bottom = info_y - box_h  # Track where info box ends

        c.setStrokeColor(LIGHT_GRAY)
        c.setLineWidth(0.5)
        c.rect(info_x, info_box_bottom, 160, box_h, fill=False, stroke=True)

        row_h_info = 15
        info_row_y = info_y

        # Date row
        c.setFillColor(GRAY_HEADER)
        c.rect(info_x, info_row_y - row_h_info, 160, row_h_info, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, "Date:")
        info_row_y -= row_h_info
        c.setFillColor(DARK)
        c.setFont("Helvetica", 9)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, report_date)
        info_row_y -= row_h_info

        # Inspected By row
        c.setFillColor(GRAY_HEADER)
        c.rect(info_x, info_row_y - row_h_info, 160, row_h_info, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, "Inspected By:")
        info_row_y -= row_h_info
        c.setFillColor(DARK)
        c.setFont("Helvetica", 9)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, _escape(inspector)[:25])
        info_row_y -= row_h_info

        # Property row - allow 2 lines for address
        c.setFillColor(GRAY_HEADER)
        c.rect(info_x, info_row_y - row_h_info, 160, row_h_info, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, "Property:")
        info_row_y -= row_h_info

        # Address can span 2 lines
        c.setFillColor(DARK)
        c.setFont("Helvetica", 8)
        addr = _escape(address)
        if len(addr) > 28:
            # Split into 2 lines
            c.drawString(info_x + 6, info_row_y - row_h_info + 4, addr[:28])
            info_row_y -= row_h_info
            c.drawString(info_x + 6, info_row_y - row_h_info + 4, addr[28:56])
        else:
            c.drawString(info_x + 6, info_row_y - row_h_info + 4, addr)
            info_row_y -= row_h_info

        # Horizontal rule - well BELOW the info box to not cut off address
        rule_y = info_box_bottom - 30
        c.setStrokeColor(black)
        c.setLineWidth(1)
        c.line(CONTENT_LEFT, rule_y, CONTENT_RIGHT, rule_y)

        # Title - position just above the horizontal rule
        title_y = rule_y + 8
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(CONTENT_LEFT, title_y, "Site Recommendation Report")

        # Return y with small gap below horizontal rule
        return rule_y - 14

    def draw_footer(page_number, total):
        """Draw page footer."""
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor("#666666"))
        c.drawString(CONTENT_LEFT, 24, FOOTER_TEXT)
        c.drawRightString(CONTENT_RIGHT, 24, f"Page {page_number} of {total}")

    # Flatten all photos with category info for easier processing
    all_rows = []  # List of (category_name, is_first_in_cat, photos_in_row, photo_nums)
    for cat_name, cat_photos in categories.items():
        photos_in_cat = len(cat_photos)
        rows_in_cat = (photos_in_cat + 1) // 2
        photo_num = 1
        for row_idx in range(rows_in_cat):
            is_first = (row_idx == 0)
            row_start = row_idx * 2
            row_photos = cat_photos[row_start:row_start + 2]
            row_nums = list(range(photo_num, photo_num + len(row_photos)))
            photo_num += len(row_photos)
            all_rows.append((cat_name, is_first, row_photos, row_nums))

    # Count pages
    def count_pages():
        pages = 1
        rows_on_page = 0
        is_page1 = True
        current_cat = None

        for cat_name, is_first_in_cat, row_photos, row_nums in all_rows:
            # New category = new page (unless we're at start of a page)
            if cat_name != current_cat and current_cat is not None:
                pages += 1
                rows_on_page = 0
                is_page1 = False
            current_cat = cat_name

            # Determine max rows for this page
            if is_page1:
                max_rows = 2  # Page 1 has header + section header
            elif rows_on_page == 0 and is_first_in_cat:
                max_rows = 2  # First page of new section has section header
            else:
                max_rows = 3  # Continuation pages have no headers

            # Check if this row fits
            if rows_on_page >= max_rows:
                pages += 1
                rows_on_page = 0
                is_page1 = False

            rows_on_page += 1

        return pages

    total_pages = count_pages()

    # Draw pages
    page_num = 1
    rows_on_page = 0
    is_page1 = True
    current_cat = None
    current_y = 0

    for cat_name, is_first_in_cat, row_photos, row_nums in all_rows:
        # New category = new page (unless at start of page)
        if cat_name != current_cat and current_cat is not None:
            draw_footer(page_num, total_pages)
            c.showPage()
            page_num += 1
            rows_on_page = 0
            is_page1 = False

        current_cat = cat_name

        # Determine max rows for current page state
        if is_page1:
            max_rows = 2
        elif rows_on_page == 0 and is_first_in_cat:
            max_rows = 2  # First page of section has section header
        else:
            max_rows = 3

        # Check if we need a new page
        if rows_on_page >= max_rows:
            draw_footer(page_num, total_pages)
            c.showPage()
            page_num += 1
            rows_on_page = 0
            is_page1 = False

        # Set up page if this is first row on it
        if rows_on_page == 0:
            if is_page1:
                current_y = draw_page1_header()
                current_y = draw_section_header(current_y, cat_name)
            else:
                current_y = CONTENT_TOP
                if is_first_in_cat:
                    current_y = draw_section_header(current_y, cat_name)
        else:
            current_y -= ROW_GAP

        # Draw the row
        for col, (photo_data, num) in enumerate(zip(row_photos, row_nums)):
            x = COL1_LEFT if col == 0 else COL2_LEFT
            draw_photo(x, current_y, photo_data["buffer"], photo_data["note"], num)

        current_y -= ROW_HEIGHT
        rows_on_page += 1

    # Draw footer on last page
    draw_footer(page_num, total_pages)

    c.save()
    buffer.seek(0)

    return (buffer.getvalue(), "site-report.pdf")


def generate_before_after_report(metadata, before_buffers, after_buffers):
    """Generate before/after comparison report.

    Args:
        metadata: dict with address, inspector, date, originalReport, photos
        before_buffers: list of BytesIO buffers (before photos)
        after_buffers: list of BytesIO buffers (after photos)

    Returns:
        tuple: (pdf_bytes, filename) where pdf_bytes is the raw PDF content
    """
    address = metadata.get("address", "Unknown Property")
    inspector = metadata.get("inspector", "")
    original_report = metadata.get("originalReport", "")
    report_date = metadata.get("date", "")
    photo_metas = metadata.get("photos", [])

    # Group photos by category (preserving order of first appearance)
    categories = OrderedDict()
    for i, pmeta in enumerate(photo_metas):
        cat = pmeta.get("beforeCategory", "") or "Uncategorized"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "index": i,
            "meta": pmeta,
            "before_buf": before_buffers[i] if i < len(before_buffers) else None,
            "after_buf": after_buffers[i] if i < len(after_buffers) else None,
        })

    # Build PDF with direct canvas control
    buffer = io.BytesIO()
    page_w, page_h = letter  # 612 x 792

    # MASTER GRID COORDINATES (from spec)
    LEFT_MARGIN = 40
    RIGHT_MARGIN = 40
    TOP_MARGIN = 40
    BOTTOM_MARGIN = 50

    CONTENT_LEFT = LEFT_MARGIN  # 40
    CONTENT_RIGHT = page_w - RIGHT_MARGIN  # 572
    CONTENT_WIDTH = CONTENT_RIGHT - CONTENT_LEFT  # 532
    CONTENT_TOP = page_h - TOP_MARGIN  # 752
    CONTENT_BOTTOM = BOTTOM_MARGIN  # 50
    USABLE_HEIGHT = CONTENT_TOP - CONTENT_BOTTOM  # 702

    # Column grid
    GUTTER = 16
    COL_WIDTH = (CONTENT_WIDTH - GUTTER) / 2  # 258
    COL1_LEFT = CONTENT_LEFT  # 40
    COL2_LEFT = COL1_LEFT + COL_WIDTH + GUTTER  # 314

    # Row grid - calculate for 3 pairs on normal page
    PAIR_GAP = 14
    NOTE_H = 30
    LABEL_H = 16  # BEFORE/AFTER label height
    PAIRS_NORMAL = 3
    TOTAL_GAP = PAIR_GAP * (PAIRS_NORMAL - 1)  # 28
    PAIR_HEIGHT = (USABLE_HEIGHT - TOTAL_GAP) / PAIRS_NORMAL  # ~224
    PHOTO_HEIGHT = PAIR_HEIGHT - LABEL_H - NOTE_H  # ~178

    # Category header
    CAT_HEADER_HEIGHT = 24
    CAT_PADDING = 10

    c = pdf_canvas.Canvas(buffer, pagesize=letter)

    def draw_pair(y_top, before_buf, after_buf, before_note, after_note, pair_num):
        """Draw a before/after photo pair with numbered notes. y_top is the top of the pair."""
        # Photo area y positions
        photo_top = y_top - LABEL_H
        photo_bottom = photo_top - PHOTO_HEIGHT
        note_bottom = photo_bottom - NOTE_H

        def draw_photo_fill(buf, x):
            """Draw photo scaled to fill the box (crop if needed), not fit."""
            if not buf:
                return
            buf.seek(0)
            try:
                # Get image dimensions
                pil_img = Image.open(buf)
                img_w, img_h = pil_img.size
                buf.seek(0)

                # Calculate scale to FILL (not fit) - image will cover entire box
                scale_w = COL_WIDTH / img_w
                scale_h = PHOTO_HEIGHT / img_h
                scale = max(scale_w, scale_h)  # Use larger scale to fill

                # Scaled dimensions (one dimension will match, other will overflow)
                scaled_w = img_w * scale
                scaled_h = img_h * scale

                # Center the overflow
                offset_x = (COL_WIDTH - scaled_w) / 2
                offset_y = (PHOTO_HEIGHT - scaled_h) / 2

                # Use clipping to crop the overflow
                c.saveState()
                p = c.beginPath()
                p.rect(x, photo_bottom, COL_WIDTH, PHOTO_HEIGHT)
                c.clipPath(p, stroke=0)

                # Draw image larger than box (clipped to box)
                c.drawImage(
                    ImageReader(buf),
                    x + offset_x, photo_bottom + offset_y,
                    width=scaled_w, height=scaled_h
                )
                c.restoreState()
            except:
                pass

        # Draw BEFORE column - banner, photo, note box all with same x and width
        # Banner
        c.setFillColor(HexColor("#DC2626"))
        c.rect(COL1_LEFT, photo_top, COL_WIDTH, LABEL_H, fill=True, stroke=False)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.rect(COL1_LEFT, photo_top, COL_WIDTH, LABEL_H, fill=False, stroke=True)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        text_w = c.stringWidth("BEFORE", "Helvetica-Bold", 10)
        c.drawString(COL1_LEFT + (COL_WIDTH - text_w) / 2, photo_top + 4, "BEFORE")

        # Photo - fill and crop
        draw_photo_fill(before_buf, COL1_LEFT)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.rect(COL1_LEFT, photo_bottom, COL_WIDTH, PHOTO_HEIGHT, fill=False, stroke=True)

        # Note box
        c.rect(COL1_LEFT, note_bottom, COL_WIDTH, NOTE_H, fill=False, stroke=True)

        # Draw AFTER column - banner, photo, note box all with same x and width
        # Banner
        c.setFillColor(HexColor("#16A34A"))
        c.rect(COL2_LEFT, photo_top, COL_WIDTH, LABEL_H, fill=True, stroke=False)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.rect(COL2_LEFT, photo_top, COL_WIDTH, LABEL_H, fill=False, stroke=True)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        text_w = c.stringWidth("AFTER", "Helvetica-Bold", 10)
        c.drawString(COL2_LEFT + (COL_WIDTH - text_w) / 2, photo_top + 4, "AFTER")

        # Photo - fill and crop
        draw_photo_fill(after_buf, COL2_LEFT)
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.rect(COL2_LEFT, photo_bottom, COL_WIDTH, PHOTO_HEIGHT, fill=False, stroke=True)

        # Note box
        c.rect(COL2_LEFT, note_bottom, COL_WIDTH, NOTE_H, fill=False, stroke=True)

        # Draw numbered note text
        c.setFillColor(DARK)
        c.setFont("Helvetica", 8)
        max_chars = int((COL_WIDTH - 8) / 4)

        def draw_note_text(note, x, num):
            if note:
                note_text = f"{num}. Note: {note[:NOTE_CHAR_LIMIT]}"
            else:
                note_text = f"{num}."

            y = note_bottom + NOTE_H - 10
            words = note_text.split()
            line = ""
            for word in words:
                test = f"{line} {word}".strip()
                if len(test) <= max_chars:
                    line = test
                else:
                    if line:
                        c.drawString(x + 4, y, line)
                        y -= 10
                        if y < note_bottom + 4:
                            break
                    line = word
            if line and y >= note_bottom + 4:
                c.drawString(x + 4, y, line)

        draw_note_text(before_note, COL1_LEFT, pair_num)
        draw_note_text(after_note, COL2_LEFT, pair_num)

    def draw_section_header(y_top, category):
        """Draw a category header bar. Returns y for first pair."""
        header_bottom = y_top - CAT_HEADER_HEIGHT
        c.setFillColor(GRAY_HEADER)
        c.rect(CONTENT_LEFT, header_bottom, CONTENT_WIDTH, CAT_HEADER_HEIGHT, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(CONTENT_LEFT + 8, header_bottom + 7, category)
        # Normal gap between category bar and first pair
        return header_bottom - PAIR_GAP

    def draw_page1_header():
        """Draw the header on page 1. Returns y for content."""
        y = CONTENT_TOP

        # Logo
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            try:
                c.drawImage(logo_path, CONTENT_LEFT, y - 42, width=180, height=42, preserveAspectRatio=True)
            except:
                pass

        # Info box on right - extra height for longer addresses
        info_x = CONTENT_RIGHT - 160
        info_y = y - 10
        box_h = 105  # Increased from 90 to fit longer addresses
        info_box_bottom = info_y - box_h  # Track where info box ends

        c.setStrokeColor(LIGHT_GRAY)
        c.setLineWidth(0.5)
        c.rect(info_x, info_box_bottom, 160, box_h, fill=False, stroke=True)

        row_h_info = 15
        info_row_y = info_y

        # Date row
        c.setFillColor(GRAY_HEADER)
        c.rect(info_x, info_row_y - row_h_info, 160, row_h_info, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, "Date:")
        info_row_y -= row_h_info
        c.setFillColor(DARK)
        c.setFont("Helvetica", 9)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, report_date)
        info_row_y -= row_h_info

        # Inspected By row
        c.setFillColor(GRAY_HEADER)
        c.rect(info_x, info_row_y - row_h_info, 160, row_h_info, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, "Inspected By:")
        info_row_y -= row_h_info
        c.setFillColor(DARK)
        c.setFont("Helvetica", 9)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, _escape(inspector)[:25])
        info_row_y -= row_h_info

        # Property row - allow 2 lines for address
        c.setFillColor(GRAY_HEADER)
        c.rect(info_x, info_row_y - row_h_info, 160, row_h_info, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(info_x + 6, info_row_y - row_h_info + 4, "Property:")
        info_row_y -= row_h_info

        # Address can span 2 lines
        c.setFillColor(DARK)
        c.setFont("Helvetica", 8)
        addr = _escape(address)
        if len(addr) > 28:
            # Split into 2 lines
            c.drawString(info_x + 6, info_row_y - row_h_info + 4, addr[:28])
            info_row_y -= row_h_info
            c.drawString(info_x + 6, info_row_y - row_h_info + 4, addr[28:56])
        else:
            c.drawString(info_x + 6, info_row_y - row_h_info + 4, addr)
            info_row_y -= row_h_info

        # Horizontal rule - well BELOW the info box to not cut off address
        rule_y = info_box_bottom - 30
        c.setStrokeColor(black)
        c.setLineWidth(1)
        c.line(CONTENT_LEFT, rule_y, CONTENT_RIGHT, rule_y)

        # Title - position just above the horizontal rule
        title_y = rule_y + 8
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(CONTENT_LEFT, title_y, "Before & After Report")

        # Return y with small gap below horizontal rule
        return rule_y - 14

    def draw_footer(page_number, total):
        """Draw page footer."""
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor("#666666"))
        c.drawString(CONTENT_LEFT, 24, FOOTER_TEXT)
        c.drawRightString(CONTENT_RIGHT, 24, f"Page {page_number} of {total}")

    # Flatten all pairs with category info for easier processing
    all_pairs = []  # List of (category_name, is_first_in_cat, photo_data, pair_num)
    for cat_name, cat_photos in categories.items():
        for pair_idx, photo_data in enumerate(cat_photos):
            is_first = (pair_idx == 0)
            pair_num = pair_idx + 1
            all_pairs.append((cat_name, is_first, photo_data, pair_num))

    # Count pages
    def count_pages():
        pages = 1
        pairs_on_page = 0
        is_page1 = True
        current_cat = None

        for cat_name, is_first_in_cat, photo_data, pair_num in all_pairs:
            # New category = new page (unless at start of page)
            if cat_name != current_cat and current_cat is not None:
                pages += 1
                pairs_on_page = 0
                is_page1 = False
            current_cat = cat_name

            # Determine max pairs for this page
            if is_page1:
                max_pairs = 2  # Page 1 has header + section header
            elif pairs_on_page == 0 and is_first_in_cat:
                max_pairs = 2  # First page of new section has section header
            else:
                max_pairs = 3  # Continuation pages have no headers

            # Check if this pair fits
            if pairs_on_page >= max_pairs:
                pages += 1
                pairs_on_page = 0
                is_page1 = False

            pairs_on_page += 1

        return pages

    total_pages = count_pages()

    # Draw pages
    page_num = 1
    pairs_on_page = 0
    is_page1 = True
    current_cat = None
    current_y = 0

    for cat_name, is_first_in_cat, photo_data, pair_num in all_pairs:
        # New category = new page (unless at start of page)
        if cat_name != current_cat and current_cat is not None:
            draw_footer(page_num, total_pages)
            c.showPage()
            page_num += 1
            pairs_on_page = 0
            is_page1 = False

        current_cat = cat_name

        # Determine max pairs for current page state
        if is_page1:
            max_pairs = 2
        elif pairs_on_page == 0 and is_first_in_cat:
            max_pairs = 2  # First page of section has section header
        else:
            max_pairs = 3

        # Check if we need a new page
        if pairs_on_page >= max_pairs:
            draw_footer(page_num, total_pages)
            c.showPage()
            page_num += 1
            pairs_on_page = 0
            is_page1 = False

        # Set up page if this is first pair on it
        if pairs_on_page == 0:
            if is_page1:
                current_y = draw_page1_header()
                current_y = draw_section_header(current_y, cat_name)
            else:
                current_y = CONTENT_TOP
                if is_first_in_cat:
                    current_y = draw_section_header(current_y, cat_name)
        else:
            current_y -= PAIR_GAP

        # Draw this pair
        pmeta = photo_data["meta"]
        before_buf = photo_data["before_buf"]
        after_buf = photo_data["after_buf"]

        draw_pair(
            current_y,
            before_buf,
            after_buf,
            pmeta.get("beforeNote", ""),
            pmeta.get("afterNote", ""),
            pair_num
        )

        current_y -= PAIR_HEIGHT
        pairs_on_page += 1

    # Draw footer on last page
    if pairs_on_page > 0 or page_num == 1:
        draw_footer(page_num, total_pages)

    c.save()
    buffer.seek(0)

    return (buffer.getvalue(), "before-after-report.pdf")


# ── Contract PDF Generation ──────────────────────────

# Color palette for contracts
CONTRACT_GREEN = HexColor("#3A5F4B")
CONTRACT_DARK = HexColor("#1A2E24")
CONTRACT_GRAY = HexColor("#666666")
CONTRACT_LIGHT_GRAY = HexColor("#F5F5F5")
CONTRACT_RED = HexColor("#C62828")
CONTRACT_BORDER = HexColor("#CCCCCC")

# Default service descriptions for residential contracts
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

# Terms & Conditions clauses (shared between residential and commercial)
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


def generate_contract_pdf(metadata, service_map_buffer=None):
    """Generate a contract PDF — residential (3 pages) or commercial (5-6 pages).

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
    buffer = io.BytesIO()
    page_w, page_h = letter  # 612 x 792

    LEFT = 40
    RIGHT = page_w - 40  # 572
    WIDTH = RIGHT - LEFT  # 532
    TOP = page_h - 40  # 752
    BOTTOM = 50

    company = metadata.get("companyName", "Endurance Services")
    phone = metadata.get("companyPhone", "(407) 579-4403")
    website = metadata.get("companyWebsite", "endurancefl.com")
    city = metadata.get("companyCity", "Orlando, FL")
    footer_text = f"{phone}  |  {website}  |  {city}"

    customer = metadata.get("customerName", "")
    customer_company = metadata.get("customerCompany", "")
    billing_addr = metadata.get("billingAddress", "")
    prop_addr = metadata.get("propertyAddress", "")
    contract_id = metadata.get("contractId", "")
    generated_date = metadata.get("generatedDate", "")
    monthly = metadata.get("monthlyPayment", 0)
    services = metadata.get("services", [])
    contract_value = metadata.get("contractValue", 0)

    c = pdf_canvas.Canvas(buffer, pagesize=letter)
    page_count = 3
    page_num = [1]  # mutable for closure

    def draw_footer():
        c.setFont("Helvetica", 8)
        c.setFillColor(CONTRACT_GRAY)
        c.drawString(LEFT, 24, footer_text)
        c.drawRightString(RIGHT, 24, f"Page {page_num[0]} of {page_count}")

    # ── PAGE 1: Quote Page ──────────────────────────
    y = TOP

    # Bold company header
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT, y - 4, company)

    # Gray info box (top-right)
    box_w = 170
    box_h = 72
    box_x = RIGHT - box_w
    box_y = y - box_h + 8
    c.setFillColor(HexColor("#F0F0F0"))
    c.rect(box_x, box_y, box_w, box_h, fill=True, stroke=False)
    c.setStrokeColor(CONTRACT_BORDER)
    c.setLineWidth(0.5)
    c.rect(box_x, box_y, box_w, box_h, fill=False, stroke=True)

    info_y = box_y + box_h - 14
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(box_x + 8, info_y, "Contract #:")
    c.setFont("Helvetica", 9)
    c.drawString(box_x + 80, info_y, _escape(contract_id))
    info_y -= 14
    c.setFont("Helvetica-Bold", 8)
    c.drawString(box_x + 8, info_y, "Date:")
    c.setFont("Helvetica", 9)
    c.drawString(box_x + 80, info_y, _escape(generated_date))
    info_y -= 14
    c.setFont("Helvetica-Bold", 8)
    c.drawString(box_x + 8, info_y, "Monthly:")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(CONTRACT_GREEN)
    c.drawString(box_x + 80, info_y, f"${monthly:,.2f}")
    info_y -= 14
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(box_x + 8, info_y, "Annual:")
    c.setFont("Helvetica", 9)
    c.drawString(box_x + 80, info_y, f"${contract_value:,.2f}")

    # Recipient section
    y -= 90
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(CONTRACT_GRAY)
    c.drawString(LEFT, y, "RECIPIENT")
    y -= 14
    c.setFont("Helvetica", 10)
    c.setFillColor(CONTRACT_DARK)
    if customer:
        c.drawString(LEFT, y, _escape(customer))
        y -= 14
    if customer_company:
        c.drawString(LEFT, y, _escape(customer_company))
        y -= 14
    if billing_addr:
        # Split address if long
        addr_parts = billing_addr.split(",")
        for part in addr_parts:
            c.drawString(LEFT, y, _escape(part.strip()))
            y -= 14

    # Property address
    y -= 6
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(CONTRACT_GRAY)
    c.drawString(LEFT, y, "SERVICE LOCATION")
    y -= 14
    c.setFont("Helvetica", 10)
    c.setFillColor(CONTRACT_DARK)
    if prop_addr:
        addr_parts = prop_addr.split(",")
        for part in addr_parts:
            c.drawString(LEFT, y, _escape(part.strip()))
            y -= 14

    # Horizontal rule
    y -= 8
    c.setStrokeColor(CONTRACT_BORDER)
    c.setLineWidth(0.5)
    c.line(LEFT, y, RIGHT, y)
    y -= 16

    # Services table header
    col_widths = [WIDTH * 0.35, WIDTH * 0.30, WIDTH * 0.10, WIDTH * 0.12, WIDTH * 0.13]
    headers_labels = ["Product/Service", "Description", "Qty", "Unit Price", "Total"]

    c.setFillColor(CONTRACT_GREEN)
    c.rect(LEFT, y - 16, WIDTH, 18, fill=True, stroke=False)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    x_pos = LEFT + 4
    for i, hdr in enumerate(headers_labels):
        if i >= 3:  # right-align numbers
            c.drawRightString(x_pos + col_widths[i] - 4, y - 12, hdr)
        else:
            c.drawString(x_pos, y - 12, hdr)
        x_pos += col_widths[i]
    y -= 20

    # Service rows
    c.setFont("Helvetica", 9)
    c.setFillColor(CONTRACT_DARK)
    annual_total = 0
    for svc in services:
        if y < BOTTOM + 60:
            break  # Safety — shouldn't happen for residential
        name = svc.get("name", "")
        desc = svc.get("description", "")[:40]
        freq = svc.get("frequency", "")
        annual = svc.get("annualTotal", 0)
        cost_per = svc.get("costPerOccurrence", 0)
        annual_total += annual

        # Alternate row background
        if services.index(svc) % 2 == 1:
            c.setFillColor(CONTRACT_LIGHT_GRAY)
            c.rect(LEFT, y - 14, WIDTH, 16, fill=True, stroke=False)
            c.setFillColor(CONTRACT_DARK)

        x_pos = LEFT + 4
        c.setFont("Helvetica", 8)
        c.drawString(x_pos, y - 10, _escape(name)[:35])
        x_pos += col_widths[0]
        c.drawString(x_pos, y - 10, _escape(desc)[:30])
        x_pos += col_widths[1]
        c.drawString(x_pos, y - 10, str(freq))
        x_pos += col_widths[2]
        c.drawRightString(x_pos + col_widths[3] - 4, y - 10, f"${cost_per:,.2f}")
        x_pos += col_widths[3]
        c.drawRightString(x_pos + col_widths[4] - 4, y - 10, f"${annual:,.2f}")
        y -= 16

    # Total row
    y -= 4
    c.setStrokeColor(CONTRACT_DARK)
    c.setLineWidth(1)
    c.line(LEFT, y, RIGHT, y)
    y -= 16
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT + 4, y, "Total Annual Value")
    c.drawRightString(RIGHT - 4, y, f"${annual_total:,.2f}")

    # Valid for 30 days note
    y -= 30
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(CONTRACT_GRAY)
    c.drawString(LEFT, y, "This quote is valid for the next 30 days from the date shown above.")

    draw_footer()
    c.showPage()
    page_num[0] += 1

    # ── PAGE 2: Description of Services ────────────
    y = TOP

    # Get primary service name
    primary_svc = services[0].get("name", "Landscape Maintenance") if services else "Landscape Maintenance"
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT, y - 4, _escape(primary_svc))
    y -= 20
    c.setFont("Helvetica", 10)
    c.setFillColor(CONTRACT_GRAY)
    c.drawString(LEFT, y, "Description of Services")
    y -= 8
    c.setStrokeColor(CONTRACT_BORDER)
    c.setLineWidth(0.5)
    c.line(LEFT, y, RIGHT, y)
    y -= 20

    # Get descriptions — use defaults if not provided
    desc_items = RESIDENTIAL_SERVICE_DESCRIPTIONS.get(primary_svc, [])
    if not desc_items:
        # Build from service data
        for svc in services:
            svc_name = svc.get("name", "")
            svc_desc = svc.get("description", "Service included as specified.")
            desc_items.append((svc_name, [svc_desc]))

    for idx, (heading, sub_items) in enumerate(desc_items):
        # Bold numbered heading
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(CONTRACT_DARK)
        line = f"{idx + 1}. {heading}"
        c.drawString(LEFT + 8, y, line)
        y -= 16

        # Sub-items with letter prefix
        for si, text in enumerate(sub_items):
            sub_letter = chr(ord('a') + si)
            c.setFont("Helvetica", 9)
            c.setFillColor(CONTRACT_DARK)

            # Word-wrap long text
            prefix = f"    {sub_letter}. "
            max_chars = 80
            full_text = prefix + text
            lines = []
            while len(full_text) > max_chars:
                # Find last space before limit
                break_at = full_text.rfind(' ', 0, max_chars)
                if break_at <= len(prefix):
                    break_at = max_chars
                lines.append(full_text[:break_at])
                full_text = "       " + full_text[break_at:].lstrip()
            lines.append(full_text)

            # Highlight irrigation repair clause
            is_highlight = "irrigation" in heading.lower() and "$100" in text.lower()

            for line in lines:
                if y < BOTTOM + 30:
                    draw_footer()
                    c.showPage()
                    page_num[0] += 1
                    page_count += 1  # Dynamic page count adjustment
                    y = TOP

                if is_highlight:
                    c.setFillColor(HexColor("#FFF3E0"))
                    c.rect(LEFT, y - 4, WIDTH, 14, fill=True, stroke=False)
                    c.setFillColor(CONTRACT_DARK)

                c.drawString(LEFT + 16, y, line)
                y -= 13

        y -= 6  # Gap between sections

    draw_footer()
    c.showPage()
    page_num[0] += 1

    # ── PAGE 3: Terms & Conditions + Signatures ────
    y = TOP

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT, y - 4, "Terms and Conditions")
    y -= 22

    effective = metadata.get("effectiveDate", metadata.get("startDate", ""))
    c.setFont("Helvetica", 10)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT, y, f"Effective Date: {_escape(effective)}")
    y -= 8
    c.setStrokeColor(CONTRACT_BORDER)
    c.setLineWidth(0.5)
    c.line(LEFT, y, RIGHT, y)
    y -= 16

    clauses = _get_terms_clauses(metadata)
    for idx, (title, text) in enumerate(clauses):
        # Check page space
        if y < BOTTOM + 50:
            draw_footer()
            c.showPage()
            page_num[0] += 1
            page_count += 1
            y = TOP

        # Numbered bold title
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(CONTRACT_DARK)
        c.drawString(LEFT + 4, y, f"{idx + 1}. {title}")
        y -= 13

        # Highlight specific clauses (price increase and tropical event)
        is_red = idx >= 10  # clauses 11 and 12

        # Highlight specific clauses (price increase and tropical event)
        is_red = idx >= 10  # clauses 11 and 12

        c.setFont("Helvetica", 8)
        if is_red:
            c.setFillColor(CONTRACT_RED)
        else:
            c.setFillColor(CONTRACT_DARK)

        # Text can be a string or a list of sub-items (clause 12)
        text_items = text if isinstance(text, list) else [text]
        indent = LEFT + 16

        for sub_idx, sub_text in enumerate(text_items):
            # For list items, prefix with sub-number
            if isinstance(text, list):
                line_text = f"{sub_idx + 1}. {sub_text}"
            else:
                line_text = sub_text

            # Word-wrap clause text
            max_chars = 90
            remaining = line_text
            while remaining:
                if len(remaining) <= max_chars:
                    c.drawString(indent, y, remaining)
                    y -= 11
                    remaining = ""
                else:
                    break_at = remaining.rfind(' ', 0, max_chars)
                    if break_at <= 0:
                        break_at = max_chars
                    c.drawString(indent, y, remaining[:break_at])
                    y -= 11
                    remaining = remaining[break_at:].lstrip()

                    if y < BOTTOM + 50:
                        draw_footer()
                        c.showPage()
                        page_num[0] += 1
                        page_count += 1
                        y = TOP
                        if is_red:
                            c.setFont("Helvetica", 8)
                            c.setFillColor(CONTRACT_RED)

        y -= 4  # Gap between clauses

    # ── Signature Section ──
    y -= 10
    if y < BOTTOM + 120:
        draw_footer()
        c.showPage()
        page_num[0] += 1
        page_count += 1
        y = TOP

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT, y, "Signature Section")
    y -= 8
    c.setStrokeColor(CONTRACT_BORDER)
    c.line(LEFT, y, RIGHT, y)
    y -= 40

    # Two-column signatures
    mid = LEFT + WIDTH / 2
    sig_line_w = WIDTH / 2 - 20

    # Left column — Company
    c.setStrokeColor(CONTRACT_DARK)
    c.setLineWidth(0.5)
    c.line(LEFT, y, LEFT + sig_line_w, y)
    y_left = y - 14
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y_left, "Jack McMahon")
    y_left -= 14
    c.setFont("Helvetica", 9)
    c.drawString(LEFT, y_left, company)
    y_left -= 14
    c.drawString(LEFT, y_left, f"Date: {_escape(generated_date)}")

    # Right column — Customer
    signed_name = metadata.get("signedName", "")
    signed_at = _format_signed_at(metadata.get("signedAt", ""))
    if signed_name and _HAS_DANCING_SCRIPT:
        c.setFont("DancingScript", 18)
        c.setFillColor(CONTRACT_DARK)
        c.drawString(mid + 10, y + 6, _escape(signed_name))
    c.line(mid + 10, y, mid + 10 + sig_line_w, y)
    y_right = y - 14
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(mid + 10, y_right, _escape(customer) if customer else "________________")
    y_right -= 14
    c.setFont("Helvetica", 9)
    c.drawString(mid + 10, y_right, _escape(prop_addr)[:40] if prop_addr else "")
    y_right -= 14
    if signed_at:
        c.drawString(mid + 10, y_right, f"Signed: {_escape(signed_at)}")
    else:
        c.drawString(mid + 10, y_right, f"Date: {_escape(generated_date)}")

    draw_footer()
    c.save()
    buffer.seek(0)

    contract_id_clean = contract_id.replace(" ", "-") if contract_id else "contract"
    suffix = "-signed" if signed_name else ""
    return (buffer.getvalue(), f"{contract_id_clean}-contract{suffix}.pdf")


def _generate_commercial_contract(metadata, service_map_buffer=None):
    """Generate a 5-6 page commercial contract PDF."""
    buffer = io.BytesIO()
    page_w, page_h = letter  # 612 x 792

    LEFT = 40
    RIGHT = page_w - 40  # 572
    WIDTH = RIGHT - LEFT  # 532
    TOP = page_h - 40  # 752
    BOTTOM = 50

    company = metadata.get("companyName", "Endurance Services")
    phone = metadata.get("companyPhone", "(407) 579-4403")
    website = metadata.get("companyWebsite", "endurancefl.com")
    city = metadata.get("companyCity", "Orlando, FL")
    footer_text = f"{phone}  |  {website}  |  {city}"

    customer = metadata.get("customerName", "")
    customer_company = metadata.get("customerCompany", "")
    billing_addr = metadata.get("billingAddress", "")
    prop_addr = metadata.get("propertyAddress", "")
    contract_id = metadata.get("contractId", "")
    generated_date = metadata.get("generatedDate", "")
    start_date = metadata.get("startDate", "")
    end_date = metadata.get("endDate", "")
    duration = metadata.get("duration", 12)
    services = metadata.get("services", [])
    payment_schedule = metadata.get("paymentSchedule", [])
    contract_value = metadata.get("contractValue", 0)
    monthly = metadata.get("monthlyPayment", 0)

    # Parse dates for title
    try:
        from datetime import datetime
        sd = datetime.strptime(start_date, "%Y-%m-%d")
        ed = datetime.strptime(end_date, "%Y-%m-%d")
        start_month = sd.strftime("%B")
        start_year = sd.strftime("%Y")
        end_month = ed.strftime("%B")
        end_year = ed.strftime("%Y")
        fy_year = sd.strftime("%Y")
    except Exception:
        start_month = start_year = end_month = end_year = fy_year = ""

    # Split services by billing tier
    fixed_services = [s for s in services if s.get("billingTier", "fixed") == "fixed"]
    billed_services = [s for s in services if s.get("billingTier") == "billed"]
    recommended_services = [s for s in services if s.get("billingTier") == "recommended"]

    fixed_total = sum(s.get("annualTotal", 0) for s in fixed_services)
    billed_total = sum(s.get("annualTotal", 0) for s in billed_services)
    recommended_total = sum(s.get("annualTotal", 0) for s in recommended_services)

    c = pdf_canvas.Canvas(buffer, pagesize=letter)
    page_num = [1]
    total_pages = [0]  # Will be filled after we know how many pages

    def draw_footer():
        c.setFont("Helvetica", 8)
        c.setFillColor(CONTRACT_GRAY)
        c.drawString(LEFT, 24, footer_text)
        c.drawRightString(RIGHT, 24, f"Page {page_num[0]}")

    def draw_gray_header_bar(y_pos, text):
        """Draw a full-width gray header bar with white text. Returns y below bar."""
        c.setFillColor(CONTRACT_GRAY)
        c.rect(LEFT, y_pos - 18, WIDTH, 20, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LEFT + 8, y_pos - 14, text)
        return y_pos - 26

    def new_page():
        draw_footer()
        c.showPage()
        page_num[0] += 1
        return TOP

    # ── PAGE 1: Cover Page ─────────────────────────
    y = TOP

    # Logo
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, LEFT, y - 42, width=180, height=42, preserveAspectRatio=True)
        except Exception:
            pass

    # Gray info box (top-right)
    box_w = 200
    box_h = 120
    box_x = RIGHT - box_w
    box_y = y - box_h + 8

    c.setFillColor(HexColor("#F0F0F0"))
    c.rect(box_x, box_y, box_w, box_h, fill=True, stroke=False)
    c.setStrokeColor(CONTRACT_BORDER)
    c.setLineWidth(0.5)
    c.rect(box_x, box_y, box_w, box_h, fill=False, stroke=True)

    info_y = box_y + box_h - 14
    info_items = [
        ("Date:", generated_date),
        ("Proposal #:", contract_id),
        ("Property:", prop_addr[:35] if prop_addr else ""),
        ("", prop_addr[35:70] if len(prop_addr) > 35 else ""),
        ("Billing Contact:", customer),
        ("Company:", customer_company),
        ("Billing Address:", billing_addr[:35] if billing_addr else ""),
    ]

    for label, val in info_items:
        if not label and not val:
            continue
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(CONTRACT_DARK)
        if label:
            c.drawString(box_x + 6, info_y, label)
        c.setFont("Helvetica", 8)
        if label:
            c.drawString(box_x + 85, info_y, _escape(val))
        else:
            c.drawString(box_x + 85, info_y, _escape(val))
        info_y -= 13

    # Title bar
    y -= 140
    prop_name = prop_addr.split(",")[0] if prop_addr else "Property"
    title = f"FY{fy_year} Landscape Maintenance Agreement"
    subtitle = f"{_escape(prop_name)} ({start_month} {start_year} - {end_month} {end_year})"

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT, y, title)
    y -= 18
    c.setFont("Helvetica", 11)
    c.setFillColor(CONTRACT_GRAY)
    c.drawString(LEFT, y, subtitle)
    y -= 16
    c.setStrokeColor(CONTRACT_GREEN)
    c.setLineWidth(2)
    c.line(LEFT, y, RIGHT, y)
    y -= 20

    # Service map image (optional)
    if service_map_buffer:
        try:
            service_map_buffer.seek(0)
            map_w = WIDTH
            map_h = min(y - BOTTOM - 40, 340)
            c.drawImage(
                ImageReader(service_map_buffer), LEFT, y - map_h,
                width=map_w, height=map_h,
                preserveAspectRatio=True, anchor='c'
            )
            c.setStrokeColor(CONTRACT_BORDER)
            c.setLineWidth(0.5)
            c.rect(LEFT, y - map_h, map_w, map_h, fill=False, stroke=True)
        except Exception:
            pass

    draw_footer()
    c.showPage()
    page_num[0] += 1

    # ── PAGE 2: Services Tables ────────────────────
    y = TOP

    def draw_services_table(y_pos, svc_list, show_initials=False):
        """Draw a services table. Returns y position after table."""
        # Column headers
        if show_initials:
            cols = [WIDTH * 0.06, WIDTH * 0.34, WIDTH * 0.18, WIDTH * 0.20, WIDTH * 0.22]
            col_headers = ["Initial", "Service", "Frequency", "Cost/Occ.", "Annual Cost"]
        else:
            cols = [WIDTH * 0.40, WIDTH * 0.18, WIDTH * 0.20, WIDTH * 0.22]
            col_headers = ["Service", "Frequency", "Cost/Occ.", "Annual Cost"]

        c.setFillColor(HexColor("#E8E8E8"))
        c.rect(LEFT, y_pos - 14, WIDTH, 16, fill=True, stroke=False)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(CONTRACT_DARK)
        x = LEFT + 4
        for i, h in enumerate(col_headers):
            if i >= len(col_headers) - 2:
                c.drawRightString(x + cols[i] - 4, y_pos - 10, h)
            else:
                c.drawString(x, y_pos - 10, h)
            x += cols[i]
        y_pos -= 18

        # Group by category
        current_cat = None
        total = 0

        for svc in svc_list:
            if y_pos < BOTTOM + 40:
                y_pos = new_page()

            cat = svc.get("category", "")
            if cat and cat != current_cat:
                current_cat = cat
                # Category sub-header
                c.setFont("Helvetica-Bold", 8)
                c.setFillColor(CONTRACT_GREEN)
                c.drawString(LEFT + 4, y_pos - 10, _escape(cat))
                y_pos -= 16

            name = svc.get("name", "")
            freq = svc.get("frequency", "")
            cost_per = svc.get("costPerOccurrence", 0)
            annual = svc.get("annualTotal", 0)
            total += annual

            c.setFont("Helvetica", 8)
            c.setFillColor(CONTRACT_DARK)
            x = LEFT + 4
            if show_initials:
                # Draw initial box
                c.setStrokeColor(CONTRACT_BORDER)
                c.rect(x + 2, y_pos - 12, 12, 12, fill=False, stroke=True)
                x += cols[0]

            start_col = 1 if show_initials else 0
            c.drawString(x, y_pos - 10, _escape(name)[:40])
            x += cols[start_col]
            c.drawString(x, y_pos - 10, str(freq))
            x += cols[start_col + 1]
            c.drawRightString(x + cols[start_col + 2] - 4, y_pos - 10, f"${cost_per:,.2f}")
            x += cols[start_col + 2]
            c.drawRightString(x + cols[start_col + 3] - 4, y_pos - 10, f"${annual:,.2f}")
            y_pos -= 14

        # Total row
        y_pos -= 4
        c.setStrokeColor(CONTRACT_DARK)
        c.setLineWidth(0.5)
        c.line(LEFT, y_pos, RIGHT, y_pos)
        y_pos -= 14
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(RIGHT - 4, y_pos, f"${total:,.2f}")
        y_pos -= 10

        return y_pos

    # Fixed Payment Services
    if fixed_services:
        y = draw_gray_header_bar(y, "Fixed Payment Services")
        y = draw_services_table(y, fixed_services)
        y -= 10

    # Services Billed Separately
    if billed_services:
        if y < BOTTOM + 100:
            y = new_page()
        y = draw_gray_header_bar(y, "Services Billed Separately Once Completed")
        y = draw_services_table(y, billed_services)
        y -= 10

    # Recommended Services
    if recommended_services:
        if y < BOTTOM + 100:
            y = new_page()
        y = draw_gray_header_bar(y, "Recommended Services")
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(CONTRACT_GRAY)
        c.drawString(LEFT + 4, y, "Initial next to optional service(s) you would like added to your contract")
        y -= 14
        y = draw_services_table(y, recommended_services, show_initials=True)

    draw_footer()
    c.showPage()
    page_num[0] += 1

    # ── PAGE 3: Payment Schedule ───────────────────
    y = TOP
    y = draw_gray_header_bar(y, "Payment Schedule (Fixed Payment Services Only)")
    y -= 6

    # Table headers
    sched_cols = [WIDTH * 0.40, WIDTH * 0.30, WIDTH * 0.30]
    c.setFillColor(HexColor("#E8E8E8"))
    c.rect(LEFT, y - 14, WIDTH, 16, fill=True, stroke=False)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT + 8, y - 10, "Schedule")
    c.drawRightString(LEFT + sched_cols[0] + sched_cols[1] - 4, y - 10, "Price")
    c.drawRightString(RIGHT - 4, y - 10, "Total Price")
    y -= 20

    running_total = 0
    for i, pay in enumerate(payment_schedule):
        month_name = pay.get("month", "")
        amount = pay.get("amount", 0)
        running_total += amount

        if i % 2 == 1:
            c.setFillColor(CONTRACT_LIGHT_GRAY)
            c.rect(LEFT, y - 12, WIDTH, 16, fill=True, stroke=False)

        c.setFont("Helvetica", 9)
        c.setFillColor(CONTRACT_DARK)
        c.drawString(LEFT + 8, y - 8, month_name)
        c.drawRightString(LEFT + sched_cols[0] + sched_cols[1] - 4, y - 8, f"${amount:,.2f}")
        c.drawRightString(RIGHT - 4, y - 8, f"${running_total:,.2f}")
        y -= 16

    # Bold total
    y -= 4
    c.setStrokeColor(CONTRACT_DARK)
    c.setLineWidth(1)
    c.line(LEFT, y, RIGHT, y)
    y -= 16
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT + 8, y, "Total")
    c.drawRightString(RIGHT - 4, y, f"${running_total:,.2f}")

    draw_footer()
    c.showPage()
    page_num[0] += 1

    # ── PAGE 4+: Description of Services ───────────
    y = TOP
    y = draw_gray_header_bar(y, "Description of Services")
    y -= 6

    tier_groups = [
        ("Fixed Payment Services", fixed_services),
        ("Services Billed Separately", billed_services),
        ("Recommended Services", recommended_services),
    ]

    for tier_label, tier_svcs in tier_groups:
        if not tier_svcs:
            continue

        if y < BOTTOM + 80:
            y = new_page()
            y = draw_gray_header_bar(y, "Description of Services (continued)")
            y -= 6

        # Tier sub-header
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(CONTRACT_GREEN)
        c.drawString(LEFT, y, tier_label)
        y -= 6
        c.setStrokeColor(CONTRACT_GREEN)
        c.setLineWidth(0.5)
        c.line(LEFT, y, RIGHT, y)
        y -= 14

        for svc in tier_svcs:
            name = svc.get("name", "")
            desc = svc.get("description", "Service included as specified in the agreement.")

            if y < BOTTOM + 60:
                y = new_page()
                y = draw_gray_header_bar(y, "Description of Services (continued)")
                y -= 6

            # Service name (bold, underlined)
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(CONTRACT_DARK)
            c.drawString(LEFT + 8, y, _escape(name))
            name_w = c.stringWidth(_escape(name), "Helvetica-Bold", 9)
            c.setStrokeColor(CONTRACT_DARK)
            c.setLineWidth(0.3)
            c.line(LEFT + 8, y - 2, LEFT + 8 + name_w, y - 2)
            y -= 14

            # Description paragraph (word-wrapped)
            c.setFont("Helvetica", 8)
            c.setFillColor(CONTRACT_DARK)
            max_chars = 85
            remaining = desc
            while remaining:
                if y < BOTTOM + 30:
                    y = new_page()
                    y = draw_gray_header_bar(y, "Description of Services (continued)")
                    y -= 6

                if len(remaining) <= max_chars:
                    c.drawString(LEFT + 16, y, _escape(remaining))
                    y -= 11
                    remaining = ""
                else:
                    break_at = remaining.rfind(' ', 0, max_chars)
                    if break_at <= 0:
                        break_at = max_chars
                    c.drawString(LEFT + 16, y, _escape(remaining[:break_at]))
                    y -= 11
                    remaining = remaining[break_at:].lstrip()

            y -= 8  # Gap between services

    draw_footer()
    c.showPage()
    page_num[0] += 1

    # ── Terms & Conditions Page ────────────────────
    y = TOP
    y = draw_gray_header_bar(y, "Terms and Conditions")
    y -= 6

    effective = metadata.get("effectiveDate", start_date)
    c.setFont("Helvetica", 9)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT, y, f"Effective Date: {_escape(effective)}")
    y -= 6
    c.setStrokeColor(CONTRACT_BORDER)
    c.line(LEFT, y, RIGHT, y)
    y -= 14

    clauses = _get_terms_clauses(metadata)
    for idx, (title, text) in enumerate(clauses):
        if y < BOTTOM + 50:
            y = new_page()

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(CONTRACT_DARK)
        c.drawString(LEFT + 4, y, f"{idx + 1}. {title}")
        y -= 12

        is_red = idx >= 10
        c.setFont("Helvetica", 7.5)
        if is_red:
            c.setFillColor(CONTRACT_RED)
        else:
            c.setFillColor(CONTRACT_DARK)

        # Text can be a string or a list of sub-items (clause 12)
        text_items = text if isinstance(text, list) else [text]

        for sub_idx, sub_text in enumerate(text_items):
            if isinstance(text, list):
                line_text = f"{sub_idx + 1}. {sub_text}"
            else:
                line_text = sub_text

            max_chars = 95
            remaining = line_text
            while remaining:
                if y < BOTTOM + 30:
                    y = new_page()
                    if is_red:
                        c.setFont("Helvetica", 7.5)
                        c.setFillColor(CONTRACT_RED)

                if len(remaining) <= max_chars:
                    c.drawString(LEFT + 16, y, remaining)
                    y -= 10
                    remaining = ""
                else:
                    break_at = remaining.rfind(' ', 0, max_chars)
                    if break_at <= 0:
                        break_at = max_chars
                    c.drawString(LEFT + 16, y, remaining[:break_at])
                    y -= 10
                    remaining = remaining[break_at:].lstrip()

        y -= 3

    draw_footer()
    c.showPage()
    page_num[0] += 1

    # ── Last Page: Signature Page ──────────────────
    y = TOP

    # White space at top, then signature at bottom
    sig_y = 240  # Position signatures about 1/3 from bottom

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT, sig_y + 60, "Signature Section")
    c.setStrokeColor(CONTRACT_BORDER)
    c.line(LEFT, sig_y + 52, RIGHT, sig_y + 52)

    mid = LEFT + WIDTH / 2
    sig_line_w = WIDTH / 2 - 20

    # Left column — Company
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(CONTRACT_GRAY)
    c.drawString(LEFT, sig_y + 30, "By")
    c.setStrokeColor(CONTRACT_DARK)
    c.setLineWidth(0.5)
    c.line(LEFT, sig_y, LEFT + sig_line_w, sig_y)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(LEFT, sig_y - 14, "Jack McMahon")
    c.setFont("Helvetica", 9)
    c.drawString(LEFT, sig_y - 28, company)
    c.drawString(LEFT, sig_y - 42, f"Date: {_escape(generated_date)}")

    # Right column — Customer
    signed_name = metadata.get("signedName", "")
    signed_at = _format_signed_at(metadata.get("signedAt", ""))
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(CONTRACT_GRAY)
    c.drawString(mid + 10, sig_y + 30, "By")
    if signed_name and _HAS_DANCING_SCRIPT:
        c.setFont("DancingScript", 18)
        c.setFillColor(CONTRACT_DARK)
        c.drawString(mid + 10, sig_y + 6, _escape(signed_name))
    c.line(mid + 10, sig_y, mid + 10 + sig_line_w, sig_y)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(CONTRACT_DARK)
    c.drawString(mid + 10, sig_y - 14, _escape(customer) if customer else "________________")
    c.setFont("Helvetica", 9)
    c.drawString(mid + 10, sig_y - 28, _escape(customer_company) if customer_company else "")
    if signed_at:
        c.drawString(mid + 10, sig_y - 42, f"Signed: {_escape(signed_at)}")
    else:
        c.drawString(mid + 10, sig_y - 42, f"Date: {_escape(generated_date)}")

    draw_footer()
    c.save()
    buffer.seek(0)

    contract_id_clean = contract_id.replace(" ", "-") if contract_id else "contract"
    suffix = "-signed" if signed_name else ""
    return (buffer.getvalue(), f"{contract_id_clean}-contract{suffix}.pdf")


# ── Legacy helpers (unused but kept for reference) ──

def _build_header(address, inspector, report_date, usable_w):
    """Build the page 1 header: logo left, info box right, title below."""
    elements = []

    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

    # Logo + info box as a table
    logo_cell = []
    if os.path.exists(logo_path):
        try:
            logo_cell.append(RLImage(logo_path, width=180, height=42, kind="proportional"))
        except Exception:
            pass

    # Info box: Date / Inspected By / Property
    info_style = ParagraphStyle("info", fontName="Helvetica", fontSize=9, leading=12, textColor=DARK)
    info_label_style = ParagraphStyle("infolabel", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=white)

    info_data = [
        [Paragraph("<b>Date:</b>", info_label_style)],
        [Paragraph(report_date, info_style)],
        [Paragraph("<b>Inspected By:</b>", info_label_style)],
        [Paragraph(inspector, info_style)],
        [Paragraph("<b>Property:</b>", info_label_style)],
        [Paragraph(_escape(address), info_style)],
    ]
    info_table = Table(info_data, colWidths=[160])
    info_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_HEADER),  # Date label row
        ("BACKGROUND", (0, 2), (-1, 2), GRAY_HEADER),  # Inspected By label row
        ("BACKGROUND", (0, 4), (-1, 4), GRAY_HEADER),  # Property label row
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    header_table = Table(
        [[logo_cell, info_table]],
        colWidths=[usable_w - 170, 170],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)

    # Title
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Site Recommendation Report", TITLE_STYLE))
    elements.append(Spacer(1, 6))

    return elements


def _build_ba_header(address, inspector, original_report, report_date, usable_w):
    """Build header for before/after report."""
    elements = []

    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

    logo_cell = []
    if os.path.exists(logo_path):
        try:
            logo_cell.append(RLImage(logo_path, width=180, height=42, kind="proportional"))
        except Exception:
            pass

    info_style = ParagraphStyle("info", fontName="Helvetica", fontSize=9, leading=12, textColor=DARK)
    info_label_style = ParagraphStyle("infolabel", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=white)

    info_data = [
        [Paragraph("<b>Date:</b>", info_label_style)],
        [Paragraph(report_date, info_style)],
        [Paragraph("<b>Inspected By:</b>", info_label_style)],
        [Paragraph(_escape(inspector), info_style)],
        [Paragraph("<b>Property:</b>", info_label_style)],
        [Paragraph(_escape(address), info_style)],
    ]
    info_table = Table(info_data, colWidths=[160])
    info_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_HEADER),  # Date label row
        ("BACKGROUND", (0, 2), (-1, 2), GRAY_HEADER),  # Inspected By label row
        ("BACKGROUND", (0, 4), (-1, 4), GRAY_HEADER),  # Property label row
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    header_table = Table(
        [[logo_cell, info_table]],
        colWidths=[usable_w - 170, 170],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)

    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Before &amp; After Report", TITLE_STYLE))
    elements.append(Spacer(1, 6))
    elements.append(HRule(usable_w, thickness=1, color=black))
    elements.append(Spacer(1, 12))

    return elements


def _escape(text):
    """Escape HTML special chars for ReportLab Paragraph."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
