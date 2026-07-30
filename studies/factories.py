import wagtail_factories

from .models import StudyIndexPage


class StudyIndexPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = StudyIndexPage
