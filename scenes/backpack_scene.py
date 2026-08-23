"""
Dungeon Warriors V1.0.3 — 背包场景
8×8 网格，左键拿起/放下，右键弹出菜单
"""

import pygame
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    INVENTORY_COLS, INVENTORY_ROWS, INVENTORY_SIZE,
    COLOR_TEXT, COLOR_TEXT_DIM,
)
from entities.player import Player
from entities.item import Weapon, Armor, Consumable
from systems.inventory import use_item, destroy_item, get_slot_at_position
from rendering.pixel_style import draw_overlay
from rendering.renderer import get_button_font, get_hud_font

SLOT_SIZE = 48
SLOT_GAP = 4



# 物品图标映射 (V1.0.3 P7 完整版)
ITEM_ICONS = {
    # 剑
    "铜剑": "icon/Items/Weapon/剑/ItemSprite_copper-sword.webp",
    "铁剑": "icon/Items/Weapon/剑/ItemSprite_iron-sword.webp",
    "金剑": "icon/Items/Weapon/剑/ItemSprite_golden-sword.webp",
    "钻石剑": "icon/Items/Weapon/剑/ItemSprite_diamond-sword.webp",
    "下界合金剑": "icon/Items/Weapon/剑/ItemSprite_netherite-sword.webp",
    # 斧
    "铜斧": "icon/Items/Weapon/斧/ItemSprite_copper-axe.webp",
    "铁斧": "icon/Items/Weapon/斧/ItemSprite_axe.webp",
    "金斧": "icon/Items/Weapon/斧/ItemSprite_golden-axe.webp",
    "钻石斧": "icon/Items/Weapon/斧/ItemSprite_diamond-axe.webp",
    "下界合金斧": "icon/Items/Weapon/斧/ItemSprite_netherite-axe.webp",
    # 矛
    "铜矛": "icon/Items/Weapon/矛/ItemSprite_copper-spear.webp",
    "铁矛": "icon/Items/Weapon/矛/ItemSprite_iron-spear.webp",
    "金矛": "icon/Items/Weapon/矛/ItemSprite_golden-spear.webp",
    "钻石矛": "icon/Items/Weapon/矛/ItemSprite_diamond-spear.webp",
    "下界合金矛": "icon/Items/Weapon/矛/ItemSprite_netherite-spear.webp",
    # 匕首
    "匕首": "icon/Items/Weapon/100px-Daggers_(MCD).webp",
    # 远程
    "弓": "icon/Items/Weapon/ItemSprite_bow.webp",
    "弩": "icon/Items/Weapon/ItemSprite_crossbow.webp",
    # 特殊武器
    "精英之弓": "icon/Items/Weapon/DungeonsItemSprite_elite-power-bow.webp",
    "幻术师之弓": "icon/Items/Weapon/DungeonsItemSprite_call-of-the-void.webp",
    "机械弩": "icon/Items/Weapon/DungeonsItemSprite_auto-crossbow.webp",
    "杀戮之弩": "icon/Items/Weapon/DungeonsItemSprite_slayer-crossbow.webp",
    "机械链锯": "icon/Items/Weapon/DungeonsItemSprite_mechanized-sawblade.webp",
    "三叉戟": "icon/Items/Weapon/ItemSprite_trident.webp",
    # 护甲
    "战袍": "icon/Items/Armor/160px-Battle_Robe_(MCD).webp",
    "猎人之甲": "icon/Items/Armor/160px-Hunter's_Armor_(MCD).webp",
    "弓箭手之甲": "icon/Items/Armor/160px-Archer's_Armor_(MCD).webp",
    "冷酷战甲": "icon/Items/Armor/160px-Grim_Armor_(MCD).webp",
    "窃贼之甲": "icon/Items/Armor/160px-Thief_Armor_(MCD).webp",
    "幻影长袍": "icon/Items/Armor/160px-Splendid_Robe_(MCD).webp",
    "凋零之甲": "icon/Items/Armor/Wither_Armor_(MCD).png",
    "守卫者之甲": "icon/Items/Armor/160px-Gilded_Glory_(MCD).webp",
    "高地战甲": "icon/Items/Armor/160px-Highland_Armor_(MCD).webp",
    # 消耗品
    "面包": "icon/Items/Consumables/ItemSprite_bread.webp",
    "力量药水": "icon/Items/Consumables/160px-Sweet_Brew.webp",
    "迅捷药水": "icon/Items/Consumables/160px-Swiftness_Potion.webp",
    "生命药水": "icon/Items/Consumables/160px-Strength_Potion_Dungeons.webp",
    "隐身药水": "icon/Items/Consumables/160px-Shadow_Brew.webp",
}

