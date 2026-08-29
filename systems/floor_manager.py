"""
Dungeon Warriors V1.0.5 — 楼层管理器
多房间楼层架构：每个房间是独立的20×15网格，切换时整个画面变化
"""

import random
import math
from enum import Enum
from dataclasses import dataclass, field
from config import (
    MAP_COLS, MAP_ROWS, TILE_SIZE,
    BOSS_FLOORS, FINAL_BOSS_FLOOR,
    MONSTER_SCALE_PER_FLOOR,
    MONSTER_PER_5_FLOORS_HP, MONSTER_PER_5_FLOORS_ATK,
    PORTAL_MIN_EDGE_DIST, PORTAL_COUNT_MIN, PORTAL_COUNT_MAX,
    DUNGEON_ROOM_CHANCE, TREASURE_ROOM_CHANCE,
    BRANCH_COUNTS, DUNGEON_ROOM_CHANCES, DUNGEON_MAX_PER_FLOOR,
    BOSS_BRANCH_COUNT,
    TREASURE_ROOM_CHANCE_BATTLE, TREASURE_ROOM_DUNGEON_CHANCE,
)
from entities.monster import Monster
from data.monsters import (
    NORMAL_MONSTERS, NATURAL_NORMAL, ELITE_MONSTERS,
    SNOW_ELITE_MONSTERS, HEAD_BOSS_MELEE, HEAD_BOSS_RANGED, FINAL_BOSS,
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
    """V1.0.5 房间数据类 — 每个房间是独立的20×15网格"""
    room_idx: int
    room_type: RoomType
    grid: list[list[int]] = field(default_factory=list)
    portals: list[Portal] = field(default_factory=list)
    cleared: bool = False
    has_floor_portal: bool = False
    spawn_pos: tuple[int, int] = (0, 0)
    monster_positions: list[tuple[float, float]] = field(default_factory=list)
    unlocked: bool = False   # 特殊宝藏房间：是否已用钥匙解锁（V1.0.5.6）

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


def _opposite_side(side: str) -> str:
    return {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}[side]


# ============================================================
# 楼层生成
# ============================================================

def generate_floor(floor_num: int = 1) -> FloorLayout:
    """V1.0.5 生成完整楼层布局
    每个房间是独立的20×15网格
    """
    floor_type = get_floor_type(floor_num)

    if floor_type in ("boss", "final_boss"):
        return _generate_boss_floor(floor_num, floor_type)

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

    _connect_rooms_with_portals(rooms)

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


def _generate_boss_floor(floor_num: int, floor_type: str) -> FloorLayout:
    """V1.0.5.6 BOSS战斗楼层：多房间（出生点 + 分支）
    头目楼层(10/20)：1 BOSS战 + 2 增强战斗 + 1 特殊宝藏
    首领楼层(30)：  1 BOSS战 + 3 增强战斗
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

    # 出生点固定 4 分支，各分支仅与出生点相通（增强战斗房间之间不互通）
    _connect_rooms_with_portals(rooms, force_count=BOSS_BRANCH_COUNT,
                                with_treasure=False)

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


def _generate_room_grid(room: Room) -> None:
    """为单个房间生成20×15网格
    值: 0=地板, 1=墙壁, 2=出生点, 3=下一楼层传送门, 4=陷阱, 5=房间传送门
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
                                with_treasure: bool = True) -> None:
    """在房间之间建立传送门连接
    force_count: 指定传送门/分支数（BOSS楼层出生点固定 4 分支）
    with_treasure: 是否为本楼层战斗房间/副本额外连接宝藏室（增强战斗/特殊宝藏房间不生成）
    """
    spawn_room = rooms[0]
    branch_rooms = rooms[1:]

    if not branch_rooms:
        return

    sides = ["right", "bottom", "left", "top"]
    random.shuffle(sides)

    if force_count is not None:
        n_portals = min(force_count, len(branch_rooms), len(sides))
    else:
        n_portals = min(len(branch_rooms), len(sides), PORTAL_COUNT_MAX)
        n_portals = max(n_portals, PORTAL_COUNT_MIN)

    for i in range(n_portals):
        side = sides[i]
        branch_room = branch_rooms[i % len(branch_rooms)]

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
        _generate_treasure_rooms(rooms)


def _place_portal_on_grid(room: Room, portal: Portal) -> None:
    """在房间网格上放置传送门（值=5）"""
    col, row = room._portal_grid_pos(portal)
    if 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS:
        room.grid[row][col] = 5


