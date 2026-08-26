"""
Dungeon Warriors v2.0 — 玩家数据类
HP成长、Buff计时器、伤害减免
"""

from dataclasses import dataclass, field
from config import (
    PLAYER_BASE_HP, PLAYER_HP_PER_FLOOR, PLAYER_HP_PER_BOSS_KILL,
    PLAYER_BASE_SPEED,
    STRENGTH_POTION_DURATION, INVIS_POTION_DURATION,
    SWIFT_POTION_DURATION, BREAD_HEAL_DURATION, BREAD_HEAL_PER_SEC,
    POWER_POTION_MULT, SWIFT_POTION_MULT,
)
from entities.item import Weapon, Armor


@dataclass
class Player:
    """玩家实体 v2.0"""
    # 基础属性
    base_hp: int = PLAYER_BASE_HP
    current_hp: int = PLAYER_BASE_HP
    current_floor: int = 1     # 当前楼层（用于HP上限计算）
    boss_kills: int = 0        # 头目击杀数 (+10HP each)
    elite_kills: int = 0       # 精英击杀数 (+2HP each)

    # 装备（双武器槽：近战 + 远程）
    melee_weapon: Weapon | None = None
    ranged_weapon: Weapon | None = None
    armor: Armor | None = None

    # Buff 计时器（key -> 剩余秒数）
    buffs: dict[str, float] = field(default_factory=dict)
    _consumable_cooldowns: dict[str, float] = field(default_factory=dict)
    # 状态效果（凋零、燃烧等）
    status_effects: dict[str, float] = field(default_factory=dict)
    _burn_dmg: float = 7.0  # 当前燃烧每秒伤害

    # 近战连击系统
    combo_counter: int = 0

    # 运行时状态
    x: float = 0.0
    y: float = 0.0
    facing_angle: float = 0.0
    attack_cooldown: float = 0.0   # 近战冷却（秒）
    ranged_cooldown: float = 0.0   # 远程冷却（秒）
    speed: int = PLAYER_BASE_SPEED

    # ================================================================
    # 属性计算
    # ================================================================

    def total_max_hp(self, floor: int | None = None) -> int:
        """HP（仅此处取整）"""
        if floor is None:
            floor = self.current_floor
        hp = float(self.base_hp + (floor-1)*5 + self.boss_kills*10 + self.elite_kills*2)
        if self.armor and self.armor.hp_bonus_pct > 0:
            hp *= (1 + self.armor.hp_bonus_pct)
        return round(hp)

    def base_attack_bonus(self) -> int:
        """基础攻击加成：每5精英+1 / 每1头目+1"""
        return self.elite_kills // 5 + self.boss_kills

    def total_melee_attack(self) -> float:
        """近战攻击力（浮点，仅HP变更时取整）"""
        atk = float((self.melee_weapon.attack_bonus if self.melee_weapon else 0) + self.base_attack_bonus())
        if self.armor and self.armor.melee_dmg_pct > 0:
            atk *= (1 + self.armor.melee_dmg_pct)
        if 'strength' in self.buffs and self.buffs['strength'] > 0:
            atk *= POWER_POTION_MULT
        return atk
    def total_ranged_attack(self) -> float:
        """远程攻击力（浮点）"""
        atk = float((self.ranged_weapon.attack_bonus if self.ranged_weapon else 0) + self.base_attack_bonus())
        if self.armor and self.armor.ranged_dmg_pct > 0:
            atk *= (1 + self.armor.ranged_dmg_pct)
        if 'strength' in self.buffs and self.buffs['strength'] > 0:
            atk *= POWER_POTION_MULT
        return atk
    def total_speed(self) -> float:
        """移动速度（浮点）。霜冻期间降为 60%"""
        spd = float(self.speed)
        if self.armor and self.armor.speed_bonus_pct > 0:
            spd *= (1 + self.armor.speed_bonus_pct)
        if 'swift' in self.buffs and self.buffs['swift'] > 0:
            spd *= SWIFT_POTION_MULT
        if self.has_status("frost"):
            spd *= 0.6
        return max(1.0, spd)
    def damage_reduction(self) -> float:  # 浮点
        """伤害减免比例"""
        dr = 0.0
        if self.armor:
            dr = self.armor.damage_reduction
        return dr

    def is_invisible(self) -> bool:
        """是否隐身"""
        return "invisible" in self.buffs and self.buffs["invisible"] > 0

    # ================================================================
    # 战斗方法
    # ================================================================

    def take_damage(self, damage: float) -> bool:
        """受到伤害（含减免），仅HP变更时取整"""
        reduced = round(damage * (1 - self.damage_reduction()))
        self.current_hp = max(0, self.current_hp - reduced)
        return self.current_hp <= 0

    def heal(self, amount: int) -> None:
        """回复指定量的生命"""
        max_hp = self.total_max_hp()
        self.current_hp = min(max_hp, self.current_hp + amount)

    def heal_ratio(self, ratio: float) -> None:
        """按比例回复生命"""
        max_hp = self.total_max_hp()
        self.heal(int(max_hp * ratio))

    def heal_full(self) -> None:
        """回满生命（使用当前楼层的HP上限）"""
        self.current_hp = self.total_max_hp()

    def is_alive(self) -> bool:
        return self.current_hp > 0

    # ================================================================
    # 装备
    # ================================================================

    def equip_melee_weapon(self, weapon: Weapon) -> Weapon | None:
        """装备近战武器（仅接受近战类别）"""
        if weapon.category != "melee":
            return None  # 拒绝非近战武器
        old = self.melee_weapon
        self.melee_weapon = weapon
        self.combo_counter = 0
        return old

    def equip_ranged_weapon(self, weapon: Weapon) -> Weapon | None:
        """装备远程武器（仅接受远程类别）"""
        if weapon.category != "ranged":
            return None  # 拒绝非远程武器
        old = self.ranged_weapon
        self.ranged_weapon = weapon
        return old

    def equip_armor(self, armor: Armor) -> Armor | None:
        """装备护甲"""
        old = self.armor
        self.armor = armor
        return old

    # ================================================================
    # Buff 管理
    # ================================================================

    def add_buff(self, buff_type: str, duration: float) -> None:
        """添加 buff（已有同种时取最大剩余时长）"""
        current = self.buffs.get(buff_type, 0)
        self.buffs[buff_type] = max(current, duration)

    # 消耗品使用冷却
    CONSUMABLE_CD = 5.0  # 同种消耗品冷却 5 秒

    def can_use_consumable(self, item_type: str, current_time: float) -> bool:
        last = self._consumable_cooldowns.get(item_type, -999.0)
        return (current_time - last) >= self.CONSUMABLE_CD

    def mark_consumable_used(self, item_type: str, current_time: float) -> None:
        self._consumable_cooldowns[item_type] = current_time

    def update_buffs(self, dt: float) -> None:
        """每帧更新 buff 和状态效果倒计时"""
        for d in [self.buffs, self.status_effects]:
            expired = [k for k, v in d.items() if v <= 0]
            for k in expired:
                del d[k]
            for k in list(d.keys()):
                d[k] -= dt

    def clear_buffs(self) -> None:
        """清除所有 buff"""
        self.buffs.clear()

    def has_buff(self, buff_type: str) -> bool:
        """是否有活跃的指定 buff"""
        return buff_type in self.buffs and self.buffs[buff_type] > 0

    def has_status(self, effect: str) -> bool:
        """是否有活跃的状态效果"""
        return effect in self.status_effects and self.status_effects[effect] > 0

    def add_status(self, effect: str, duration: float, dmg: float = 0) -> None:
        """添加状态效果。燃烧叠加：每额外命中+40%时长"""
        cur = self.status_effects.get(effect, 0)
        if effect == "burn" and cur > 0:
            # 多枚火球叠加：已有燃烧 + 新时长×40%
            self.status_effects[effect] = cur + duration * 0.4
        else:
            self.status_effects[effect] = max(cur, duration)
        if effect == "burn" and dmg > 0:
            self._burn_dmg = max(self._burn_dmg, dmg)

    def can_heal(self) -> bool:
        """是否可回复生命（凋零期间不可）"""
        return not self.has_status("wither")
