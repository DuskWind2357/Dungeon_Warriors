"""
Dungeon Warriors — A* 网格寻路
V1.0.5 多房间系统适配
"""

import heapq
import math
from config import TILE_SIZE, MAP_COLS, MAP_ROWS

DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # 上下左右


def astar(grid: list[list[int]],
          start: tuple[int, int],
          goal: tuple[int, int]) -> list[tuple[int, int]] | None:
    """
    A* 寻路。返回网格路径 [(col,row), ...] 或 None。
    V1.0.5: 传送门(值=5)视为墙壁
    """
    if start == goal:
        return [start]
    if grid[goal[1]][goal[0]] in (1, 5):  # 目标不可达（墙壁或传送门）
        return None

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            # 回溯路径
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for dc, dr in DIRS:
            nc, nr = current[0] + dc, current[1] + dr
            if 0 <= nc < MAP_COLS and 0 <= nr < MAP_ROWS:
                if grid[nr][nc] in (1, 5):  # 墙壁或传送门不可通过
                    continue
                neighbor = (nc, nr)
                tentative = g_score.get(current, 999) + 1
                if tentative < g_score.get(neighbor, 999):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    h = abs(nc - goal[0]) + abs(nr - goal[1])  # 曼哈顿
                    heapq.heappush(open_set, (tentative + h, neighbor))

    return None  # 不可达


def simplify_path(grid: list[list[int]],
                  path: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """移除中间节点：若从 A 到 C 直线无墙，跳过 B"""
    if len(path) <= 2:
        return path
    result = [path[0]]
    i = 0
    while i < len(path) - 1:
        # 从当前点能直线到达的最远点
        farthest = i + 1
        for j in range(len(path) - 1, i, -1):
            if _line_clear(grid, path[i], path[j]):
                farthest = j
                break
        result.append(path[farthest])
        i = farthest
    return result


def _line_clear(grid: list[list[int]],
                a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Bresenham 直线是否无墙
    V1.0.5: 传送门(值=5)视为墙壁
    """
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    cx, cy = x0, y0
    while cx != x1 or cy != y1:
        if grid[cy][cx] in (1, 5):  # 墙壁或传送门遮挡视线
            return False
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy
    return True


def pixel_to_grid(px: float, py: float) -> tuple[int, int]:
    return (int(px // TILE_SIZE), int(py // TILE_SIZE))


def grid_to_pixel(col: int, row: int) -> tuple[float, float]:
    return (col * TILE_SIZE + TILE_SIZE // 2,
            row * TILE_SIZE + TILE_SIZE // 2)


def random_walkable(grid: list[list[int]]) -> tuple[int, int] | None:
    """随机返回一个可行走格
    V1.0.5: 传送门(值=5)不可行走
    """
    import random
    candidates = [(c, r) for r in range(1, MAP_ROWS - 1)
                  for c in range(1, MAP_COLS - 1)
                  if grid[r][c] not in (1, 5)]
    return random.choice(candidates) if candidates else None
