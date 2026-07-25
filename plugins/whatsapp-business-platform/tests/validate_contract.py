#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "whatsapp-business-platform"
SKILL = ROOT / "skills" / NAME / "SKILL.md"
REF = ROOT / "skills" / NAME / "references" / "official-meta-sources.md"
MANIFESTS = [ROOT / ".codex-plugin" / "plugin.json", ROOT / ".claude-plugin" / "plugin.json"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    require(SKILL.is_file(), f"missing {SKILL}")
    require(REF.is_file(), f"missing {REF}")
    manifests = [path for path in MANIFESTS if path.is_file()]
    require(len(manifests) == 1, "expected exactly one runtime manifest")
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    require(manifest.get("name") == NAME, "manifest name mismatch")
    require(manifest.get("version") == "1.0.0", "manifest version mismatch")

    repo = ROOT.parents[1]
    if manifests[0].parent.name == ".codex-plugin":
        marketplace_path = repo / ".agents" / "plugins" / "marketplace.json"
        install_command = "codex plugin add whatsapp-business-platform@codex-skills"
    else:
        marketplace_path = repo / ".claude-plugin" / "marketplace.json"
        install_command = "claude plugin install whatsapp-business-platform@claude-skills"
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    entries = [item for item in marketplace.get("plugins", []) if item.get("name") == NAME]
    require(len(entries) == 1, "marketplace must contain exactly one plugin entry")
    readme = (repo / "README.md").read_text(encoding="utf-8")
    require(install_command in readme, "README install command missing")
    require("/whatsapp-business-platform modo=provider" in readme, "README usage missing")

    text = SKILL.read_text(encoding="utf-8")
    ref = REF.read_text(encoding="utf-8")
    for token in [
        "Technology Provider", "Embedded Signup v4", "whatsapp_business_messaging",
        "whatsapp_business_management", "whatsapp_business_app_onboarding",
        "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING", "is_on_biz_app,platform_type",
        "smb_message_echoes", "account_update", "Phone Number ID", "business tokens", "20 mps",
    ]:
        require(token in text, f"missing required contract token: {token}")
    for token in [
        "/whatsapp/overview", "/get-started-for-tech-providers", "/embedded-signup/overview",
        "/embedded-signup/version-4", "/onboarding-business-app-users/",
    ]:
        require(token in ref, f"missing official source: {token}")

    require(text.count("```") % 2 == 0, "unbalanced Markdown fences")
    require(not re.search(r"\bEAA[A-Za-z0-9_-]{20,}\b", text + ref), "possible real Meta token")
    require("745214375347093" not in text + ref, "real Phone Number ID leaked")
    print("contract ok", ROOT)


if __name__ == "__main__":
    main()
