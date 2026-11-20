import logging

import pytest

from app.core.logging_config import attach_error_handler


class _Collect(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture()
def error_handler():
    handler = _Collect()
    attach_error_handler(handler)
    yield handler
    for logger in [logging.getLogger()] + [
        logging.getLogger(name) for name in logging.root.manager.loggerDict
    ]:
        if handler in getattr(logger, "handlers", []):
            logger.removeHandler(handler)


@pytest.mark.parametrize(
    "logger_name",
    [
        # Library loggers propagate to the root logger.
        "tessera_sdk.infra.events.nats_router",
        # The app's loggers stop propagation at "uvicorn" and "app".
        "uvicorn",
        "uvicorn.error",
        "app.commands.access_rules.create_access_rule_command",
    ],
)
def test_errors_from_every_logger_are_reported_once(error_handler, logger_name):
    logging.getLogger(logger_name).error("boom")

    assert [r.name for r in error_handler.records] == [logger_name]


def test_below_error_is_not_reported(error_handler):
    logging.getLogger("tessera_sdk.infra.events.nats_router").warning("meh")
    logging.getLogger("app.anything").warning("meh")

    assert error_handler.records == []


def test_attaching_twice_does_not_duplicate_reports(error_handler):
    attach_error_handler(error_handler)

    logging.getLogger("tessera_sdk.anything").error("boom")

    assert len(error_handler.records) == 1
