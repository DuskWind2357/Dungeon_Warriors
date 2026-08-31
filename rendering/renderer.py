"""
Dungeon Warriors V1.0.5.12 — 渲染器
绘制地图、玩家、怪物、掉落物品、HUD
"""

import math
import os
import random
import pygame
from config import (
    TILE_SIZE, MAP_COLS, MAP_ROWS,
    TOTAL_FLOORS, HUD_WHITE_FLOOR_RANGES,
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
from entities.item import Weapon, Armor, Consumable, KeyItem
from rendering.pixel_style import draw_progress_bar
from systems.floor_manager import RoomType
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
    "掠夺者突袭队长": "icon/120px-TowerGuardFace.webp",   # V1.0.5.11 图标更换
    "卫道士突袭队长": "icon/RoyalGuardFace.webp",
    "冰霜僵尸": "icon/FrozenZombieFace.webp",
    "流髑": "icon/StrayFace.png",
    # V1.0.5.12 新增特殊实体图标
    "宝箱": "icon/BlockSprite_chest-front.png",
    "试炼刷怪笼": "icon/BlockSprite_trial-spawner-inactive.webp",
}
# 高塔之主按阶段
BOSS_PHASE_ICONS: dict[int, str] = {
    1: "icon/WraithFace.webp",   # V1.0.5.11 第一阶段图标更换
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


# 地图主题贴图路径映射（V1.0.5）
_THEME_TEXTURE_PATHS: dict[str, dict[str, str]] = {
    "dungeon": {
        "spawn":     "icon/block/地牢/出生点.webp",
        "floor":     "icon/block/地牢/地砖.png",
        "floor_var": "icon/block/地牢/地砖变种.png",
        "wall":      "icon/block/地牢/墙壁.png",
        "wall_var1": "icon/block/地牢/墙壁变种1.webp",
        "wall_var2": "icon/block/地牢/墙壁变种2.webp",
        "portal":    "icon/block/传送门.webp",
    },
    "snow": {
        "spawn":     "icon/block/雪地/玩家出生点.png",
        "floor":     "icon/block/雪地/地砖.webp",
        "floor_var": "icon/block/雪地/地砖变种.webp",
        "wall":      "icon/block/雪地/墙壁.webp",
        "wall_var1": "icon/block/雪地/墙壁变种.webp",
        "portal":    "icon/block/传送门.webp",
    },
    "hell": {
        "spawn":     "icon/block/地狱/出生点.png",
        "floor":     "icon/block/地狱/地砖.png",
        "floor_var": "icon/block/地狱/地砖变种.png",
        "wall":      "icon/block/地狱/墙壁.png",
        "trap":      "icon/block/地狱/陷阱.webp",
        "portal":    "icon/block/传送门.webp",
    },
    "boss": {
        "spawn":     "icon/block/头目/BlockSprite_lodestone.webp",
        "floor":     "icon/block/头目/头目楼层地砖.webp",
        "wall":      "icon/block/头目/头目楼层墙壁.png",
        "portal":    "icon/block/传送门.webp",
    },
}

# V1.0.5 特殊房间贴图
_SPECIAL_ROOM_TEXTURES: dict[str, dict[str, str]] = {
    "dungeon_room": {
        "floor": "icon/block/夹层/地砖.webp",
        "wall":  "icon/block/夹层/墙壁.webp",
    },
    "treasure_room": {
        "floor": "icon/block/宝藏室/BlockSprite_block-of-gold.webp",
        "wall":  "icon/block/宝藏室/BlockSprite_block-of-netherite.webp",
    },
    "portal": "icon/block/传送门.webp",
    "portal_active": "icon/block/传送门激活中.webp",
    "dungeon_portal": "icon/block/BlockSprite_end-gateway.webp",  # 副本传送门
    "floor_portal_inactive": "icon/block/传送门激活器.webp",  # 通关传送门（未激活）
    "floor_portal_active": "icon/block/传送门.webp",  # 通关传送门（已激活）
    "floor_portal": "icon/block/传送门.webp",
}

# 各主题变种概率（V1.0.4）
_THEME_VARIANTS: dict[str, dict] = {
    "dungeon": {"floor_var": 0.20, "wall_var1": 0.10, "wall_var2": 0.10},
    "snow":    {"floor_var": 0.20, "wall_var1": 0.20},
    "hell":    {"floor_var": 0.20},
    "boss":    {},
}


def _load_map_textures() -> None:
    """预加载全部主题地图贴图并缩放至 TILE_SIZE"""
    if _map_textures:
        return
    for theme, paths in _THEME_TEXTURE_PATHS.items():
        _map_textures[theme] = {}
        for key, path in paths.items():
            full = resource_path(path)
            if os.path.exists(full):
                try:
                    img = pygame.image.load(full).convert_alpha()
                    _map_textures[theme][key] = pygame.transform.scale(
                        img, (TILE_SIZE, TILE_SIZE))
                except Exception:
                    _map_textures[theme][key] = None
            else:
                _map_textures[theme][key] = None

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
             in_spawn_zone: bool,
             theme: str = "dungeon",
             floor_layout=None,
             current_room=None) -> None:
    """绘制地图网格（V1.0.5 多房间版本）
    grid 就是当前房间的独立20×15网格"""
    _load_map_textures()
    if theme not in _THEME_TEXTURE_PATHS:
        theme = "dungeon"
    texs = _map_textures.get(theme, {})
    probs = _THEME_VARIANTS.get(theme, {})
    sc, sr = spawn_pos

    room_type_val = current_room.room_type.value if current_room else None

    for row in range(len(grid)):
        for col in range(len(grid[row])):
            x = col * TILE_SIZE
            y = row * TILE_SIZE

            # 出生点方格只在出生点房间使用主题专属图片
            if (col, row) == (sc, sr) and room_type_val == "spawn":
                tex = texs.get("spawn")
                if tex:
                    screen.blit(tex, (x, y))
                else:
                    pygame.draw.rect(screen, COLOR_SPAWN[:3], (x, y, TILE_SIZE, TILE_SIZE))
                continue

            cell = grid[row][col]
            if cell == 1:
                # 墙壁变种（固定种子，避免闪烁）
                if room_type_val == "dungeon":
                    special = _SPECIAL_ROOM_TEXTURES.get("dungeon_room", {})
                    tex = _load_special_texture(special.get("wall"))
                elif room_type_val == "treasure":
                    special = _SPECIAL_ROOM_TEXTURES.get("treasure_room", {})
                    tex = _load_special_texture(special.get("wall"))
                else:
                    key = "wall"
                    v1 = probs.get("wall_var1", 0)
                    v2 = probs.get("wall_var2", 0)
                    if v1 or v2:
                        rng = random.Random(row * 1000 + col)
                        r = rng.random()
                        if r < v1:
                            key = "wall_var1"
                        elif r < v1 + v2:
                            key = "wall_var2"
                    tex = texs.get(key) or texs.get("wall")
                if tex:
                    screen.blit(tex, (x, y))
                else:
                    pygame.draw.rect(screen, COLOR_WALL, (x, y, TILE_SIZE, TILE_SIZE))
            elif cell == 2:
                # 出生点（由算法设置）
                tex = texs.get("spawn")
                if tex:
                    screen.blit(tex, (x, y))
                else:
                    pygame.draw.rect(screen, COLOR_SPAWN[:3], (x, y, TILE_SIZE, TILE_SIZE))
            elif cell == 3:
                # 通往下一楼层的传送门（先绘制地板贴图作为背景）
                if room_type_val == "dungeon":
                    special = _SPECIAL_ROOM_TEXTURES.get("dungeon_room", {})
                    tex = _load_special_texture(special.get("floor"))
                elif room_type_val == "treasure":
                    special = _SPECIAL_ROOM_TEXTURES.get("treasure_room", {})
                    tex = _load_special_texture(special.get("floor"))
                else:
                    key = "floor"
                    fv = probs.get("floor_var", 0)
                    if fv:
                        rng = random.Random(row * 1000 + col + 50000)
                        if rng.random() < fv:
                            key = "floor_var"
                    tex = texs.get(key) or texs.get("floor")
                if tex:
                    screen.blit(tex, (x, y))
                else:
                    pygame.draw.rect(screen, COLOR_FLOOR, (x, y, TILE_SIZE, TILE_SIZE))
                _draw_floor_portal(screen, x, y, portal_active)
            elif cell == 4:
                # 陷阱格（地狱主题）
                tex = texs.get("trap") or texs.get("floor")
                if tex:
                    screen.blit(tex, (x, y))
                else:
                    pygame.draw.rect(screen, COLOR_FLOOR, (x, y, TILE_SIZE, TILE_SIZE))
            elif cell == 5:
                # V1.0.5 传送门墙壁（根据目标房间类型选择贴图）
                portal_type = "portal"
                if current_room and floor_layout:
                    for p in current_room.portals:
                        pcol, prow = current_room._portal_grid_pos(p)
                        if (col, row) == (pcol, prow):
                            target_room = floor_layout.get_room_by_idx(p.target_room_idx)
                            if target_room:
                                # 副本→非宝藏室传送门用副本贴图（副本→宝藏室保持普通贴图）
                                if current_room.room_type == RoomType.DUNGEON and target_room.room_type != RoomType.TREASURE:
                                    portal_type = "dungeon_portal"
                                # 其他房间→副本传送门用副本贴图
                                elif target_room.room_type == RoomType.DUNGEON:
                                    portal_type = "dungeon_portal"
                            break
                _draw_portal_wall(screen, x, y, texs, portal_type)
            else:
                # 地板变种（固定种子，避免闪烁）
                if room_type_val == "dungeon":
                    special = _SPECIAL_ROOM_TEXTURES.get("dungeon_room", {})
                    tex = _load_special_texture(special.get("floor"))
                elif room_type_val == "treasure":
                    special = _SPECIAL_ROOM_TEXTURES.get("treasure_room", {})
                    tex = _load_special_texture(special.get("floor"))
                else:
                    key = "floor"
                    fv = probs.get("floor_var", 0)
                    if fv:
                        rng = random.Random(row * 1000 + col + 50000)
                        if rng.random() < fv:
                            key = "floor_var"
                    tex = texs.get(key) or texs.get("floor")
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

    # 绘制通往下一楼层的传送门
    if portal_pos:
        px, py = portal_pos
        portal_x = px * TILE_SIZE + TILE_SIZE // 2
        portal_y = py * TILE_SIZE + TILE_SIZE // 2
        _draw_floor_portal(screen, px * TILE_SIZE, py * TILE_SIZE, portal_active)


