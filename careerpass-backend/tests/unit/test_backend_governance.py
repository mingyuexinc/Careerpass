from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = BACKEND_ROOT.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_backend_bootstrap_gate_is_declared_at_both_project_levels() -> None:
    root_agents = _read(REPOSITORY_ROOT / "AGENTS.md")
    backend_agents = _read(BACKEND_ROOT / "AGENTS.md")

    assert "后端任务强制启动门禁" in root_agents
    assert "第一次仓库读取" in root_agents
    assert "## 0. 后端任务强制启动门禁" in backend_agents
    assert "第一次仓库读取必须完整包含" in backend_agents
    assert "scripts/backend-readiness.ps1" in backend_agents
    assert "不得据此断言 Docker CLI 未安装" in backend_agents


def test_readiness_evidence_gate_is_part_of_workflow_and_slice_template() -> None:
    workflow = _read(REPOSITORY_ROOT / ".harness" / "rules" / "AI coding workflow.md")
    template = _read(
        BACKEND_ROOT
        / "docs"
        / "development"
        / "slices"
        / "slice-technical-design-template.md"
    )

    assert "scripts/backend-readiness.ps1" in workflow
    assert "execution_denied" in workflow
    assert "启动门禁证据" in template
    assert "故障案例匹配" in template
    assert "预检状态与时间" in template


def test_backend_readiness_script_preserves_docker_conclusion_boundaries() -> None:
    script = _read(BACKEND_ROOT / "scripts" / "backend-readiness.ps1")

    assert "Get-Command docker" in script
    assert "Test-Path -LiteralPath" in script
    assert "$env:LOCALAPPDATA" in script
    assert '"absolute_path"' in script
    assert '"execution_denied"' in script
    assert '"engine_status_unverified"' in script
    assert '@("version", "--format", "{{.Server.Version}}")' in script
    assert '"config", "--quiet"' in script
