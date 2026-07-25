#!/usr/bin/env python3
"""Validate the WhatsApp plugin contract and cross-runtime parity."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

NAME = "whatsapp-business-platform"
LOCAL_ROOT = Path(__file__).resolve().parents[1]
SHARED_PATHS = (
    Path("skills") / NAME / "SKILL.md",
    Path("skills") / NAME / "references" / "official-meta-sources.md",
    Path("tests") / "validate_contract.py",
)
CANONICAL_URLS = {
    "https://developers.facebook.com/documentation/business-messaging/whatsapp/overview",
    "https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/get-started-for-tech-providers",
    "https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/overview",
    "https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/versions",
    "https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/version-4",
    "https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users/",
}
TEXT_SUFFIXES = {".md", ".json", ".py", ".txt", ".yaml", ".yml"}


def require(condition: bool, message: str) -> None:
    """Raise an assertion with a useful contract message when condition is false."""
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_corpus(root: Path) -> str:
    """Read every documentation, fixture, manifest, and validator text file in a plugin."""
    chunks: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            chunks.append(f"\n--- {path.relative_to(root)} ---\n")
            chunks.append(path.read_text(encoding="utf-8"))
    return "".join(chunks)


def validate_marketplace_entry(runtime: str, entry: dict[str, object], repo: Path) -> None:
    """Validate the runtime-specific marketplace contract completely."""
    if runtime == "codex":
        require(
            entry.get("source") == {
                "source": "local",
                "path": "./plugins/whatsapp-business-platform",
            },
            f"Codex marketplace source mismatch in {repo}",
        )
        require(
            entry.get("policy") == {
                "installation": "AVAILABLE",
                "authentication": "ON_INSTALL",
            },
            f"Codex marketplace policy mismatch in {repo}",
        )
        require(entry.get("category") == "Development", f"Codex marketplace category mismatch in {repo}")
    else:
        require(entry.get("source") == "./plugins/whatsapp-business-platform", f"Claude marketplace source mismatch in {repo}")
        require(entry.get("version") == "1.0.0", f"Claude marketplace version mismatch in {repo}")
        require(entry.get("category") == "development", f"Claude marketplace category mismatch in {repo}")
        tags_value = entry.get("tags")
        if not isinstance(tags_value, list):
            raise AssertionError(f"Claude marketplace tags missing in {repo}")
        tags = set(tags_value)
        require({"whatsapp", "meta", "coexistence"} <= tags, f"Claude marketplace tags mismatch in {repo}")


def validate_official_sources(reference: str, root: Path) -> None:
    """Require canonical HTTPS sources hosted only on Meta's developer domain."""
    urls = set(re.findall(r"https://[^\s)]+", reference))
    require(CANONICAL_URLS <= urls, f"missing canonical Meta sources in {root}: {sorted(CANONICAL_URLS - urls)}")
    for url in urls:
        parsed = urlparse(url)
        require(parsed.scheme == "https", f"non-HTTPS source in {root}: {url}")
        require(parsed.hostname == "developers.facebook.com", f"non-official source domain in {root}: {url}")


def validate_no_secrets_or_real_ids(corpus: str, root: Path) -> None:
    """Reject common credential formats and raw long numeric Meta identifiers."""
    patterns = {
        "Meta access token": r"\bEAA[A-Za-z0-9_-]{20,}\b",
        "GitHub token": r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b",
        "OpenAI-style token": r"\bsk-[A-Za-z0-9_-]{20,}\b",
        "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
        "raw numeric Meta/phone ID": r"(?<![<A-Z_])\b\d{10,20}\b(?![>A-Z_])",
    }
    for label, pattern in patterns.items():
        require(not re.search(pattern, corpus), f"possible {label} in {root}")


def validate_runtime(root: Path) -> str:
    """Validate one Codex or Claude plugin plus its repository registration."""
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
    validate_marketplace_entry(runtime, entries[0], repo)

    readme = (repo / "README.md").read_text(encoding="utf-8")
    require(install_command in readme, f"README install command missing in {repo}")
    for command in (
        "/whatsapp-business-platform modo=provider",
        "/whatsapp-business-platform modo=coexistence",
    ):
        require(command in readme, f"README usage missing in {repo}: {command}")

    text = skill.read_text(encoding="utf-8")
    reference_text = reference.read_text(encoding="utf-8")
    for token in [
        "Technology Provider", "Embedded Signup v4", "whatsapp_business_messaging",
        "whatsapp_business_management", "whatsapp_business_app_onboarding",
        "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING", "is_on_biz_app,platform_type",
        "smb_message_echoes", "account_update", "Phone Number ID", "business tokens", "20 mps",
        "X-Hub-Signature-256", "PARTNER_REMOVED", "ACCOUNT_OFFBOARDED",
        "ACCOUNT_RECONNECTED", "tempo constante", "confirmação explícita do usuário",
        "v2 e v3", "allowlist exata", "janela móvel de sete dias",
    ]:
        require(token in text, f"missing required contract token in {root}: {token}")

    require("Verificação deste catálogo" in reference_text and "2026-07-25" in reference_text, f"source verification date missing in {root}")
    validate_official_sources(reference_text, root)
    require(text.count("```") % 2 == 0, f"unbalanced Markdown fences in {skill}")
    validate_no_secrets_or_real_ids(collect_corpus(root), root)
    return runtime


def validate_pair(local_root: Path, counterpart_root: Path) -> None:
    """Validate both runtimes and enforce byte-identical shared bundle files."""
    local_runtime = validate_runtime(local_root)
    counterpart_runtime = validate_runtime(counterpart_root)
    require(local_runtime != counterpart_runtime, "counterpart must be the other runtime")

    for relative in SHARED_PATHS:
        local_file = local_root / relative
        counterpart_file = counterpart_root / relative
        require(counterpart_file.is_file(), f"counterpart missing shared path: {counterpart_file}")
        require(sha256(local_file) == sha256(counterpart_file), f"shared bundle drift: {relative}")
    print("pair parity ok", local_runtime, counterpart_runtime)


def parse_args() -> argparse.Namespace:
    """Parse an optional path to the counterpart runtime plugin root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--counterpart",
        type=Path,
        help="Path to the counterpart plugin root, e.g. .../plugins/whatsapp-business-platform",
    )
    return parser.parse_args()


def main() -> None:
    """Run local validation and optional cross-runtime parity validation."""
    args = parse_args()
    runtime = validate_runtime(LOCAL_ROOT)
    print("contract ok", runtime, LOCAL_ROOT)
    if args.counterpart:
        validate_pair(LOCAL_ROOT, args.counterpart.resolve())


if __name__ == "__main__":
    main()
