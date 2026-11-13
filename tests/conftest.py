import pytest
from mistralai.workflows import testing as workflows_testing


def _align_test_task_queue() -> None:
    from mistralai.workflows.core.config import config as app_config

    app_config.temporal.task_queue = workflows_testing.DEFAULT_TEST_TASK_QUEUE


_align_test_task_queue()


@pytest.fixture(autouse=True)
def disable_otel(monkeypatch):
    import mistralai.workflows.core.workflow as workflows_core_workflow

    monkeypatch.setattr(
        workflows_core_workflow,
        "set_otel_trace_id_in_current_workflow_execution",
        lambda: None,
    )
