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

    # 循伤索敌系统（V1.0.4 P3）
    track_attacker_timer: float = 0.0   # 循伤索敌持续时间
    track_attacker_x: float = 0.0       # 攻击来源X
    track_attacker_y: float = 0.0       # 攻击来源Y
    base_detect_range: float = MONSTER_DETECT_RANGE  # 原始索敌范围
    speed_boost_timer: float = 0.0      # 速度加成剩余时间（已锁定玩家时触发）

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


    # ================================================================
    # 循伤索敌系统（V1.0.4 P3）
    # ================================================================

    def set_track_attacker(self, src_x: float, src_y: float, duration: float = 1.0) -> None:
        """
        循伤索敌：怪物遭受远程攻击后：
        - 未锁定玩家：向攻击来源方向移动，索敌范围×1.5
        - 已锁定玩家：获得速度×1.5加成
        BOSS不受影响。
        """
        if self.monster_type in ("head_boss", "final_boss"):
            return
        if self.aggro:
            # 已锁定玩家 → 速度加成
            self.speed_boost_timer = duration
        else:
            # 未锁定玩家 → 向攻击来源移动
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

    def get_current_speed(self) -> float:
        """获取当前速度（速度加成期间×1.5）"""
        if self.speed_boost_timer > 0:
            return self.speed * 1.5
        return self.speed
