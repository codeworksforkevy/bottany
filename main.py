
# --- FIXED SECTION FOR /freegames now (syntax-safe) ---

@freegames_group.command(name="now", description="Show current free games/giveaway entry points (official sources).")
async def freegames_now(interaction: discord.Interaction):
    if not await enforce_rate_limit(interaction, "freegames_now", cooldown_seconds=10):
        return

    # Normalize sources: dict -> list
    sources_obj = FREEGAMES_REG.get("sources", {}) or {}
    if isinstance(sources_obj, dict):
        sources = list(sources_obj.values())
    elif isinstance(sources_obj, list):
        sources = sources_obj
    else:
        sources = []

    try:
        epic_items = _epic_free_games()
    except Exception:
        epic_items = []

    ICON = {
        "epic": "🕹️",
        "gog": "🎁",
        "default": "🔗",
        "spark": "✨",
    }

    embed = discord.Embed(
        title=f"{ICON['spark']} Free Games — Official Sources",
        description="Official entry points and best-effort current Epic promotions."
    )

    if epic_items:
        epic_lines = [f"• {ICON['epic']} [{title}]({url})" for title, url in epic_items[:5]]
        embed.add_field(
            name="Epic (current promotions)",
            value="\n".join(epic_lines),
            inline=False
        )
    else:
        embed.add_field(
            name="Epic (current promotions)",
            value="No current Epic promotions could be fetched (best-effort).",
            inline=False
        )

    class _FGView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=180)
            added = 0

            for s in sources[:6]:
                if added >= 4:
                    break

                name = (s.get("name") or "Source").strip()
                url = (s.get("url") or "").strip()

                if not url:
                    store_base = (s.get("store_base") or "").strip()
                    if "epicgames.com" in store_base:
                        url = store_base.rstrip("/") + "/free-games"
                        name = "Epic Games Store"
                    elif "gog.com" in store_base:
                        url = store_base.rstrip("/") + "/en/partner/free_games"
                        name = "GOG"

                if not url:
                    endpoints = s.get("endpoints") or []
                    if isinstance(endpoints, list) and endpoints:
                        url = str(endpoints[0]).strip()

                if not url or not _allowed_domain("gaming_deals", url):
                    continue

                icon = ICON["default"]
                if "epicgames.com" in url:
                    icon = ICON["epic"]
                elif "gog.com" in url:
                    icon = ICON["gog"]

                self.add_item(discord.ui.Button(label=f"{icon} {name}"[:80], url=url))
                added += 1

            for title, url in epic_items[:3]:
                if _allowed_domain("gaming_deals", url):
                    self.add_item(
                        discord.ui.Button(
                            label=f"{ICON['epic']} Epic: {title}"[:80],
                            url=url
                        )
                    )

    embed.set_footer(
        text="Official-source buttons are allowlist-checked. Weekly announcements post only to #gaming."
    )

    await interaction.response.send_message(embed=embed, view=_FGView())

# --- END FIXED SECTION ---
