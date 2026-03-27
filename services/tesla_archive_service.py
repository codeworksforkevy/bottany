from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

log = logging.getLogger(__name__)

# Module-level cache — keyed by resolved path so different data_dirs
# don't collide if the service is used in tests or multiple contexts.
_CACHE: Dict[str, Dict[str, Any]] = {}


def load_archive(data_dir) -> Dict[str, Any]:
    """
    Load tesla_academic_archive.json and return:
        {"items": [...], "count": N}

    The result is cached in memory after the first successful load.
    Returns {"items": [], "count": 0} on any error so callers never crash.
    """
    path = os.path.realpath(os.path.join(str(data_dir), "tesla_academic_archive.json"))

    if path in _CACHE:
        return _CACHE[path]

    if not os.path.exists(path):
        log.error("Tesla archive not found at %s", path)
        return {"items": [], "count": 0}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        log.error("Tesla archive malformed at %s: %s", path, exc)
        return {"items": [], "count": 0}
    except OSError as exc:
        log.error("Could not read Tesla archive at %s: %s", path, exc)
        return {"items": [], "count": 0}

    # The JSON is a bare list — wrap it for consistent access
    items = raw if isinstance(raw, list) else raw.get("items", [])

    result = {"items": items, "count": len(items)}
    _CACHE[path] = result
    log.info("Tesla archive loaded: %d patents from %s", len(items), path)
    return result
