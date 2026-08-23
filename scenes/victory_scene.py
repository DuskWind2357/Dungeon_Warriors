"""
Dungeon Warriors — 胜利场景
金色"胜利" + 自动退出倒计时
"""

import os
import pygame
from config import WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_VICTORY_TEXT, COLOR_TEXT
from rendering.pixel_style import draw_overlay

EXIT_COUNTDOWN = 5.0  # 5秒后自动退出


class VictoryScene:
    """胜利场景"""

    def __init__(self) -> None:
        self._font_large: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._countdown: float = EXIT_COUNTDOWN

    def handle_event(self, event: pygame.event.Event) -> str | None:
        # 仍允许按任意键提前退出
        if event.type == pygame.KEYDOWN:
            return "menu"
        return None

    def update(self, dt: float) -> str | None:
        self._countdown -= dt
        if self._countdown <= 0:
            return "menu"
        return None

    def draw(self, screen: pygame.Surface) -> None:
        if self._font_large is None:
            self._font_large = self._get_font(72)
        if self._font_small is None:
            self._font_small = self._get_font(24)

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        draw_overlay(screen, 200)

        # 金色 "胜利"
        text_surf = self._font_large.render("胜利", True, COLOR_VICTORY_TEXT)
        text_rect = text_surf.get_rect(center=(cx, cy - 30))
        screen.blit(text_surf, text_rect)

        # 倒计时（金色小字）
        sec = max(0, int(self._countdown) + 1)
        hint = f"{sec} 秒后自动退出"
        hint_surf = self._font_small.render(hint, True, COLOR_VICTORY_TEXT)
        hint_rect = hint_surf.get_rect(center=(cx, cy + 40))
        screen.blit(hint_surf, hint_rect)

        # 提示
        tip = self._font_small.render("按任意键提前退出", True, (180, 180, 180))
        tip_rect = tip.get_rect(center=(cx, cy + 70))
        screen.blit(tip, tip_rect)

    @staticmethod
    def _get_font(size: int) -> pygame.font.Font:
        from utils import resource_path
        for fname in ["font.ttf", "font.otf"]:
            path = resource_path(fname)
            if os.path.exists(path):
                return pygame.font.Font(path, size)
        return pygame.font.Font(None, size)
