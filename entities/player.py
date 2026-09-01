"""
Dungeon Warriors V1.0.5.8 — 玩家数据类（平衡性重做）
HP成长、Buff计时器、伤害减免、击退定身
"""

from dataclasses import dataclass, field
from config import (
    PLAYER_BASE_HP, DIFFICULTY_MODIFIERS,
    PLAYER_BASE_SPEED,
    STRENGTH_POTION_DURATION, INVIS_POTION_DURATION,
    SWIFT_POTION_DURATION, BREAD_HEAL_DURATION, BREAD_HEAL_PER_SEC,
    POWER_POTION_MULT, SWIFT_POTION_MULT,
    MAX_HP_PENALTY_FLOOR,
)
from entities.item import Weapon, Armor


# V1.0.5.8 平衡性重做：BUFF效果常量
BURN_DAMAGE = {1: 5, 2: 7, 3: 9}  # 燃烧I/II/III级每秒伤害
FROST_SLOW = {1: 0.4, 2: 0.6}     # 霜冻I/II级速度倍率（0.4=SPD×40%）
STRENGTH_MULT = 2.0                # 力量：ATK×200%
SWIFT_MULT = 2.0                   # 迅捷：SPD×200%
HEAL_OVER_TIME_RATIO = 0.10        # 生命恢复：每秒回复10%HP


