import factory
import factory.fuzzy

from datasets.factories import DatasetFactory

from .models import SampleRecord


class SampleRecordFactory(factory.django.DjangoModelFactory[SampleRecord]):
    class Meta:
        model = SampleRecord

    sample = factory.Sequence(lambda n: f"SAMPLE{n}")
    source_study = factory.Faker("word")
    all_samples_same_case = factory.SelfAttribute("sample")
    population = "AF-W"
    qc_pass = True
    exclusion_reason = "Analysis_set"
    sample_type = "gDNA"
    was_in_previous_release = False
    dataset = factory.SubFactory(DatasetFactory)