_special_texture_cache: dict[str, pygame.Surface | None] = {}

def _load_special_texture(path: str | None) -> pygame.Surface | None:
    """加载特殊房间贴图（带缓存，避免每帧重复加载导致卡顿）"""
    if not path:
        return None
    if path in _special_texture_cache:
        return _special_texture_cache[path]
    full = resource_path(path)
    if not os.path.exists(full):
        _special_texture_cache[path] = None
        return None
    try:
        img = pygame.image.load(full).convert_alpha()
        tex = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
        _special_texture_cache[path] = tex
        return tex
    except Exception:
        _special_texture_cache[path] = None
        return None


def _draw_portal_wall(screen: pygame.Surface, x: int, y: int,
                      texs: dict, portal_type: str = "portal") -> None:
    """绘制V1.0.5传送门墙壁（只用贴图，无额外渲染）"""
    # 先绘制地板贴图作为背景
    floor_tex = texs.get("floor")
    if floor_tex:
        screen.blit(floor_tex, (x, y))
    else:
        pygame.draw.rect(screen, COLOR_FLOOR, (x, y, TILE_SIZE, TILE_SIZE))
    
    # 再绘制传送门贴图（根据类型选择）
    portal_tex = _load_special_texture(_SPECIAL_ROOM_TEXTURES.get(portal_type))
    if portal_tex:
        screen.blit(portal_tex, (x, y))
    else:
        pygame.draw.rect(screen, (120, 0, 200), (x, y, TILE_SIZE, TILE_SIZE))


