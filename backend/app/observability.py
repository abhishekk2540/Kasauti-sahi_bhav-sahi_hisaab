"""Optional Sentry error monitoring. Does nothing unless SENTRY_DSN is set."""
import logging
import os
from importlib import import_module

log = logging.getLogger(__name__)


def init_sentry() -> bool:
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return False
    sentry_sdk = import_module("sentry_sdk")

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("APP_ENV", "development"),
        release=os.getenv("GIT_SHA") or None,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0")),
        send_default_pii=False,          # no IPs / cookies / auth headers
        max_request_body_size="never",   # never ship request bodies (login passwords, customer phones)
    )
    log.info("Sentry enabled")
    return True
