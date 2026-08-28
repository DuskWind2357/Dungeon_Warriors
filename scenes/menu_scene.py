"""
Dungeon Warriors — 主菜单场景
标题 + 4 个石灰色按钮
"""

import pygame
from rendering.pixel_style import draw_pixel_text, draw_stone_button
from rendering.renderer import get_title_font, get_button_font, get_font


# 按钮标签
BUTTON_CONTINUE = 0
BUTTON_NEW_GAME = 1
BUTTON_SETTINGS = 2
BUTTON_QUIT = 3


class MenuScene:
    """主菜单场景"""

    def __init__(self) -> None:
        self.buttons: list[pygame.Rect] = []
        self.button_labels: list[str] = []
        self.hovered_index: int = -1
        self._layout_buttons()

    def _layout_buttons(self) -> None:
        """计算按钮位置"""
        screen_w, screen_h = 960, 720
        btn_w, btn_h = 280, 50
        btn_gap = 15
        start_y = 340

        self.buttons = []
        self.button_labels = []

        for i in range(4):
            rect = pygame.Rect(
                (screen_w - btn_w) // 2,
                start_y + i * (btn_h + btn_gap),
                btn_w, btn_h
            )
            self.buttons.append(rect)

    def refresh_labels(self, has_save: bool) -> None:
        """根据存档状态刷新按钮标签"""
        self.button_labels = [
            "继续游戏" if has_save else "开始游戏",
            "新游戏",
            "设置",
            "退出游戏",
        ]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """处理事件，返回下一个场景名称或 None"""
        if event.type == pygame.MOUSEMOTION:
            self.hovered_index = -1
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos):
                    self.hovered_index = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos):
                    return self._on_click(i)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit"

        return None

    def _on_click(self, index: int) -> str | None:
        """按钮点击处理"""
        if index == BUTTON_CONTINUE:
            return "continue_or_start"
        elif index == BUTTON_NEW_GAME:
            return "new_game"
        elif index == BUTTON_SETTINGS:
            return "settings"
        elif index == BUTTON_QUIT:
            return "quit"
        return None

    def update(self, dt: float) -> None:
        """菜单无更新逻辑"""
        pass

    def draw(self, screen: pygame.Surface) -> None:
        """绘制主菜单"""
        from config import COLOR_BG
        screen.fill(COLOR_BG)

        title_font = get_title_font()
        btn_font = get_button_font()
        screen_center_x = screen.get_width() // 2

        # 标题
        draw_pixel_text(screen, "Dungeon Warriors",
                        title_font, (255, 200, 50),
                        screen_center_x, 160, shadow=True)

        # 副标题
        sub_font = get_button_font()
        sub_surf = sub_font.render("— 每层新局，鏖战高塔 —", True, (180, 180, 200))
        sub_rect = sub_surf.get_rect(center=(screen_center_x, 230))
        screen.blit(sub_surf, sub_rect)

        # 按钮
        for i, rect in enumerate(self.buttons):
            if i < len(self.button_labels):
                draw_stone_button(screen, rect, self.button_labels[i],
                                  btn_font, hover=(i == self.hovered_index))

        # 作者署名 + 版本号（使用项目字体以支持中文）
        small_font = get_font(14)

        credit = small_font.render(
            "作者：Dusk_Wind  重庆大学大数据与软件学院",
            True, (120, 120, 140)
        )
        credit_rect = credit.get_rect(center=(screen_center_x, screen.get_height() - 20))
        screen.blit(credit, credit_rect)

        version = small_font.render("V1.0.5.4", True, (120, 120, 140))
        version_rect = version.get_rect(bottomright=(screen.get_width() - 15, screen.get_height() - 10))
        screen.blit(version, version_rect)
