"""
Dungeon Warriors V1.0.3 — 物品数据类
"""

from dataclasses import dataclass, field


@dataclass
class Weapon:
    """武器"""
    name: str
    weapon_type: str
    category: str
    attack_bonus: int
    tier: int
    cooldown: float
    attack_range: float
    combo_count: int = 0
    move_restricted: bool = False
    crit_chance: float = 0.0
    crit_mult: float = 1.0
    instakill: dict | None = None
    overheat_count: int = 0        # 过热触发次数
    overheat_cd: float = 0.0       # 过热冷却时间
    triple_shot_chance: float = 0.0  # 三重射击概率

    def __repr__(self):
        return f"Weapon({self.name}, +{self.attack_bonus}, T{self.tier})"


@dataclass
class Armor:
    """护甲 V1.0.3 — 百分比HP + DR + 类型加成"""
    name: str
    armor_type: str        # "战袍"|"猎人之甲"|...|"special"
    hp_bonus_pct: float     # HP百分比加成
    damage_reduction: float  # 伤害减免 0.0~1.0
    tier: int
    # 类型加成
    crit_chance: float = 0.0
    crit_mult: float = 1.0
    melee_dmg_pct: float = 0.0
    ranged_dmg_pct: float = 0.0
    lifesteal: float = 0.0
    speed_bonus_pct: float = 0.0
    # 特殊效果
    on_kill_invis: bool = False
    on_kill_speed: bool = False
    invis_cd: float = 0.0
    invis_dur: float = 0.0

    def __repr__(self):
        return f"Armor({self.name}, HP+{self.hp_bonus_pct*100:.0f}%, DR={self.damage_reduction*100:.0f}%)"


@dataclass
class Consumable:
    """消耗品"""
    name: str
    item_type: str

    def __repr__(self):
        return f"Consumable({self.name})"


Item = Weapon | Armor | Consumable
