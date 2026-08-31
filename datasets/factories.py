import factory
import wagtail_factories

from .models import Dataset, DatasetIndexPage


class DatasetIndexPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = DatasetIndexPage


class DatasetFactory(factory.django.DjangoModelFactory[Dataset]):
    class Meta:
        model = Dataset

    dataset_id = factory.Sequence(lambda n: f"ds{n}")
    name = factory.Sequence(lambda n: f"Dataset {n}")
