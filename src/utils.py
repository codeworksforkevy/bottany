import json
import os
import hashlib
from typing import Any, Dict, List


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def safe_join(base_dir: str, *parts: str) -> str:
    joined = os.path.abspath(os.path.join(base_dir, *parts))
    base_abs = os.path.abspath(base_dir)
    if not joined.startswith(base_abs + os.sep) and joined != base_abs:
        raise ValueError("Unsafe path traversal detected.")
    return joined


def validate_pool(pool: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    items = pool.get("items")
    if not isinstance(items, list):
        issues.append("Pool 'items' must be a list.")
        return issues
    for i, it in enumerate(items[:5]):  # light sanity-check sample
        if not isinstance(it, dict):
            issues.append(f"Item {i} must be an object.")
            continue
        if "text" not in it:
            issues.append(f"Item {i} missing 'text'.")
    return issues
