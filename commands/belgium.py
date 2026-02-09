
import discord
from discord import app_commands

# Correct import: module exists
from belgian_chocolate import register_belgium_chocolate

def register_belgium(client, tree, data_dir):
    # Register chocolate subcommands under /belgium
    # belgian_chocolate internally attaches to bot.tree,
    # so we just forward the client and data_dir.
    awaitable = register_belgium_chocolate(client, data_dir)
    # If coroutine, let main.py await it via _call
    return awaitable
