"""
Dungeon Warriors — 渲染器
绘制地图、玩家、怪物、掉落物品、HUD
"""

import math
import os
import random
import pygame
from config import (
    TILE_SIZE, MAP_COLS, MAP_ROWS,
    COLOR_BG, COLOR_WALL, COLOR_FLOOR,
    COLOR_SPAWN, COLOR_PORTAL,
    COLOR_PLAYER,
    COLOR_HP_BAR, COLOR_HP_BAR_BG,
    COLOR_MONSTER_NORMAL, COLOR_MONSTER_ELITE,
    COLOR_MONSTER_BOSS, COLOR_MONSTER_FINAL_BOSS,
    COLOR_TEXT, COLOR_TEXT_DIM, COLOR_HUD,
    COLOR_DROP_HEAL, COLOR_DROP_POWER,
    COLOR_BUFF_ACTIVE, COLOR_INVIS, COLOR_SWIFT,
)
from entities.player import Player
from entities.monster import Monster
from entities.item import Weapon, Armor, Consumable
from rendering.pixel_style import draw_progress_bar
from utils import resource_path

# 怪物图标缓存
_monster_icons: dict[str, pygame.Surface] = {}

# 地图贴图缓存
_map_textures: dict[str, pygame.Surface] = {}

# 粗体字体缓存（仅战斗界面使用）
_bold_font_cache: dict[int, pygame.font.Font] = {}

# 怪物 → 图标文件映射
MONSTER_ICON_MAP: dict[str, str] = {
    "僵尸": "icon/ZombieFace.webp",
    "蜘蛛": "icon/SpiderFace.png",
    "骷髅": "icon/SkeletonFace.png",
    "蝙蝠": "icon/BatFace.webp",
    "大型史莱姆": "icon/SlimeFace.webp",
    "中型史莱姆": "icon/SlimeFace.webp",
    "小型史莱姆": "icon/SlimeFace.webp",
    "小型岩浆史莱姆": "icon/MagmaCubeFace.png",
    "中型岩浆史莱姆": "icon/MagmaCubeFace.png",
    "精英骷髅": "icon/SkeletonVanguardFace.webp",
    "精英僵尸": "icon/HuskFace.webp",
    "烈焰使者": "icon/BlazeFace.png",
    "暗影骑士": "icon/WitherSkeletonFace.png",
    "暗黑骑士": "icon/WitherFace.png",
    "炎魔": "icon/WildfireFace.webp",
    "掠夺者突袭队长": "icon/EnchanterFace.webp",
    "卫道士突袭队长": "icon/RoyalGuardFace.webp",
}
# 高塔之主按阶段
BOSS_PHASE_ICONS: dict[int, str] = {
    1: "icon/TowerWraithFace.webp",
    2: "icon/NamelessOneFace.webp",
    3: "icon/NecromancerFace.webp",
}

def _load_icon(filename: str, size: int) -> pygame.Surface | None:
    try:
        path = resource_path(filename)
        if os.path.exists(path):
            img = pygame.image.load(path)
            return pygame.transform.scale(img, (size, size))
    except Exception:
        pass
    return None


# 地图贴图路径映射
_MAP_TEXTURE_PATHS = {
    "wall":       "icon/block/墙壁.png",
    "wall_var":   "icon/block/墙壁变种.webp",
    "floor":      "icon/block/地砖.png",
    "floor_var":  "icon/block/地砖变种.png",
    "spawn":      "icon/block/出生点.webp",
}


def _load_map_textures() -> None:
    """预加载地图贴图并缩放至 TILE_SIZE"""
    if _map_textures:
        return
    for key, path in _MAP_TEXTURE_PATHS.items():
        full = resource_path(path)
        if os.path.exists(full):
            try:
                img = pygame.image.load(full).convert_alpha()
                _map_textures[key] = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
            except Exception:
                _map_textures[key] = None
        else:
            _map_textures[key] = None

