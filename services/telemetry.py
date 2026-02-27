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
        "Unhandled exception | Context=%s | User=%s | Guild=%s | Error=%s",
        context,
        user_id,
        guild_id,
        repr(error),
    )

    # FORCE full traceback to stdout (Railway friendly)
    traceback.print_exception(
        type(error),
        error,
        error.__traceback__
    )