def _draw_floor_portal(screen: pygame.Surface, x: int, y: int, active: bool) -> None:
    """绘制通往下一楼层的传送门
    未激活：传送门激活器贴图（暗色）
    已激活：传送门贴图 + 紫色脉冲光效
    """
    if active:
        tex = _load_special_texture(_SPECIAL_ROOM_TEXTURES.get("floor_portal_active"))
    else:
        tex = _load_special_texture(_SPECIAL_ROOM_TEXTURES.get("floor_portal_inactive"))
    if tex:
        screen.blit(tex, (x, y))
    else:
        color = (140, 50, 200) if active else (60, 60, 70)
        radius = TILE_SIZE // 2 - 2 if active else TILE_SIZE // 3
        center_x = x + TILE_SIZE // 2
        center_y = y + TILE_SIZE // 2
        pygame.draw.circle(screen, color, (center_x, center_y), radius)

    if active:
        import time
        pulse = (math.sin(time.time() * 3) + 1) / 2
        center_x = x + TILE_SIZE // 2
        center_y = y + TILE_SIZE // 2
        radius = TILE_SIZE // 3 + int(pulse * 4)
        alpha = int(120 + pulse * 80)
        glow = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (140, 50, 200, alpha),
                         (radius * 3 // 2, radius * 3 // 2), radius * 1.5)
        screen.blit(glow, (center_x - radius * 3 // 2, center_y - radius * 3 // 2))


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

    # V1.0.5.12 玩家头顶不显示血条


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

    # V1.0.5.12 特殊实体使用方块大小
    if monster.monster_type in ("chest", "trial_spawner"):
        size = TILE_SIZE
        color = (120, 80, 50) if monster.monster_type == "chest" else (120, 120, 120)
    else:
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

    # V1.0.5.12 HP 条（宝箱不显示血条；V1.0.5.12 补丁: 试炼刷怪笼要求显示）
    if monster.monster_type != "chest":
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
        elif isinstance(item, KeyItem):
            color = (255, 215, 0); shape = "key"  # V1.0.5.6 藏宝室钥匙=金色
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
        elif shape == "key":
            # V1.0.5.6 钥匙造型：环 + 柄 + 齿
            pygame.draw.circle(screen, color, (x - 3, y), 3, width=2)
            pygame.draw.line(screen, color, (x, y), (x + 6, y), 2)
            pygame.draw.line(screen, color, (x + 4, y), (x + 4, y + 3), 2)
        else:
            rect = pygame.Rect(x - 4, y - 4, 8, 8)
            pygame.draw.rect(screen, color, rect, border_radius=2)


def draw_hud(screen: pygame.Surface, player: Player,
             current_floor: int, revive_count: int,
             font: pygame.font.Font | None = None) -> None:
    """绘制 HUD v2.2（V1.0.4 P2 中文文案 + 主题色）"""
    if font is None:
        font = _get_default_font()

    max_hp = player.total_max_hp(current_floor)

    # 第一行：生命值 + 当前楼层 + 剩余生命条数（雪地/地狱层白色，其余深灰）
    hp_text = f"生命值: {player.current_hp}/{max_hp}"
    floor_text = f"当前楼层: {current_floor}/{TOTAL_FLOORS}"
    revive_text = f"剩余生命条数: {revive_count}"
    first_line = f"{hp_text}   {floor_text}   {revive_text}"
    hud_color = (255, 255, 255) if any(lo <= current_floor <= hi
                                       for lo, hi in HUD_WHITE_FLOOR_RANGES) else COLOR_HUD

    y_offset = 10
    surf = font.render(first_line, True, hud_color)
    screen.blit(surf, (10, y_offset))
    y_offset += 22

    # HP 条
    bar_width = 150
    draw_progress_bar(screen, 10, y_offset + 2, bar_width, 10,
                      player.current_hp / max_hp, COLOR_HP_BAR)

    # V1.0.5.11: 移除战斗界面装备信息显示（M:/R:/A: 三行已删除）

    # 右上：BUFF 列表（V1.0.4：统一“名称 秒数”格式与主题色）
    buff_y = 10
    buff_colors = {
        "strength":       (180, 80, 255),   # 力量：紫色
        "swift":          (80, 160, 255),   # 迅捷：蓝色
        "invisible":      (255, 215, 0),    # 隐身：金色
        "heal_over_time": (255, 80, 80),    # 生命恢复：红色
    }
    buff_names = {
        "strength": "力量", "invisible": "隐身",
        "swift": "迅捷", "heal_over_time": "生命恢复",
    }
    for buff_type, remaining in sorted(player.buffs.items()):
        if remaining > 0:
            color = buff_colors.get(buff_type, COLOR_TEXT)
            name = buff_names.get(buff_type, buff_type)
            buf_text = f"{name} {remaining:.1f}s"
            buf_surf = font.render(buf_text, True, color)
            screen.blit(buf_surf, (screen.get_width() - buf_surf.get_width() - 10, buff_y))
            buff_y += 18

    # 负面状态效果（右上方，buff下方）V1.0.5.8: 显示等级
    se_names = {"wither": "凋零", "burn": "燃烧", "frost": "霜冻"}
    se_colors = {
        "wither": (80, 60, 40),     # 凋零：棕黑色
        "burn":   (255, 140, 0),    # 燃烧：橙色
        "frost":  (180, 220, 255),  # 霜冻：淡蓝色
    }
    # V1.0.5.8: 状态效果等级标记
    se_level_names = {1: "I", 2: "II", 3: "III"}
    for se_type, remaining in sorted(player.status_effects.items()):
        if remaining > 0 and se_type in se_names:
            # 获取等级
            level = 1
            if se_type == "burn":
                level = player._burn_level
            elif se_type == "frost":
                level = 2 if remaining >= 5.0 else 1
            level_str = se_level_names.get(level, "")
            se_text = f"{se_names[se_type]} {level_str} {remaining:.1f}s"
            se_surf = font.render(se_text, True, se_colors.get(se_type, (255, 100, 100)))
            screen.blit(se_surf, (screen.get_width() - se_surf.get_width() - 10, buff_y))
            buff_y += 18


def draw_toast(screen: pygame.Surface, toast: dict | None,
               font: pygame.font.Font | None = None,
               offset: int = 0,
               color: tuple = None) -> None:
    """绘制 toast 消息（渐隐），offset 用于多条堆叠
    支持多段着色：toast["segments"] = [(text, color), ...]
    """
    if toast is None or toast["timer"] <= 0:
        return

    if font is None:
        font = _get_default_font()

    alpha = int(255 * min(1.0, toast["timer"] / 0.5))

    # 多段着色渲染
    segments = toast.get("segments")
    if segments:
        # 计算总宽度
        segment_surfs = []
        total_width = 0
        for text, seg_color in segments:
            seg_surf = font.render(text, True, seg_color)
            segment_surfs.append(seg_surf)
            total_width += seg_surf.get_width()
        # 居中绘制
        screen_w = screen.get_width()
        base_y = screen.get_height() // 2 + 150
        x = screen_w // 2 - total_width // 2
        y = base_y + offset * 28
        for seg_surf in segment_surfs:
            seg_surf.set_alpha(alpha)
            screen.blit(seg_surf, (x, y))
            x += seg_surf.get_width()
        return

    if color is None:
        color = toast.get("color") or COLOR_HP_BAR

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



# ================================================================
# V1.0.5.11 近战弧形剑气特效（120°白色弧光, 快速淡出）
# V1.0.5.12 补丁: 支持按特效自定义 角度/颜色/时长（剑三段式 75°白色 / 45°金色）
# ================================================================
SLASH_ARC_SPAN = math.radians(120)   # 剑气弧形角度
SLASH_DURATION = 0.18                # 特效存活秒数

def draw_slash_effects(screen: pygame.Surface, effects: list) -> None:
    """绘制近战剑气: 以挥击方向为中心的弧线, 亮度/线宽随时间衰减
    特效 dict 可选字段: span_deg(总角度), color(RGB), dur(存活秒数)
    """
    for s in effects:
        t = s.get("t", 0.0)
        dur = float(s.get("dur", SLASH_DURATION))
        p = max(0.0, min(1.0, t / dur)) if dur > 0 else 1.0
        fade = 1.0 - p
        if fade <= 0:
            continue
        radius = int(s.get("radius", TILE_SIZE))
        cx, cy = int(s["x"]), int(s["y"])
        span = math.radians(float(s.get("span_deg", 120.0)))
        color = tuple(int(c) for c in s.get("color", (255, 255, 255)))
        base = s.get("angle", 0.0) - span / 2 + span * p * 0.25
        steps = 20
        for width, rr, alpha in ((5, radius, fade), (3, max(6, radius - 8), fade * 0.8)):
            if rr <= 0 or alpha <= 0:
                continue
            col = (int(color[0] * alpha), int(color[1] * alpha), int(color[2] * alpha))
            pts = []
            for k in range(steps + 1):
                th = base + span * (k / steps) * (1.0 - 0.15 * p)
                pts.append((cx + math.cos(th) * rr, cy + math.sin(th) * rr))
            pygame.draw.lines(screen, col, False, pts, width)


# ================================================================
# V1.0.5.12 连击&战斗特效: V形剑气（沿攻击方向向前飞行, 开口朝向玩家）
# 每条剑气可指定 张角/颜色/臂长（剑·斧金V120° / 矛金V60° / 矛·匕首白V45°）
# ================================================================
V_SLASH_SPAN = math.radians(60.0)   # V形剑气默认张角（每侧30°）
V_SLASH_LENGTH = 44                 # 单侧臂长 px
V_SLASH_DURATION = 0.2              # V形剑气默认存活秒数

def draw_v_slashes(screen: pygame.Surface, slashes: list[dict]) -> None:
    """绘制V形剑气: 顶点位于锋尖(朝前), 两条线段向后张开(开口朝向玩家), 亮度/线宽随时间衰减
    剑气 dict 可选字段: span_deg(总张角), color(RGB), length(单侧臂长px), dur(存活秒数)
    """
    for s in slashes:
        t = s.get("t", 0.0)
        dur = float(s.get("dur", V_SLASH_DURATION))
        p = max(0.0, min(1.0, t / dur)) if dur > 0 else 1.0
        fade = 1.0 - p
        if fade <= 0:
            continue
        cx, cy = int(s["x"]), int(s["y"])
        angle = s.get("angle", 0.0)
        span = math.radians(float(s.get("span_deg", math.degrees(V_SLASH_SPAN))))
        half = span / 2
        length = int(s.get("length", V_SLASH_LENGTH))
        base_color = tuple(int(c) for c in s.get("color", (255, 200, 0)))  # 默认金色
        # V字开口朝向玩家：顶点朝前(飞行方向)，两臂向后张开
        back_angle = angle + math.pi
        for width, alpha in ((5, fade), (3, fade * 0.8)):
            if alpha <= 0:
                continue
            col = (int(base_color[0] * alpha),
                   int(base_color[1] * alpha),
                   int(base_color[2] * alpha))
            tip_l = (cx + math.cos(back_angle - half) * length,
                     cy + math.sin(back_angle - half) * length)
            tip_r = (cx + math.cos(back_angle + half) * length,
                     cy + math.sin(back_angle + half) * length)
            pygame.draw.line(screen, col, (cx, cy), tip_l, width)
            pygame.draw.line(screen, col, (cx, cy), tip_r, width)
