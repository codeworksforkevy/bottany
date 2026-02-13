SOURCE_FOOTER = "Data curated from official and publicly accessible institutional sources."

def apply_source_footer(embed):
    embed.set_footer(text=SOURCE_FOOTER)
    return embed
