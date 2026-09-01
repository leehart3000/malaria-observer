import django_filters
from django import forms
from django.db.models import Q, QuerySet

from .models import SampleRecord

SORTABLE_COLUMNS = [
    ("sample", "Sample"),
    ("source_study", "Source Study"),
    ("country", "Country"),
    ("year", "Year"),
    ("qc_pass", "QC Pass"),
    ("sample_type", "Sample Type"),
    ("ena", "ENA"),
]
SORT_FIELDS = [field for field, _ in SORTABLE_COLUMNS]

GENERAL_SEARCH_FIELDS = ["sample", "study", "country", "sample_type", "ena"]

# Nullable columns checked by the "Missing" checkbox, handled directly
# in the view (see ExplorerTableView.get_queryset) rather than through
# this FilterSet -- a plain presence/absence checkbox interacts
# awkwardly with django-filter's BooleanFilter/NullBooleanField widget
# plumbing, so a direct query-param check is more transparent here.
MISSING_VALUE_FIELDS = ["country", "year", "ena"]


class SampleRecordFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method="filter_general",
        label="Text Filter",
        widget=forms.TextInput(attrs={"size": "40"}),
    )
    year = django_filters.NumberFilter(
        label="Year",
        widget=forms.NumberInput(attrs={"maxlength": "4", "style": "width: 5em;"}),
    )
    qc_pass = django_filters.TypedChoiceFilter(
        label="QC Pass",
        choices=(("", ""), ("true", "True"), ("false", "False")),
        coerce=lambda value: value == "true",
        empty_value="",
    )

    class Meta:
        model = SampleRecord
        fields = ["q", "year", "qc_pass"]

    def filter_general(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        if not value:
            return queryset
        query = Q()
        for field in GENERAL_SEARCH_FIELDS:
            query |= Q(**{f"{field}__icontains": value})
        return queryset.filter(query)
