import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


def init_sentry(dsn: str) -> None:
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[DjangoIntegration()],
            traces_sample_rate=0.2,
            send_default_pii=False,
        )
