SOURCE_FOOTER = "Verified using official and institutional sources only."

def apply_source_footer(embed):
    embed.set_footer(text=SOURCE_FOOTER)
    return embed
