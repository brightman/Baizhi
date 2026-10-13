from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / ".codex" / "skills" / "baizhi-apps"


def test_skill_routes_apps_work_through_standalone_cli_and_named_hosts():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    hosts = (SKILL_ROOT / "references" / "hosts.md").read_text(encoding="utf-8")
    reference = (SKILL_ROOT / "references" / "cli-reference.md").read_text(encoding="utf-8")

    assert "baizhi-apps" in skill
    assert "cli-reference.md" in skill
    assert "baizhi-apps env set" in hosts
    assert "baizhi-apps data get" in reference
    assert "production" in reference and "staging" in reference and "test" in reference


def test_skill_never_falls_back_to_mcp_runtime_session_or_direct_database_access():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    api = (SKILL_ROOT / "references" / "apps-api.md").read_text(encoding="utf-8")

    assert "Never fall back to MCP" in skill
    assert "App Runtime Session" in api
    assert "GraphQL" in api
    assert "must not" in api
    assert "PostgreSQL" in skill


def test_skill_keeps_appid_manifest_and_confirmation_gates_for_all_lifecycle_paths():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    lifecycle = (SKILL_ROOT / "references" / "app-lifecycle.md").read_text(encoding="utf-8")
    h5 = (SKILL_ROOT / "references" / "h5-hosting.md").read_text(encoding="utf-8")

    assert "APPID-first lifecycle" in skill
    assert "inspect the App first" in skill
    assert "schema apply" in lifecycle
    assert "--confirm" in lifecycle
    assert "baizhi-apps h5 publish" in h5
    assert "baizhi-apps h5 rollback" in h5
    assert "release_id" in h5


def test_cli_package_does_not_depend_on_agent_runtime_or_mcp():
    package = (REPO_ROOT / "tools" / "baizhi-apps-cli" / "pyproject.toml").read_text(encoding="utf-8")

    assert '"httpx>=0.28"' in package
    assert '"keyring>=25"' in package
    assert "mcp" not in package.lower()
    assert "baizhi-agent-runtime" not in package
