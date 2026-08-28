"""
Dungeon Warriors — 像素风格渲染辅助
调色板、边框样式、像素文字效果
"""

import pygame
from config import (
    COLOR_TITLE, COLOR_TITLE_SHADOW,
    COLOR_TEXT, COLOR_TEXT_DIM,
    COLOR_DEATH_TEXT, COLOR_VICTORY_TEXT, COLOR_TOAST,
)


def draw_pixel_text(screen: pygame.Surface, text: str,
                    font: pygame.font.Font, color: tuple[int, int, int],
                    center_x: int, y: int, shadow: bool = True) -> None:
    """绘制像素风格文字（居中，带投影）"""
    if shadow:
        shadow_surf = font.render(text, True, COLOR_TITLE_SHADOW)
        shadow_rect = shadow_surf.get_rect(center=(center_x + 3, y + 3))
        screen.blit(shadow_surf, shadow_rect)

    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=(center_x, y))
    screen.blit(text_surf, text_rect)


def draw_stone_button(screen: pygame.Surface, rect: pygame.Rect,
                      text: str, font: pygame.font.Font,
                      hover: bool = False) -> None:
    """绘制石灰色按钮"""
    from config import (
        COLOR_BUTTON, COLOR_BUTTON_HOVER,
        COLOR_BUTTON_BORDER, COLOR_BUTTON_TEXT
    )

    color = COLOR_BUTTON_HOVER if hover else COLOR_BUTTON

    # 主体
    pygame.draw.rect(screen, color, rect, border_radius=6)
    # 边框
    pygame.draw.rect(screen, COLOR_BUTTON_BORDER, rect, width=2, border_radius=6)

    # 文字
    text_surf = font.render(text, True, COLOR_BUTTON_TEXT)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)


def draw_panel_bg(screen: pygame.Surface, rect: pygame.Rect,
                  alpha: int = 200) -> None:
    """绘制半透明面板背景"""
    from config import COLOR_PANEL_BG
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    panel.fill(COLOR_PANEL_BG[:3] + (alpha,))
    screen.blit(panel, rect.topleft)


def draw_overlay(screen: pygame.Surface, alpha: int = 180) -> None:
    """全屏半透明遮罩"""
    from config import COLOR_OVERLAY
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    screen.blit(overlay, (0, 0))


def draw_progress_bar(screen: pygame.Surface, x: int, y: int,
                      width: int, height: int,
                      ratio: float,
                      fill_color: tuple[int, int, int],
                      bg_color: tuple[int, int, int] | None = None) -> None:
    """绘制进度条（HP 条等）"""
    from config import COLOR_HP_BAR_BG
    if bg_color is None:
        bg_color = COLOR_HP_BAR_BG

    # 背景
    pygame.draw.rect(screen, bg_color, (x, y, width, height), border_radius=2)
    # 填充
    if ratio > 0:
        fill_width = max(0, int(width * ratio))
        pygame.draw.rect(screen, fill_color, (x, y, fill_width, height), border_radius=2)


def make_toast(text: str, color: tuple = None) -> dict:
    """创建一个 toast 消息"""
    return {
        "text": text,
        "timer": 2.0,      # 2 秒持续
        "alpha": 255,
        "color": color,
    }
