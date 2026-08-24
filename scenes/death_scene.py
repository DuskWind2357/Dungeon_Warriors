"""
Dungeon Warriors — 死亡场景
红色 "你死了" + 倒计时
"""

import pygame
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    COLOR_DEATH_TEXT, COLOR_TEXT, COLOR_BG,
)
from systems.revive_system import ReviveSystem
from rendering.pixel_style import draw_overlay
from rendering.renderer import get_font


class DeathScene:
    """死亡场景"""

    def __init__(self, revive_system: ReviveSystem,
                 countdown_seconds: int = 5) -> None:
        self.revive_system = revive_system
        self.countdown: float = float(countdown_seconds)
        self._font_large: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None

    def handle_event(self, event: pygame.event.Event) -> str | None:
        # 死亡场景不响应键盘事件，等待倒计时
        return None

    def update(self, dt: float) -> str | None:
        """倒计时"""
        self.countdown -= dt
        if self.countdown <= 0:
            return "revive"
        return None

    def draw(self, screen: pygame.Surface) -> None:
        """绘制死亡画面"""
        if self._font_large is None:
            self._font_large = get_font(72)
        if self._font_small is None:
            self._font_small = get_font(24)

        screen_center_x = WINDOW_WIDTH // 2
        screen_center_y = WINDOW_HEIGHT // 2

        # 半透明暗色叠加
        draw_overlay(screen, 200)

        # 红色 "你死了"
        text_surf = self._font_large.render("你死了", True, COLOR_DEATH_TEXT)
        text_rect = text_surf.get_rect(center=(screen_center_x, screen_center_y - 40))
        screen.blit(text_surf, text_rect)

        # 倒计时
        seconds_left = max(0, int(self.countdown) + 1)
        count_text = f"楼层将在 {seconds_left} 秒后重置"
        count_surf = self._font_small.render(count_text, True, COLOR_DEATH_TEXT)
        count_rect = count_surf.get_rect(center=(screen_center_x, screen_center_y + 30))
        screen.blit(count_surf, count_rect)

        # 剩余复活次数
        remaining = self.revive_system.revives_remaining
        revive_text = f"剩余复活次数: {remaining}"
        revive_surf = self._font_small.render(revive_text, True, COLOR_TEXT)
        revive_rect = revive_surf.get_rect(center=(screen_center_x, screen_center_y + 60))
        screen.blit(revive_surf, revive_rect)