class BackpackScene:
    def __init__(self, player: Player, backpack: list,
                 audio=None) -> None:
        self.player = player
        self.backpack = backpack
        self.audio = audio
        self.grid_x = 0; self.grid_y = 0
        self._calc_grid()
        self.hovered_slot: int | None = None
        self.status_text = ""
        # 拿起/放下
        self._held_item = None
        self._held_from = -1
        # 右键菜单
        self._menu_slot: int | None = None
        self._menu_btns: list[pygame.Rect] = []
        self._menu_labels: list[str] = []
        self._menu_item_name: str = ""

    def _calc_grid(self):
        tw = INVENTORY_COLS * SLOT_SIZE + (INVENTORY_COLS-1) * SLOT_GAP
        th = INVENTORY_ROWS * SLOT_SIZE + (INVENTORY_ROWS-1) * SLOT_GAP
        self.grid_x = (WINDOW_WIDTH - tw) // 2
        self.grid_y = (WINDOW_HEIGHT - th) // 2 - 20

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_b, pygame.K_ESCAPE):
                if self._held_item:
                    self.backpack[self._held_from] = self._held_item
                    self._held_item = None
                return "close"
        elif event.type == pygame.MOUSEMOTION:
            self.hovered_slot = get_slot_at_position(
                event.pos[0], event.pos[1], self.grid_x, self.grid_y, SLOT_SIZE, SLOT_GAP)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键
                return self._on_left_click(event.pos)
            elif event.button == 3:  # 右键
                self._on_right_click(event.pos)
        return None

    def _on_left_click(self, pos) -> str | None:
        # 先检查右键菜单按钮
        if self._menu_slot is not None:
            for i, btn in enumerate(self._menu_btns):
                if btn.collidepoint(pos):
                    return self._menu_action(i)

        slot = get_slot_at_position(pos[0], pos[1], self.grid_x, self.grid_y, SLOT_SIZE, SLOT_GAP)
        self._menu_slot = None
        if slot is None:
            if self._held_item:
                self.backpack[self._held_from] = self._held_item
                self._held_item = None
            return None

        if self._held_item:
            # 放下：只能放到空格或原格子
            if self.backpack[slot] is None:
                self.backpack[slot] = self._held_item
                self._held_item = None
            elif slot == self._held_from:
                self.backpack[slot] = self._held_item
                self._held_item = None
            # 否则忽略（不能放到有物品的非原格子）
        else:
            # 拿起
            if self.backpack[slot] is not None:
                self._held_item = self.backpack[slot]
                self._held_from = slot
                self.backpack[slot] = None
        return None

    def _on_right_click(self, pos):
        slot = get_slot_at_position(pos[0], pos[1], self.grid_x, self.grid_y, SLOT_SIZE, SLOT_GAP)
        if slot is None or self.backpack[slot] is None:
            self._menu_slot = None; return
        self._menu_slot = slot
        item = self.backpack[slot]
        self._menu_item_name = item.name
        self._menu_btns = []
        self._menu_labels = []
        sx = self.grid_x + (slot % INVENTORY_COLS) * (SLOT_SIZE + SLOT_GAP)
        sy = self.grid_y + (slot // INVENTORY_COLS) * (SLOT_SIZE + SLOT_GAP) + SLOT_SIZE + 2
        if isinstance(item, Consumable):
            self._menu_labels = ["使用", "销毁"]
        else:
            self._menu_labels = ["替换", "销毁"]
        for i, _ in enumerate(self._menu_labels):
            self._menu_btns.append(pygame.Rect(sx, sy + i*22, SLOT_SIZE+20, 20))

    def _menu_action(self, idx: int) -> str | None:
        slot = self._menu_slot
        self._menu_slot = None
        if slot is None: return None
        item = self.backpack[slot]
        if item is None: return None
        action = self._menu_labels[idx]
        if action == "使用" or action == "替换":
            self.status_text = use_item(self.player, self.backpack, slot)
        elif action == "销毁":
            self.status_text = destroy_item(self.backpack, slot)
        return None

    def draw(self, screen: pygame.Surface):
        draw_overlay(screen, 180)
        font = get_hud_font()
        title_f = get_button_font()
        cx = WINDOW_WIDTH // 2

        t = title_f.render("背包 (64格)", True, COLOR_TEXT)
        screen.blit(t, t.get_rect(center=(cx, self.grid_y - 24)))

        for i in range(INVENTORY_SIZE):
            r = i // INVENTORY_COLS; c = i % INVENTORY_COLS
            x = self.grid_x + c * (SLOT_SIZE + SLOT_GAP)
            y = self.grid_y + r * (SLOT_SIZE + SLOT_GAP)
            rect = pygame.Rect(x, y, SLOT_SIZE, SLOT_SIZE)
            bg = (60, 60, 75) if i == self.hovered_slot else (40, 40, 50)
            pygame.draw.rect(screen, bg, rect, border_radius=2)
            pygame.draw.rect(screen, (80, 80, 90), rect, width=1, border_radius=2)
            item = self.backpack[i] if i < len(self.backpack) else None
            if item and not (self._held_item and i == self._held_from):
                self._draw_item(screen, item, rect, font)
        # 手持物品跟随鼠标
        if self._held_item:
            mx, my = pygame.mouse.get_pos()
            r2 = pygame.Rect(mx-16, my-16, 32, 32)
            self._draw_item(screen, self._held_item, r2, font, held=True)

        # 装备槽
        ey = self.grid_y + INVENTORY_ROWS * (SLOT_SIZE + SLOT_GAP) + 8
        for label in [f"M: {self.player.melee_weapon.name}" if self.player.melee_weapon else "M: 空",
                       f"R: {self.player.ranged_weapon.name}" if self.player.ranged_weapon else "R: 空",
                       f"A: {self.player.armor.name}" if self.player.armor else "A: 空"]:
            s = font.render(label, True, COLOR_TEXT_DIM)
            screen.blit(s, s.get_rect(center=(cx, ey))); ey += 16

        # 右键菜单 + 物品名称
        if self._menu_slot is not None:
            name_surf = font.render(self._menu_item_name, True, (255, 220, 80))
            first_btn = self._menu_btns[0] if self._menu_btns else pygame.Rect(0,0,0,0)
            screen.blit(name_surf, name_surf.get_rect(center=(first_btn.centerx, first_btn.top - 14)))
            for i, btn in enumerate(self._menu_btns):
                pygame.draw.rect(screen, (50, 50, 60), btn)
                pygame.draw.rect(screen, (120, 120, 140), btn, width=1)
                t2 = font.render(self._menu_labels[i], True, COLOR_TEXT)
                screen.blit(t2, t2.get_rect(center=btn.center))

        # 状态
        if self.status_text:
            st = font.render(self.status_text, True, (255, 200, 50))
            screen.blit(st, st.get_rect(center=(cx, WINDOW_HEIGHT - 60)))
        hint = font.render("B/ESC 关闭 | 左键 拿起/放下 | 右键 菜单", True, COLOR_TEXT_DIM)
        screen.blit(hint, hint.get_rect(center=(cx, WINDOW_HEIGHT - 30)))

    def _draw_item(self, screen, item, rect, font, held=False):
        import os
        from utils import resource_path
        # 尝试使用定制图标（精确 → 去后缀 → 去T标 → 关键词匹配）
        icon_key = item.name
        if icon_key not in ITEM_ICONS:
            import re
            base = re.sub(r'[\s（(]*[Tt]\d*[）)]*', '', item.name).strip()
            base = re.sub(r'[（(][^）)]*[）)]', '', base).strip()
            if base in ITEM_ICONS: icon_key = base
            else:
                # 关键词匹配：弩/弓/匕首/剑/斧/矛
                for kw in ["弩","弓","匕首","剑","斧","矛"]:
                    if kw in item.name and kw in ITEM_ICONS:
                        icon_key = kw; break
        if icon_key in ITEM_ICONS:
            if not hasattr(self, '_item_icons'): self._item_icons = {}
            if icon_key not in self._item_icons:
                try:
                    path = resource_path(ITEM_ICONS[icon_key])
                    if os.path.exists(path):
                        img = pygame.image.load(path)
                        self._item_icons[icon_key] = pygame.transform.scale(img, (rect.width-4, rect.height-4))
                    else:
                        self._item_icons[icon_key] = None
                except: self._item_icons[icon_key] = None
            icon = self._item_icons.get(icon_key)
            if icon:
                screen.blit(icon, (rect.x+2, rect.y+2))
                return
        # Fallback: 颜色+文字
        if isinstance(item, Weapon):
            color = (180, 180, 220)
            label = f"+{item.attack_bonus}"
        elif isinstance(item, Armor):
            color = (180, 220, 180)
            label = "A"
        elif isinstance(item, Consumable):
            if item.item_type.startswith("heal"): color = (220, 100, 100); label = "HP"
            else: color = (255, 200, 50); label = "x2"
        else: return
        inner = rect.inflate(-6, -6)
        pygame.draw.rect(screen, color, inner, border_radius=2)
        n = font.render(label, True, (255, 255, 255))
        screen.blit(n, n.get_rect(center=rect.center))
