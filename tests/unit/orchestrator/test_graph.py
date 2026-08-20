from __future__ import annotations

from orchestrator.graph.build_graph import build_initial_run_state, build_orchestrator_graph
from orchestrator.models.task import QAResult, Task
from orchestrator.storage.task_store import TaskStore


class FakeQARunner:
    def run(self, *, task_id: str, prompt: str, cwd: str, timeout=None):
        return QAResult(task_id=task_id, status="accepted", summary="Accepted", issues=[])


def test_graph_executes_minimal_flow(tmp_path):
    backlog_path = tmp_path / "backlog.json"
    store = TaskStore(backlog_path)
    store.save_tasks([Task(id="T-1", title="Task", description="Task description")])
    graph = build_orchestrator_graph(task_store=store, qa_runner=FakeQARunner(), max_parallel_tasks=1)

    result = graph.invoke(build_initial_run_state("run-1"))

    assert result["phase"] == "route_accepted_or_rejected"
    assert result["human_approval_required"] is False
    assert result["current_task_ids"] == ["T-1"]
    assert len(result["qa_results"]) == 1
