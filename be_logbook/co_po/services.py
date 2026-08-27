from __future__ import annotations

import decimal
from collections import defaultdict

from be_logbook.reviews.models import Review
from be_logbook.reviews.models import ReviewMark


class COPOService:
    """Computes CO/PO attainment from finalized review marks.

    IMPORTANT: The official BE marking Excel workbook (Stage-I / Stage-II
    rubric, maximum marks and CO mapping) was NOT available in this repository
    at build time. Therefore this service implements a transparent, documented
    DEFAULT method only:

        normalized_criterion = obtained / max
        CO attainment  = weighted avg of normalized_criterion over criteria
                         mapped to that CO (weight = criterion.weight)
        PO attainment  = weighted avg of normalized_criterion over criteria
                         mapped to that PO

    This is deliberately simple and is NOT the official academic formula.
    Replace `compute_for_review` / `compute_for_group` with the official
    mapping once the workbook is supplied. The interface is stable.
    """

    ATTAINMENT_METHOD = "weighted_normalized_default"

    @classmethod
    def compute_for_review(cls, review: Review) -> dict[str, decimal.Decimal]:
        co_ratios: dict[str, list[tuple[decimal.Decimal, decimal.Decimal]]] = (
            defaultdict(list)
        )
        po_ratios: dict[str, list[tuple[decimal.Decimal, decimal.Decimal]]] = (
            defaultdict(list)
        )
        for mark in review.marks.select_related("criterion").all():
            criterion = mark.criterion
            if criterion.max_marks and criterion.max_marks > 0:
                ratio = mark.obtained_marks / criterion.max_marks
            else:
                ratio = decimal.Decimal(0)
            weight = criterion.weight or decimal.Decimal(1)
            if criterion.co_code:
                co_ratios[criterion.co_code].append((ratio, weight))
            if criterion.po_code:
                po_ratios[criterion.po_code].append((ratio, weight))
        co_attainment = {
            co: cls._weighted_avg(pairs) for co, pairs in co_ratios.items()
        }
        po_attainment = {
            po: cls._weighted_avg(pairs) for po, pairs in po_ratios.items()
        }
        return {"co": co_attainment, "po": po_attainment}

    @classmethod
    def _weighted_avg(cls, pairs):
        total_w = decimal.Decimal(0)
        total = decimal.Decimal(0)
        for ratio, weight in pairs:
            total += ratio * weight
            total_w += weight
        if total_w == 0:
            return decimal.Decimal(0)
        return (total / total_w) * decimal.Decimal(100)

    @classmethod
    def compute_for_group(cls, group) -> dict:
        co_agg: dict[str, list[tuple[decimal.Decimal, decimal.Decimal]]] = defaultdict(
            list
        )
        po_agg: dict[str, list[tuple[decimal.Decimal, decimal.Decimal]]] = defaultdict(
            list
        )
        reviews = Review.objects.filter(
            group=group, status__in=("FINALIZED", "CORRECTED")
        ).select_related()
        for review in reviews:
            result = cls.compute_for_review(review)
            for co, val in result["co"].items():
                co_agg[co].append((val / decimal.Decimal(100), decimal.Decimal(1)))
            for po, val in result["po"].items():
                po_agg[po].append((val / decimal.Decimal(100), decimal.Decimal(1)))
        return {
            "co": {co: cls._weighted_avg(p) for co, p in co_agg.items()},
            "po": {po: cls._weighted_avg(p) for po, p in po_agg.items()},
        }

    @classmethod
    def snapshot_for_group(cls, group, request=None):
        """Persist attainment snapshots for a group."""
        from be_logbook.co_po.models import COPOAttainment

        data = cls.compute_for_group(group)
        COPOAttainment.objects.filter(group=group).delete()
        snapshots = []
        for co, val in data["co"].items():
            snapshots.append(
                COPOAttainment(
                    group=group,
                    co_code=co,
                    attainment=val,
                    method=cls.ATTAINMENT_METHOD,
                )
            )
        for po, val in data["po"].items():
            snapshots.append(
                COPOAttainment(
                    group=group,
                    po_code=po,
                    attainment=val,
                    method=cls.ATTAINMENT_METHOD,
                )
            )
        COPOAttainment.objects.bulk_create(snapshots)
        return snapshots
