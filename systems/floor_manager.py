"""
Dungeon Warriors V1.0.2 — 楼层管理器
怪物个体化生成、楼层分段配置
"""

import random
import math
from collections import deque
from config import (
    MAP_COLS, MAP_ROWS, TILE_SIZE,
    BOSS_FLOORS, FINAL_BOSS_FLOOR,
    MONSTER_SCALE_PER_FLOOR,
    MONSTER_PER_5_FLOORS_HP, MONSTER_PER_5_FLOORS_ATK,
)
from entities.monster import Monster
from data.monsters import (
    NORMAL_MONSTERS, NATURAL_NORMAL, ELITE_MONSTERS,
    HEAD_BOSS_MELEE, HEAD_BOSS_RANGED, FINAL_BOSS,
)


def get_floor_type(floor_num: int) -> str:
    if floor_num == FINAL_BOSS_FLOOR:
        return "final_boss"
    elif floor_num in BOSS_FLOORS:
        return "boss"
    return "battle"


def generate_map(cols=MAP_COLS, rows=MAP_ROWS):
    grid = [[0]*cols for _ in range(rows)]
    for col in range(cols):
        grid[0][col] = 1
        grid[rows-1][col] = 1
    for row in range(rows):
        grid[row][0] = 1
        grid[row][cols-1] = 1
    # 均匀分布墙壁：将地图分为 3×2 共 6 个区域，每区随机放置 2-6 个墙壁
    sections = [(2, cols//3, 2, rows//2-1), (cols//3, 2*cols//3, 2, rows//2-1),
                (2*cols//3, cols-2, 2, rows//2-1),
                (2, cols//3, rows//2, rows-2), (cols//3, 2*cols//3, rows//2, rows-2),
                (2*cols//3, cols-2, rows//2, rows-2)]
    for x1, x2, y1, y2 in sections:
        for _ in range(random.randint(2, 6)):
            for _ in range(5):  # 重试
                col = random.randint(x1, x2)
                row = random.randint(y1, y2)
                if abs(col-cols//2) < 3 and abs(row-rows//2) < 3:
                    continue
                grid[row][col] = 1
                break
    sp = find_spawn_point(grid, cols, rows)
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            sc, sr = sp[0]+dc, sp[1]+dr
            if 1 <= sc < cols-1 and 1 <= sr < rows-1:
                grid[sr][sc] = 0
    _ensure_path(grid, cols, rows, sp[0], sp[1], cols//2, rows//2)
    return grid


def find_spawn_point(grid, cols, rows):
    candidates = []
    for col in range(2, cols//3):
        for row in range(2, rows//3):
            if grid[row][col] == 0:
                clear = True
                for dc in range(-1, 2):
                    for dr in range(-1, 2):
                        nc, nr = col+dc, row+dr
                        if 0 <= nc < cols and 0 <= nr < rows and grid[nr][nc] == 1:
                            clear = False; break
                    if not clear: break
                if clear: candidates.append((col, row))
    if candidates: return random.choice(candidates)
    for col in range(1, cols-1):
        for row in range(1, rows-1):
            if grid[row][col] == 0: return (col, row)
    return (cols//4, rows//2)


def spawn_monsters(grid, cols, rows, spawn_pos, floor_type, floor_num, spawn_mult=1.0):
    """V1.0.2 怪物生成"""
    monsters = []
    sc, sr = spawn_pos
    valid = []
    for col in range(1, cols-1):
        for row in range(1, rows-1):
            if grid[row][col] == 0:
                if math.sqrt((col-sc)**2+(row-sr)**2) > 5:
                    valid.append((col, row))
    if not valid:
        for col in range(1, cols-1):
            for row in range(1, rows-1):
                if grid[row][col] == 0: valid.append((col, row))
    random.shuffle(valid)
    pi = [0]

    scale = MONSTER_SCALE_PER_FLOOR ** (floor_num - 1)
    fb = (floor_num - 1) // 5

    def make_m(mdef, mtype):
        if pi[0] >= len(valid): return None
        col, row = valid[pi[0]]; pi[0] += 1
        px = col*TILE_SIZE + TILE_SIZE//2
        py = row*TILE_SIZE + TILE_SIZE//2
        if mtype in ("normal", "elite"):
            hp = int(mdef["hp"]*scale) + fb*MONSTER_PER_5_FLOORS_HP
            atk = int(mdef["atk"]*scale) + fb*MONSTER_PER_5_FLOORS_ATK
        else:
            hp, atk = mdef["hp"], mdef["atk"]
        return Monster(name=mdef["name"], monster_type=mtype,
                       hp=hp, max_hp=hp, attack=atk,
                       attack_range=mdef["range"], attack_cooldown=mdef["cd"],
                       ranged_attacker=mdef.get("ranged", False),
                       speed=mdef["speed"], x=float(px), y=float(py))

    if floor_type == "final_boss":
        fb_data = FINAL_BOSS
        px = cols//2*TILE_SIZE + TILE_SIZE//2
        py = rows//2*TILE_SIZE + TILE_SIZE//2
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
        for d in [md, rd]:
            m = make_m(d, "head_boss")
            if m: monsters.append(m)
        return monsters

    # Battle floor
    if floor_num <= 9:
        n_min, n_max = 4, 6
        e_cfg = [(1, 0.6), (2, 0.4)]
    elif floor_num <= 19:
        n_min, n_max = 6, 8
        e_cfg = [(2, 0.5), (3, 0.5)]
    else:
        n_min, n_max = 8, 12
        e_cfg = [(3, 0.6), (4, 0.4)]

    nc = max(1, int(random.randint(n_min, n_max) * spawn_mult))
    ec = 0
    r = random.random(); cum = 0
    for cnt, rate in e_cfg:
        cum += rate
        if r < cum: ec = cnt; break
    ec = max(0, int(ec * spawn_mult))

    natural = [m for m in NORMAL_MONSTERS if m["name"] in NATURAL_NORMAL]
    for _ in range(nc):
        m = make_m(random.choice(natural), "normal")
        if m: monsters.append(m)
    # 1-5层：至多1个烈焰使者或暗影骑士
    if floor_num <= 5 and ec >= 1:
        special_elites = []
        for _ in range(ec):
            pool = [e for e in ELITE_MONSTERS if not (
                ('烈焰使者' in e['name'] and ('烈焰使者' in [x['name'] for x in special_elites] or '暗影骑士' in [x['name'] for x in special_elites])) or
                ('暗影骑士' in e['name'] and ('烈焰使者' in [x['name'] for x in special_elites] or '暗影骑士' in [x['name'] for x in special_elites])))]
            if not pool: pool = [e for e in ELITE_MONSTERS if e not in special_elites]
            if not pool: pool = ELITE_MONSTERS
            chosen = random.choice(pool)
            m = make_m(chosen, "elite")
            if m:
                monsters.append(m)
                if '烈焰使者' in chosen['name'] or '暗影骑士' in chosen['name']:
                    special_elites.append(chosen)
    else:
        for _ in range(ec):
            m = make_m(random.choice(ELITE_MONSTERS), "elite")
            if m: monsters.append(m)
    # 史莱姆上限50%: 超额部分替换为非史莱姆普通怪物（保持位置和数量）
    slime_n = sum(1 for m in monsters if '史莱姆' in m.name)
    max_slimes = len(monsters) // 2
    non_slime_pool = [m for m in NORMAL_MONSTERS if m["name"] in NATURAL_NORMAL and '史莱姆' not in m["name"]]
    for i in range(len(monsters)):
        if slime_n <= max_slimes: break
        if '史莱姆' in monsters[i].name:
            replacement = random.choice(non_slime_pool)
            old = monsters[i]
            monsters[i] = Monster(name=replacement["name"], monster_type="normal",
                                  hp=int(replacement["hp"]*scale)+fb*MONSTER_PER_5_FLOORS_HP,
                                  max_hp=int(replacement["hp"]*scale)+fb*MONSTER_PER_5_FLOORS_HP,
                                  attack=int(replacement["atk"]*scale)+fb*MONSTER_PER_5_FLOORS_ATK,
                                  attack_range=replacement["range"],
                                  attack_cooldown=replacement["cd"],
                                  ranged_attacker=replacement.get("ranged", False),
                                  speed=replacement["speed"],
                                  x=old.x, y=old.y)
            slime_n -= 1
    return monsters


def _ensure_path(grid, cols, rows, fc, fr, tc, tr):
    visited = set(); q = deque(); q.append((fc, fr)); visited.add((fc, fr))
    while q:
        c, r = q.popleft()
        if c == tc and r == tr: return
        for dc, dr in [(0,1),(0,-1),(1,0),(-1,0)]:
            nc, nr = c+dc, r+dr
            if 0 <= nc < cols and 0 <= nr < rows and (nc,nr) not in visited and grid[nr][nc] == 0:
                visited.add((nc,nr)); q.append((nc,nr))
    dx, dy = tc-fc, tr-fr
    steps = max(abs(dx), abs(dy))*2
    for i in range(steps+1):
        t = i/steps if steps else 0
        c, r = int(fc+dx*t), int(fr+dy*t)
        if 0 <= c < cols and 0 <= r < rows: grid[r][c] = 0
