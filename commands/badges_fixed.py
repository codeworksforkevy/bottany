# This wrapper ensures ONLY ONE /badges group is registered.
# It delegates to the advanced twitch_badges_watch implementation.

from twitch_badges_watch import register_badges

def register_badges_fixed(bot, tree, data_dir):
    # register_badges only needs (bot, data_dir)
    return register_badges(bot, data_dir)