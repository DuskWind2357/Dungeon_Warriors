"""
Dungeon Warriors V1.0.5.8 — 游戏常量配置（平衡性重做）
基于 frame/V 1.0.5/平衡性重做/ 设计文档
"""

# ============================================================
# 窗口
# ============================================================
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720
FPS = 60

# ============================================================
# 地图网格
# ============================================================
TILE_SIZE = 48
MAP_COLS = 20
MAP_ROWS = 15

# ============================================================
# 玩家 (frame.txt + improvement.txt)
# ============================================================
PLAYER_BASE_HP = 100
PLAYER_HP_PER_FLOOR = 5       # 每层 +5 生命上限
PLAYER_HP_PER_BOSS_KILL = 5   # 每击杀头目 +5 生命上限
PLAYER_BASE_SPEED = 4         # px/frame
PLAYER_DEFAULT_WEAPON = "铜剑"  # 初始武器
PLAYER_DEFAULT_ARMOR = "战袍 (T1)"   # 初始护甲

# ============================================================
# 怪物 (V1.0.5.8 平衡性重做)
# ============================================================
# 格式: hp, attack, attack_range(格), attack_cooldown(秒)
MONSTER_NORMAL_HP = 30
MONSTER_NORMAL_ATK = 4
MONSTER_NORMAL_RANGE = 1.5
MONSTER_NORMAL_CD = 1.2

MONSTER_ELITE_HP = 50
MONSTER_ELITE_ATK = 6
MONSTER_ELITE_RANGE = 1.5
MONSTER_ELITE_CD = 1.2

MONSTER_HEAD_BOSS_HP = 800
MONSTER_HEAD_BOSS_ATK = 12
MONSTER_HEAD_BOSS_RANGE = 1.2
MONSTER_HEAD_BOSS_CD = 1.2

MONSTER_FINAL_BOSS_HP = 5000
MONSTER_FINAL_BOSS_ATK_P1 = 12
MONSTER_FINAL_BOSS_ATK_P2 = 15
MONSTER_FINAL_BOSS_CD_P1 = 1.2
MONSTER_FINAL_BOSS_CD_P2 = 1.0
MONSTER_FINAL_BOSS_RANGE = 3.0
MONSTER_FINAL_BOSS_P2_DR = 0.40    # 二阶段 40% 远程伤害减免
MONSTER_FINAL_BOSS_SUMMON_INTERVAL = 10.0  # 每10秒召唤
MONSTER_FINAL_BOSS_SUMMON_CHANCE = 0.50
MONSTER_FINAL_BOSS_RANGED_IMMUNE_HP = 0.25  # HP<25% 远程免疫

MONSTER_SPEED = 2
MONSTER_DETECT_RANGE = 480     # px
MONSTER_SCALE_PER_FLOOR = 1.07  # 保留旧缩放（兼容 floor_manager）

# 每5层怪物成长
MONSTER_PER_5_FLOORS_HP = 10
MONSTER_PER_5_FLOORS_ATK = 2

# ============================================================
# 楼层
# ============================================================
TOTAL_FLOORS = 30
BOSS_FLOORS = [10, 20]
FINAL_BOSS_FLOOR = 30

BATTLE_NORMAL_MIN = 4
BATTLE_NORMAL_MAX = 8
BATTLE_ELITE_MIN = 0
BATTLE_ELITE_MAX = 3        # 默认: 最多3名精英

# ============================================================
# V1.0.5 楼层架构
# ============================================================
PORTAL_MIN_EDGE_DIST = 6      # 传送门距边缘最小距离（格）
PORTAL_COUNT_MIN = 2          # 出生点房间传送门数量下限
PORTAL_COUNT_MAX = 4          # 出生点房间传送门数量上限
DUNGEON_ROOM_CHANCE = 0.50    # 副本房间概率（调试用，已由分段表 DUNGEON_ROOM_CHANCES 取代）
TREASURE_ROOM_CHANCE = 0.20   # 战斗房间额外连接宝藏房间概率（已废弃）
TREASURE_ROOM_CHANCE_BATTLE = 0.10  # 战斗房间宝藏室刷新概率（V1.0.5.6：10%）
TREASURE_ROOM_DUNGEON_CHANCE = 0.60  # 副本房间宝藏室刷新概率（V1.0.5.6：60%）
PORTAL_TRAVEL_DELAY = 4.0     # 传送倒计时（秒）
FLOOR_PORTAL_TRAVEL_DELAY = 5.0  # 通往下一楼层传送倒计时（秒）
ROOM_IDLE_SOUND_INTERVAL = 3.0  # 房间环境音播放间隔（秒）

