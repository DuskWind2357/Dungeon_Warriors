"""
Dungeon Warriors — 胜利场景
金色"胜利" + 按任意键退出（V1.0.5.21 起取消自动退出倒计时）
"""

import pygame
from config import WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_VICTORY_TEXT
from rendering.pixel_style import draw_overlay
from rendering.renderer import get_font


class VictoryScene:
    """胜利场景"""

    def __init__(self) -> None:
        self._font_large: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None

    def handle_event(self, event: pygame.event.Event) -> str | None:
        # 仅支持按任意键退出，不再自动倒计时返回
        if event.type == pygame.KEYDOWN:
            return "menu"
        return None

    def update(self, dt: float) -> str | None:
        # 胜利界面持续停留，直到玩家按键退出
        return None

    def draw(self, screen: pygame.Surface) -> None:
        if self._font_large is None:
            self._font_large = get_font(72)
        if self._font_small is None:
            self._font_small = get_font(24)

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        draw_overlay(screen, 200)

        # 金色 "胜利"
        text_surf = self._font_large.render("胜利", True, COLOR_VICTORY_TEXT)
        text_rect = text_surf.get_rect(center=(cx, cy - 30))
        screen.blit(text_surf, text_rect)

        # 提示
        tip = self._font_small.render("按任意键退出", True, (180, 180, 180))
        tip_rect = tip.get_rect(center=(cx, cy + 50))
        screen.blit(tip, tip_rect)
