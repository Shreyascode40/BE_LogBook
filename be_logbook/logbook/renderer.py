from __future__ import annotations

import io
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .template_mapping import A4_HEIGHT, A4_WIDTH, Placement

EXPECTED_PAGE_COUNT = 40


class PDFRenderer:
    """Renders overlay placements onto a copy of the official template.

    The template is never modified; overlays are drawn on transparent A4
    pages and merged on top of each template page, preserving the exact
    static layout (logos, headings, tables, official wording).
    """

    MARGIN = 18  # keep text inside page boundaries

    def render(self, template_bytes: bytes, placements: List[Placement]) -> bytes:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(template_bytes))
        writer = pypdf.PdfWriter()

        by_page: dict[int, List[Placement]] = {}
        for pl in placements:
            by_page.setdefault(pl.page, []).append(pl)

        for idx, page in enumerate(reader.pages, start=1):
            page_placements = by_page.get(idx, [])
            if page_placements:
                overlay_bytes = self._build_overlay(page_placements)
                overlay_page = pypdf.PdfReader(io.BytesIO(overlay_bytes)).pages[0]
                page.merge_page(overlay_page)
            writer.add_page(page)

        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()

    # ------------------------------------------------------------------ #
    def _build_overlay(self, placements: List[Placement]) -> bytes:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        for pl in placements:
            if pl.image_path:
                self._draw_image(c, pl)
            elif pl.text is not None:
                self._draw_text(c, pl)
        c.save()
        return buf.getvalue()

    def _draw_text(self, c, pl: Placement) -> None:
        font = pl.font
        size = pl.font_size or 9
        text = pl.text
        max_width = A4_WIDTH - pl.x - self.MARGIN

        if pl.wrap_width:
            lines = self._wrap(text, font, size, pl.wrap_width)
        else:
            # Single line: auto-shrink font to stay inside the page.
            while size > 6 and stringWidth(text, font, size) > max_width:
                size -= 0.5
            lines = [text]

        c.setFont(font, size)
        y = pl.y
        leading = size + 2
        for line in lines:
            if pl.align == "center":
                c.drawCentredString(pl.x, y, line)
            else:
                c.drawString(pl.x, y, line)
            y -= leading

    def _draw_image(self, c, pl: Placement) -> None:
        from PIL import Image

        try:
            with Image.open(pl.image_path) as img:
                img_w, img_h = img.size
        except Exception:
            return
        if img_w <= 0 or img_h <= 0:
            return
        # Fit within max box preserving aspect ratio.
        max_w, max_h = pl.image_max_w, pl.image_max_h
        ratio = min(max_w / img_w, max_h / img_h)
        w = img_w * ratio
        h = img_h * ratio
        # Anchor centered on the "photo" text location.
        x0 = pl.x - w / 2
        y0 = pl.y - h / 2
        # Clamp inside page.
        x0 = max(self.MARGIN, min(x0, A4_WIDTH - self.MARGIN - w))
        y0 = max(self.MARGIN, min(y0, A4_HEIGHT - self.MARGIN - h))
        try:
            c.drawImage(
                pl.image_path, x0, y0, width=w, height=h, preserveAspectRatio=True
            )
        except Exception:
            return

    @staticmethod
    def _wrap(text: str, font: str, size: float, max_width: float) -> List[str]:
        words = text.split()
        if not words:
            return [""]
        lines: List[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if stringWidth(candidate, font, size) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines


class PDFValidationService:
    """Validates that the generated PDF preserves the official structure."""

    @staticmethod
    def validate(pdf_bytes: bytes) -> dict:
        import pypdf

        result = {
            "valid": False,
            "page_count": 0,
            "errors": [],
        }
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as exc:  # noqa: BLE001
            result["errors"].append(f"PDF could not be opened: {exc}")
            return result

        page_count = len(reader.pages)
        result["page_count"] = page_count
        if page_count != EXPECTED_PAGE_COUNT:
            result["errors"].append(
                f"Page count is {page_count}, expected {EXPECTED_PAGE_COUNT}."
            )
        try:
            _ = reader.pages[0].mediabox
        except Exception as exc:  # noqa: BLE001
            result["errors"].append(f"First page is invalid: {exc}")
        result["valid"] = page_count == EXPECTED_PAGE_COUNT and not result["errors"]
        return result
