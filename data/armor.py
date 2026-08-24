"""
Dungeon Warriors V1.0.3 — 护甲定义（百分比HP/DR + 类型加成）
"""

from entities.item import Armor

ARMOR_TYPES = {
    "战袍":       {"crit": 0.15,  "melee": 0,    "ranged": 0,    "ls": 0,    "spd": 0},
    "猎人之甲":   {"crit": 0,     "melee": 0.05,  "ranged": 0,    "ls": 0,    "spd": 0},
    "弓箭手之甲": {"crit": 0,     "melee": 0,     "ranged": 0.05, "ls": 0,    "spd": 0},
    "冷酷战甲":   {"crit": 0,     "melee": 0,     "ranged": 0,    "ls": 0.12, "spd": 0},
    "窃贼之甲":   {"crit": 0,     "melee": 0,     "ranged": 0,    "ls": 0,    "spd": 0.05},
}

LEVEL_BONUS = {1: (0.20, 0.05), 2: (0.40, 0.10), 3: (0.60, 0.15),
               4: (0.80, 0.20), 5: (1.00, 0.25)}


def _make(at, t):
    hp, dr = LEVEL_BONUS[t]
    m = ARMOR_TYPES[at]
    return Armor(name=f"{at} (T{t})", armor_type=at,
                 hp_bonus_pct=hp, damage_reduction=dr, tier=t,
                 crit_chance=m["crit"]*t, crit_mult=2.5,
                 melee_dmg_pct=m["melee"]*t, ranged_dmg_pct=m["ranged"]*t,
                 lifesteal=m["ls"]*t, speed_bonus_pct=m["spd"]*t)


ARMORS = [_make(at, t) for at in ARMOR_TYPES for t in range(1, 6)]

SPECIAL_ARMORS = [
    Armor("幻影长袍", "special", 1.25, 0.40, 5, speed_bonus_pct=0.40,
          on_kill_invis=True, invis_cd=6.0, invis_dur=4.0),
    Armor("高地战甲", "special", 1.25, 0.40, 5,
          melee_dmg_pct=0.40, ranged_dmg_pct=0.40, speed_bonus_pct=0.40),
    Armor("守卫者之甲", "special", 1.25, 0.60, 5,
          melee_dmg_pct=0.40, ranged_dmg_pct=0.40),
    Armor("凋零之甲", "special", 1.25, 0.40, 5,
          lifesteal=0.75, crit_chance=0.40, crit_mult=2.5),
]

ALL_ARMORS = ARMORS + SPECIAL_ARMORS
ARMOR_BY_NAME = {a.name: a for a in ALL_ARMORS}
ARMOR_BY_TIER: dict[int, list[Armor]] = {}
for a in ARMORS:
    ARMOR_BY_TIER.setdefault(a.tier, []).append(a)
