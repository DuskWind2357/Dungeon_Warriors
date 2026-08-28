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
                 revive_system, current_floor: int,
                 auto_destroy: bool = False) -> None:
        self.player = player
        self.backpack = backpack
        self.revive_system = revive_system
        self.current_floor = current_floor
        self.auto_destroy = auto_destroy

        # 生成4个奖励选项
        self.options: list[tuple[str, str, object | None]] = []
        self._generate_options()

        # UI
        self.buttons: list[pygame.Rect] = []
        self.hovered: int = -1
        self.selected: int = -1
        self.confirmed: bool = False
        self.revealed_text: str = ""
        self.max_warning: bool = False      # 生命条数已达上限红字提示
        self.blocked_text: str = ""         # 空间不足禁止确认提示
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
        """生成神秘奖励（选择前隐藏内容）。复活选项始终可刷出，满条时确认仅提示。"""
        roll = random.random()
        if roll < 0.20:
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

    def _needed_slots(self) -> int:
        """当前选中奖励所需的背包空位数"""
        _, _, reward = self.options[self.selected]
        if reward == "revive":
            return 0
        if isinstance(reward, list):
            return len(reward)
        if isinstance(reward, (Weapon, Armor)):
            if self._reward_will_auto_equip():
                # 自动替换：被替换装备开启销毁则占0 / 关闭保留则占1；无旧装备占0
                if not self.auto_destroy and self._old_item() is not None:
                    return 1
                return 0
            # 不触发替换：奖励本身入背包占1
            return 1
        return 1

    def _can_confirm(self) -> bool:
        """背包空位是否足够容纳所选奖励"""
        from systems.inventory import count_empty_slots
        return count_empty_slots(self.backpack) >= self._needed_slots()

    def _confirm(self) -> None:
        from entities.item import Weapon, Armor, Consumable
        from systems.inventory import add_item

        # 空间不足 → 禁止确认
        if not self._can_confirm():
            self.blocked_text = f"背包空位不足（需 {self._needed_slots()} 格），无法确认！"
            return
        self.blocked_text = ""

        _, _, reward = self.options[self.selected]

        if reward == "revive":
            self.revealed_text = "获得：生命条数+1"
            if self.revive_system.revives_remaining < MAX_REVIVES:
                self.revive_system.revive_count += 1
                self.max_warning = False
            else:
                self.max_warning = True
        elif isinstance(reward, list):
            for item in reward:
                add_item(self.backpack, item)
            self.revealed_text = f"获得：{reward[0].name} ×{len(reward)}"
        elif isinstance(reward, (Weapon, Armor, Consumable)):
            # 检查是否需要自动装备（奖励等级更高时替换）
            if isinstance(reward, (Weapon, Armor)):
                if self._reward_will_auto_equip():
                    # 先取被替换的旧装备（在覆盖槽位之前）
                    replaced = self._old_item()
                    # 自动装备到对应槽位
                    if isinstance(reward, Weapon):
                        if self.options[self.selected][0].startswith("近战"):
                            self.player.melee_weapon = reward
                        elif self.options[self.selected][0].startswith("远程"):
                            self.player.ranged_weapon = reward
                    else:
                        self.player.armor = reward
                    self.revealed_text = f"获得并装备：{reward.name}"
                    # 被替换装备去向：开启销毁则丢弃；关闭则放入背包
                    if not self.auto_destroy and replaced is not None:
                        add_item(self.backpack, replaced)
                else:
                    # 等级相等（或非装备）不替换，奖励直接入背包
                    add_item(self.backpack, reward)
                    self.revealed_text = f"获得：{reward.name}"
            else:
                add_item(self.backpack, reward)
                self.revealed_text = f"获得：{reward.name}"

        self.confirmed = True
        self._reveal_timer = 1.5  # 1.5秒展示时间

    def _should_auto_equip_weapon(self, new_weapon: Weapon, old_weapon: Weapon | None) -> bool:
        """判断是否应该自动装备新武器"""
        if old_weapon is None:
            return True
        
        # T5和特殊视为同级
        new_level = new_weapon.tier if new_weapon.tier < 5 else 5
        old_level = old_weapon.tier if old_weapon.tier < 5 else 5
        
        return new_level > old_level

    def _should_auto_equip_armor(self, new_armor: Armor, old_armor: Armor | None) -> bool:
        """判断是否应该自动装备新护甲"""
        if old_armor is None:
            return True
        
        # T5和特殊视为同级
        new_level = new_armor.tier if new_armor.tier < 5 else 5
        old_level = old_armor.tier if old_armor.tier < 5 else 5
        
        return new_level > old_level

    def _reward_will_auto_equip(self) -> bool:
        """当前选中奖励是否会触发自动装备替换（新装备等级更高）"""
        from entities.item import Weapon, Armor
        _, _, reward = self.options[self.selected]
        if isinstance(reward, Weapon):
            if self.options[self.selected][0].startswith("近战"):
                return self._should_auto_equip_weapon(reward, self.player.melee_weapon)
            if self.options[self.selected][0].startswith("远程"):
                return self._should_auto_equip_weapon(reward, self.player.ranged_weapon)
        elif isinstance(reward, Armor):
            return self._should_auto_equip_armor(reward, self.player.armor)
        return False

    def _old_item(self) -> Weapon | Armor | None:
        """返回选中奖励对应槽位的当前装备；未装备或无对应槽位返回 None"""
        from entities.item import Weapon, Armor
        _, _, reward = self.options[self.selected]
        if isinstance(reward, Weapon):
            if self.options[self.selected][0].startswith("近战"):
                return self.player.melee_weapon
            if self.options[self.selected][0].startswith("远程"):
                return self.player.ranged_weapon
        elif isinstance(reward, Armor):
            return self.player.armor
        return None

    def update(self, dt: float) -> str | None:
        """展示揭示文字后延迟返回"""
        if self.confirmed and hasattr(self, '_reveal_timer'):
            self._reveal_timer -= dt
            if self._reveal_timer <= 0:
                return "combat"
        return None

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
        needed = self._needed_slots() if self.selected >= 0 else 1
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
            # 空间不足禁止确认提示（红色）
            if self.blocked_text:
                blk = get_font(16).render(self.blocked_text, True, (255, 60, 60))
                screen.blit(blk, blk.get_rect(center=(cx, self.confirm_btn.bottom + 18)))

        # 神秘奖励揭晓
        if self.confirmed and self.revealed_text:
            rev = get_font(22).render(self.revealed_text, True, COLOR_TITLE)
            screen.blit(rev, rev.get_rect(center=(cx, WINDOW_HEIGHT - 40)))
            # 生命条数已达上限红字提示
            if self.max_warning:
                warn = get_font(16).render(
                    "剩余生命条数已达上限，不再增加！", True, (255, 60, 60))
                screen.blit(warn, warn.get_rect(center=(cx, WINDOW_HEIGHT - 16)))
        elif self.selected < 0:
            hint = get_font(16).render("点击选择一项奖励", True, (160, 160, 160))
            screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 40)))
