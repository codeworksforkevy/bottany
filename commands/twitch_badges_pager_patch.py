import discord
from typing import List, Callable, Optional, Any

class BadgePagerView(discord.ui.View):
    """Reliable 1-item-per-page pager.
    - Always ACKs interactions
    - Defaults to 15 minutes timeout (set timeout=None for persistent)
    - Optional author lock: only the user who ran the command can page
    """
    def __init__(
        self,
        items: List[Any],
        build_embed: Callable[[Any, int, int], discord.Embed],
        *,
        author_id: Optional[int] = None,
        start_index: int = 0,
        timeout: Optional[float] = 900,
    ):
        super().__init__(timeout=timeout)
        self.items = items
        self.build_embed = build_embed
        self.author_id = author_id
        self.i = max(0, min(start_index, max(0, len(items) - 1)))

        # Initial button state
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        n = len(self.items)
        self.prev_btn.disabled = (n <= 1 or self.i <= 0)
        self.next_btn.disabled = (n <= 1 or self.i >= n - 1)

    async def _guard(self, interaction: discord.Interaction) -> bool:
        if self.author_id is not None and interaction.user and interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the command invoker can use these buttons.",
                ephemeral=True,
            )
            return False
        return True

    def current_embed(self) -> discord.Embed:
        n = len(self.items)
        item = self.items[self.i] if n else None
        return self.build_embed(item, self.i, n)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._guard(interaction):
            return
        # respond fast to avoid "Interaction failed"
        self.i = max(0, self.i - 1)
        self._sync_buttons()
        try:
            await interaction.response.edit_message(embed=self.current_embed(), view=self)
        except discord.InteractionResponded:
            await interaction.edit_original_response(embed=self.current_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._guard(interaction):
            return
        self.i = min(len(self.items) - 1, self.i + 1)
        self._sync_buttons()
        try:
            await interaction.response.edit_message(embed=self.current_embed(), view=self)
        except discord.InteractionResponded:
            await interaction.edit_original_response(embed=self.current_embed(), view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._guard(interaction):
            return
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        try:
            await interaction.response.edit_message(view=self)
        except discord.InteractionResponded:
            await interaction.edit_original_response(view=self)

    async def on_timeout(self) -> None:
        # Gracefully disable to avoid dead buttons after timeout
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

# Usage sketch inside your command:
#
# def build_badge_embed(badge, i, n):
#     e = discord.Embed(title="New Twitch Badges Detected", color=0x89CFF0)
#     e.description = f"{i+1}/{n}\n\n{badge['name']}\n{badge['description']}"
#     e.set_thumbnail(url=badge['image_url'])
#     return e
#
# view = BadgePagerView(badges, build_badge_embed, author_id=interaction.user.id, timeout=900)
# await interaction.response.send_message(embed=view.current_embed(), view=view, ephemeral=False)
