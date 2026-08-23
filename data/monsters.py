"""
Dungeon Warriors V1.0.2 — 怪物个体化定义
每个怪物有独立属性
"""

# ================================================================
# 普通怪物（个体化属性）
# ================================================================
NORMAL_MONSTERS = [
    {"name": "僵尸",     "hp": 30, "atk": 4, "range": 1.5, "cd": 1.2, "speed": 2.0, "detect": 450, "color": "green_dark", "ranged": False},
    {"name": "骷髅",     "hp": 30, "atk": 5, "range": 1.5, "cd": 2.0, "speed": 2.5, "detect": 450, "color": "white",     "ranged": True},
    {"name": "蜘蛛",     "hp": 25, "atk": 4, "range": 1.2, "cd": 1.2, "speed": 2.5, "detect": 400, "color": "black",     "ranged": False},
    {"name": "蝙蝠",     "hp": 20, "atk": 3, "range": 1.0, "cd": 1.0, "speed": 3.0, "detect": 400, "color": "brown",     "ranged": False},
    {"name": "大型史莱姆", "hp": 45, "atk": 5, "range": 1.0, "cd": 2.0, "speed": 1.5, "detect": 450, "color": "green_bright", "ranged": False, "split": "large"},
    {"name": "中型史莱姆", "hp": 30, "atk": 3, "range": 1.0, "cd": 2.0, "speed": 1.8, "detect": 400, "color": "green_bright", "ranged": False, "split": "medium"},
    {"name": "小型史莱姆", "hp": 10, "atk": 1, "range": 1.0, "cd": 2.0, "speed": 2.1, "detect": 350, "color": "green_bright", "ranged": False, "split": "small"},
    {"name": "小型岩浆史莱姆", "hp": 10, "atk": 1, "range": 1.0, "cd": 2.0, "speed": 2.1, "detect": 350, "color": "red", "ranged": False, "split": "small", "burn": 3.0, "burn_dmg": 5},
    {"name": "中型岩浆史莱姆", "hp": 30, "atk": 3, "range": 1.0, "cd": 2.0, "speed": 1.8, "detect": 400, "color": "red", "ranged": False, "split": "medium", "burn": 3.0, "burn_dmg": 5},
]
# 自然刷新的普通怪物（中/小型史莱姆不自然刷新）
NATURAL_NORMAL = ["僵尸", "骷髅", "蜘蛛", "蝙蝠", "大型史莱姆"]

# ================================================================
# 精英怪物
# ================================================================
ELITE_MONSTERS = [
    {"name": "精英僵尸",   "hp": 50, "atk": 6,  "range": 1.5, "cd": 1.2, "speed": 1.5, "detect": 500, "color": "green_black", "ranged": False},
    {"name": "精英骷髅",   "hp": 50, "atk": 8,  "range": 1.5, "cd": 2.0, "speed": 2.5, "detect": 500, "color": "gray_white",  "ranged": True},
    {"name": "暗影骑士",   "hp": 50, "atk": 7,  "range": 2.0, "cd": 2.0, "speed": 3.0, "detect": 500, "color": "purple_dark", "ranged": False, "wither": 3.0},
    {"name": "烈焰使者",   "hp": 50, "atk": 0,  "range": 1.5, "cd": 5.0, "speed": 1.5, "detect": 500, "color": "gold",       "ranged": True,  "fireball": 3, "fire_interval": 0.3, "burn": 3.0, "burn_dmg": 7},
]

# ================================================================
# 头目 BOSS
# ================================================================
HEAD_BOSS_MELEE = [
    {"name": "卫道士突袭队长", "hp": 150, "atk": 12, "range": 1.5, "cd": 2.0, "speed": 2.0, "detect": 600, "color": "gold",  "ranged": False},
    {"name": "暗黑骑士",      "hp": 150, "atk": 9,  "range": 2.0, "cd": 1.2, "speed": 3.0, "detect": 600, "color": "purple_dark", "ranged": False, "wither": 5.0},
]
HEAD_BOSS_RANGED = [
    {"name": "掠夺者突袭队长", "hp": 150, "atk": 15, "range": 1.5, "cd": 2.5, "speed": 2.5, "detect": 600, "color": "blue_light", "ranged": True},
    {"name": "炎魔",         "hp": 150, "atk": 0,  "range": 1.5, "cd": 6.0, "speed": 2.0, "detect": 600, "color": "red",        "ranged": True, "fireball": 3, "fire_interval": 0.2, "burn": 5.0, "burn_dmg": 9},
]

# ================================================================
# 首领
# ================================================================
FINAL_BOSS = {
    "name": "高塔之主",
    "hp": 400, "atk_p1": 8, "cd_p1": 1.2, "speed_p1": 2.0,
    "atk_p2": 12, "cd_p2": 1.0, "speed_p2": 2.5,
    "speed_p3": 3.0, "dr_p3": 0.20,
    "range": 2.0, "detect": 800, "color": "red_dark",
    "summon_interval": 10.0, "summon_chance": 0.50,
    "p2_fireball_interval": 10.0,
}

# ================================================================
# 颜色映射
# ================================================================
COLOR_MAP = {
    "green_dark":   (60, 140, 40),
    "white":        (220, 220, 220),
    "black":        (30, 30, 30),
    "brown":        (120, 80, 50),
    "green_bright": (80, 220, 60),
    "green_black":  (40, 100, 30),
    "gray_white":   (180, 180, 190),
    "purple_dark":  (80, 30, 120),
    "gold":         (220, 180, 50),
    "blue_light":   (140, 180, 240),
    "red":          (220, 60, 40),
    "red_dark":     (180, 20, 20),
}
