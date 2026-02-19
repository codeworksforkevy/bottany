# =========================================================
# REGISTER (HYBRID LOADER COMPATIBLE)
# =========================================================

async def register(bot: discord.Client, data_dir: str):

    existing = bot.tree.get_command("utility")

    # Eğer zaten doğru group varsa tekrar ekleme
    if isinstance(existing, app_commands.Group):
        group = existing
    elif existing:
        raise RuntimeError(
            "Command name collision: 'utility' already exists and is not a Group."
        )
    else:
        group = UtilityGroup(bot, data_dir)
        bot.tree.add_command(group)

    # Duplicate guard
    if getattr(bot, "_utility_registered", False):
        return

    bot._utility_registered = True

    # -----------------------------------------------------
    # BACKGROUND REMINDER LOOP
    # -----------------------------------------------------

    if hasattr(bot, "_utility_task"):
        return

    async def reminder_loop():

        await bot.wait_until_ready()
        path = _path(data_dir)

        while not bot.is_closed():

            async with _lock:
                data = _load_json(path)
                reminders: List[Dict] = data["reminders"]

                if not reminders:
                    await asyncio.sleep(30)
                    continue

                reminders.sort(key=lambda r: r["due"])
                next_due = datetime.fromisoformat(reminders[0]["due"])
                now = _utc_now()

                if next_due > now:
                    await asyncio.sleep(
                        min((next_due - now).total_seconds(), 60)
                    )
                    continue

                keep = []

                for r in reminders:
                    due = datetime.fromisoformat(r["due"])

                    if due <= now:
                        _message_queue.append(
                            (
                                r["channel_id"],
                                f"<@{r['user_id']}> ⏰ Reminder: {r['text']}"
                            )
                        )

                        if r.get("repeat") == "daily":
                            r["due"] = (due + timedelta(days=1)).isoformat()
                            keep.append(r)
                        elif r.get("repeat") == "weekly":
                            r["due"] = (due + timedelta(weeks=1)).isoformat()
                            keep.append(r)

                    else:
                        keep.append(r)

                data["reminders"] = keep
                _save_json(path, data)

            await asyncio.sleep(5)

    bot._utility_task = asyncio.create_task(reminder_loop())
    bot._utility_worker = asyncio.create_task(_message_worker(bot))
