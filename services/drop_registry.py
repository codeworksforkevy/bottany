import os
import json
import time
from typing import List, Dict, Any

class DropRegistry:

    def __init__(self, data_dir: str):
        self.path = os.path.join(data_dir, "twitch_drops_registry.json")
        self._cache: List[Dict[str, Any]] = []
        self._mtime = 0

    def get_active(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []

        mtime = os.path.getmtime(self.path)

        if mtime != self._mtime:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            self._cache = [
                d for d in obj.get("drops", [])
                if d.get("status") == "active"
            ]
            self._mtime = mtime

        return self._cache
