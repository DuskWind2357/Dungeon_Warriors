"""
Dungeon Warriors v2.0 — 怪物数据类
攻击范围、冷却时间、BOSS多阶段、召唤系统、击退定身、循伤索敌
"""

from dataclasses import dataclass, field
from config import MONSTER_SPEED, MONSTER_DETECT_RANGE, TILE_SIZE


@dataclass
class Monster:
    """怪物实体 v2.0"""
    name: str
    monster_type: str   # "normal"|"elite"|"head_boss"|"final_boss"
    hp: int
    max_hp: int
    attack: int
    attack_range: float     # 攻击范围（格）
    attack_cooldown: float  # 冷却时间（秒）

    # 运行时状态
    x: float = 0.0
    y: float = 0.0
    cooldown_remaining: float = 0.0   # 当前剩余冷却（秒）
    speed: int = MONSTER_SPEED
    alive: bool = True
    aggro: bool = False       # 是否已进入战斗状态

    # 攻击类型
    ranged_attacker: bool = False       # 是否为远程攻击怪物（骷髅）

    # BOSS 专属
    phase: int = 1                      # 阶段 (1 or 2)
    summon_timer: float = 0.0           # 召唤倒计时
    damage_reduction: float = 0.0       # 伤害减免
    ranged_immune: bool = False         # 远程免疫

    # 击退/定身系统（V1.0.4 P3）
    stagger_immune_timer: float = 0.0   # 定身免疫计时器（5秒内最多一次）
    stagger_timer: float = 0.0          # 定身剩余时间（无法移动/攻击）

    # 循伤索敌系统（V1.0.4 P3）
    track_attacker_timer: float = 0.0   # 循伤索敌持续时间
    track_attacker_x: float = 0.0       # 攻击来源X
    track_attacker_y: float = 0.0       # 攻击来源Y
    base_detect_range: float = MONSTER_DETECT_RANGE  # 原始索敌范围

    def take_damage(self, damage: int) -> bool:
        """受到伤害（含减免），返回是否死亡"""
        reduced = int(damage * (1 - self.damage_reduction))
        self.hp = max(0, self.hp - reduced)
        if self.hp <= 0:
            self.alive = False
        return not self.alive

    def is_alive(self) -> bool:
        return self.alive and self.hp > 0

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0.0

    # ================================================================
    # BOSS 阶段管理
    # ================================================================

    def check_phase_transition(self) -> bool:
        """
        检查并执行 BOSS 阶段转换。
        返回 True 表示阶段发生了变化。
        """
        if self.monster_type != "final_boss":
            return False

        hp_pct = self.hp_ratio

        # 远程免疫（HP<25%）
        if hp_pct < 0.25 and not self.ranged_immune:
            self.ranged_immune = True
            return True

        # 二阶段（HP<50%）
        if hp_pct < 0.50 and self.phase == 1:
            self.phase = 2
            self.attack = 7                        # ATK +7
            self.attack_cooldown = 0.4              # CD 0.4s
            self.damage_reduction = 0.20            # 20% 减伤
            return True

        return False

    # ================================================================
    # 击退/定身系统（V1.0.4 P3）
    # ================================================================

    def is_staggered(self) -> bool:
        """是否处于定身状态"""
        return self.stagger_timer > 0

    def apply_stagger(self, duration: float) -> None:
        """
        应用定身效果（含免疫检查）。
        规则：每5秒任意实体最多获得一次定身效果，其余自动免疫。
        """
        if duration <= 0:
            return
        if self.stagger_immune_timer > 0:
            return  # 免疫期间
        self.stagger_timer = max(self.stagger_timer, duration)
        self.stagger_immune_timer = 5.0  # 触发免疫计时

    def apply_knockback(self, src_x: float, src_y: float, distance: float) -> None:
        """
        应用击退效果。
        src_x/src_y: 攻击来源坐标
        distance: 击退距离（像素，正值表示推开）
        """
        if distance <= 0:
            return
        dx = self.x - src_x
        dy = self.y - src_y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 0.1:
            # 攻击来源与目标重合，随机方向击退
            import random
            angle = random.uniform(0, 2 * 3.14159265)
            import math
            self.x += math.cos(angle) * distance
            self.y += math.sin(angle) * distance
        else:
            self.x += (dx / dist) * distance
            self.y += (dy / dist) * distance

    # ================================================================
    # 循伤索敌系统（V1.0.4 P3）
    # ================================================================

    def set_track_attacker(self, src_x: float, src_y: float, duration: float = 1.0) -> None:
        """
        设置循伤索敌：怪物遭受远程攻击且未识别玩家时，
        主动向攻击来源方向移动，索敌范围×1.5。
        """
        if self.aggro:
            return  # 已识别玩家，无需循伤
        if self.monster_type in ("head_boss", "final_boss"):
            return  # BOSS不受影响
        self.track_attacker_x = src_x
        self.track_attacker_y = src_y
        self.track_attacker_timer = duration

    def is_tracking_attacker(self) -> bool:
        """是否处于循伤索敌状态"""
        return self.track_attacker_timer > 0

    def get_current_detect_range(self) -> float:
        """获取当前索敌范围（循伤期间×1.5）"""
        if self.is_tracking_attacker():
            return self.base_detect_range * 1.5
        return self.base_detect_range