# ============================================================
# V1.0.5.6 战斗楼层分支规则（等概率取一）
# ============================================================
# (floor_min, floor_max) -> 可选的该段分支数（等概率随机取一个）
BRANCH_COUNTS: dict[tuple[int, int], list[int]] = {
    (1, 5):   [1, 2],
    (6, 9):   [1, 2, 3],
    (11, 19): [2, 3, 4],
    (21, 29): [3, 4],
}
# 各段副本生成概率（逐分支判定）
DUNGEON_ROOM_CHANCES: dict[tuple[int, int], float] = {
    (1, 5):   0.0,
    (6, 9):   0.10,
    (11, 19): 0.20,
    (21, 29): 0.40,
}
# 各段每层副本数量上限（超限副本自动替换为战斗房间）
DUNGEON_MAX_PER_FLOOR: dict[tuple[int, int], int] = {
    (1, 5):   0,
    (6, 9):   1,
    (11, 19): 1,
    (21, 29): 2,
}
# BOSS 战斗楼层出生点房间固定分支数
BOSS_BRANCH_COUNT = 4

# ============================================================
# 奖励系统
# ============================================================
AUTO_DESTROY_LOW_LEVEL_GEAR = False  # 低级装备自动销毁开关（默认关闭）
MUSIC_ENABLED = True                 # 音乐控制开关（默认开启，关闭时停止游戏内所有音乐）

# ============================================================
# 难度系统（V1.0.5.8 平衡性重做）
# ============================================================
# 基础难度：刷怪倍率1.0，怪物属性每层线性缩放
# 冒险难度：刷怪倍率1.25，每房间额外刷新50%精英
# 末日难度：刷怪倍率1.5，每房间额外刷新100%精英
DIFFICULTY_MODIFIERS = {
    "easy": {
        "label": "默认",
        "spawn_mult": 1.0,
        "hp_scale_per_floor": 1.18,      # 每层+18%血量
        "atk_scale_per_floor": 1.18,     # 每层+18%攻击力
        "cd_scale_per_floor": 0.99,      # 每层-1%攻击冷却
        "skill_cd_scale_per_floor": 0.99, # 每层-1%技能冷却
        "elite_extra_mult": 0.0,         # 无额外精英
        "boss_cd_mult": 1.0,             # BOSS攻击冷却倍率
        "boss_skill_cd_mult": 1.0,       # BOSS技能冷却倍率
        "boss_atk_mult": 1.0,            # BOSS攻击力倍率
        "boss_hp_mult": 1.0,             # BOSS血量倍率
        "treasure_room_chance_battle": 0.10,  # 战斗房间宝藏室概率
        "treasure_room_chance_dungeon": 0.60, # 副本房间宝藏室概率
    },
    "normal": {
        "label": "冒险",
        "spawn_mult": 1.25,
        "hp_scale_per_floor": 1.18,
        "atk_scale_per_floor": 1.18,
        "cd_scale_per_floor": 0.985,     # 每层-1.5%攻击冷却
        "skill_cd_scale_per_floor": 0.985,
        "elite_extra_mult": 0.50,        # 额外50%精英
        "boss_cd_mult": 0.9,             # BOSS攻击冷却×0.9
        "boss_skill_cd_mult": 0.8,       # BOSS技能冷却×0.8
        "boss_atk_mult": 1.1,            # BOSS攻击力×1.1
        "boss_hp_mult": 1.2,             # BOSS血量×1.2
        "treasure_room_chance_battle": 0.20,
        "treasure_room_chance_dungeon": 0.80,
    },
    "hard": {
        "label": "末日",
        "spawn_mult": 1.5,
        "hp_scale_per_floor": 1.26,      # 每层+26%血量
        "atk_scale_per_floor": 1.26,     # 每层+26%攻击力
        "cd_scale_per_floor": 0.98,      # 每层-2%攻击冷却
        "skill_cd_scale_per_floor": 0.98,
        "elite_extra_mult": 1.00,        # 额外100%精英
        "boss_cd_mult": 0.8,             # BOSS攻击冷却×0.8
        "boss_skill_cd_mult": 0.6,       # BOSS技能冷却×0.6
        "boss_atk_mult": 1.2,            # BOSS攻击力×1.2
        "boss_hp_mult": 1.5,             # BOSS血量×1.5
        "treasure_room_chance_battle": 0.40,
        "treasure_room_chance_dungeon": 1.00,
    },
}
DEFAULT_DIFFICULTY = "easy"

# 延迟刷新
SPAWN_DELAY_SEC = 3.0

