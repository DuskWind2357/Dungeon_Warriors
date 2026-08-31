"""
Dungeon Warriors V1.0.5.12 — 楼层管理器（平衡性重做）
多房间楼层架构：每个房间是独立的20×15网格，切换时整个画面变化
"""

import random
import math
from enum import Enum
from dataclasses import dataclass, field
from config import (
    MAP_COLS, MAP_ROWS, TILE_SIZE,
    BOSS_FLOORS, FINAL_BOSS_FLOOR,
    MONSTER_SPEED_SCALE,
    PORTAL_MIN_EDGE_DIST,
    BRANCH_COUNTS, DUNGEON_ROOM_CHANCES, DUNGEON_MAX_PER_FLOOR,
    BOSS_BRANCH_COUNT,
    DIFFICULTY_MODIFIERS,
    TREASURE_ROOM_CHESTS, TREASURE_ROOM_CONSUMABLES, TREASURE_ROOM_MAX_POTIONS,
    TREASURE_ROOM_EQUIP_COUNT, TREASURE_ROOM_EQUIP_MAX_TIER,
    SPECIAL_TREASURE_ROOM_CHESTS, SPECIAL_TREASURE_ROOM_CONSUMABLES,
    SPECIAL_TREASURE_ROOM_MIN_POTIONS, SPECIAL_TREASURE_ROOM_EQUIP_COUNT,
    SPECIAL_TREASURE_ROOM_EQUIP_MIN_TIER,
)
from entities.monster import Monster
from data.monsters import (
    NORMAL_MONSTERS, NATURAL_NORMAL, ELITE_MONSTERS,
    SNOW_ELITE_MONSTERS, HEAD_BOSS_MELEE, HEAD_BOSS_RANGED, FINAL_BOSS,
    CHEST, TRIAL_SPAWNER, TRIAL_SPAWNER_BASE_HP, TRIAL_SPAWNER_HP_PER_FLOOR,
)


class RoomType(Enum):
    """房间类型枚举（V1.0.5.6 扩展）"""
    SPAWN = "spawn"
    BATTLE = "battle"
    TREASURE = "treasure"
    DUNGEON = "dungeon"
    ENHANCED_BATTLE = "enhanced_battle"   # 增强战斗房间（BOSS楼层）
    BOSS_BATTLE = "boss_battle"           # BOSS战房间
    SPECIAL_TREASURE = "special_treasure" # 特殊宝藏房间（需钥匙解锁）


@dataclass
class Portal:
    """传送门数据类
    side: 传送门所在的墙壁 ("left", "right", "top", "bottom")
    offset: 在该墙壁上的偏移位置（从左/上角开始数）
    """
    side: str
    offset: int
    target_room_idx: int
    target_side: str
    target_offset: int
    is_floor_portal: bool = False  # 通往下一楼层的传送门


