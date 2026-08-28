from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List, Optional

from reportlab.pdfbase.pdfmetrics import stringWidth

from .data_assembler import LogBookData

A4_WIDTH = 595.28
A4_HEIGHT = 841.89


@dataclass
class Placement:
    """A single overlay instruction for one template page (1-based index)."""

    page: int
    x: float
    y: float
    text: Optional[str] = None
    image_path: Optional[str] = None
    font_size: float = 9
    font: str = "Helvetica"
    align: str = "left"
    wrap_width: Optional[float] = None
    image_max_w: float = 70
    image_max_h: float = 90


class TemplateMappingService:
    """Locates template anchors and maps assembled data to overlay placements.

    The official 40-page template is the immutable master. This service never
    recreates pages; it only computes *where* real data must be drawn on top
    of the existing static layout.
    """

    TEMPLATE_NAME = "Project Log book.pdf"

    def __init__(self, template_bytes: bytes):
        import pypdf

        self._reader = pypdf.PdfReader(io.BytesIO(template_bytes))
        # Pre-extract runs per page for fast anchor lookup.
        self._runs: list[list[dict]] = [
            self._extract_runs(p) for p in self._reader.pages
        ]

    # ------------------------------------------------------------------ #
    # Run extraction
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_runs(page) -> list[dict]:
        runs: list[dict] = []

        def visitor(text, cm, tm, fd, sc):
            if text:
                runs.append(
                    {
                        "text": text,
                        "x": tm[4],
                        "y": tm[5],
                        "size": sc if sc else 9,
                    }
                )

        try:
            page.extract_text(visitor_text=visitor)
        except Exception:
            pass
        return runs

    # ------------------------------------------------------------------ #
    # Anchor lookup
    # ------------------------------------------------------------------ #
    def find_anchor(
        self, page_index: int, anchor: str, occurrence: int = 0
    ) -> Optional[dict]:
        """Return the run dict for the given anchor (1-based page)."""
        anchor = anchor.strip()
        if not anchor:
            return None
        runs = self._runs[page_index - 1]
        found = 0
        for run in runs:
            stripped = (run["text"] or "").strip()
            idx = stripped.find(anchor)
            if idx != -1:
                if found == occurrence:
                    # Compute x at the start of the matched substring.
                    prefix = stripped[:idx]
                    x = run["x"] + stringWidth(prefix, "Helvetica", run["size"])
                    return {
                        "x": x,
                        "y": run["y"],
                        "size": run["size"],
                        "text": stripped,
                    }
                found += 1
        return None

    # ------------------------------------------------------------------ #
    # Public: build all placements
    # ------------------------------------------------------------------ #
    def build_placements(self, data: LogBookData) -> List[Placement]:
        p: List[Placement] = []
        p.extend(self._page1(data))
        p.extend(self._member_pages(data))
        p.extend(self._page5(data))
        p.extend(self._page6(data))
        p.extend(self._topic_pages(data))
        p.extend(self._committee_pages(data))
        p.extend(self._external_feedback_pages(data))
        p.extend(self._competition_pages(data))
        p.extend(self._sponsored_pages(data))
        # Pages 2, 9-21 (activity charts), 11-12 (RTM), 14-15 (cost),
        # 22-23/30-31 (review covers), 26/36 (checklists), 40 (notes) keep
        # the official static content unchanged.
        return [pl for pl in p if pl is not None]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _after(
        self,
        page,
        anchor,
        value,
        occurrence=0,
        font_size=None,
        uppercase=False,
        wrap_width=None,
    ):
        if not value:
            return None
        loc = self.find_anchor(page, anchor, occurrence)
        if not loc:
            return None
        fs = font_size or loc["size"]
        x = loc["x"] + stringWidth(anchor.strip(), "Helvetica", fs)
        return Placement(
            page=page,
            x=x,
            y=loc["y"],
            text=value.upper() if uppercase else value,
            font_size=fs,
            wrap_width=wrap_width,
        )

    def _below(
        self,
        page,
        anchor,
        value,
        occurrence=0,
        dy=16,
        wrap_width=None,
        font_size=None,
    ):
        if not value:
            return None
        loc = self.find_anchor(page, anchor, occurrence)
        if not loc:
            return None
        fs = font_size or loc["size"]
        return Placement(
            page=page,
            x=loc["x"],
            y=loc["y"] - dy,
            text=value,
            font_size=fs,
            wrap_width=wrap_width,
        )

    # ------------------------------------------------------------------ #
    # Page 1
    # ------------------------------------------------------------------ #
    def _page1(self, data: LogBookData) -> List[Placement]:
        out = []
        out.append(self._after(1, "Department of ", data.department_name))
        out.append(self._after(1, "BE PROJECT LOG BOOK A.Y. ", data.academic_year))
        out.append(self._after(1, "Group No: ", data.group_number))
        out.append(
            self._after(1, "Project Title: ", data.project_title, wrap_width=380)
        )
        out.append(self._after(1, "Area of Project: ", data.area))
        out.append(self._after(1, "Project Guide: ", data.guide_name))
        return out

    # ------------------------------------------------------------------ #
    # Member pages (3 and 4)
    # ------------------------------------------------------------------ #
    def _member_pages(self, data: LogBookData) -> List[Placement]:
        out: List[Placement] = []
        sub_fields = [
            ("Name:", "name"),
            ("TE Result:", "te_result"),
            ("Roll No:", "roll_number"),
            ("Mobile No:", "mobile"),
            ("Exam Seat No:", "exam_seat_number"),
            ("Email ID:", "email"),
            ("Contribution:", "contribution"),
        ]
        for member_idx, member in enumerate(data.members):
            if member_idx >= 4:  # template has slots for 4 members
                break
            page = 3 if member_idx < 2 else 4
            occ = member_idx % 2
            for anchor, attr in sub_fields:
                out.append(self._after(page, anchor, getattr(member, attr), occ))
            # Photo
            if member.photo_path:
                loc = self.find_anchor(page, "photo", occ)
                if loc:
                    out.append(
                        Placement(
                            page=page,
                            x=loc["x"],
                            y=loc["y"],
                            image_path=member.photo_path,
                        )
                    )
        return out

    # ------------------------------------------------------------------ #
    # Page 5 - Undertaking
    # ------------------------------------------------------------------ #
    def _page5(self, data: LogBookData) -> List[Placement]:
        out = []
        out.append(self._after(5, "B. E. ", data.department_name))
        out.append(self._after(5, "batch ", data.academic_year))
        out.append(self._after(5, "academic year ", data.academic_year))
        out.append(
            self._below(
                5, "The Project entitled", data.project_title, dy=20, wrap_width=400
            )
        )
        for i, member in enumerate(data.members[:5]):
            if member.name:
                out.append(self._after(5, f"{i + 1}.", member.name, occurrence=i))
        return out

    # ------------------------------------------------------------------ #
    # Page 6 - Schedule
    # ------------------------------------------------------------------ #
    def _page6(self, data: LogBookData) -> List[Placement]:
        out = []
        for label, date_str in data.schedule_dates.items():
            if not date_str:
                continue
            loc = self.find_anchor(6, label, 0)
            if not loc:
                continue
            x = loc["x"] + stringWidth(label, "Helvetica", loc["size"]) + 8
            out.append(
                Placement(page=6, x=x, y=loc["y"], text=date_str, font_size=loc["size"])
            )
        return out

    # ------------------------------------------------------------------ #
    # Topic finalization (pages 7 / 8)
    # ------------------------------------------------------------------ #
    def _topic_pages(self, data: LogBookData) -> List[Placement]:
        out = []
        if data.topic_1:
            out.append(
                self._below(
                    7, "Proposed Project Topic 1:", data.topic_1, dy=18, wrap_width=420
                )
            )
        if data.topic_1_approved:
            out.append(self._after(7, "Approved (Yes / No)", "Yes"))
        elif data.topic_1_approved is not None:
            out.append(self._after(7, "Approved (Yes / No)", "No"))
        out.append(
            self._after(7, "Name and Signature of Reviewer 1:", data.reviewer_1_name)
        )
        out.append(self._after(7, "Reviewer 2:", data.reviewer_2_name))
        out.append(
            self._after(7, "Signature of Project Coordinator:", data.coordinator_name)
        )
        # Topic 2 only when topic 1 rejected (template rule).
        if data.topic_1_approved is False and data.topic_2:
            out.append(
                self._below(
                    8, "Proposed Project Topic 2:", data.topic_2, dy=18, wrap_width=420
                )
            )
        return out

    # ------------------------------------------------------------------ #
    # Evaluation committee (pages 25, 34)
    # ------------------------------------------------------------------ #
    def _committee_pages(self, data: LogBookData) -> List[Placement]:
        out = []
        for page in (25, 34):
            out.append(self._after(page, "Prof.", data.evaluator_1_name, occurrence=0))
            out.append(self._after(page, "Prof.", data.evaluator_2_name, occurrence=1))
        return out

    # ------------------------------------------------------------------ #
    # External examiner feedback (pages 27, 35)
    # ------------------------------------------------------------------ #
    def _external_feedback_pages(self, data: LogBookData) -> List[Placement]:
        out = []
        for page in (27, 35):
            out.append(self._after(page, "Project Title:", data.project_title))
        return out

    # ------------------------------------------------------------------ #
    # Competition + Publication tables (pages 28, 39)
    # ------------------------------------------------------------------ #
    def _competition_pages(self, data: LogBookData) -> List[Placement]:
        out = []
        for page in (28, 39):
            # Competition columns
            headers = {
                "name": self.find_anchor(page, "Name of Project"),
                "date": self.find_anchor(page, "Date"),
                "college": self.find_anchor(page, "College &"),
                "type": self.find_anchor(page, "Type of participation"),
                "award": self.find_anchor(page, "Award/"),
            }
            if headers["name"]:
                row_y = (
                    min(
                        (h["y"] for h in headers.values() if h),
                        default=headers["name"]["y"],
                    )
                    - 16
                )
                for i, comp in enumerate(data.competitions[:4]):
                    y = row_y - i * 16
                    if comp.name and headers["name"]:
                        out.append(
                            Placement(
                                page=page,
                                x=headers["name"]["x"],
                                y=y,
                                text=comp.name,
                                font_size=8,
                            )
                        )
                    if comp.date and headers["date"]:
                        out.append(
                            Placement(
                                page=page,
                                x=headers["date"]["x"],
                                y=y,
                                text=comp.date,
                                font_size=8,
                            )
                        )
                    if comp.college and headers["college"]:
                        out.append(
                            Placement(
                                page=page,
                                x=headers["college"]["x"],
                                y=y,
                                text=comp.college,
                                font_size=8,
                            )
                        )
                    if comp.participation_type and headers["type"]:
                        out.append(
                            Placement(
                                page=page,
                                x=headers["type"]["x"],
                                y=y,
                                text=comp.participation_type,
                                font_size=8,
                            )
                        )
                    if comp.award and headers["award"]:
                        out.append(
                            Placement(
                                page=page,
                                x=headers["award"]["x"],
                                y=y,
                                text=comp.award,
                                font_size=8,
                            )
                        )
            # Publication columns
            pub_headers = {
                "title": self.find_anchor(page, "Title of Paper"),
                "conf": self.find_anchor(page, "Conference"),
                "issn": self.find_anchor(page, "ISSN No."),
                "vol": self.find_anchor(page, "Vol No."),
                "page": self.find_anchor(page, "Page no"),
            }
            if pub_headers["title"]:
                base_y = min(
                    (h["y"] for h in pub_headers.values() if h),
                    default=pub_headers["title"]["y"],
                )
                # Publications table sits below the competition table.
                row_y = base_y - 16
                for i, pub in enumerate(data.publications[:4]):
                    y = row_y - i * 16
                    if pub.title and pub_headers["title"]:
                        out.append(
                            Placement(
                                page=page,
                                x=pub_headers["title"]["x"],
                                y=y,
                                text=pub.title,
                                font_size=8,
                            )
                        )
                    if pub.conference and pub_headers["conf"]:
                        out.append(
                            Placement(
                                page=page,
                                x=pub_headers["conf"]["x"],
                                y=y,
                                text=pub.conference,
                                font_size=8,
                            )
                        )
                    if pub.issn and pub_headers["issn"]:
                        out.append(
                            Placement(
                                page=page,
                                x=pub_headers["issn"]["x"],
                                y=y,
                                text=pub.issn,
                                font_size=8,
                            )
                        )
                    if pub.volume and pub_headers["vol"]:
                        out.append(
                            Placement(
                                page=page,
                                x=pub_headers["vol"]["x"],
                                y=y,
                                text=pub.volume,
                                font_size=8,
                            )
                        )
                    if pub.page_no and pub_headers["page"]:
                        out.append(
                            Placement(
                                page=page,
                                x=pub_headers["page"]["x"],
                                y=y,
                                text=pub.page_no,
                                font_size=8,
                            )
                        )
        return out

    # ------------------------------------------------------------------ #
    # Sponsored project (pages 37, 38)
    # ------------------------------------------------------------------ #
    def _sponsored_pages(self, data: LogBookData) -> List[Placement]:
        out = []
        if data.is_sponsored and data.sponsored_company:
            for page in (37, 38):
                out.append(
                    self._after(
                        page, "Name of the Sponsored Company:", data.sponsored_company
                    )
                )
        return out