# ============================================================
# 掉落概率 (improvement.txt)
# ============================================================
# 普通怪物: 5%药水(4选1), 20%面包(最多1个)
DROP_NORMAL_POTION = 0.05  # V1.0.3: 5%
DROP_NORMAL_BREAD = 0.10  # V1.0.3: 10%
# 精英怪物: 20%药水(4选1), 50%面包(最多2个)
DROP_ELITE_POTION = 0.15  # V1.0.3: 15%
DROP_ELITE_BREAD = 0.30  # V1.0.3: 30%
# 头目BOSS: 100%高一级装备, 90%面包, 50%药水(4选1)
DROP_BOSS_EQUIP = 1.0
DROP_BOSS_BREAD = 0.80  # V1.0.3: 80%
DROP_BOSS_POTION = 0.80  # V1.0.3: 80%

# ============================================================
# 消耗品 Buff 持续时间（秒）
# ============================================================
STRENGTH_POTION_DURATION = 15.0
INVIS_POTION_DURATION = 15.0
SWIFT_POTION_DURATION = 15.0
BREAD_HEAL_DURATION = 5.0
BREAD_HEAL_PER_SEC = 0.10    # 每秒 10%
BREAD_HEAL_CAP = 0.50        # 总上限 50%
POWER_POTION_MULT = 2.0
SWIFT_POTION_MULT = 2.0

# ============================================================
# 背包
# ============================================================
INVENTORY_COLS = 8
INVENTORY_ROWS = 8           # 8×8 = 64格
INVENTORY_SIZE = 64

# ============================================================
# 复活
# ============================================================
MAX_REVIVES = 3
REVIVE_COUNTDOWN_SEC = 5
GAME_OVER_DELAY_SEC = 3
REVIVE_HP_RESTORE_RATIO = 1.0

# ============================================================
# 远程投射物（V1.0.5.8 平衡性重做）
# ============================================================
PROJECTILE_SPEED = 16         # 玩家箭矢速度
PROJECTILE_RANGE = 960        # 玩家箭矢射程
PROJECTILE_SIZE = 6

ENEMY_ARROW_SPEED = 12        # 敌方箭矢速度
ENEMY_ARROW_RANGE = 960       # 敌方箭矢射程

FIREBALL_SPEED = 8            # 火球速度
FIREBALL_RANGE = 640          # 火球射程

ICE_FIREBALL_SPEED = 10       # 冰焰弹速度
ICE_FIREBALL_RANGE = 720      # 冰焰弹射程

ICE_BOMB_SPEED = 12           # 冰弹速度
ICE_BOMB_RANGE = 720          # 冰弹射程

# ============================================================
# 颜色
# ============================================================
COLOR_BG = (15, 15, 25)
COLOR_WALL = (50, 50, 60)
COLOR_FLOOR = (30, 30, 40)
COLOR_SPAWN = (0, 100, 0, 80)
COLOR_PORTAL = (120, 0, 200)
COLOR_PLAYER = (60, 140, 240)
COLOR_HP_BAR = (200, 50, 50)
COLOR_HP_BAR_BG = (60, 60, 60)
COLOR_MONSTER_NORMAL = (220, 80, 30)
COLOR_MONSTER_ELITE = (200, 180, 30)
COLOR_MONSTER_BOSS = (200, 30, 30)
COLOR_MONSTER_FINAL_BOSS = (180, 20, 20)
COLOR_TEXT = (220, 220, 220)
COLOR_TEXT_DIM = (150, 150, 150)
COLOR_HUD = (40, 40, 40)
COLOR_TITLE = (255, 200, 50)
COLOR_TITLE_SHADOW = (80, 50, 0)
COLOR_BUTTON = (70, 70, 80)
COLOR_BUTTON_HOVER = (90, 90, 105)
COLOR_BUTTON_BORDER = (100, 100, 115)
COLOR_BUTTON_TEXT = (220, 220, 220)
COLOR_PANEL_BG = (20, 20, 35, 200)
COLOR_OVERLAY = (0, 0, 0, 180)
COLOR_DEATH_TEXT = (220, 30, 30)
COLOR_VICTORY_TEXT = (255, 215, 0)
COLOR_TOAST = (255, 60, 60)
COLOR_DROP_HEAL = (220, 50, 50)
COLOR_DROP_POWER = (255, 200, 50)
COLOR_PROJECTILE = (100, 200, 255)
COLOR_BUFF_ACTIVE = (100, 255, 100)
COLOR_INVIS = (160, 160, 220)
COLOR_SWIFT = (100, 220, 255)