def _get_monster_icon(monster, size: int) -> pygame.Surface | None:
    """获取怪物图标（含BOSS阶段判定）"""
    key = None
    if monster.name == "高塔之主":
        icon_file = BOSS_PHASE_ICONS.get(monster.phase)
        key = f"boss_p{monster.phase}"
    else:
        icon_file = MONSTER_ICON_MAP.get(monster.name)
        key = monster.name
    if not icon_file or not key:
        return None
    if key not in _monster_icons:
        _monster_icons[key] = _load_icon(icon_file, size)
    return _monster_icons.get(key)


def draw_map(screen: pygame.Surface, grid: list[list[int]],
             spawn_pos: tuple[int, int],
             portal_pos: tuple[int, int],
             portal_active: bool,
             in_spawn_zone: bool) -> None:
    """绘制地图网格（贴图版本）"""
    _load_map_textures()
    sc, sr = spawn_pos

    for row in range(len(grid)):
        for col in range(len(grid[row])):
            x = col * TILE_SIZE
            y = row * TILE_SIZE

            # 出生点方格使用独立图片，不参与变种
            if (col, row) == (sc, sr):
                tex = _map_textures.get("spawn")
                if tex:
                    screen.blit(tex, (x, y))
                else:
                    pygame.draw.rect(screen, COLOR_SPAWN[:3], (x, y, TILE_SIZE, TILE_SIZE))
                continue

            if grid[row][col] == 1:
                # 墙壁：10% 概率使用变种贴图（固定种子，避免闪烁）
                seed = row * 1000 + col
                rng = random.Random(seed)
                is_variant = rng.random() < 0.1
                key = "wall_var" if is_variant else "wall"
                tex = _map_textures.get(key)
                if tex:
                    screen.blit(tex, (x, y))
                else:
                    pygame.draw.rect(screen, COLOR_WALL, (x, y, TILE_SIZE, TILE_SIZE))
            else:
                # 地板：10% 概率使用变种贴图（固定种子，避免闪烁）
                seed = row * 1000 + col + 50000
                rng = random.Random(seed)
                is_variant = rng.random() < 0.1
                key = "floor_var" if is_variant else "floor"
                tex = _map_textures.get(key)
                if tex:
                    screen.blit(tex, (x, y))
                else:
                    pygame.draw.rect(screen, COLOR_FLOOR, (x, y, TILE_SIZE, TILE_SIZE))

    # 绘制出生点区域
    if in_spawn_zone:
        sx, sy = spawn_pos
        rect = pygame.Rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        s.fill((0, 100, 0, 80))
        screen.blit(s, rect.topleft)

    # 绘制传送门
    px, py = portal_pos
    portal_x = px * TILE_SIZE + TILE_SIZE // 2
    portal_y = py * TILE_SIZE + TILE_SIZE // 2
    color = COLOR_PORTAL if portal_active else (60, 60, 80)
    radius = TILE_SIZE // 2 - 2 if portal_active else TILE_SIZE // 3

    # 脉冲效果
    if portal_active:
        import time
        pulse = (math.sin(time.time() * 3) + 1) / 2  # 0~1
        radius += int(pulse * 4)
        alpha = int(150 + pulse * 105)
        glow = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*COLOR_PORTAL[:3], alpha),
                           (radius * 3 // 2, radius * 3 // 2), radius * 1.5)
        screen.blit(glow, (portal_x - radius * 3 // 2, portal_y - radius * 3 // 2))

    pygame.draw.circle(screen, color, (portal_x, portal_y), radius)


def draw_player(screen: pygame.Surface, player: Player) -> None:
    """绘制玩家（图标 + 方向指示器）"""
    x, y = int(player.x), int(player.y)
    size = TILE_SIZE // 3 * 2

    # 玩家图标
    key = "player"
    if key not in _monster_icons:
        _monster_icons[key] = _load_icon("icon/HumanFace.png", size)
    icon = _monster_icons.get(key)
    if icon:
        screen.blit(icon, (x - size // 2, y - size // 2))
    else:
        pygame.draw.circle(screen, COLOR_PLAYER, (x, y), TILE_SIZE // 3)

    # 方向指示器
    tip_x = x + math.cos(player.facing_angle) * (size // 2 + 3)
    tip_y = y + math.sin(player.facing_angle) * (size // 2 + 3)
    pygame.draw.circle(screen, (255, 255, 255), (int(tip_x), int(tip_y)), 3)

    # HP 条（在玩家上方）
    if player.current_hp < player.total_max_hp():
        bar_width = TILE_SIZE
        bar_height = 5
        bar_x = x - bar_width // 2
        bar_y = y - size // 2 - 12
        draw_progress_bar(screen, bar_x, bar_y, bar_width, bar_height,
                          player.current_hp / player.total_max_hp(),
                          COLOR_HP_BAR)


def draw_monster(screen: pygame.Surface, monster: Monster) -> None:
    """绘制怪物（根据类型不同大小和颜色）"""
    try:
        _draw_monster_impl(screen, monster)
    except Exception:
        # 防御性降级：任何渲染异常用简单矩形代替
        x, y = int(monster.x), int(monster.y)
        size = TILE_SIZE // 3
        pygame.draw.rect(screen, (200, 30, 30),
                         (x - size//2, y - size//2, size, size))

def _draw_monster_impl(screen: pygame.Surface, monster: Monster) -> None:
    """怪物绘制实现"""
    x, y = int(monster.x), int(monster.y)

    # 根据类型决定大小和颜色
    size_map = {
        "normal":      (TILE_SIZE // 3,      COLOR_MONSTER_NORMAL),
        "elite":       (TILE_SIZE // 3 + 4,  COLOR_MONSTER_ELITE),
        "head_boss":   (TILE_SIZE // 2 + 2,  COLOR_MONSTER_BOSS),
        "final_boss":  (TILE_SIZE - 4,       COLOR_MONSTER_FINAL_BOSS),
    }
    size, color = size_map.get(monster.monster_type, (TILE_SIZE // 3, COLOR_MONSTER_NORMAL))

    # 普通怪物按名称个性化颜色
    name_colors = {
        "僵尸":  (60, 140, 40),
        "骷髅":  (220, 220, 220),
        "蜘蛛":  (60, 55, 55),
        "蝙蝠":  (30, 30, 30),
        "大型史莱姆": (80, 220, 60),
        "中型史莱姆": (80, 220, 60),
        "小型史莱姆": (80, 220, 60),
        "小型岩浆史莱姆": (220, 60, 40),
        "中型岩浆史莱姆": (220, 60, 40),
    }
    if monster.name in name_colors:
        color = name_colors[monster.name]

    half = size // 2
    rect = pygame.Rect(x - half, y - half, size, size)

    # 尝试使用图标
    icon = _get_monster_icon(monster, size)
    if icon:
        screen.blit(icon, (x - size // 2, y - size // 2))
    elif monster.monster_type in ("head_boss", "final_boss"):
        points = [(x, y - half), (x + half, y), (x, y + half), (x - half, y)]
        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, (255, 255, 255, 80), points, width=2)
    else:
        pygame.draw.rect(screen, color, rect, border_radius=4)
        pygame.draw.rect(screen, (255, 255, 255, 60), rect, width=1, border_radius=4)

    # HP 条
    bar_width = TILE_SIZE
    bar_height = 4
    bar_x = x - bar_width // 2
    bar_y = y - half - 10
    draw_progress_bar(screen, bar_x, bar_y, bar_width, bar_height,
                      monster.hp_ratio, COLOR_HP_BAR)

    # 怪物名称（深灰色，不加粗）
    font_small = _get_small_font()
    if font_small:
        name_surf = font_small.render(monster.name, True, COLOR_HUD)
        name_rect = name_surf.get_rect(center=(x, y + half + 12))
        screen.blit(name_surf, name_rect)


def draw_drops(screen: pygame.Surface,
               drops: list[tuple[object, float, float]]) -> None:
    """绘制地面掉落物品"""
    for item, px, py in drops:
        x, y = int(px), int(py)

        # V1.0.3 P6 掉落颜色规则
        if isinstance(item, Consumable):
            if item.item_type.startswith("heal"):
                color = (139,90,43); shape = "circle"  # 面包=棕色
            else:
                color = (160,60,200); shape = "diamond"  # 药水=紫色
        elif isinstance(item, Weapon):
            color = (220,180,40) if item.tier >= 5 and (item.crit_chance or item.instakill or item.overheat_count) else (180,180,180)  # 金色/灰白
            shape = "rect"
        elif isinstance(item, Armor):
            color = (220,180,40) if item.tier >= 5 and item.armor_type == 'special' else (180,180,180)  # 金色/灰白
            shape = "rect"
        else:
            continue

        # 外发光
        glow = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color[:3], 80), (10, 10), 10)
        screen.blit(glow, (x - 10, y - 10))

        # 物品本体
        if shape == "circle":
            pygame.draw.circle(screen, color, (x, y), 5)
        elif shape == "diamond":
            pts = [(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)]
            pygame.draw.polygon(screen, color, pts)
        else:
            rect = pygame.Rect(x - 4, y - 4, 8, 8)
            pygame.draw.rect(screen, color, rect, border_radius=2)


def draw_hud(screen: pygame.Surface, player: Player,
             current_floor: int, revive_count: int,
             font: pygame.font.Font | None = None) -> None:
    """绘制 HUD v2.1（HP成长、Buff计时器、装备信息）"""
    if font is None:
        font = _get_default_font()

    max_hp = player.total_max_hp(current_floor)

    # 第一行：生命值 + 楼层 + 复活（并排显示，深灰色）
    hp_text = f"HP: {player.current_hp}/{max_hp}"
    floor_text = f"Floor: {current_floor}/30"
    revive_text = f"Revives: {revive_count}"
    first_line = f"{hp_text}   {floor_text}   {revive_text}"

    y_offset = 10
    surf = font.render(first_line, True, COLOR_HUD)
    screen.blit(surf, (10, y_offset))
    y_offset += 22

    # HP 条
    bar_width = 150
    draw_progress_bar(screen, 10, y_offset + 2, bar_width, 10,
                      player.current_hp / max_hp, COLOR_HP_BAR)

    # 装备（左下方，深灰色）
    equip_y = y_offset + 18
    mw = player.melee_weapon
    rw = player.ranged_weapon
    weapon_text = f"M: {mw.name} (+{mw.attack_bonus})" if mw else "M: None"
    ranged_text = f"R: {rw.name} (+{rw.attack_bonus})" if rw else "R: None"
    armor_text = f"A: {player.armor.name}" if player.armor else "A: None"
    for text in [weapon_text, ranged_text, armor_text]:
        surf = font.render(text, True, COLOR_HUD)
        screen.blit(surf, (10, equip_y))
        equip_y += 18

    # 右上：活跃 Buff 列表
    buff_y = 10
    buff_colors = {
        "strength": COLOR_DROP_POWER,
        "invisible": COLOR_INVIS,
        "swift": COLOR_SWIFT,
        "heal_over_time": COLOR_BUFF_ACTIVE,
    }
    buff_names = {
        "strength": "STR x2", "invisible": "隐身",
        "swift": "迅捷", "heal_over_time": "回复",
    }
    for buff_type, remaining in sorted(player.buffs.items()):
        if remaining > 0:
            color = buff_colors.get(buff_type, COLOR_TEXT)
            name = buff_names.get(buff_type, buff_type)
            buf_text = f"{name} {remaining:.1f}s"
            buf_surf = font.render(buf_text, True, color)
            screen.blit(buf_surf, (screen.get_width() - buf_surf.get_width() - 10, buff_y))
            buff_y += 18

    # 负面状态效果（右上方，buff下方）
    se_names = {"wither": "凋零", "burn": f"燃烧({int(player._burn_dmg)}/s)"}
    se_colors = {"wither": (80, 80, 80), "burn": (255, 80, 30)}
    for se_type, remaining in sorted(player.status_effects.items()):
        if remaining > 0 and se_type in se_names:
            se_text = f"{se_names[se_type]} {remaining:.1f}s"
            se_surf = font.render(se_text, True, se_colors.get(se_type, (255, 100, 100)))
            screen.blit(se_surf, (screen.get_width() - se_surf.get_width() - 10, buff_y))
            buff_y += 18


def draw_toast(screen: pygame.Surface, toast: dict | None,
               font: pygame.font.Font | None = None,
               offset: int = 0,
               color: tuple = None) -> None:
    """绘制 toast 消息（渐隐），offset 用于多条堆叠"""
    if toast is None or toast["timer"] <= 0:
        return

    if font is None:
        font = _get_default_font()
    if color is None:
        color = toast.get("color", COLOR_HP_BAR)

    alpha = int(255 * min(1.0, toast["timer"] / 0.5))
    text_surf = font.render(toast["text"], True, color)
    text_surf.set_alpha(alpha)

    screen_w = screen.get_width()
    base_y = screen.get_height() // 2 + 150
    text_rect = text_surf.get_rect(center=(screen_w // 2, base_y + offset * 28))
    screen.blit(text_surf, text_rect)


# -------- 内部字体缓存 --------

_font_cache: dict[int, pygame.font.Font] = {}


def _get_default_font() -> pygame.font.Font:
    return _get_font(18)


def _get_small_font() -> pygame.font.Font | None:
    try:
        return _get_font(12)
    except Exception:
        return None


def _get_font(size: int) -> pygame.font.Font:
    """获取字体（带缓存，内部使用）"""
    return get_font(size)


def get_font(size: int) -> pygame.font.Font:
    """获取字体（带缓存，公开接口）"""
    if size in _font_cache:
        return _font_cache[size]

    from utils import resource_path
    font_paths = [
        resource_path("font.ttf"),
        resource_path("font.otf"),
    ]

    for path in font_paths:
        if os.path.exists(path):
            font = pygame.font.Font(path, size)
            _font_cache[size] = font
            return font

    # 系统回退
    font = pygame.font.Font(None, size)
    _font_cache[size] = font
    return font


def get_bold_font(size: int) -> pygame.font.Font:
    """获取粗体字体（带缓存，仅战斗界面使用）"""
    if size in _bold_font_cache:
        return _bold_font_cache[size]

    from utils import resource_path
    font_paths = [
        resource_path("font.ttf"),
        resource_path("font.otf"),
    ]

    for path in font_paths:
        if os.path.exists(path):
            font = pygame.font.Font(path, size)
            font.set_bold(True)
            _bold_font_cache[size] = font
            return font

    font = pygame.font.Font(None, size)
    font.set_bold(True)
    _bold_font_cache[size] = font
    return font


def get_bold_small_font() -> pygame.font.Font | None:
    """获取粗体小字体（怪物名称等）"""
    try:
        return get_bold_font(12)
    except Exception:
        return None


def get_bold_hud_font() -> pygame.font.Font:
    """获取粗体HUD字体（战斗界面专用）"""
    return get_bold_font(18)


def get_title_font() -> pygame.font.Font:
    """获取标题大字体"""
    return _get_font(64)


def get_button_font() -> pygame.font.Font:
    """获取按钮字体"""
    return _get_font(28)


def get_hud_font() -> pygame.font.Font:
    """获取 HUD 字体"""
    return _get_font(18)
