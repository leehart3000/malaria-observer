import factory
import factory.fuzzy

from datasets.factories import DatasetFactory

from .models import SampleRecord


class SampleRecordFactory(factory.django.DjangoModelFactory[SampleRecord]):
    class Meta:
        model = SampleRecord

    sample = factory.Sequence(lambda n: f"SAMPLE{n}")
    study = factory.Faker("word")
    all_samples_same_case = factory.SelfAttribute("sample")
    population = "AF-W"
    qc_pass = True
    exclusion_reason = "Analysis_set"
    sample_type = "gDNA"
    was_in_previous_release = False
    source_order = factory.Sequence(lambda n: n)
    ena = factory.Sequence(lambda n: f"ERR{n:07d}")
    dataset = factory.SubFactory(DatasetFactory)