@dataclass
class Player:
    """玩家实体 V1.0.5.8"""
    # 基础属性
    base_hp: int = PLAYER_BASE_HP
    current_hp: int = PLAYER_BASE_HP
    current_floor: int = 1     # 当前楼层（用于HP/攻击成长计算）
    boss_kills: int = 0        # 头目击杀数（生命+10/15/20、攻击+9%/12%/15% 按难度）
    elite_kills: int = 0       # 精英击杀数（生命+2/3/5、攻击+1% 按难度）
    difficulty: str = "easy"   # V1.0.5.10: 成长参数按难度取值

    # V1.0.6: 生命上限惩罚乘数（楼层重置×0.9 / 退出重进×0.95 递乘, 保底50%）
    max_hp_mult: float = 1.0

    # 装备（双武器槽：近战 + 远程）
    melee_weapon: Weapon | None = None
    ranged_weapon: Weapon | None = None
    armor: Armor | None = None

    # Buff 计时器（key -> 剩余秒数）
    buffs: dict[str, float] = field(default_factory=dict)
    _consumable_cooldowns: dict[str, float] = field(default_factory=dict)
    # 状态效果（凋零、燃烧等）
    status_effects: dict[str, float] = field(default_factory=dict)
    status_levels: dict[str, int] = field(default_factory=dict)  # V1.0.5.9: 状态显式等级
    _burn_dmg: float = 7.0  # 当前燃烧每秒伤害
    _burn_level: int = 2    # 当前燃烧等级（1/2/3）

    # 近战连击系统
    combo_counter: int = 0
    melee_stage: int = 0  # V1.0.5.12 补丁: 剑三段式当前段数（1/2/3；0=未开始/已重置）

    # 运行时状态
    x: float = 0.0
    y: float = 0.0
    facing_angle: float = 0.0
    attack_cooldown: float = 0.0   # 近战冷却（秒）
    ranged_cooldown: float = 0.0   # 远程冷却（秒）
    speed: int = PLAYER_BASE_SPEED
    _root_timer: float = 0.0       # V1.0.5.9: 定身剩余秒数（被冰弹命中等）

    # ================================================================
    # 属性计算
    # ================================================================

    def _growth(self) -> dict:
        """V1.0.5.10: 当前难度的玩家成长参数（防御式回退默认难度）"""
        return DIFFICULTY_MODIFIERS.get(self.difficulty, DIFFICULTY_MODIFIERS["easy"])

    def total_max_hp(self, floor: int | None = None) -> int:
        """HP（仅此处取整）。V1.0.5.10 计算规则：
        玩家HP = (基础生命值 + 楼层生命加成 + 精英/头目击杀生命加成) × (1+护甲倍率)
        生命加成按难度：每层+5/8/10，每精英+2/3/5，每头目+10/15/20
        V1.0.6: 再乘生命上限惩罚系数 max_hp_mult（楼层重置×0.9/退出重进×0.95 递乘），
        保底 = 无惩罚上限 × MAX_HP_PENALTY_FLOOR(50%)。
        """
        if floor is None:
            floor = self.current_floor
        g = self._growth()
        hp = float(self.base_hp
                   + (floor - 1) * g["player_hp_per_floor"]
                   + self.elite_kills * g["player_hp_per_elite"]
                   + self.boss_kills * g["player_hp_per_boss"])
        if self.armor and self.armor.hp_bonus_pct > 0:
            hp *= (1 + self.armor.hp_bonus_pct)
        full = hp  # 无惩罚生命上限
        # V1.0.6 生命上限惩罚（保底 50%）
        if self.max_hp_mult < 1.0:
            hp = max(hp * self.max_hp_mult, full * MAX_HP_PENALTY_FLOOR)
        return round(hp)

    def apply_max_hp_penalty(self, ratio: float) -> None:
        """V1.0.6: 扣除当前生命上限的 ratio（楼层重置 0.10 / 退出重进 0.05）。
        累乘递减；保底=无惩罚上限的50%。扣后强制当前HP不超过新上限。
        """
        if not (0.0 < ratio < 1.0):
            return
        self.max_hp_mult = self.max_hp_mult * (1.0 - ratio)
        new_max = self.total_max_hp()
        if self.current_hp > new_max:
            self.current_hp = new_max

    def base_attack_mult(self) -> float:
        """基础攻击倍率（V1.0.5.10）：
        = 1 + 每层攻击加成×(floor-1) + 精英击杀×1% + 头目击杀×9%/12%/15%（按难度）
        """
        g = self._growth()
        return (1.0
                + (self.current_floor - 1) * g["player_atk_per_floor"]
                + self.elite_kills * g["player_atk_per_elite"]
                + self.boss_kills * g["player_atk_per_boss"])

    def total_melee_attack(self) -> float:
        """近战攻击力（浮点）。V1.0.5.10 计算规则：
        ATK = (武器伤害 × 基础攻击倍率) × 护甲加成(如有) × 力量(如有)
        （暴击为命中时独立判定，见 systems/combat.py）
        """
        atk = float(self.melee_weapon.attack_bonus if self.melee_weapon else 0) * self.base_attack_mult()
        if self.armor and self.armor.melee_dmg_pct > 0:
            atk *= (1 + self.armor.melee_dmg_pct)
        if 'strength' in self.buffs and self.buffs['strength'] > 0:
            atk *= STRENGTH_MULT
        return atk

    def total_ranged_attack(self) -> float:
        """远程攻击力（浮点）。计算规则同近战（护甲加成取远程加成）"""
        atk = float(self.ranged_weapon.attack_bonus if self.ranged_weapon else 0) * self.base_attack_mult()
        if self.armor and self.armor.ranged_dmg_pct > 0:
            atk *= (1 + self.armor.ranged_dmg_pct)
        if 'strength' in self.buffs and self.buffs['strength'] > 0:
            atk *= STRENGTH_MULT
        return atk

    def total_speed(self) -> float:
        """移动速度（浮点）。V1.0.5.8: 霜冻I=SPD×40%, 霜冻II=SPD×60%, 迅捷=SPD×200%"""
        spd = float(self.speed)
        if self.armor and self.armor.speed_bonus_pct > 0:
            spd *= (1 + self.armor.speed_bonus_pct)
        if 'swift' in self.buffs and self.buffs['swift'] > 0:
            spd *= SWIFT_MULT
        if self.has_status("frost"):
            frost_level = self._get_status_level("frost")
            frost_mult = FROST_SLOW.get(frost_level, 0.6)
            spd *= frost_mult
        return max(1.0, spd)

    def damage_reduction(self) -> float:
        """伤害减免比例"""
        dr = 0.0
        if self.armor:
            dr = self.armor.damage_reduction
        return dr

    def is_invisible(self) -> bool:
        """是否隐身"""
        return "invisible" in self.buffs and self.buffs["invisible"] > 0

    # ================================================================
    # V1.0.5.8 状态效果辅助方法
    # ================================================================

    def _get_status_level(self, effect: str) -> int:
        """获取状态效果等级（V1.0.5.9: 显式等级存储，缺省按等级1）"""
        if effect == "burn":
            return self._burn_level
        return self.status_levels.get(effect, 1)

    # ================================================================
    # 战斗方法
    # ================================================================

    def take_damage(self, damage: float) -> bool:
        """受到伤害（含减免），仅HP变更时取整"""
        reduced = round(damage * (1 - self.damage_reduction()))
        self.current_hp = max(0, self.current_hp - reduced)
        return self.current_hp <= 0

    def heal(self, amount: int) -> None:
        """回复指定量的生命（凋零期间不可回复）"""
        if not self.can_heal():
            return
        max_hp = self.total_max_hp()
        self.current_hp = min(max_hp, self.current_hp + amount)

    def heal_ratio(self, ratio: float) -> None:
        """按比例回复生命（凋零期间不可回复）"""
        if not self.can_heal():
            return
        max_hp = self.total_max_hp()
        self.heal(int(max_hp * ratio))

    def heal_full(self) -> None:
        """回满生命（使用当前楼层的HP上限，凋零期间不可回复）"""
        if not self.can_heal():
            return
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

    def add_status(self, effect: str, duration: float, dmg: float = 0,
                   level: int = 0, mode: str = "max") -> None:
        """添加状态效果。V1.0.5.9: 显式等级存储（status_levels）
        V1.0.5.11 弹射物附加BUFF机制（mode 参数）:
        - "max"（默认）: 取最大时长（近战/箭矢等保持原逻辑；燃烧旧叠法+40%仅此模式保留）
        - "refresh": 刷新为新时长（多枚火球/冰弹依次命中，BUFF时长刷新而不叠加）
        - "stack":   叠加时长（多枚冰焰弹命中，BUFF时长叠加）
        等级与燃烧伤害始终取最高。
        """
        cur = self.status_effects.get(effect, 0)
        if mode == "refresh":
            self.status_effects[effect] = duration
        elif mode == "stack":
            self.status_effects[effect] = cur + duration
        elif effect == "burn" and cur > 0:
            # 旧叠法（仅默认模式）：已有燃烧 + 新时长×40%
            self.status_effects[effect] = cur + duration * 0.4
        else:
            self.status_effects[effect] = max(cur, duration)
        if level > 0:
            self.status_levels[effect] = max(self.status_levels.get(effect, 0), level)
        if effect == "burn":
            self._burn_level = self.status_levels.get("burn", self._burn_level)
        if effect == "burn" and dmg > 0:
            self._burn_dmg = max(self._burn_dmg, dmg)

    def get_burn_damage(self) -> float:
        """获取当前燃烧伤害（V1.0.5.8: 按等级计算）"""
        return BURN_DAMAGE.get(self._burn_level, 7)

    def can_heal(self) -> bool:
        """是否可回复生命（凋零期间不可）"""
        return not self.has_status("wither")

    # ================================================================
    # 击退/定身系统（V1.0.4 P3）
    # ================================================================


