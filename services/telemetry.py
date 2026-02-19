import logging
import traceback
from typing import Optional

logger = logging.getLogger("bottany.telemetry")

def capture_exception(
    error: Exception,
    *,
    context: Optional[str] = None,
    user_id: Optional[int] = None,
    guild_id: Optional[int] = None,
):

    logger.error(
        "Unhandled exception",
        extra={
            "context": context,
            "user_id": user_id,
            "guild_id": guild_id,
        },
        exc_info=error,
    )
