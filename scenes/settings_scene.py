"""
Dungeon Warriors — 设置场景
难度选择（默认 / 冒险 / 末日）+ 低级装备自动销毁开关 + 音乐控制开关
"""

import pygame
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_BG, COLOR_TITLE,
    COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_BUTTON_BORDER, COLOR_BUTTON_TEXT,
    COLOR_TEXT, COLOR_TEXT_DIM,
    DIFFICULTY_MODIFIERS, DEFAULT_DIFFICULTY,
    AUTO_DESTROY_LOW_LEVEL_GEAR, MUSIC_ENABLED,
)
from systems.audio_manager import AudioManager
from rendering.pixel_style import draw_pixel_text
from rendering.renderer import get_font


class SettingsScene:
    """设置场景"""

    def __init__(self, current_difficulty: str = DEFAULT_DIFFICULTY,
                 auto_destroy: bool = AUTO_DESTROY_LOW_LEVEL_GEAR,
                 music_on: bool = MUSIC_ENABLED,
                 audio_manager: AudioManager | None = None) -> None:
        self.current = current_difficulty
        self.auto_destroy = auto_destroy
        self.music_on = music_on
        self.audio_manager = audio_manager
        self.buttons: list[pygame.Rect] = []
        self.toggle_btn: pygame.Rect | None = None       # 低级装备自动销毁
        self.music_btn: pygame.Rect | None = None        # 音乐控制
        self.hovered: int = -1
        self._layout()

    def _layout(self) -> None:
        self.buttons = []
        btn_w, btn_h = 300, 50
        gap = 14
        start_y = 280
        for i in range(3):
            rect = pygame.Rect((WINDOW_WIDTH - btn_w) // 2,
                               start_y + i * (btn_h + gap), btn_w, btn_h)
            self.buttons.append(rect)

        # 两个开关并排排列：低级装备自动销毁 | 音乐控制
        toggle_w, toggle_h = 200, 40
        toggle_y = start_y + 3 * (btn_h + gap) + 60
        cx = WINDOW_WIDTH // 2
        spacing = 24  # 两开关间隔
        self.toggle_btn = pygame.Rect(cx - toggle_w - spacing // 2, toggle_y, toggle_w, toggle_h)
        self.music_btn = pygame.Rect(cx + spacing // 2, toggle_y, toggle_w, toggle_h)

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
            if self.toggle_btn and self.toggle_btn.collidepoint(event.pos):
                self.hovered = 10  # 低级装备自动销毁开关
            if self.music_btn and self.music_btn.collidepoint(event.pos):
                self.hovered = 11  # 音乐控制开关

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos):
                    keys = list(DIFFICULTY_MODIFIERS.keys())
                    if i < len(keys):
                        self.current = keys[i]
                    return None  # 留在设置界面
            # 低级装备自动销毁开关
            if self.toggle_btn and self.toggle_btn.collidepoint(event.pos):
                self.auto_destroy = not self.auto_destroy
                return None
            # 音乐控制开关（即时生效）
            if self.music_btn and self.music_btn.collidepoint(event.pos):
                self.music_on = not self.music_on
                if self.audio_manager is not None:
                    self.audio_manager.set_bgm_enabled(self.music_on)
                return None

        return None

    def get_difficulty(self) -> str:
        return self.current

    def get_auto_destroy(self) -> bool:
        return self.auto_destroy

    def get_music_on(self) -> bool:
        return self.music_on

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_BG)

        font_title = get_font(48)
        font_btn = get_font(24)
        font_hint = get_font(18)
        cx = WINDOW_WIDTH // 2

        draw_pixel_text(screen, "设置", font_title, COLOR_TITLE, cx, 100, shadow=True)

        # 难度标签
        diff_label = font_btn.render("选择难度", True, COLOR_TEXT)
        screen.blit(diff_label, diff_label.get_rect(center=(cx, 200)))

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
        screen.blit(desc_surf, desc_surf.get_rect(center=(cx, 480)))

        # ---- 两个开关并排：低级装备自动销毁 | 音乐控制 ----
        if self.toggle_btn and self.music_btn:
            toggle_label = font_btn.render("低级装备自动销毁", True, COLOR_TEXT)
            screen.blit(toggle_label, toggle_label.get_rect(
                center=(self.toggle_btn.centerx, self.toggle_btn.y - 25)))

            # 低级装备自动销毁开关
            is_on = self.auto_destroy
            color = (100, 180, 100) if is_on else (80, 80, 90)
            pygame.draw.rect(screen, color, self.toggle_btn, border_radius=6)
            pygame.draw.rect(screen, COLOR_BUTTON_BORDER, self.toggle_btn, width=2, border_radius=6)
            toggle_text = "ON" if is_on else "OFF"
            text_color = (220, 255, 220) if is_on else (180, 180, 180)
            toggle_surf = font_btn.render(toggle_text, True, text_color)
            screen.blit(toggle_surf, toggle_surf.get_rect(center=self.toggle_btn.center))

            # 音乐控制开关（ON 时蓝色）
            music_label = font_btn.render("音乐控制", True, COLOR_TEXT)
            screen.blit(music_label, music_label.get_rect(
                center=(self.music_btn.centerx, self.music_btn.y - 25)))

            music_on = self.music_on
            color2 = (80, 150, 200) if music_on else (80, 80, 90)
            pygame.draw.rect(screen, color2, self.music_btn, border_radius=6)
            pygame.draw.rect(screen, COLOR_BUTTON_BORDER, self.music_btn, width=2, border_radius=6)
            music_text = "ON" if music_on else "OFF"
            text_color2 = (220, 235, 255) if music_on else (180, 180, 180)
            music_surf = font_btn.render(music_text, True, text_color2)
            screen.blit(music_surf, music_surf.get_rect(center=self.music_btn.center))

        # 返回提示
        hint = font_hint.render("ESC 返回主菜单", True, COLOR_TEXT_DIM)
        screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))