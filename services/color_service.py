import random
from typing import List, Tuple

def random_color() -> int:
    """
    Returns a random Discord embed color (integer).
    """
    return random.randint(0, 0xFFFFFF)


def generate_palette(base_color: int, steps: int = 5) -> List[int]:
    """
    Generates a simple monochrome palette from a base color.
    """
    r = (base_color >> 16) & 0xFF
    g = (base_color >> 8) & 0xFF
    b = base_color & 0xFF

    palette = []

    for i in range(steps):
        factor = 1 - (i * 0.15)
        nr = int(r * factor)
        ng = int(g * factor)
        nb = int(b * factor)

        palette.append((nr << 16) + (ng << 8) + nb)

    return palette
