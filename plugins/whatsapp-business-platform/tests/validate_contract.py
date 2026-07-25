#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

NAME = "whatsapp-business-platform"
LOCAL_ROOT = Path(__file__).resolve().parents[1]
SHARED_PATHS = (
    Path("skills") / NAME / "SKILL.md",
    Path("skills") / NAME / "references" / "official-meta-sources.md",
    Path("tests") / "validate_contract.py",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_runtime(root: Path) -> str:
    root = root.resolve()
    skill = root / SHARED_PATHS[0]
    reference = root / SHARED_PATHS[1]
    manifest_candidates = [
        root / ".codex-plugin" / "plugin.json",
        root / ".claude-plugin" / "plugin.json",
    ]

    require(skill.is_file(), f"missing {skill}")
    require(reference.is_file(), f"missing {reference}")
    manifests = [path for path in manifest_candidates if path.is_file()]
    require(len(manifests) == 1, f"expected exactly one runtime manifest in {root}")

    manifest_path = manifests[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("name") == NAME, f"manifest name mismatch in {root}")
    require(manifest.get("version") == "1.0.0", f"manifest version mismatch in {root}")

    repo = root.parents[1]
    if manifest_path.parent.name == ".codex-plugin":
        runtime = "codex"
        marketplace_path = repo / ".agents" / "plugins" / "marketplace.json"
        install_command = "codex plugin add whatsapp-business-platform@codex-skills"
    else:
        runtime = "claude"
        marketplace_path = repo / ".claude-plugin" / "marketplace.json"
        install_command = "claude plugin install whatsapp-business-platform@claude-skills"

    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    entries = [item for item in marketplace.get("plugins", []) if item.get("name") == NAME]
    require(len(entries) == 1, f"marketplace must contain exactly one plugin entry in {repo}")
    readme = (repo / "README.md").read_text(encoding="utf-8")
    require(install_command in readme, f"README install command missing in {repo}")
    require("/whatsapp-business-platform modo=provider" in readme, f"README usage missing in {repo}")

    text = skill.read_text(encoding="utf-8")
    ref = reference.read_text(encoding="utf-8")
    for token in [
        "Technology Provider", "Embedded Signup v4", "whatsapp_business_messaging",
        "whatsapp_business_management", "whatsapp_business_app_onboarding",
        "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING", "is_on_biz_app,platform_type",
        "smb_message_echoes", "account_update", "Phone Number ID", "business tokens", "20 mps",
        "X-Hub-Signature-256", "PARTNER_REMOVED", "ACCOUNT_OFFBOARDED",
        "ACCOUNT_RECONNECTED", "tempo constante", "confirmação explícita do usuário",
    ]:
        require(token in text, f"missing required contract token in {root}: {token}")
    for token in [
        "/whatsapp/overview", "/get-started-for-tech-providers", "/embedded-signup/overview",
        "/embedded-signup/version-4", "/onboarding-business-app-users/",
    ]:
        require(token in ref, f"missing official source in {root}: {token}")

    require(text.count("```") % 2 == 0, f"unbalanced Markdown fences in {skill}")
    require(not re.search(r"\bEAA[A-Za-z0-9_-]{20,}\b", text + ref), f"possible real Meta token in {root}")
    require("745214375347093" not in text + ref, f"real Phone Number ID leaked in {root}")
    return runtime


def validate_pair(local_root: Path, counterpart_root: Path) -> None:
    local_runtime = validate_runtime(local_root)
    counterpart_runtime = validate_runtime(counterpart_root)
    require(local_runtime != counterpart_runtime, "counterpart must be the other runtime")

    for relative in SHARED_PATHS:
        local_file = local_root / relative
        counterpart_file = counterpart_root / relative
        require(counterpart_file.is_file(), f"counterpart missing shared path: {counterpart_file}")
        require(
            sha256(local_file) == sha256(counterpart_file),
            f"shared bundle drift: {relative}",
        )
    print("pair parity ok", local_runtime, counterpart_runtime)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate WhatsApp plugin contract and optional cross-runtime parity")
    parser.add_argument(
        "--counterpart",
        type=Path,
        help="Path to the counterpart plugin root, e.g. .../plugins/whatsapp-business-platform",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime = validate_runtime(LOCAL_ROOT)
    print("contract ok", runtime, LOCAL_ROOT)
    if args.counterpart:
        validate_pair(LOCAL_ROOT, args.counterpart.resolve())


if __name__ == "__main__":
    main()
