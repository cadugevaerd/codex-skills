#!/usr/bin/env python3
"""Deterministic contract validator for the mirrored LangGraph Architecture plugin."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
from typing import Any

PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parents[1]
VERSION = "1.0.0"
PLUGIN_NAME = "langgraph-architecture"
SKILLS = {
    "langgraph-architecture-plan": "langgraph_architect",
    "langgraph-repository-review": "langgraph_reviewer",
}
COMMON_PATHS = {
    "skills/langgraph-architecture-plan/SKILL.md",
    "skills/langgraph-architecture-plan/assets/LANGGRAPH-ARCHITECTURE-PLAN.example.md",
    "skills/langgraph-repository-review/SKILL.md",
    "skills/langgraph-repository-review/assets/LANGGRAPH-REVIEW.example.md",
    "tests/validate_contract.py",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    require(text.startswith("---\n"), f"frontmatter ausente: {path}")
    _, raw, body = text.split("---\n", 2)
    data: dict[str, Any] = {}
    current_list: str | None = None
    for line in raw.splitlines():
        if line.startswith("  - ") and current_list:
            value = line[4:].strip()
            values = data.setdefault(current_list, [])
            require(isinstance(values, list), f"lista inválida: {current_list}")
            values.append(value)
            continue
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"')
        if value:
            data[key] = value
            current_list = None
        else:
            data[key] = []
            current_list = key
    return data, body


def validate_common(runtime: str) -> None:
    actual = {
        str(path.relative_to(PLUGIN))
        for path in PLUGIN.rglob("*")
        if path.is_file()
    }
    require(COMMON_PATHS <= actual, f"bundle comum incompleto: {COMMON_PATHS - actual}")

    minimum_markers = [
        "quality_gate", "thread_id", "user_id", "trimming", "summarization",
        "grounding", "trajetória", "node isolado", "5–10", "HITL",
        "contexto isolado", "BLOCKED",
    ]
    for skill_name, role in SKILLS.items():
        path = PLUGIN / "skills" / skill_name / "SKILL.md"
        meta, body = frontmatter(path)
        require(meta.get("name") == skill_name, f"nome de skill incorreto: {path}")
        require(bool(meta.get("description")), f"descrição ausente: {path}")
        require(bool(meta.get("argument-hint")), f"argument-hint ausente: {path}")
        require(role in body, f"skill não roteia para {role}: {path}")
        require("não" in body.lower() and "fallback" in body.lower(), f"fallback não bloqueado: {path}")
        for marker in minimum_markers:
            require(marker.lower() in body.lower(), f"mínimo {marker!r} ausente em {path}")

    plan_example = (PLUGIN / "skills/langgraph-architecture-plan/assets/LANGGRAPH-ARCHITECTURE-PLAN.example.md").read_text(encoding="utf-8")
    for heading in (
        "## Arquitetura proposta", "## State schema e reducers",
        "## Quality gate, retries, HITL e limites", "## Observabilidade e evals",
        "## Matriz requisito → mudança → teste/evidência",
    ):
        require(heading in plan_example, f"heading ausente no plano exemplo: {heading}")
    review_example = (PLUGIN / "skills/langgraph-repository-review/assets/LANGGRAPH-REVIEW.example.md").read_text(encoding="utf-8")
    for marker in ("LG-001", "Severidade", "Localização", "Evidência", "Critério de aceite", "UNVERIFIED"):
        require(marker in review_example, f"campo ausente na revisão exemplo: {marker}")

    root_readme = (REPO / "README.md").read_text(encoding="utf-8")
    plugin_readme = (PLUGIN / "README.md").read_text(encoding="utf-8")
    require(PLUGIN_NAME in root_readme, "plugin ausente no README raiz")
    require("langgraph-architecture-plan" in root_readme, "skill plan ausente no README raiz")
    require("langgraph-repository-review" in root_readme, "skill review ausente no README raiz")
    require(PLUGIN_NAME in plugin_readme, "nome do plugin ausente no README do plugin")
    require("gpt-5.6" in plugin_readme if runtime == "codex" else "opus" in plugin_readme, "modelo topo ausente no README")


def validate_codex() -> None:
    manifest = load_json(PLUGIN / ".codex-plugin/plugin.json")
    market = load_json(REPO / ".agents/plugins/marketplace.json")
    entries = [item for item in market["plugins"] if item.get("name") == PLUGIN_NAME]
    require(len(entries) == 1, "entrada Codex deve ser única")
    entry = entries[0]
    require(manifest["version"] == VERSION == entry.get("version"), "drift de versão Codex")
    require(entry["source"] == {"source": "local", "path": "./plugins/langgraph-architecture"}, "source Codex incorreta")
    require(entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "policy Codex incorreta")

    agent_files = sorted(path.name for path in (PLUGIN / "agents").glob("*.toml"))
    require(agent_files == ["langgraph-architect.toml", "langgraph-reviewer.toml"], f"agents Codex inesperados: {agent_files}")
    expected = {
        "langgraph-architect.toml": ("langgraph_architect", "workspace-write"),
        "langgraph-reviewer.toml": ("langgraph_reviewer", "read-only"),
    }
    for filename, (name, sandbox) in expected.items():
        data = tomllib.loads((PLUGIN / "agents" / filename).read_text(encoding="utf-8"))
        require(data.get("name") == name, f"name incorreto: {filename}")
        require(bool(data.get("description")), f"description ausente: {filename}")
        require(data.get("model") == "gpt-5.6", f"modelo não topo: {filename}")
        require(data.get("model_reasoning_effort") == "max", f"reasoning não max: {filename}")
        require(data.get("sandbox_mode") == sandbox, f"sandbox incorreto: {filename}")
        require(bool(data.get("developer_instructions")), f"instructions ausentes: {filename}")
        require("__CODEX_HOME__" in data["developer_instructions"], f"placeholder CODEX_HOME ausente: {filename}")

    installer = PLUGIN / "scripts/install_codex_agents.py"
    original = 'profile = "keep"\n\n[agents.existing]\ndescription = "preserve"\n'
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "codex home with spaces"
        home.mkdir(parents=True)
        config = home / "config.toml"
        config.write_text(original, encoding="utf-8")
        cmd = [sys.executable, str(installer), "--codex-home", str(home)]
        for iteration in (1, 2):
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
            require(result.returncode == 0, f"install {iteration} falhou: {result.stderr}")
            parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            require(set(parsed["agents"]) == {"existing", "langgraph_architect", "langgraph_reviewer"}, "roles instaladas divergentes")
        backup = home / "config.toml.bak-langgraph-architecture"
        require(backup.read_text(encoding="utf-8") == original, "backup não preservou config original")
        installed = sorted(path.name for path in (home / "agents").glob("langgraph-*.toml"))
        require(installed == ["langgraph-architect.toml", "langgraph-reviewer.toml"], "arquivos instalados divergentes")
        for filename in installed:
            rendered = (home / "agents" / filename).read_text(encoding="utf-8")
            require("__CODEX_HOME__" not in rendered, f"placeholder não renderizado: {filename}")
            require(home.resolve().as_posix() in rendered, f"CODEX_HOME ativo ausente: {filename}")
        for rel in COMMON_PATHS:
            if rel.startswith("skills/"):
                require((home / "agents/langgraph-architecture-knowledge" / rel).is_file(), f"conhecimento ausente: {rel}")
        result = subprocess.run([*cmd, "--uninstall"], text=True, capture_output=True, timeout=30)
        require(result.returncode == 0, f"uninstall falhou: {result.stderr}")
        require(config.read_text(encoding="utf-8") == original, "uninstall não restaurou bytes originais")
        require(not (home / "agents/langgraph-architecture-knowledge").exists(), "knowledge residual")
        require(not any((home / "agents").glob("langgraph-*.toml")), "agent residual")

    for original_edge in ('profile = "keep"', ""):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / "config.toml"
            config.write_text(original_edge, encoding="utf-8")
            cmd = [sys.executable, str(installer), "--codex-home", str(home)]
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
            require(result.returncode == 0, f"install edge falhou: {result.stderr}")
            result = subprocess.run([*cmd, "--uninstall"], text=True, capture_output=True, timeout=30)
            require(result.returncode == 0, f"uninstall edge falhou: {result.stderr}")
            require(config.read_text(encoding="utf-8") == original_edge, "edge sem newline não foi restaurado byte a byte")

    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        config = home / "config.toml"
        conflict = "[agents.langgraph_architect]\ndescription = \"custom\"\n"
        config.write_text(conflict, encoding="utf-8")
        result = subprocess.run([sys.executable, str(installer), "--codex-home", str(home)], text=True, capture_output=True, timeout=30)
        require(result.returncode == 1, "conflito unmanaged deveria falhar")
        require(config.read_text(encoding="utf-8") == conflict, "conflito alterou config")


def validate_claude() -> None:
    manifest = load_json(PLUGIN / ".claude-plugin/plugin.json")
    market = load_json(REPO / ".claude-plugin/marketplace.json")
    entries = [item for item in market["plugins"] if item.get("name") == PLUGIN_NAME]
    require(len(entries) == 1, "entrada Claude deve ser única")
    entry = entries[0]
    require(manifest["version"] == VERSION == entry.get("version"), "drift de versão Claude")
    require(entry["source"] == "./plugins/langgraph-architecture", "source Claude incorreta")

    agent_files = sorted(path.name for path in (PLUGIN / "agents").glob("*.md"))
    require(agent_files == ["langgraph-architect.md", "langgraph-reviewer.md"], f"agents Claude inesperados: {agent_files}")
    expected = {
        "langgraph-architect.md": ("langgraph-architect", "langgraph-architecture:langgraph-architecture-plan", True),
        "langgraph-reviewer.md": ("langgraph-reviewer", "langgraph-architecture:langgraph-repository-review", False),
    }
    for filename, (name, skill, writable) in expected.items():
        data, body = frontmatter(PLUGIN / "agents" / filename)
        require(data.get("name") == name, f"name incorreto: {filename}")
        require(bool(data.get("description")), f"description ausente: {filename}")
        require(data.get("model") == "opus", f"modelo não topo: {filename}")
        require(data.get("effort") == "max", f"effort não max: {filename}")
        require(data.get("isolation") == "worktree", f"isolamento ausente: {filename}")
        skills = data.get("skills", [])
        require(isinstance(skills, list) and skill in skills, f"skill namespaced ausente: {filename}")
        tools = str(data.get("tools", ""))
        require("Bash" not in tools, f"Bash permitiria mutações fora do contrato: {filename}")
        if writable:
            require("Write" in tools and "Edit" not in tools, "architect deve criar só plano")
        else:
            require("Write" not in tools and "Edit" not in tools, "reviewer deve ser read-only")
        require("não" in body.lower(), f"fronteira negativa ausente: {filename}")


def main() -> int:
    if (PLUGIN / ".codex-plugin/plugin.json").is_file():
        runtime = "codex"
    elif (PLUGIN / ".claude-plugin/plugin.json").is_file():
        runtime = "claude"
    else:
        raise AssertionError("runtime não identificado")
    validate_common(runtime)
    if runtime == "codex":
        validate_codex()
    else:
        validate_claude()
    print(f"OK: {PLUGIN_NAME} {VERSION} contract ({runtime})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
