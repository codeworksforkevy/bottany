import json
import os
from typing import Any, Dict

def load_help_registry(data_dir: str) -> Dict[str, Any]:
    """Load help registry from data/help_registry.json.

    The registry is expected to be JSON with:
      { "<category>": { "description": str, "commands": [ {name, usage, description}, ... ] }, ... }
    """
    path = os.path.join(data_dir, "help_registry.json")
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    # Normalize keys to lowercase categories to simplify lookup
    if isinstance(obj, dict):
        return {str(k).lower(): v for k, v in obj.items()}
    return {}
