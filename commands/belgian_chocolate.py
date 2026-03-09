@group.command(
    name="chocolate_brands",
    description="Filter Belgian chocolate houses or get a random one"
)
@app_commands.describe(
    year_before="Show brands founded before this year",
    year_after="Show brands founded after this year",
    certification="Filter by certification keyword",
    production_model="bean_to_bar | couverture | hybrid",
    random_choice="Show only one random brand"
)
async def chocolate_brands(
    interaction: discord.Interaction,
    year_before: Optional[int] = None,
    year_after: Optional[int] = None,
    certification: Optional[str] = None,
    production_model: Optional[str] = None,
    random_choice: bool = False
):
    items = _load_dataset(data_dir)
    if not items:
        await interaction.response.send_message("Chocolate dataset not found.", ephemeral=True)
        return

    # Filters
    if year_before:
        items = [i for i in items if i.get("foundation_year") and i["foundation_year"] < year_before]
    if year_after:
        items = [i for i in items if i.get("foundation_year") and i["foundation_year"] > year_after]
    if certification:
        cert_lower = certification.lower()
        items = [i for i in items if any(cert_lower in c.lower() for c in i.get("certifications", []))]
    if production_model:
        items = [i for i in items if (i.get("production_model") or "").lower() == production_model.lower()]

    if not items:
        await interaction.response.send_message("No brands matched your filters.", ephemeral=True)
        return

    # Random single brand
    if random_choice:
        items = [random.choice(items)]

    # Gönderilecek embed
    for item in items[:10]:  # maksimum 10 marka embed
        embed = discord.Embed(
            title=f"{item.get('name', 'Unknown')}",
            description=_format_item(item),
            color=0x4B2E2E
        )

        # Görsel ekleme (logo_url veya placeholder)
        image_url = item.get("logo_url") or item.get("image_url") or "https://via.placeholder.com/300x150.png?text=Chocolate"
        embed.set_thumbnail(url=image_url)

        await interaction.response.send_message(embed=embed)