def _is_portal_adjacent(portal1: Portal, portal2: Portal) -> bool:
    """检查两个传送门是否相邻"""
    # 同一墙壁上的传送门
    if portal1.side == portal2.side:
        return abs(portal1.offset - portal2.offset) <= 1
    
    # 相邻墙壁
    adjacent_walls = {
        "left": ["top", "bottom"],
        "right": ["top", "bottom"],
        "top": ["left", "right"],
        "bottom": ["left", "right"]
    }
    
    if portal2.side in adjacent_walls.get(portal1.side, []):
        # 检查角落位置
        if portal1.side == "left" and portal2.side == "top":
            return portal1.offset == 0 and portal2.offset == 0
        elif portal1.side == "left" and portal2.side == "bottom":
            return portal1.offset == MAP_ROWS - 2 and portal2.offset == MAP_COLS - 2
        elif portal1.side == "right" and portal2.side == "top":
            return portal1.offset == 0 and portal2.offset == 0
        elif portal1.side == "right" and portal2.side == "bottom":
            return portal1.offset == MAP_ROWS - 2 and portal2.offset == MAP_COLS - 2
        elif portal1.side == "top" and portal2.side == "left":
            return portal1.offset == 0 and portal2.offset == 0
        elif portal1.side == "top" and portal2.side == "right":
            return portal1.offset == MAP_COLS - 2 and portal2.offset == 0
        elif portal1.side == "bottom" and portal2.side == "left":
            return portal1.offset == 0 and portal2.offset == MAP_ROWS - 2
        elif portal1.side == "bottom" and portal2.side == "right":
            return portal1.offset == MAP_COLS - 2 and portal2.offset == MAP_ROWS - 2
    
    return False


def _generate_treasure_rooms(rooms: list[Room]) -> None:
    """为战斗房间/副本生成宝藏室"""
    from config import TREASURE_ROOM_CHANCE_BATTLE, TREASURE_ROOM_DUNGEON_CHANCE
    
    for room in rooms[1:]:  # 跳过出生点房间
        # 确定宝藏室刷新概率
        if room.room_type == RoomType.DUNGEON:
            chance = TREASURE_ROOM_DUNGEON_CHANCE
        elif room.room_type == RoomType.BATTLE:
            chance = TREASURE_ROOM_CHANCE_BATTLE
        else:
            continue
        
        if random.random() >= chance:
            continue
        
        # 创建宝藏室
        treasure_room = Room(room_idx=len(rooms), room_type=RoomType.TREASURE)
        _generate_room_grid(treasure_room)
        rooms.append(treasure_room)
        
        # 确保宝藏室传送门与出生点房间传送门不相邻（不在同一面墙或相邻墙上）
        used_sides = set()
        used_offsets = {}
        
        # 收集房间已有的传送门信息
        for portal in room.portals:
            used_sides.add(portal.side)
            if portal.side not in used_offsets:
                used_offsets[portal.side] = []
            used_offsets[portal.side].append(portal.offset)
        
        # 相邻墙壁映射
        _ADJACENT_WALLS = {
            "left": {"top", "bottom"},
            "right": {"top", "bottom"},
            "top": {"left", "right"},
            "bottom": {"left", "right"},
        }
        
        # 禁止使用的墙壁 = 已有传送门的墙壁 + 相邻墙壁
        blocked_sides = set(used_sides)
        for side in used_sides:
            blocked_sides |= _ADJACENT_WALLS.get(side, set())
        
        # 选择一个与现有传送门不相邻的位置
        available_sides = ["left", "right", "top", "bottom"]
        random.shuffle(available_sides)
        
        treasure_portal = None
        for side in available_sides:
            if side in blocked_sides:
                continue
            
            # 计算可用的偏移位置
            max_offset = MAP_COLS - 2 - PORTAL_MIN_EDGE_DIST if side in ("top", "bottom") else MAP_ROWS - 2 - PORTAL_MIN_EDGE_DIST
            possible_offsets = list(range(PORTAL_MIN_EDGE_DIST, max_offset + 1))
            
            # 移除与现有传送门相邻的位置
            for existing_side, existing_offsets in used_offsets.items():
                if existing_side == side:
                    for offset in existing_offsets:
                        if offset in possible_offsets:
                            possible_offsets.remove(offset)
                        if offset - 1 in possible_offsets:
                            possible_offsets.remove(offset - 1)
                        if offset + 1 in possible_offsets:
                            possible_offsets.remove(offset + 1)
            
            if possible_offsets:
                offset = random.choice(possible_offsets)
                treasure_portal = Portal(
                    side=side,
                    offset=offset,
                    target_room_idx=treasure_room.room_idx,
                    target_side=_opposite_side(side),
                    target_offset=offset,
                    is_floor_portal=False
                )
                break
        
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
                            spawn_mult: float = 1.0) -> list[Monster]:
    """为指定房间生成怪物"""
    monsters = []

    # BOSS楼层的出生点/增强战斗房间：按第一层标准刷怪（V1.0.5.6）
    if room.room_type in (RoomType.SPAWN, RoomType.ENHANCED_BATTLE):
        if get_floor_type(floor_num) in ("boss", "final_boss"):
            floor_num = 1

    scale = MONSTER_SCALE_PER_FLOOR ** (floor_num - 1)
    fb = (floor_num - 1) // 5

    if floor_num <= 4:
        n_count, e_count = 6, 2
    elif floor_num <= 9:
        n_count, e_count = 8, 2
    elif floor_num <= 19:
        n_count, e_count = 12, 4
    else:
        n_count, e_count = 18, 6

    nc = max(1, int(n_count * spawn_mult))
    ec = max(0, int(e_count * spawn_mult))

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
            hp = int(mdef["hp"] * scale) + fb * MONSTER_PER_5_FLOORS_HP
            atk = int(mdef["atk"] * scale) + fb * MONSTER_PER_5_FLOORS_ATK
        else:
            hp, atk = mdef["hp"], mdef["atk"]
        return Monster(name=mdef["name"], monster_type=mtype,
                      hp=hp, max_hp=hp, attack=atk,
                      attack_range=mdef["range"], attack_cooldown=mdef["cd"],
                      ranged_attacker=mdef.get("ranged", False),
                      speed=mdef["speed"], x=float(px), y=float(py))

    # 精英怪池
    if floor_num <= 9:
        elite_pool = [e for e in ELITE_MONSTERS if e["name"] in ("精英僵尸", "精英骷髅")]
    elif floor_num <= 19:
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
                    hp=int(replacement["hp"] * scale) + fb * MONSTER_PER_5_FLOORS_HP,
                    max_hp=int(replacement["hp"] * scale) + fb * MONSTER_PER_5_FLOORS_HP,
                    attack=int(replacement["atk"] * scale) + fb * MONSTER_PER_5_FLOORS_ATK,
                    attack_range=replacement["range"],
                    attack_cooldown=replacement["cd"],
                    ranged_attacker=replacement.get("ranged", False),
                    speed=replacement["speed"],
                    x=old.x, y=old.y)
                slime_n -= 1

    return monsters


