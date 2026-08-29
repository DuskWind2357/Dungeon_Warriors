"""
Dungeon Warriors V1.0.5.8 — 怪物个体化定义（平衡性重做）
每个怪物有独立属性，数值依据 frame/V 1.0.5/平衡性重做/怪物数值重置.txt
移速 = 设计文档原值 × 0.75（还原旧版基础难度手感）
"""

# ================================================================
# 普通怪物（个体化属性）
# ================================================================
NORMAL_MONSTERS = [
    {"name": "僵尸",     "hp": 30, "atk": 4, "range": 1.5, "cd": 1.2, "speed": 1.5,   "detect": 480, "color": "green_dark", "ranged": False},
    {"name": "骷髅",     "hp": 30, "atk": 5, "range": 1.5, "cd": 2.0, "speed": 1.875, "detect": 480, "color": "white",     "ranged": True},
    {"name": "蜘蛛",     "hp": 25, "atk": 3, "range": 1.2, "cd": 1.2, "speed": 1.875, "detect": 360, "color": "black",     "ranged": False},
    {"name": "蝙蝠",     "hp": 20, "atk": 3, "range": 1.0, "cd": 1.0, "speed": 2.7,   "detect": 360, "color": "brown",     "ranged": False},
    {"name": "大型史莱姆", "hp": 50, "atk": 6, "range": 1.0, "cd": 1.8, "speed": 1.125, "detect": 480, "color": "green_bright", "ranged": False, "split": "large"},
    {"name": "中型史莱姆", "hp": 30, "atk": 4, "range": 1.0, "cd": 1.8, "speed": 1.35,  "detect": 420, "color": "green_bright", "ranged": False, "split": "medium"},
    {"name": "小型史莱姆", "hp": 10, "atk": 2, "range": 1.0, "cd": 1.8, "speed": 1.575, "detect": 360, "color": "green_bright", "ranged": False, "split": "small"},
    {"name": "小型岩浆史莱姆", "hp": 10, "atk": 2, "range": 1.0, "cd": 1.8, "speed": 1.575, "detect": 360, "color": "red", "ranged": False, "split": "small", "burn": 3.0, "burn_dmg": 5},
    {"name": "中型岩浆史莱姆", "hp": 30, "atk": 4, "range": 1.0, "cd": 1.8, "speed": 1.35,  "detect": 420, "color": "red", "ranged": False, "split": "medium", "burn": 3.0, "burn_dmg": 5},
]
# 自然刷新的普通怪物（中/小型史莱姆不自然刷新）
NATURAL_NORMAL = ["僵尸", "骷髅", "蜘蛛", "蝙蝠", "大型史莱姆"]

# ================================================================
# 精英怪物
# ================================================================
ELITE_MONSTERS = [
    {"name": "精英僵尸",   "hp": 50, "atk": 6,  "range": 1.5, "cd": 1.2, "speed": 1.35,  "detect": 720, "color": "green_black", "ranged": False},
    {"name": "精英骷髅",   "hp": 50, "atk": 8,  "range": 1.5, "cd": 2.0, "speed": 1.875, "detect": 720, "color": "gray_white",  "ranged": True},
    {"name": "暗影骑士",   "hp": 50, "atk": 7,  "range": 2.0, "cd": 1.8, "speed": 1.875, "detect": 720, "color": "purple_dark", "ranged": False, "wither": 4.0},
    {"name": "烈焰使者",   "hp": 50, "atk": 0,  "range": 1.5, "cd": 5.0, "speed": 1.125, "detect": 720, "color": "gold",       "ranged": True,  "fireball": 3, "fire_interval": 0.3, "burn": 4.0, "burn_dmg": 7},
]

# ================================================================
# 雪地特有精英（V1.0.4）：攻击附加霜冻
# ================================================================
SNOW_ELITE_MONSTERS = [
    {"name": "冰霜僵尸",   "hp": 50, "atk": 6,  "range": 1.5, "cd": 1.2, "speed": 1.35,  "detect": 720, "color": "blue_light", "ranged": False, "frost": 5.0},
    {"name": "流髑",       "hp": 50, "atk": 8,  "range": 1.5, "cd": 2.0, "speed": 1.875, "detect": 720, "color": "gray_white", "ranged": True,  "frost": 5.0},
]

# ================================================================
# 头目 BOSS（10%远程伤害减免，5%近战伤害减免）
# ================================================================
HEAD_BOSS_MELEE = [
    {"name": "卫道士突袭队长", "hp": 800, "atk": 12, "range": 1.2, "cd": 1.2, "speed": 1.875, "detect": 960, "color": "gold",  "ranged": False, "dr_ranged": 0.10, "dr_melee": 0.05},
    {"name": "暗黑骑士",      "hp": 800, "atk": 9,  "range": 2.0, "cd": 1.2, "speed": 2.25,  "detect": 960, "color": "purple_dark", "ranged": False, "wither": 6.0, "dr_ranged": 0.10, "dr_melee": 0.05, "combo_hits": 3, "combo_interval": 0.3},
]
HEAD_BOSS_RANGED = [
    {"name": "掠夺者突袭队长", "hp": 800, "atk": 15, "range": 1.5, "cd": 1.5, "speed": 2.25,  "detect": 960, "color": "blue_light", "ranged": True, "dr_ranged": 0.10, "dr_melee": 0.05},
    {"name": "炎魔",         "hp": 800, "atk": 0,  "range": 1.5, "cd": 5.0, "speed": 1.875, "detect": 960, "color": "red",        "ranged": True, "fireball": 5, "fire_interval": 0.2, "burn": 5.0, "burn_dmg": 9, "dr_ranged": 0.10, "dr_melee": 0.05},
]

# ================================================================
# 首领（高塔之主）
# ================================================================
FINAL_BOSS = {
    "name": "高塔之主",
    "hp": 5000,
    "atk_p1": 12, "cd_p1": 1.2, "speed_p1": 1.5,
    "atk_p2": 15, "cd_p2": 1.0, "speed_p2": 1.875,
    "speed_p3": 2.25, "dr_p3": 0.30,
    "range": 3.0, "detect": 1200, "color": "red_dark",
    "dps_cap": 50, "hit_cap": 20,
    "dr_ranged_p1": 0.10, "dr_melee_p1": 0.10,
    "dr_ranged_p2": 0.40, "dr_melee_p2": 0.20,
    "dr_ranged_p3": 1.00, "dr_melee_p3": 0.30,
    "summon_interval": 10.0, "summon_chance": 0.50,
    "p2_fireball_interval": 10.0,
}

# ================================================================
# 怪物召唤映射（供 combat_scene._boss_summon 使用）
# ================================================================

# 基础属性映射：monster_type -> {"hp", "attack", "attack_range", "attack_cooldown"}
MONSTER_BASE_STATS = {
    "normal": {"hp": 30, "attack": 5, "attack_range": 1.5, "attack_cooldown": 1.2},
    "elite":  {"hp": 50, "attack": 7, "attack_range": 2.0, "attack_cooldown": 1.8},
}

# 名称映射：monster_type -> [可能的怪物名称]
MONSTER_NAMES = {
    "normal": ["僵尸", "骷髅", "蜘蛛", "蝙蝠"],
    "elite":  ["精英僵尸", "精英骷髅", "暗影骑士", "烈焰使者"],
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
