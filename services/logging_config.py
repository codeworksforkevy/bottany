import logging
import json
import sys
import os

def setup_logging():

    level = os.getenv("LOG_LEVEL", "INFO").upper()

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "time": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_record)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
