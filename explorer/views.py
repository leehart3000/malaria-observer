from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from datasets.models import Dataset

from .models import SampleRecord


class ExplorerTableView(ListView):
    template_name = "explorer/table.html"
    context_object_name = "samples"
    paginate_by = 50

    def get_queryset(self):
        dataset_id = self.request.GET.get("set")
        self.dataset = get_object_or_404(Dataset, dataset_id=dataset_id)
        return SampleRecord.objects.filter(dataset=self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dataset"] = self.dataset
        return context
