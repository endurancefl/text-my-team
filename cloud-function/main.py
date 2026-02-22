import io
import json
import os
from collections import OrderedDict

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
from PIL import Image


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
