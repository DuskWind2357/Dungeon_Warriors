"""
Dungeon Warriors V1.0.3 P5 — 武器定义（公式化生成）
"""

from entities.item import Weapon

# ================================================================
# 近战武器（公式生成）
# ================================================================
BASE_NAMES = {"sword": "剑", "axe": "斧", "spear": "矛", "dagger": "匕首",
              "bow": "弓", "crossbow": "弩"}
TIER_LABELS = {1: "铜", 2: "铁", 3: "金", 4: "钻石", 5: "下界合金"}
BOW_LABELS = {1: "普通", 2: "改进", 3: "精制", 4: "卓越", 5: "史诗"}

# 剑: 2+2T, CD 0.2, RNG 1.5
SWORDS = [Weapon(name=f"{TIER_LABELS[t]}{BASE_NAMES['sword']}",
                 weapon_type="sword", category="melee",
                 attack_bonus=2+2*t, tier=t, cooldown=0.2, attack_range=1.5)
          for t in range(1, 6)]

# 斧: 3+3T, CD 0.5, RNG 2.0
AXES = [Weapon(name=f"{TIER_LABELS[t]}{BASE_NAMES['axe']}",
               weapon_type="axe", category="melee",
               attack_bonus=3+3*t, tier=t, cooldown=0.5, attack_range=2.0)
        for t in range(1, 6)]

# 矛: 2+2T, CD 1.0, RNG 3.0, 三段连击
SPEARS = [Weapon(name=f"{TIER_LABELS[t]}{BASE_NAMES['spear']}",
                 weapon_type="spear", category="melee",
                 attack_bonus=2+2*t, tier=t, cooldown=1.0, attack_range=3.0,
                 combo_count=3)
          for t in range(1, 6)]

# 匕首: 2+1T, CD 0s, RNG 1.0
DAGGERS = [Weapon(name=f"{TIER_LABELS[t]}{BASE_NAMES['dagger']}",
                  weapon_type="dagger", category="melee",
                  attack_bonus=2+1*t, tier=t, cooldown=0.0, attack_range=1.0)
           for t in range(1, 6)]

# 弓: 5+3T, CD 0.5s, 移动不可
BOWS = [Weapon(name=f"弓（{BOW_LABELS[t]}）",
               weapon_type="bow", category="ranged",
               attack_bonus=5+3*t, tier=t, cooldown=0.5, attack_range=999,
               move_restricted=True)
        for t in range(1, 6)]

# 弩: 5+3T, CD 1.0s
CROSSBOWS = [Weapon(name=f"弩（{BOW_LABELS[t]}）",
                    weapon_type="crossbow", category="ranged",
                    attack_bonus=5+3*t, tier=t, cooldown=1.0, attack_range=999)
             for t in range(1, 6)]

# ================================================================
# 特殊武器
# ================================================================
SPECIAL_WEAPONS = [
    Weapon("三叉戟", "spear", "melee", 18, 5, 0.3, 2.5),
    Weapon("机械链锯", "sword", "melee", 10, 5, 0.0, 1.5,
           overheat_count=10, overheat_cd=1.0),
    Weapon("精英之弓", "bow", "ranged", 25, 5, 0.6, 999,
           crit_chance=0.4, crit_mult=3.0),
    Weapon("杀戮之弩", "crossbow", "ranged", 20, 5, 1.2, 999,
           instakill={"normal": 0.45, "elite": 0.15, "head_boss": 0.05, "final_boss": 0.01}),
    Weapon("机械弩", "crossbow", "ranged", 6, 5, 0.0, 999,
           overheat_count=20, overheat_cd=2.0),
    Weapon("幻术师之弓", "bow", "ranged", 18, 5, 1.0, 999,
           triple_shot_chance=0.45),
]

# ================================================================
# 汇总
# ================================================================
MELEE_WEAPONS = SWORDS + AXES + SPEARS + DAGGERS
RANGED_WEAPONS = BOWS + CROSSBOWS
ALL_WEAPONS = MELEE_WEAPONS + RANGED_WEAPONS + SPECIAL_WEAPONS
WEAPON_BY_NAME = {w.name: w for w in ALL_WEAPONS}
WEAPON_BY_TYPE_TIER: dict[tuple[str, int], Weapon] = {}
for w in MELEE_WEAPONS + RANGED_WEAPONS:  # 不含特殊武器
    WEAPON_BY_TYPE_TIER[(w.weapon_type, w.tier)] = w
