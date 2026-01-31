
# Patched: disabled cog-based registration for discord.Client compatibility

def register_gaming_news(*args, **kwargs):
    # Intentionally no-op to avoid add_cog errors on discord.Client
    return None
