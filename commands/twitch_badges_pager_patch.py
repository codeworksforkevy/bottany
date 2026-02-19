import discord
from typing import List, Callable, Optional, Any


class BadgePagerView(discord.ui.View):
    """
    Stable 1-item-per-page pager.

    ✔ Always ACKs interaction
    ✔ Author-locked (optional)
    ✔ Safe timeout handling
    ✔ No crash if items empty
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

        self.items = items or []
        self.build_embed = build_embed
        self.author_id = author_id
        self.i = max(0, min(start_index, max(0, len(self.items) - 1)))
        self.message: Optional[discord.Message] = None

        self._sync_buttons()

    # -------------------------------------------------

    def _sync_buttons(self) -> None:
        n = len(self.items)

        if hasattr(self, "prev_btn"):
            self.prev_btn.disabled = (n <= 1 or self.i <= 0)

        if hasattr(self, "next_btn"):
            self.next_btn.disabled = (n <= 1 or self.i >= n - 1)

    # -------------------------------------------------

    async def _guard(self, interaction: discord.Interaction) -> bool:
        if (
            self.author_id is not None
            and interaction.user
            and interaction.user.id != self.author_id
        ):
            await interaction.response.send_message(
                "Only the command invoker can use these buttons.",
                ephemeral=True,
            )
            return False
        return True

    # -------------------------------------------------

    def current_embed(self) -> discord.Embed:
        n = len(self.items)

        if n == 0:
            return discord.Embed(
                title="No items available",
                color=0x2B2D31
            )

        item = self.items[self.i]
        return self.build_embed(item, self.i, n)

    # -------------------------------------------------

    async def _safe_edit(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(
                    embed=self.current_embed(),
                    view=self
                )
            else:
                await interaction.edit_original_response(
                    embed=self.current_embed(),
                    view=self
                )
        except Exception:
            pass

    # -------------------------------------------------

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not await self._guard(interaction):
            return

        self.i = max(0, self.i - 1)
        self._sync_buttons()
        await self._safe_edit(interaction)

    # -------------------------------------------------

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not await self._guard(interaction):
            return

        self.i = min(len(self.items) - 1, self.i + 1)
        self._sync_buttons()
        await self._safe_edit(interaction)

    # -------------------------------------------------

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not await self._guard(interaction):
            return

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(view=self)
            else:
                await interaction.edit_original_response(view=self)
        except Exception:
            pass

    # -------------------------------------------------

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass
