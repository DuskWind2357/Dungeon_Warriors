"""
Dungeon Warriors V1.0.5.12 — 怪物数据类（平衡性重做）
攻击范围、冷却时间、BOSS多阶段、召唤系统、击退定身、循伤索敌
"""

import pygame
from dataclasses import dataclass, field
from config import MONSTER_SPEED, MONSTER_DETECT_RANGE, TILE_SIZE


@dataclass
class Monster:
    """怪物实体 V1.0.5.8"""
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
    speed: float = MONSTER_SPEED
    alive: bool = True
    aggro: bool = False       # 是否已进入战斗状态

    # 攻击类型
    ranged_attacker: bool = False       # 是否为远程攻击怪物（骷髅）

    # 索敌范围
    detect_range: float = MONSTER_DETECT_RANGE  # 索敌范围（px）

    # BOSS 专属
    phase: int = 1                      # 阶段 (1 or 2)
    summon_timer: float = 0.0           # 召唤倒计时
    damage_reduction: float = 0.0       # 伤害减免（兼容旧代码）
    dr_ranged: float = 0.0              # 远程伤害减免
    dr_melee: float = 0.0               # 近战伤害减免
    ranged_immune: bool = False         # 远程免疫

    # 循伤索敌系统（V1.0.4 P3）
    track_attacker_timer: float = 0.0   # 循伤索敌持续时间
    track_attacker_x: float = 0.0       # 攻击来源X
    track_attacker_y: float = 0.0       # 攻击来源Y
    base_detect_range: float = MONSTER_DETECT_RANGE  # 原始索敌范围
    speed_boost_timer: float = 0.0      # 速度加成剩余时间（已锁定玩家时触发）

    # V1.0.5.8 状态效果属性
    wither: float = 0.0                 # 凋零持续时间（秒）
    frost: float = 0.0                  # 霜冻持续时间（秒）
    burn: float = 0.0                   # 燃烧持续时间（秒）
    burn_dmg: int = 0                   # 燃烧伤害

    # V1.0.5.8 精英/BOSS技能
    fireball: int = 0                   # 火球散射数量
    fire_interval: float = 0.0          # 火球散射间隔
    combo_hits: int = 1                 # 连击次数（暗黑骑士）
    combo_interval: float = 0.0         # 连击间隔

    # V1.0.5.9 首领伤害上限 / 锁血 / 技能状态
    dps_cap: float = 0.0                # 每秒承受最大伤害（0=不限制，仅首领使用）
    hit_cap: float = 0.0                # 单次承受最大伤害（0=不限制，仅首领使用）
    locked: bool = False                # 起死回生锁血（HP 最低保留 1，不会死亡）
    dr_bonus: float = 0.0               # 额外伤害减免（0~1，与基础减免叠加）
    _dmg_window_start: float = 0.0      # dps 滚动窗口起点（pygame 秒）
    _dmg_window_sum: float = 0.0        # 窗口内已承受伤害累计

    # V1.0.5.12 不可移动实体（宝箱/试炼刷怪笼）
    immobile: bool = False              # 是否不可移动
    spawn_timer: float = 0.0            # 召唤计时器（试炼刷怪笼专用）
    spawn_interval: float = 0.0         # 召唤间隔（秒，0=不召唤）
    ambient_timer: float = 0.0          # 环境音计时器（试炼刷怪笼专用）

    # V1.0.5.19 精英/首领技能冷却（所有怪物统一默认 0.0；
    # 首领号令等运行时召唤路径若不显式初始化，技能判断 monster.skill_cd 会 AttributeError 崩溃）
    skill_cd: float = 0.0

    def take_damage(self, damage: int, is_ranged: bool = False) -> bool:
        """受到伤害（含减免/单次上限/每秒上限/锁血），返回是否死亡"""
        # 计算伤害减免
        if is_ranged:
            reduction = self.dr_ranged
        else:
            reduction = self.dr_melee
        # 兼容旧代码的 damage_reduction
        reduction = max(reduction, self.damage_reduction)
        # V1.0.5.9: 额外减免（起死回生等）叠加并封顶
        reduction = min(1.0, reduction + self.dr_bonus)
        reduced = damage * (1 - reduction)

        # V1.0.5.9: 单次承受上限
        if self.hit_cap > 0:
            reduced = min(reduced, self.hit_cap)

        # V1.0.5.9: 每秒承受上限（1 秒滚动窗口）
        if self.dps_cap > 0:
            now = pygame.time.get_ticks() / 1000.0
            if now - self._dmg_window_start >= 1.0:
                self._dmg_window_start = now
                self._dmg_window_sum = 0.0
            if self._dmg_window_sum + reduced > self.dps_cap:
                reduced = max(0.0, self.dps_cap - self._dmg_window_sum)
            self._dmg_window_sum += reduced

        dmg_int = int(round(reduced))
        # V1.0.5.9: 起死回生锁血（HP 最低保留 1，不会死亡）
        if self.locked:
            self.hp = max(1, self.hp - dmg_int)
            return False

        self.hp = max(0, self.hp - dmg_int)
        if self.hp <= 0:
            self.alive = False
        return not self.alive

    def is_alive(self) -> bool:
        return self.alive and self.hp > 0

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0.0

    # ================================================================
    # BOSS 阶段管理（V1.0.5.8 更新）
    # ================================================================

    def check_phase_transition(self) -> bool:
        """
        检查并执行 BOSS 阶段转换（V1.0.5.9: 阶段属性按文档比例切换）。
        返回 True 表示阶段发生了变化。
        """
        if self.monster_type != "final_boss":
            return False

        hp_pct = self.hp_ratio

        # 三阶段（HP<25%）：30%近战减免 + 免疫远程 + 速度×(1.8/1.5)
        if hp_pct < 0.25 and self.phase == 2:
            self.phase = 3
            self.dr_melee = 0.30
            self.dr_ranged = 1.00
            self.ranged_immune = True
            self.speed = self.speed * (1.8 / 1.5)
            return True

        # 二阶段（HP<50%）：攻击×(15/12) 冷却×(1.0/1.2) 速度×(1.5/1.2) DR 40/20
        if hp_pct < 0.50 and self.phase == 1:
            self.phase = 2
            self.attack = round(self.attack * (15 / 12))
            self.attack_cooldown = self.attack_cooldown * (1.0 / 1.2)
            self.speed = self.speed * (1.5 / 1.2)
            self.dr_ranged = 0.40
            self.dr_melee = 0.20
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