@dataclass
class Room:
    """V1.0.5.12 房间数据类 — 每个房间是独立的20×15网格"""
    room_idx: int
    room_type: RoomType
    grid: list[list[int]] = field(default_factory=list)
    portals: list[Portal] = field(default_factory=list)
    cleared: bool = False
    has_floor_portal: bool = False
    spawn_pos: tuple[int, int] = (0, 0)
    monster_positions: list[tuple[float, float]] = field(default_factory=list)
    unlocked: bool = False   # 特殊宝藏房间：是否已用钥匙解锁（V1.0.5.6）
    chests: list[tuple[int, int]] = field(default_factory=list)  # V1.0.5.12 宝箱位置
    spawner_pos: tuple[int, int] | None = None  # V1.0.5.12 试炼刷怪笼位置
    consumable_positions: list[tuple[int, int]] = field(default_factory=list)  # V1.0.5.12 消耗品位置
    equip_positions: list[tuple[int, int]] = field(default_factory=list)  # V1.0.5.12 装备位置

    @property
    def center(self) -> tuple[int, int]:
        return (MAP_COLS // 2, MAP_ROWS // 2)

    def get_walkable_cells(self) -> list[tuple[int, int]]:
        """返回房间内可行走的格子"""
        cells = []
        for row in range(1, MAP_ROWS - 1):
            for col in range(1, MAP_COLS - 1):
                if self.grid[row][col] not in (1, 5):
                    cells.append((col, row))
        return cells

    def get_portal_at(self, col: int, row: int) -> Portal | None:
        """获取指定位置的传送门"""
        for p in self.portals:
            px, py = self._portal_grid_pos(p)
            if (col, row) == (px, py):
                return p
        return None

    def _portal_grid_pos(self, portal: Portal) -> tuple[int, int]:
        """计算传送门的网格坐标"""
        if portal.side == "left":
            return (0, 1 + portal.offset)
        elif portal.side == "right":
            return (MAP_COLS - 1, 1 + portal.offset)
        elif portal.side == "top":
            return (1 + portal.offset, 0)
        elif portal.side == "bottom":
            return (1 + portal.offset, MAP_ROWS - 1)
        return (0, 0)


@dataclass
class FloorLayout:
    """V1.0.5 楼层布局数据类"""
    rooms: list[Room]
    current_room_idx: int = 0
    floor_portal_pos: tuple[int, int] | None = None
    floor_portal_room_idx: int | None = None

    @property
    def current_room(self) -> Room:
        return self.rooms[self.current_room_idx]

    def get_room_by_idx(self, idx: int) -> Room | None:
        for r in self.rooms:
            if r.room_idx == idx:
                return r
        return None


# ============================================================
# 工具函数
# ============================================================

def get_floor_type(floor_num: int) -> str:
    if floor_num == FINAL_BOSS_FLOOR:
        return "final_boss"
    elif floor_num in BOSS_FLOORS:
        return "boss"
    return "battle"


def get_theme(floor_num: int) -> str:
    if floor_num in BOSS_FLOORS or floor_num == FINAL_BOSS_FLOOR:
        return "boss"
    if floor_num <= 9:
        return "dungeon"
    if floor_num <= 19:
        return "snow"
    return "hell"


def head_boss_floor_boost(floor_num: int, difficulty: str = "easy") -> float:
    """V1.0.5.10 头目BOSS楼层缩放系数（floor_manager / combat_scene 共用）

    头目BOSS ATK/HP = 初始 × 难度BOSS倍率 × (1 + (Floor-1) × 难度倍率 / 3)
    本函数返回其中的 (1 + (Floor-1) × 难度倍率 / 3) 部分
    """
    diff_mod = DIFFICULTY_MODIFIERS.get(difficulty, DIFFICULTY_MODIFIERS["easy"])
    return 1.0 + (floor_num - 1) * diff_mod["hp_scale_per_floor"] / 3.0


def _opposite_side(side: str) -> str:
    return {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}[side]


# ============================================================
# 楼层生成
# ============================================================

def generate_floor(floor_num: int = 1, difficulty: str = "easy") -> FloorLayout:
    """V1.0.5.8 生成完整楼层布局（平衡性重做）
    每个房间是独立的20×15网格
    difficulty: 难度参数，影响宝藏室生成概率
    """
    floor_type = get_floor_type(floor_num)

    if floor_type in ("boss", "final_boss"):
        return _generate_boss_floor(floor_num, floor_type, difficulty)

    # V1.0.5.6 按楼层段等概率取分支数
    branch_counts, dchance, dmax = _get_band_spec(floor_num)
    n_branch = random.choice(branch_counts)
    rooms: list[Room] = []

    spawn_room = Room(room_idx=0, room_type=RoomType.SPAWN)
    _generate_room_grid(spawn_room)
    rooms.append(spawn_room)

    # 先确定所有分支类型（满足副本规则），再生成网格资源 —— 确保符合规则后才加载
    dungeon_count = 0
    branch_types: list[RoomType] = []
    for _ in range(n_branch):
        is_dungeon = (dchance > 0 and dungeon_count < dmax
                      and random.random() < dchance)
        if is_dungeon:
            dungeon_count += 1
            branch_types.append(RoomType.DUNGEON)
        else:
            branch_types.append(RoomType.BATTLE)

    # 超限副本自动替换为战斗房间（前面判定已保证不超上限，此处兜底）
    branch_types = [RoomType.BATTLE if (rt == RoomType.DUNGEON and dungeon_count > dmax) else rt
                    for rt in branch_types]

    for rtype in branch_types:
        room = Room(room_idx=len(rooms), room_type=rtype)
        _generate_room_grid(room)
        rooms.append(room)

    _connect_rooms_with_portals(rooms, difficulty=difficulty)

    floor_portal_pos = _place_floor_portal(rooms)
    floor_portal_room_idx = None
    if floor_portal_pos:
        for r in rooms:
            if r.has_floor_portal:
                floor_portal_room_idx = r.room_idx
                break

    return FloorLayout(rooms=rooms, current_room_idx=0,
                       floor_portal_pos=floor_portal_pos,
                       floor_portal_room_idx=floor_portal_room_idx)


def _get_band_spec(floor_num: int) -> tuple[list[int], float, int]:
    """返回 (可选分支数列表, 副本概率, 副本上限)，默认兜底为单分支战斗"""
    for (lo, hi), counts in BRANCH_COUNTS.items():
        if lo <= floor_num <= hi:
            return (list(counts),
                    DUNGEON_ROOM_CHANCES.get((lo, hi), 0.0),
                    DUNGEON_MAX_PER_FLOOR.get((lo, hi), 0))
    return [2], 0.0, 0


def _generate_boss_floor(floor_num: int, floor_type: str, difficulty: str = "easy") -> FloorLayout:
    """V1.0.5.12 BOSS战斗楼层：多房间（出生点 + 分支）
    头目楼层(10/20)：1 BOSS战 + 2 增强战斗 + 1 特殊宝藏
    首领楼层(30)：  1 BOSS战 + 3 增强战斗
    difficulty: 难度参数
    """
    rooms: list[Room] = []

    spawn_room = Room(room_idx=0, room_type=RoomType.SPAWN)
    _generate_room_grid(spawn_room)
    rooms.append(spawn_room)

    if floor_type == "final_boss":
        branch_spec: list[tuple[RoomType, int]] = [
            (RoomType.ENHANCED_BATTLE, 3),
            (RoomType.BOSS_BATTLE, 1),
        ]
    else:
        branch_spec = [
            (RoomType.ENHANCED_BATTLE, 2),
            (RoomType.BOSS_BATTLE, 1),
            (RoomType.SPECIAL_TREASURE, 1),
        ]

    for rtype, count in branch_spec:
        for _ in range(count):
            room = Room(room_idx=len(rooms), room_type=rtype)
            _generate_room_grid(room)
            rooms.append(room)

    # V1.0.5.12 为特殊宝藏房间生成宝箱、消耗品和装备
    for room in rooms:
        if room.room_type == RoomType.SPECIAL_TREASURE:
            _generate_special_treasure_room(room)

    # 出生点固定 4 分支，各分支仅与出生点相通（增强战斗房间之间不互通）
    _connect_rooms_with_portals(rooms, force_count=BOSS_BRANCH_COUNT,
                                with_treasure=False, difficulty=difficulty)

    floor_portal_pos = _place_floor_portal(rooms)
    floor_portal_room_idx = None
    if floor_portal_pos:
        for r in rooms:
            if r.has_floor_portal:
                floor_portal_room_idx = r.room_idx
                break

    return FloorLayout(rooms=rooms, current_room_idx=0,
                       floor_portal_pos=floor_portal_pos,
                       floor_portal_room_idx=floor_portal_room_idx)


def _generate_special_treasure_room(room: Room) -> None:
    """V1.0.5.12 为特殊宝藏房间生成宝箱、消耗品和装备
    规则：4-5个宝箱，7-8个消耗品（至少4瓶药水），2-3件T5及以上装备
    """
    walkable = room.get_walkable_cells()
    random.shuffle(walkable)
    
    # 生成宝箱位置（4-5个）
    chest_count = random.randint(*SPECIAL_TREASURE_ROOM_CHESTS)
    for i in range(min(chest_count, len(walkable))):
        room.chests.append(walkable[i])
    
    # 生成消耗品位置（7-8个，至少4瓶药水）
    consumable_count = random.randint(*SPECIAL_TREASURE_ROOM_CONSUMABLES)
    potion_count = 0
    for i in range(consumable_count):
        idx = chest_count + i
        if idx >= len(walkable):
            break
        room.consumable_positions.append(walkable[idx])
        # 至少4瓶药水
        if potion_count < SPECIAL_TREASURE_ROOM_MIN_POTIONS:
            potion_count += 1
    
    # 生成装备位置（2-3件T5及以上）
    equip_count = random.randint(*SPECIAL_TREASURE_ROOM_EQUIP_COUNT)
    for i in range(equip_count):
        idx = chest_count + consumable_count + i
        if idx < len(walkable):
            room.equip_positions.append(walkable[idx])


def _generate_room_grid(room: Room) -> None:
    """为单个房间生成20×15网格
    值: 0=地板, 1=墙壁, 2=出生点, 3=下一楼层传送门, 4=陷阱, 5=房间传送门, 6=试炼刷怪笼
    """
    grid = [[1] * MAP_COLS for _ in range(MAP_ROWS)]

    # 清空内部为地板
    for row in range(1, MAP_ROWS - 1):
        for col in range(1, MAP_COLS - 1):
            grid[row][col] = 0

    # 出生点房间：出生点偏左一格，中央留给通关传送门
    if room.room_type == RoomType.SPAWN:
        sx, sy = MAP_COLS // 2 - 1, MAP_ROWS // 2
        grid[sy][sx] = 2
        room.spawn_pos = (sx, sy)

    # V1.0.5.12 副本房间：中央放置试炼刷怪笼
    if room.room_type == RoomType.DUNGEON:
        cx, cy = MAP_COLS // 2, MAP_ROWS // 2
        grid[cy][cx] = 6  # 6=试炼刷怪笼
        room.spawner_pos = (cx, cy)

    room.grid = grid


def _add_random_walls(grid: list[list[int]], room: Room,
                      n_walls_range: tuple[int, int] = (4, 8)) -> None:
    """在房间内添加随机墙壁"""
    n_walls = random.randint(*n_walls_range)
    cx, cy = room.center

    for _ in range(n_walls):
        for _ in range(10):
            col = random.randint(2, MAP_COLS - 3)
            row = random.randint(2, MAP_ROWS - 3)
            # 不在出生点附近放墙
            if room.room_type == RoomType.SPAWN:
                if abs(col - cx) < 3 and abs(row - cy) < 3:
                    continue
            # 不在传送门位置放墙
            if grid[row][col] in (2, 3, 5):
                continue
            grid[row][col] = 1
            break


def _connect_rooms_with_portals(rooms: list[Room],
                                force_count: int | None = None,
                                with_treasure: bool = True,
                                difficulty: str = "easy") -> None:
    """在房间之间建立传送门连接
    force_count: 指定传送门/分支数（BOSS楼层出生点固定 4 分支）
    with_treasure: 是否为本楼层战斗房间/副本额外连接宝藏室（增强战斗/特殊宝藏房间不生成）
    difficulty: 难度参数，影响宝藏室生成概率
    """
    spawn_room = rooms[0]
    branch_rooms = rooms[1:]

    if not branch_rooms:
        return

    sides = ["right", "bottom", "left", "top"]
    random.shuffle(sides)

    # V1.0.5.9 单入口规则: 每个分支房间恰好一个入口（不再复用同一房间生成双入口）
    if force_count is not None:
        n_portals = min(force_count, len(branch_rooms), len(sides))
    else:
        n_portals = min(len(branch_rooms), len(sides))

    for i in range(n_portals):
        side = sides[i]
        branch_room = branch_rooms[i]

        # 出生点房间的传送门位置
        offset = random.randint(PORTAL_MIN_EDGE_DIST, 
                                MAP_COLS - 2 - PORTAL_MIN_EDGE_DIST if side in ("top", "bottom") 
                                else MAP_ROWS - 2 - PORTAL_MIN_EDGE_DIST)

        # 出生点房间的传送门
        spawn_portal = Portal(
            side=side,
            offset=offset,
            target_room_idx=branch_room.room_idx,
            target_side=_opposite_side(side),
            target_offset=offset
        )
        spawn_room.portals.append(spawn_portal)

        # 分支房间的传送门（双向）
        target_portal = Portal(
            side=_opposite_side(side),
            offset=offset,
            target_room_idx=spawn_room.room_idx,
            target_side=side,
            target_offset=offset
        )
        branch_room.portals.append(target_portal)

        # 在网格上放置传送门
        _place_portal_on_grid(spawn_room, spawn_portal)
        _place_portal_on_grid(branch_room, target_portal)

    # 为战斗房间/副本生成宝藏室（BOSS楼层的增强战斗/特殊宝藏房间不生成）
    if with_treasure:
        _generate_treasure_rooms(rooms, difficulty)


def _place_portal_on_grid(room: Room, portal: Portal) -> None:
    """在房间网格上放置传送门（值=5）"""
    col, row = room._portal_grid_pos(portal)
    if 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS:
        room.grid[row][col] = 5


def _generate_treasure_rooms(rooms: list[Room], difficulty: str = "easy") -> None:
    """为战斗房间/副本生成宝藏室
    V1.0.5.12: 宝藏室生成宝箱、消耗品和装备
    """
    from config import DIFFICULTY_MODIFIERS
    
    # 获取难度相关的宝藏室概率
    diff_mod = DIFFICULTY_MODIFIERS.get(difficulty, DIFFICULTY_MODIFIERS["easy"])
    treasure_chance_battle = diff_mod["treasure_room_chance_battle"]
    treasure_chance_dungeon = diff_mod["treasure_room_chance_dungeon"]
    
    for room in rooms[1:]:  # 跳过出生点房间
        # 确定宝藏室刷新概率
        if room.room_type == RoomType.DUNGEON:
            chance = treasure_chance_dungeon
        elif room.room_type == RoomType.BATTLE:
            chance = treasure_chance_battle
        else:
            continue
        
        if random.random() >= chance:
            continue
        
        # 宿主房间入口（V1.0.5.9 单入口规则: 有且仅有一个）
        entrance = room.portals[0] if room.portals else None
        if entrance is None:
            continue

        # 创建宝藏室
        treasure_room = Room(room_idx=len(rooms), room_type=RoomType.TREASURE)
        _generate_room_grid(treasure_room)
        rooms.append(treasure_room)

        # V1.0.5.12 生成宝箱位置
        chest_count = random.randint(*TREASURE_ROOM_CHESTS)
        walkable = treasure_room.get_walkable_cells()
        random.shuffle(walkable)
        for i in range(min(chest_count, len(walkable))):
            treasure_room.chests.append(walkable[i])

        # V1.0.5.12 生成消耗品位置（3-4个，至多2瓶药水）
        consumable_count = random.randint(*TREASURE_ROOM_CONSUMABLES)
        potion_count = 0
        for i in range(consumable_count):
            if len(walkable) <= chest_count + i:
                break
            pos = walkable[chest_count + i]
            treasure_room.consumable_positions.append(pos)
            # 至多2瓶药水
            if potion_count < TREASURE_ROOM_MAX_POTIONS:
                potion_count += 1

        # V1.0.5.12 生成装备位置（1-2件T5及以下）
        equip_count = random.randint(*TREASURE_ROOM_EQUIP_COUNT)
        for i in range(equip_count):
            idx = chest_count + consumable_count + i
            if idx < len(walkable):
                treasure_room.equip_positions.append(walkable[idx])

        # V1.0.5.9 规则: 宝藏室传送门固定位于宿主房间入口的对面墙上（随机偏移）
        side = _opposite_side(entrance.side)
        max_offset = (MAP_COLS - 2 - PORTAL_MIN_EDGE_DIST if side in ("top", "bottom")
                      else MAP_ROWS - 2 - PORTAL_MIN_EDGE_DIST)
        offset = random.randint(PORTAL_MIN_EDGE_DIST, max_offset)
        treasure_portal = Portal(
            side=side,
            offset=offset,
            target_room_idx=treasure_room.room_idx,
            target_side=_opposite_side(side),
            target_offset=offset,
            is_floor_portal=False
        )
        
        if treasure_portal:
            room.portals.append(treasure_portal)
            
            # 宝藏室的传送门（双向）
            treasure_return_portal = Portal(
                side=_opposite_side(treasure_portal.side),
                offset=treasure_portal.offset,
                target_room_idx=room.room_idx,
                target_side=treasure_portal.side,
                target_offset=treasure_portal.offset,
                is_floor_portal=False
            )
            treasure_room.portals.append(treasure_return_portal)
            
            # 在网格上放置传送门
            _place_portal_on_grid(room, treasure_portal)
            _place_portal_on_grid(treasure_room, treasure_return_portal)


def _place_floor_portal(rooms: list[Room]) -> tuple[int, int] | None:
    """在出生点房间正中央放置通往下一楼层的传送门"""
    spawn_room = rooms[0] if rooms else None
    if not spawn_room:
        return None

    px = MAP_COLS // 2
    py = MAP_ROWS // 2
    spawn_room.grid[py][px] = 3
    spawn_room.has_floor_portal = True
    return (px, py)


# ============================================================
# 怪物生成
# ============================================================

def spawn_monsters_for_room(room: Room, floor_num: int,
                            difficulty: str = "easy") -> list[Monster]:
    """为指定房间生成怪物（V1.0.5.8 平衡性重做）
    difficulty: "easy" / "normal" / "hard"
    """
    monsters = []

    # 获取难度参数
    diff_mod = DIFFICULTY_MODIFIERS.get(difficulty, DIFFICULTY_MODIFIERS["easy"])
    spawn_mult = diff_mod["spawn_mult"]
    hp_scale = diff_mod["hp_scale_per_floor"]
    atk_scale = diff_mod["atk_scale_per_floor"]
    elite_extra_mult = diff_mod["elite_extra_mult"]

    # BOSS楼层的出生点/增强战斗房间：按第一层标准刷怪（V1.0.5.6）
    actual_floor = floor_num
    if room.room_type in (RoomType.SPAWN, RoomType.ENHANCED_BATTLE):
        if get_floor_type(floor_num) in ("boss", "final_boss"):
            actual_floor = 1

    # V1.0.5.10 线性缩放（最新版）: 生物HP/ATK = 初始 × (1 + 难度倍率 × (floor-1))
    # 攻击冷却不再随楼层缩放（V1.0.5.10 移除）
    hp_mult = 1.0 + hp_scale * (actual_floor - 1)
    atk_mult = 1.0 + atk_scale * (actual_floor - 1)
    cd_mult = 1.0

    # 刷怪数量表（V1.0.5.8 设计文档）
    if actual_floor <= 4:
        n_count, e_count = 6, 2
    elif actual_floor <= 9:
        n_count, e_count = 8, 3
    elif actual_floor <= 19:
        n_count, e_count = 12, 4
    else:
        n_count, e_count = 18, 6

    # 冒险/末日难度额外精英
    extra_elites = int(e_count * elite_extra_mult)

    nc = max(1, int(n_count * spawn_mult))
    ec = max(0, int((e_count + extra_elites) * spawn_mult))

    # 获取可行走位置（排除出生点和传送门）
    valid = []
    sx, sy = room.spawn_pos if room.room_type == RoomType.SPAWN else room.center
    for row in range(1, MAP_ROWS - 1):
        for col in range(1, MAP_COLS - 1):
            if room.grid[row][col] not in (1, 5):
                if math.sqrt((col - sx)**2 + (row - sy)**2) > 3:
                    valid.append((col, row))

    if not valid:
        for row in range(1, MAP_ROWS - 1):
            for col in range(1, MAP_COLS - 1):
                if room.grid[row][col] not in (1, 5):
                    valid.append((col, row))

    random.shuffle(valid)
    pos_idx = [0]

    def make_monster(mdef, mtype):
        if pos_idx[0] >= len(valid):
            return None
        col, row = valid[pos_idx[0]]
        pos_idx[0] += 1
        px = col * TILE_SIZE + TILE_SIZE // 2
        py = row * TILE_SIZE + TILE_SIZE // 2
        if mtype in ("normal", "elite"):
            hp = int(mdef["hp"] * hp_mult)
            atk = int(mdef["atk"] * atk_mult)
            cd = mdef["cd"] * cd_mult
        else:
            hp, atk, cd = mdef["hp"], mdef["atk"], mdef["cd"]
        return Monster(name=mdef["name"], monster_type=mtype,
                      hp=hp, max_hp=hp, attack=atk,
                      attack_range=mdef["range"], attack_cooldown=cd,
                      ranged_attacker=mdef.get("ranged", False),
                      speed=mdef["speed"] * MONSTER_SPEED_SCALE, x=float(px), y=float(py),
                      wither=mdef.get("wither", 0.0), frost=mdef.get("frost", 0.0),
                      burn=mdef.get("burn", 0.0), burn_dmg=mdef.get("burn_dmg", 0),
                      fireball=mdef.get("fireball", 0), fire_interval=mdef.get("fire_interval", 0.0))

    # 精英怪池
    if actual_floor <= 9:
        elite_pool = [e for e in ELITE_MONSTERS if e["name"] in ("精英僵尸", "精英骷髅")]
    elif actual_floor <= 19:
        elite_pool = SNOW_ELITE_MONSTERS
    else:
        snow_names = {e["name"] for e in SNOW_ELITE_MONSTERS}
        elite_pool = [e for e in ELITE_MONSTERS if e["name"] not in snow_names]

    natural = [m for m in NORMAL_MONSTERS if m["name"] in NATURAL_NORMAL]

    for _ in range(nc):
        m = make_monster(random.choice(natural), "normal")
        if m:
            monsters.append(m)
    for _ in range(ec):
        m = make_monster(random.choice(elite_pool), "elite")
        if m:
            monsters.append(m)

    # 史莱姆数量限制
    slime_n = sum(1 for m in monsters if '史莱姆' in m.name)
    max_slimes = len(monsters) // 4
    non_slime_pool = [m for m in NORMAL_MONSTERS if m["name"] in NATURAL_NORMAL and '史莱姆' not in m["name"]]
    if non_slime_pool:
        for i in range(len(monsters)):
            if slime_n <= max_slimes:
                break
            if '史莱姆' in monsters[i].name:
                replacement = random.choice(non_slime_pool)
                old = monsters[i]
                monsters[i] = Monster(
                    name=replacement["name"], monster_type="normal",
                    hp=int(replacement["hp"] * hp_mult),
                    max_hp=int(replacement["hp"] * hp_mult),
                    attack=int(replacement["atk"] * atk_mult),
                    attack_range=replacement["range"],
                    attack_cooldown=replacement["cd"] * cd_mult,
                    ranged_attacker=replacement.get("ranged", False),
                    speed=replacement["speed"] * MONSTER_SPEED_SCALE,
                    x=old.x, y=old.y)
                slime_n -= 1

    return monsters


def spawn_trial_spawner(room: Room, floor_num: int, difficulty: str = "easy") -> Monster | None:
    """V1.0.5.12 为副本房间生成试炼刷怪笼
    血量 = 600 + 30 × (Floor-1)，索敌范围1200，无攻击力，不可移动
    """
    if room.room_type != RoomType.DUNGEON or room.spawner_pos is None:
        return None
    
    col, row = room.spawner_pos
    px = col * TILE_SIZE + TILE_SIZE // 2
    py = row * TILE_SIZE + TILE_SIZE // 2
    
    # 计算血量：600 + 30 × (Floor-1)
    hp = TRIAL_SPAWNER_BASE_HP + TRIAL_SPAWNER_HP_PER_FLOOR * (floor_num - 1)
    
    return Monster(
        name=TRIAL_SPAWNER["name"],
        monster_type="trial_spawner",
        hp=hp,
        max_hp=hp,
        attack=0,
        attack_range=0,
        attack_cooldown=TRIAL_SPAWNER["cd"],
        speed=0,
        x=float(px),
        y=float(py),
        detect_range=TRIAL_SPAWNER["detect"],
        immobile=True,
        spawn_interval=TRIAL_SPAWNER["spawn_interval"],
        spawn_timer=TRIAL_SPAWNER["spawn_interval"]
    )


def spawn_chests(room: Room) -> list[Monster]:
    """V1.0.5.12 为宝藏室/特殊宝藏房间生成宝箱"""
    chests = []
    for col, row in room.chests:
        px = col * TILE_SIZE + TILE_SIZE // 2
        py = row * TILE_SIZE + TILE_SIZE // 2
        chest = Monster(
            name=CHEST["name"],
            monster_type="chest",
            hp=CHEST["hp"],
            max_hp=CHEST["hp"],
            attack=0,
            attack_range=0,
            attack_cooldown=999,
            speed=0,
            x=float(px),
            y=float(py),
            detect_range=0,
            immobile=True
        )
        chests.append(chest)
    return chests


def spawn_monsters_boss(room: Room,
                        floor_type: str,
                        floor_num: int,
                        difficulty: str = "easy") -> list[Monster]:
    """BOSS战房间怪物生成（V1.0.5.8 平衡性重做）
    头目楼层(10/20)：随机 2 名头目BOSS（近战+远程各一）
    首领楼层(30)：  固定 高塔之主
    difficulty: 应用BOSS难度修饰
    """
    monsters = []
    mx = MAP_COLS // 2
    my = MAP_ROWS // 2

    # 获取难度参数
    diff_mod = DIFFICULTY_MODIFIERS.get(difficulty, DIFFICULTY_MODIFIERS["easy"])
    boss_cd_mult = diff_mod["boss_cd_mult"]
    boss_skill_cd_mult = diff_mod["boss_skill_cd_mult"]
    boss_atk_mult = diff_mod["boss_atk_mult"]
    boss_hp_mult = diff_mod["boss_hp_mult"]

    if floor_type == "final_boss":
        fb_data = FINAL_BOSS
        px = mx * TILE_SIZE + TILE_SIZE // 2
        py = my * TILE_SIZE + TILE_SIZE // 2
        # V1.0.5.10: 高塔之主基础HP 6000（仅随难度BOSS倍率缩放，不吃楼层公式）
        hp = int(fb_data["hp"] * boss_hp_mult)
        atk_p1 = int(fb_data["atk_p1"] * boss_atk_mult)
        atk_p2 = int(fb_data["atk_p2"] * boss_atk_mult)
        cd_p1 = fb_data["cd_p1"] * boss_cd_mult
        cd_p2 = fb_data["cd_p2"] * boss_cd_mult
        m = Monster(name=fb_data["name"], monster_type="final_boss",
                    hp=hp, max_hp=hp,
                    attack=atk_p1, attack_range=fb_data["range"],
                    attack_cooldown=cd_p1, speed=fb_data["speed_p1"] * MONSTER_SPEED_SCALE,
                    x=float(px), y=float(py),
                    detect_range=fb_data["detect"],
                    dr_ranged=fb_data["dr_ranged_p1"], dr_melee=fb_data["dr_melee_p1"],
                    dps_cap=fb_data["dps_cap"], hit_cap=fb_data["hit_cap"])
        monsters.append(m)
        return monsters

    if floor_type == "boss":
        md = random.choice(HEAD_BOSS_MELEE)
        rd = random.choice(HEAD_BOSS_RANGED)

        def make_boss(mdef, idx):
            px = (mx + (1 if idx == 0 else -1)) * TILE_SIZE + TILE_SIZE // 2
            py = my * TILE_SIZE + TILE_SIZE // 2
            # V1.0.5.10 头目BOSS公式: 初始 × 难度BOSS倍率 × (1 + (Floor-1) × 难度倍率/3)
            floor_boost = head_boss_floor_boost(floor_num, difficulty)
            hp = int(mdef["hp"] * boss_hp_mult * floor_boost)
            atk = int(mdef["atk"] * boss_atk_mult * floor_boost)
            cd = mdef["cd"] * boss_cd_mult
            return Monster(name=mdef["name"], monster_type="head_boss",
                           hp=hp, max_hp=hp,
                           attack=atk, attack_range=mdef["range"],
                           attack_cooldown=cd,
                           ranged_attacker=mdef.get("ranged", False),
                           speed=mdef["speed"] * MONSTER_SPEED_SCALE, x=float(px), y=float(py),
                           detect_range=mdef.get("detect", 600),
                           dr_ranged=mdef.get("dr_ranged", 0.0),
                           dr_melee=mdef.get("dr_melee", 0.0),
                           wither=mdef.get("wither", 0.0),
                           combo_hits=mdef.get("combo_hits", 1),
                           combo_interval=mdef.get("combo_interval", 0.0),
                           fireball=mdef.get("fireball", 0),
                           fire_interval=mdef.get("fire_interval", 0.0),
                           burn=mdef.get("burn", 0.0),
                           burn_dmg=mdef.get("burn_dmg", 0))

        for i, d in enumerate([md, rd]):
            monsters.append(make_boss(d, i))
        return monsters

    return monsters


def place_traps(room: Room) -> None:
    """地狱主题：10% 可行走地砖变为陷阱（值=4，可行走）"""
    sc, sr = room.spawn_pos
    walkable = []
    for row in range(1, MAP_ROWS - 1):
        for col in range(1, MAP_COLS - 1):
            if room.grid[row][col] != 0:
                continue
            if (col, row) == (sc, sr):
                continue
            walkable.append((col, row))
    n_traps = int(len(walkable) * 0.10)
    random.shuffle(walkable)
    for col, row in walkable[:n_traps]:
        room.grid[row][col] = 4
