"""
Dungeon Warriors — 设置场景
难度选择（默认 / 冒险 / 末日）
"""

import pygame
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_BG, COLOR_TITLE,
    COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_BUTTON_BORDER, COLOR_BUTTON_TEXT,
    COLOR_TEXT, COLOR_TEXT_DIM,
    DIFFICULTY_MODIFIERS, DEFAULT_DIFFICULTY,
)
from rendering.pixel_style import draw_overlay, draw_pixel_text


class SettingsScene:
    """设置场景"""

    def __init__(self, current_difficulty: str = DEFAULT_DIFFICULTY) -> None:
        self.current = current_difficulty
        self.buttons: list[pygame.Rect] = []
        self.hovered: int = -1
        self._layout()

    def _layout(self) -> None:
        self.buttons = []
        btn_w, btn_h = 300, 50
        gap = 14
        start_y = 300
        for i in range(3):
            rect = pygame.Rect((WINDOW_WIDTH - btn_w) // 2,
                               start_y + i * (btn_h + gap), btn_w, btn_h)
            self.buttons.append(rect)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "menu"

        elif event.type == pygame.MOUSEMOTION:
            self.hovered = -1
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos):
                    self.hovered = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos):
                    keys = list(DIFFICULTY_MODIFIERS.keys())
                    if i < len(keys):
                        self.current = keys[i]
                    return None  # 留在设置界面

        return None

    def get_difficulty(self) -> str:
        return self.current

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_BG)

        font_title = self._get_font(48)
        font_btn = self._get_font(24)
        font_hint = self._get_font(18)
        cx = WINDOW_WIDTH // 2

        draw_pixel_text(screen, "设置", font_title, COLOR_TITLE, cx, 120, shadow=True)

        # 难度标签
        diff_label = font_btn.render("选择难度", True, COLOR_TEXT)
        screen.blit(diff_label, diff_label.get_rect(center=(cx, 230)))

        # 难度按钮
        for i, (key, mod) in enumerate(DIFFICULTY_MODIFIERS.items()):
            rect = self.buttons[i]
            is_current = (key == self.current)
            color = (100, 140, 100) if is_current else (
                COLOR_BUTTON_HOVER if i == self.hovered else COLOR_BUTTON)

            pygame.draw.rect(screen, color, rect, border_radius=6)
            if is_current:
                pygame.draw.rect(screen, (150, 220, 150), rect, width=3, border_radius=6)
            else:
                pygame.draw.rect(screen, COLOR_BUTTON_BORDER, rect, width=2, border_radius=6)

            text = font_btn.render(mod["label"], True, COLOR_BUTTON_TEXT)
            screen.blit(text, text.get_rect(center=rect.center))

        # 当前难度描述
        mod = DIFFICULTY_MODIFIERS.get(self.current, {})
        desc = (f"怪物移速: {mod.get('speed_mult', 1.0)*100:.0f}%  |  "
                f"攻击冷却: {mod.get('cd_mult', 1.0)*100:.0f}%  |  "
                f"刷怪倍率: {mod.get('spawn_mult', 1.0):.1f}x")
        desc_surf = font_hint.render(desc, True, COLOR_TEXT_DIM)
        screen.blit(desc_surf, desc_surf.get_rect(center=(cx, 510)))

        # 返回提示
        hint = font_hint.render("ESC 返回主菜单", True, COLOR_TEXT_DIM)
        screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))

    @staticmethod
    def _get_font(size: int) -> pygame.font.Font:
        import os, sys
        from utils import resource_path
        for fname in ["font.ttf", "font.otf"]:
            path = resource_path(fname)
            if os.path.exists(path):
                return pygame.font.Font(path, size)
        return pygame.font.Font(None, size)
