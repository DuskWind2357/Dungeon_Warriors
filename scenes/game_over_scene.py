"""
Dungeon Warriors — 游戏结束场景
红色 "游戏结束"，3 秒后自动返回主菜单
"""

import pygame
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    COLOR_DEATH_TEXT, GAME_OVER_DELAY_SEC,
)
from rendering.pixel_style import draw_overlay
from rendering.renderer import get_font


class GameOverScene:
    """游戏结束场景"""

    def __init__(self) -> None:
        self._timer: float = float(GAME_OVER_DELAY_SEC)
        self._font_large: pygame.font.Font | None = None

    def handle_event(self, event: pygame.event.Event) -> str | None:
        return None

    def update(self, dt: float) -> str | None:
        self._timer -= dt
        if self._timer <= 0:
            return "menu"
        return None

    def draw(self, screen: pygame.Surface) -> None:
        if self._font_large is None:
            self._font_large = get_font(72)

        screen_center_x = WINDOW_WIDTH // 2
        screen_center_y = WINDOW_HEIGHT // 2

        draw_overlay(screen, 220)

        # 红色 "游戏结束"
        text_surf = self._font_large.render("游戏结束", True, COLOR_DEATH_TEXT)
        text_rect = text_surf.get_rect(center=(screen_center_x, screen_center_y))
        screen.blit(text_surf, text_rect)