def spawn_monsters_boss(room: Room,
                        floor_type: str,
                        floor_num: int) -> list[Monster]:
    """BOSS战房间怪物生成（V1.0.5.6）
    头目楼层(10/20)：随机 2 名头目BOSS（近战+远程各一）
    首领楼层(30)：  固定 高塔之主
    """
    monsters = []
    mx = MAP_COLS // 2
    my = MAP_ROWS // 2

    if floor_type == "final_boss":
        fb_data = FINAL_BOSS
        px = mx * TILE_SIZE + TILE_SIZE // 2
        py = my * TILE_SIZE + TILE_SIZE // 2
        m = Monster(name=fb_data["name"], monster_type="final_boss",
                    hp=fb_data["hp"], max_hp=fb_data["hp"],
                    attack=fb_data["atk_p1"], attack_range=fb_data["range"],
                    attack_cooldown=fb_data["cd_p1"], speed=fb_data["speed_p1"],
                    x=float(px), y=float(py))
        monsters.append(m)
        return monsters

    if floor_type == "boss":
        md = random.choice(HEAD_BOSS_MELEE)
        rd = random.choice(HEAD_BOSS_RANGED)

        def make_boss(mdef, idx):
            # 两个BOSS错开摆放（避免重叠）
            px = (mx + (1 if idx == 0 else -1)) * TILE_SIZE + TILE_SIZE // 2
            py = my * TILE_SIZE + TILE_SIZE // 2
            return Monster(name=mdef["name"], monster_type="head_boss",
                           hp=mdef["hp"], max_hp=mdef["hp"],
                           attack=mdef["atk"], attack_range=mdef["range"],
                           attack_cooldown=mdef["cd"],
                           ranged_attacker=mdef.get("ranged", False),
                           speed=mdef["speed"], x=float(px), y=float(py))

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
