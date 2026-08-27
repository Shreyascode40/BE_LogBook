from __future__ import annotations

from django.contrib import admin

from be_logbook.co_po.models import CO
from be_logbook.co_po.models import COPOAttainment
from be_logbook.co_po.models import PO


admin.site.register(CO)
admin.site.register(PO)
admin.site.register(COPOAttainment)
