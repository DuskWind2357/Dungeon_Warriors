"""
Dungeon Warriors v2.0 — 楼层通关奖励场景
四选一（近战/远程/护甲/神秘奖励）+ 神秘奖励概率表
"""

import random
import pygame
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_TEXT, COLOR_TITLE,
    COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_BUTTON_BORDER, COLOR_BUTTON_TEXT,
    MAX_REVIVES,
)
from entities.player import Player
from entities.item import Weapon, Armor, Consumable
from data.weapons import WEAPON_BY_TYPE_TIER, WEAPON_BY_NAME
from data.armor import ARMOR_BY_TIER, ARMOR_BY_NAME
from data.consumables import (
    HEALTH_POTION, STRENGTH_POTION, INVIS_POTION, SWIFT_POTION,
)
from rendering.pixel_style import draw_overlay
from rendering.renderer import get_font


class RewardScene:
    """楼层通关奖励场景 — 四选一"""

    def __init__(self, player: Player, backpack: list,
                 revive_system, current_floor: int) -> None:
        self.player = player
        self.backpack = backpack
        self.revive_system = revive_system
        self.current_floor = current_floor

        # 生成4个奖励选项
        self.options: list[tuple[str, str, object | None]] = []
        self._generate_options()

        # UI
        self.buttons: list[pygame.Rect] = []
        self.hovered: int = -1
        self.selected: int = -1
        self.confirmed: bool = False
        self.revealed_text: str = ""
        self.pending_rewards: list = []
        self.confirm_btn: pygame.Rect | None = None
        self._layout_buttons()

    def _generate_options(self) -> None:
        """生成四选一奖励"""
        # 1. 近战武器升级
        melee = self._gen_upgrade("melee")
        # 2. 远程武器升级
        ranged = self._gen_upgrade("ranged")
        # 3. 护甲升级
        armor = self._gen_upgrade("armor")
        # 4. 神秘奖励
        mystery = self._gen_mystery()

        self.options = [melee, ranged, armor, mystery]

    def _gen_upgrade(self, category: str) -> tuple[str, str, object | None]:
        """生成升级奖励"""
        current_tier = 0
        if category == "melee" and self.player.melee_weapon:
            current_tier = self.player.melee_weapon.tier
        elif category == "ranged" and self.player.ranged_weapon:
            current_tier = self.player.ranged_weapon.tier
        elif category == "armor" and self.player.armor:
            current_tier = self.player.armor.tier

        new_tier = min(5, current_tier + 1)
        is_max = (current_tier >= 5)

        if category == "melee":
            wtypes = ["sword", "axe", "spear", "dagger"]
            wtype = random.choice(wtypes)
            if is_max and random.random() < 0.45:
                special_names = ["三叉戟", "机械链锯"]
                name = random.choice(special_names)
                item = WEAPON_BY_NAME.get(name)
            else:
                item = WEAPON_BY_TYPE_TIER.get((wtype, new_tier))
            label = f"近战武器 (T{new_tier})" if not is_max else "近战武器 (MAX)"
            desc = item.name if item else "无"

        elif category == "ranged":
            wtype = "bow" if random.random() < 0.5 else "crossbow"
            if is_max and random.random() < 0.45:
                special_names = ["精英之弓", "杀戮之弩", "机械弩", "幻术师之弓"]
                name = random.choice(special_names)
                item = WEAPON_BY_NAME.get(name)
            else:
                item = WEAPON_BY_TYPE_TIER.get((wtype, new_tier))
            label = f"远程武器 (T{new_tier})" if not is_max else "远程武器 (MAX)"
            desc = item.name if item else "无"

        else:  # armor
            if is_max and random.random() < 0.45:
                special_names = ["幻影长袍", "高地战甲", "守卫者之甲", "凋零之甲"]
                name = random.choice(special_names)
                item = ARMOR_BY_NAME.get(name)
            else:
                pool = ARMOR_BY_TIER.get(new_tier, [])
                item = random.choice(pool) if pool else None
            label = f"护甲 (T{new_tier})" if not is_max else "护甲 (MAX)"
            desc = item.name if item else "无"

        return (label, desc, item)

    def _gen_mystery(self) -> tuple[str, str, object | None]:
        """生成神秘奖励（选择前隐藏内容）"""
        roll = random.random()
        if roll < 0.20 and self.revive_system.revives_remaining < MAX_REVIVES:
            return ("神秘奖励", "???", "revive")
        elif roll < 0.25:
            return ("神秘奖励", "???", [HEALTH_POTION, HEALTH_POTION])
        elif roll < 0.30:
            return ("神秘奖励", "???", [STRENGTH_POTION, STRENGTH_POTION])
        elif roll < 0.35:
            return ("神秘奖励", "???", [SWIFT_POTION, SWIFT_POTION])
        elif roll < 0.40:
            return ("神秘奖励", "???", [INVIS_POTION, INVIS_POTION])
        elif roll < 0.55:
            return ("神秘奖励", "???", HEALTH_POTION)
        elif roll < 0.70:
            return ("神秘奖励", "???", STRENGTH_POTION)
        elif roll < 0.85:
            return ("神秘奖励", "???", SWIFT_POTION)
        else:
            return ("神秘奖励", "???", INVIS_POTION)

    def _layout_buttons(self) -> None:
        self.buttons = []
        btn_w, btn_h = 360, 52
        start_y = 260
        gap = 14
        for i in range(4):
            rect = pygame.Rect((WINDOW_WIDTH - btn_w) // 2,
                               start_y + i * (btn_h + gap), btn_w, btn_h)
            self.buttons.append(rect)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = -1
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos):
                    self.hovered = i
                    break
            if self.confirm_btn is not None and self.confirm_btn.collidepoint(event.pos):
                self.hovered = -2  # confirm button hovered
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 检查确认按钮
            if self.selected >= 0 and self.confirm_btn is not None:
                if self.confirm_btn.collidepoint(event.pos):
                    self._confirm()
                    return None
            # 检查选项按钮（可重新选择）
            for i, rect in enumerate(self.buttons):
                if rect.collidepoint(event.pos):
                    self._select(i)
        return None

    def _select(self, index: int) -> None:
        self.selected = index
        # 显示确认按钮
        btn_w, btn_h = 180, 26
        cx = WINDOW_WIDTH // 2
        self.confirm_btn = pygame.Rect(cx - btn_w // 2, 540, btn_w, btn_h)

    def _confirm(self) -> None:
        _, _, reward = self.options[self.selected]

        if reward == "revive":
            self.revive_system.revive_count = min(MAX_REVIVES,
                                                   self.revive_system.revive_count + 1)
            self.revealed_text = "+1 复活次数"
        elif isinstance(reward, list):
            self.pending_rewards.extend(reward)
            self.revealed_text = f"{reward[0].name} ×{len(reward)}"
        elif reward is not None:
            from entities.item import Weapon, Armor
            from systems.inventory import add_item
            if isinstance(reward, Weapon):
                if reward.category == "melee":
                    old = self.player.equip_melee_weapon(reward)
                else:
                    old = self.player.equip_ranged_weapon(reward)
                self.revealed_text = f"{reward.name}"
                if old and not add_item(self.backpack, old):
                    self.pending_rewards.append(old)
            elif isinstance(reward, Armor):
                old = self.player.equip_armor(reward)
                self.revealed_text = f"{reward.name}"
                if old and not add_item(self.backpack, old):
                    self.pending_rewards.append(old)
            else:
                self.pending_rewards.append(reward)
                self.revealed_text = f"{reward.name}"

        self.confirmed = True
        self._reveal_timer = 1.5  # 1.5秒展示时间

    def update(self, dt: float) -> str | None:
        """展示揭示文字后延迟返回"""
        if self.confirmed and hasattr(self, '_reveal_timer'):
            self._reveal_timer -= dt
            if self._reveal_timer <= 0:
                return "combat"
        return None

    def get_pending_rewards(self) -> list:
        return self.pending_rewards

    def draw(self, screen: pygame.Surface) -> None:
        draw_overlay(screen, 190)

        # 标题
        font_large = get_font(36)
        font_btn = get_font(20)
        cx = WINDOW_WIDTH // 2

        title = font_large.render("选择奖励", True, COLOR_TITLE)
        screen.blit(title, title.get_rect(center=(cx, 120)))

        floor_text = get_font(24).render(
            f"第 {self.current_floor} 层 通关", True, COLOR_TEXT)
        screen.blit(floor_text, floor_text.get_rect(center=(cx, 170)))

        # 背包容量警告
        from systems.inventory import count_empty_slots
        empty = count_empty_slots(self.backpack)
        needed = len(self.pending_rewards) if self.selected >= 0 else 1
        if empty < needed:
            warn = get_font(16).render(
                f"⚠ 背包空间不足！(空位:{empty}, 需要:{needed})",
                True, (255, 100, 100))
            screen.blit(warn, warn.get_rect(center=(cx, 210)))

        # 按钮
        for i, rect in enumerate(self.buttons):
            if i >= len(self.options):
                continue
            label, desc, _ = self.options[i]

            if i == self.selected:
                color = (200, 160, 40)  # 金色选中
                border = (240, 200, 60)
            elif i == self.hovered:
                color = COLOR_BUTTON_HOVER
                border = COLOR_BUTTON_BORDER
            else:
                color = COLOR_BUTTON
                border = COLOR_BUTTON_BORDER
            pygame.draw.rect(screen, color, rect, border_radius=6)
            pygame.draw.rect(screen, border, rect, width=2, border_radius=6)

            text = font_btn.render(f"{label}: {desc}", True, COLOR_BUTTON_TEXT)
            screen.blit(text, text.get_rect(center=rect.center))

        # 确认按钮
        if self.selected >= 0 and not self.confirmed and self.confirm_btn:
            color = (100, 160, 100) if self.hovered == -2 else COLOR_BUTTON_HOVER
            pygame.draw.rect(screen, color, self.confirm_btn, border_radius=4)
            pygame.draw.rect(screen, COLOR_BUTTON_BORDER, self.confirm_btn, width=2, border_radius=4)
            cfm = font_btn.render("确认选择", True, COLOR_BUTTON_TEXT)
            screen.blit(cfm, cfm.get_rect(center=self.confirm_btn.center))

        # 神秘奖励揭晓
        if self.confirmed and self.revealed_text:
            rev = get_font(22).render(f"获得: {self.revealed_text}", True, COLOR_TITLE)
            screen.blit(rev, rev.get_rect(center=(cx, WINDOW_HEIGHT - 40)))
        elif self.selected < 0:
            hint = get_font(16).render("点击选择一项奖励", True, (160, 160, 160))
            screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))
