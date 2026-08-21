import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


def init_sentry(dsn: str, environment: str) -> None:
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[DjangoIntegration()],
            send_default_pii=False,
            traces_sample_rate=0.0,
        )
