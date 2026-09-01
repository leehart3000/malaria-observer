from django.db.models import Count, Q
from django.http import HttpRequest, QueryDict
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from datasets.models import Dataset

from .filters import (
    LEVEL_FIELDS,
    MISSING_VALUE_FIELDS,
    SORT_FIELDS,
    SORTABLE_COLUMNS,
    SampleRecordFilter,
)
from .models import SampleRecord

PAGE_SIZE_CHOICES = [25, 50, 100, 200]
SHOW_ALL_THRESHOLD = 1000


class DatasetFilteredMixin:
    """Shared dataset lookup + text/QC/missingness filtering, used by
    both the table and geo (map) views so they stay in parity."""

    request: HttpRequest  # provided by the View this mixin is combined with

    def get_filtered_queryset(self):
        dataset_id = self.request.GET.get("set")
        self.dataset = get_object_or_404(Dataset, dataset_id=dataset_id)
        base_queryset = SampleRecord.objects.filter(dataset=self.dataset)

        self.filterset = SampleRecordFilter(self.request.GET, queryset=base_queryset)
        queryset = self.filterset.qs

        filterset_active = False
        if self.filterset.form.is_valid():
            filterset_active = any(
                value not in (None, "", [])
                for value in self.filterset.form.cleaned_data.values()
            )

        self.missingness = self.request.GET.get("missingness")
        if self.missingness in ("with", "without"):
            missing_query = Q()
            for field in MISSING_VALUE_FIELDS:
                missing_query |= Q(**{f"{field}__isnull": True})
            queryset = (
                queryset.filter(missing_query)
                if self.missingness == "with"
                else queryset.exclude(missing_query)
            )

        self.is_filtered = filterset_active or self.missingness in ("with", "without")
        return queryset

    def _query(self, overrides=None, remove=None) -> str:
        query: QueryDict = self.request.GET.copy()
        for key in remove or []:
            query.pop(key, None)
        for key, value in (overrides or {}).items():
            query[key] = value
        for key in [k for k, v in query.items() if v == ""]:
            query.pop(key)
        return query.urlencode()


class ExplorerTableView(DatasetFilteredMixin, ListView):
    template_name = "explorer/table.html"
    context_object_name = "samples"
    paginate_by = 50

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get("page_size")
        if page_size == "all":
            if queryset.count() <= SHOW_ALL_THRESHOLD:
                return None
            return self.paginate_by
        if page_size and page_size.isdigit() and int(page_size) in PAGE_SIZE_CHOICES:
            return int(page_size)
        return self.paginate_by

    def get_queryset(self):
        queryset = self.get_filtered_queryset()

        self.sort = self.request.GET.get("sort")
        self.order = self.request.GET.get("order")
        if self.sort in SORT_FIELDS and self.order in ("asc", "desc"):
            prefix = "-" if self.order == "desc" else ""
            queryset = queryset.order_by(f"{prefix}{self.sort}")
        else:
            queryset = queryset.order_by("source_order")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        context["filter"] = self.filterset
        context["is_filtered"] = self.is_filtered

        sort_columns = []
        for field, label in SORTABLE_COLUMNS:
            if self.sort == field and self.order == "asc":
                query = self._query({"sort": field, "order": "desc"}, remove=["page"])
                arrow = "↑"
            elif self.sort == field and self.order == "desc":
                query = self._query(remove=["sort", "order", "page"])
                arrow = "↓"
            else:
                query = self._query({"sort": field, "order": "asc"}, remove=["page"])
                arrow = ""
            sort_columns.append(
                {"field": field, "label": label, "query": query, "arrow": arrow}
            )
        context["sort_columns"] = sort_columns

        context["reset_query"] = f"set={self.dataset.dataset_id}"

        total_count = (
            context["paginator"].count
            if context.get("paginator") is not None
            else len(context["samples"])
        )
        current_page_size = self.request.GET.get("page_size", "")
        context["page_size_choices"] = PAGE_SIZE_CHOICES
        context["current_page_size"] = current_page_size
        context["show_all_available"] = total_count <= SHOW_ALL_THRESHOLD
        context["page_size_query"] = {
            str(size): self._query({"page_size": size}, remove=["page"])
            for size in PAGE_SIZE_CHOICES
        }
        if context["show_all_available"]:
            context["page_size_query"]["all"] = self._query(
                {"page_size": "all"}, remove=["page"]
            )
        context["page_size_query"]["default"] = self._query(
            remove=["page_size", "page"]
        )

        if context["is_paginated"]:
            if context["page_obj"].has_previous():
                context["page_query_first"] = self._query({"page": 1})
                context["page_query_prev"] = self._query(
                    {"page": context["page_obj"].previous_page_number()}
                )
            if context["page_obj"].has_next():
                context["page_query_next"] = self._query(
                    {"page": context["page_obj"].next_page_number()}
                )
                context["page_query_last"] = self._query(
                    {"page": context["paginator"].num_pages}
                )

        return context


class ExplorerGeoView(DatasetFilteredMixin, ListView):
    """Aggregates filtered samples into one point per unique location
    (at the chosen coordinate level), with a sample count per point --
    plotting one marker per sample would be impractical at dataset
    sizes of tens of thousands of rows."""

    template_name = "explorer/geo.html"
    context_object_name = "locations"

    def get_queryset(self):
        queryset = self.get_filtered_queryset()

        level = self.request.GET.get("level")
        if level not in LEVEL_FIELDS:
            level = "country"
        self.level = level
        fields = LEVEL_FIELDS[self.level]

        queryset = queryset.exclude(**{f"{fields['lat']}__isnull": True})
        return (
            queryset.values(fields["lat"], fields["lon"], fields["label"])
            .annotate(count=Count("id"))
            .order_by("-count")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        context["filter"] = self.filterset
        context["is_filtered"] = self.is_filtered
        context["level"] = self.level
        context["reset_query"] = f"set={self.dataset.dataset_id}"

        fields = LEVEL_FIELDS[self.level]
        context["locations_data"] = [
            {
                "lat": loc[fields["lat"]],
                "lon": loc[fields["lon"]],
                "label": loc[fields["label"]] or "Unknown",
                "count": loc["count"],
            }
            for loc in context["locations"]
        ]
        return context
