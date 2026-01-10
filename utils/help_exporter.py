from typing import Any, Dict, List
from utils.help_loader import load_help_registry

def generate_readme_markdown(data_dir: str) -> str:
    registry = load_help_registry(data_dir)

    lines: List[str] = []
    lines.append("# Bottany Commands")
    lines.append("")
    lines.append("Generated from `data/help_registry.json`.")
    lines.append("")

    # Keep a stable order: general first, then alphabetical
    ordered = []
    if "general" in registry:
        ordered.append(("general", registry["general"]))
    for k in sorted([x for x in registry.keys() if x != "general"]):
        ordered.append((k, registry[k]))

    for category, data in ordered:
        title = category.capitalize()
        lines.append(f"## {title}")
        desc = (data or {}).get("description", "")
        if desc:
            lines.append(desc)
        lines.append("")

        cmds = (data or {}).get("commands", []) or []
        for cmd in cmds:
            name = cmd.get("name", "").strip()
            usage = cmd.get("usage", "").strip()
            cdesc = cmd.get("description", "").strip()

            if not name:
                continue

            lines.append(f"### {name}")
            if usage:
                lines.append(f"**Usage:** `{usage}`")
            if cdesc:
                lines.append(cdesc)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
