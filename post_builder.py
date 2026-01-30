def build_weekly_post(free_games, discounted_games):
    has_discounts = len(discounted_games) > 0

    if free_games and has_discounts:
        title = "Weekly free games and selected discounts"
    elif free_games:
        title = "Weekly free games"
    else:
        title = "Selected game discounts"

    lines = [f"**{title}**\n"]

    if free_games:
        lines.append("**Free to keep**")

        prime = [g for g in free_games if g.get("platform") == "prime_gaming"]
        other = [g for g in free_games if g.get("platform") != "prime_gaming"]

        if prime:
            waves = {}
            for g in prime:
                w = g.get("wave") or "Prime Gaming"
                waves.setdefault(w, []).append(g)
            for w in sorted(waves.keys()):
                lines.append(f"\n**Prime Gaming — {w}**")
                for g in waves[w]:
                    ends = g.get("claim_until")
                    end_txt = f" — Ends: `{ends}`" if ends else ""
                    lines.append(f"• **{g['title']}** — {g['url']}{end_txt}")

        for g in other:
            ends = g.get("claim_until")
            end_txt = f" — Ends: `{ends}`" if ends else ""
            lines.append(f"• **{g['title']}** — {g['url']}{end_txt}")

    if has_discounts:
        lines.append("\n**Discounted / promotional**")
        for g in discounted_games:
            ends = g.get("claim_until")
            end_txt = f" — Ends: `{ends}`" if ends else ""
            lines.append(f"• **{g['title']}** — {g['url']}{end_txt}")

        lines.append(
            "\n_Note: Only the titles listed under **“Free to keep”** are permanently free. "
            "Other entries are included for visibility and may be discounted, promotional, or time-limited._"
        )

    return "\n".join(lines)
