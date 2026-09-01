"""
Dungeon Warriors V1.0.5.21 — 战斗场景（核心玩法，平衡性重做）
V1.0.5 多房间楼层架构、墙壁传送门系统
"""

import math
import random
import pygame
from config import (
    TILE_SIZE, MAP_COLS, MAP_ROWS, FPS, SPAWN_DELAY_SEC,
    PLAYER_BASE_SPEED, GLOBAL_SPEED_MULT,
    PROJECTILE_SPEED, PROJECTILE_RANGE, PROJECTILE_SIZE,
    ENEMY_ARROW_SPEED, ENEMY_ARROW_RANGE,
    FIREBALL_SPEED, FIREBALL_RANGE,
    ICE_FIREBALL_SPEED, ICE_FIREBALL_RANGE,
    ICE_BOMB_SPEED, ICE_BOMB_RANGE,
    ENEMY_PROJECTILE_SPEED_MULT,
    MONSTER_DETECT_RANGE, MONSTER_SPEED, MONSTER_SPEED_SCALE,
    DIFFICULTY_MODIFIERS,
    DROP_NORMAL_POTION, DROP_NORMAL_BREAD,
    DROP_ELITE_POTION, DROP_ELITE_BREAD,
    DROP_BOSS_EQUIP, DROP_BOSS_BREAD, DROP_BOSS_POTION,
    BREAD_HEAL_PER_SEC, BREAD_HEAL_DURATION,
    COLOR_BG, COLOR_PROJECTILE,
    PORTAL_TRAVEL_DELAY, FLOOR_PORTAL_TRAVEL_DELAY,
    CHEST_DROP_EQUIP_WEIGHTS, CHEST_DROP_POTION_WEIGHTS, CHEST_DROP_BREAD_WEIGHTS,
    TRIAL_SPAWNER_DROP_POTIONS,
    TREASURE_ROOM_MAX_POTIONS, TREASURE_ROOM_EQUIP_MAX_TIER,
    SPECIAL_TREASURE_ROOM_MIN_POTIONS,
)
from entities.player import Player
from entities.monster import Monster
from entities.item import Weapon, Armor, Consumable, KeyItem
from systems.combat import (
    player_melee_attack, player_ranged_attack,
    projectile_hit_monster, move_toward, is_in_range, monster_attack_player,
)
from systems.inventory import add_item, consume_item
from systems.floor_manager import (
    generate_floor, spawn_monsters_for_room, spawn_monsters_boss,
    spawn_trial_spawner, spawn_trial_spawners, spawn_chests,
    get_floor_type, get_theme, place_traps, FloorLayout, Room, RoomType,
    head_boss_floor_boost,
)
from systems.pathfinding import astar, simplify_path, pixel_to_grid, grid_to_pixel, random_walkable
from systems.save_system import save_game
from systems.revive_system import ReviveSystem
from systems.audio_manager import AudioManager
from rendering.renderer import (
    draw_map, draw_player, draw_monster, draw_drops, draw_hud, draw_toast,
    draw_slash_effects, draw_v_slashes,
    draw_boss_hp_bar,
    get_bold_font,
    get_bold_hud_font,
)
from rendering.pixel_style import make_toast
from data.weapons import WEAPON_BY_NAME, WEAPON_BY_TYPE_TIER
from data.armor import ARMOR_BY_TIER
from data.consumables import BREAD, POTION_POOL
from data.keys import TREASURE_KEY
from data.monsters import (
    NORMAL_MONSTERS, ELITE_MONSTERS, SNOW_ELITE_MONSTERS,
    NATURAL_NORMAL, FINAL_BOSS, HEAD_BOSS_MELEE, HEAD_BOSS_RANGED,
    TRIAL_SPAWN_WEIGHTS,
)


# ================================================================
# V1.0.5.12 连击&战斗特效：近战武器连击系统（剑/斧/矛/匕首）
# 段参数: range(判定范围,格) / angle(扇形判定角,°) / mult(基础伤害倍率)
#         fx: ("arc", 颜色, 弧形跨度°) 原地弧形剑气 | ("v", 颜色, V形张角°) 向前飞行V形剑气
# 三叉戟沿用矛(spear)同一套机制, 唯一区别为基础伤害; 机械链锯维持过热机制不参与连击
# ================================================================
COMBO_RESET_SECONDS = 3.0       # 间隔 3 秒不攻击，连击段数自动重置
COMBO_TABLES = {
    # 剑: 三段, 段间0.2s, 无最终冷却
    "sword": {"interval": 0.2, "final_cd": 0.0, "stages": [
        {"range": 1.5, "angle": 75.0,  "mult": 1.0,        "fx": ("arc", (255, 255, 255), 75)},
        {"range": 1.5, "angle": 75.0,  "mult": 1.0,        "fx": ("arc", (255, 255, 255), 75)},
        {"range": 1.8, "angle": 100.0, "mult": 1.5,        "fx": ("v",   (255, 200, 0), 120)},
    ]},
    # 斧: 三段, 段间0.5s, 无最终冷却
    "axe": {"interval": 0.5, "final_cd": 0.0, "stages": [
        {"range": 1.8, "angle": 100.0, "mult": 1.0,        "fx": ("arc", (255, 255, 255), 100)},
        {"range": 1.8, "angle": 100.0, "mult": 1.0,        "fx": ("arc", (255, 255, 255), 100)},
        {"range": 2.0, "angle": 120.0, "mult": 5.0 / 3.0,  "fx": ("v",   (255, 200, 0), 120)},
    ]},
    # 矛: 三段连击(3次后进入冷却1.5s), 段间0.1s
    "spear": {"interval": 0.1, "final_cd": 1.5, "stages": [
        {"range": 2.5, "angle": 45.0,  "mult": 1.0,        "fx": ("v",   (255, 255, 255), 45)},
        {"range": 2.5, "angle": 45.0,  "mult": 1.0,        "fx": ("v",   (255, 255, 255), 45)},
        {"range": 3.0, "angle": 60.0,  "mult": 1.5,        "fx": ("v",   (255, 200, 0), 60)},
    ]},
    # 匕首: 五段连击(5次后进入冷却1.2s), 段间0.1s; 段1-4 白V45°, 段5 金弧90°
    "dagger": {"interval": 0.1, "final_cd": 1.2, "stages": [
        {"range": 1.0, "angle": 45.0,  "mult": 1.0,        "fx": ("v",   (255, 255, 255), 45)},
        {"range": 1.0, "angle": 45.0,  "mult": 1.0,        "fx": ("v",   (255, 255, 255), 45)},
        {"range": 1.0, "angle": 45.0,  "mult": 1.0,        "fx": ("v",   (255, 255, 255), 45)},
        {"range": 1.0, "angle": 45.0,  "mult": 1.0,        "fx": ("v",   (255, 255, 255), 45)},
        {"range": 1.5, "angle": 90.0,  "mult": 2.0,        "fx": ("arc", (255, 200, 0), 90)},
    ]},
}
CHAINSAW_FX = ("arc", (255, 200, 0), 90)   # 机械链锯: 每次攻击附加 90° 金色弧形剑气
V_SLASH_SPEED = 432.0           # V形剑气飞行速度 px/s（飞行时长 = 射程px / 速度）
V_SLASH_DURATION = 0.2          # V形剑气默认存活秒数（未指定 dur 时兜底）
SHAKE_POWER = 5.0               # 屏幕抖动强度(px)
SHAKE_DURATION = 0.18           # 屏幕抖动时长（秒）
FLASH_DURATION = 0.12           # 轻微闪烁时长（秒）

# 独特装备名称集合（拾取提示橙色显示 / 特殊宝藏房间独特装备判定）
UNIQUE_WEAPON_NAMES = {"三叉戟", "机械链锯", "精英之弓", "杀戮之弩", "机械弩", "幻术师之弓"}


class CombatScene:
    """战斗场景 v2.0"""

    def __init__(self, player: Player, backpack: list,
                 revive_system: ReviveSystem,
                 current_floor: int,
                 monsters_killed: int = 0,
                 audio_manager: AudioManager | None = None,
                 difficulty: str = "easy",
                 floor_layout_cache: dict | None = None,
                 auto_destroy: bool = False) -> None:
        self.player = player
        self.backpack = backpack
        self.revive_system = revive_system
        self.current_floor = current_floor
        self.monsters_killed = monsters_killed
        self.audio = audio_manager
        self.difficulty = difficulty
        self.player.difficulty = difficulty  # V1.0.5.10: 玩家成长参数随难度
        self.auto_destroy = auto_destroy

        # 楼层数据
        self.grid: list[list[int]] = []
        self.spawn_pos: tuple[int, int] = (0, 0)
        self.portal_pos: tuple[int, int] | None = None
        self.portal_active: bool = False
        self.in_spawn_zone: bool = True
        self.spawn_timer: float = -1.0
        self.monsters: list[Monster] = []
        self.drops: dict[int, list[tuple[object, float, float]]] = {}  # room_idx → drops
        self.projectiles: list[dict] = []
        self.slash_effects: list[dict] = []  # V1.0.5.11 近战弧形剑气特效
        self.v_slashes: list[dict] = []      # V1.0.5.12 补丁: V形剑气（向前飞行）
        self._attack_held: bool = False      # V1.0.5.12 连击&战斗特效: 长按左键自动连续近战攻击
        self._shake_timer: float = 0.0       # V1.0.5.12 补丁: 屏幕抖动剩余时间（秒）
        self._shake_power: float = 0.0       # V1.0.5.12 补丁: 屏幕抖动强度(px)
        self._flash_timer: float = 0.0       # V1.0.5.12 补丁: 屏幕轻微闪烁剩余时间（秒）

        # V1.0.5 多房间系统
        self.floor_layout: FloorLayout | None = None
        self.current_room: Room | None = None
        self.room_monsters: dict[int, list[Monster]] = {}
        self.room_cleared: dict[int, bool] = {}
        self._room_spawned: dict[int, bool] = {}
        self._portal_timer: float = -1.0
        self._portal_target = None
        self._portal_proximity_sound_playing: bool = False
        self._floor_portal_timer: float = -1.0

        # 战斗状态
        self.toasts: list[dict] = []
        self._spawn_toast: dict | None = None
        self._portal_countdown: dict | None = None
        self._portal_toast: dict | None = None
        self._portal_hint: dict | None = None  # 传送门提示
        self._unlock_block_travel: bool = False  # V1.0.5.6 解锁当帧阻止按住F直接传送
        self._floor_clear_toast_shown: bool = False  # 楼层通关提示是否已显示
        self.floor_type: str = "battle"
        self._heal_frac: float = 0.0
        self._burn_frac: float = 0.0

        # 暂停菜单状态
        self._paused: bool = False
        self._pause_confirm_reset: bool = False
        self._reset_countdown: float = -1.0
        self._melee_last_used_time: float = 0.0
        self._ranged_last_used_time: float = 0.0   # 远程武器最后出招时间（机械弩过热计数 3 秒重置用）
        self._last_esc_time: float = 0.0
        self._floor_clearing: bool = False

        # V1.0.5 楼层布局缓存（跨场景持久化，解决地图锁定问题）
        self._floor_layout_cache: dict[int, tuple[FloorLayout, dict[int, bool]]] = floor_layout_cache if floor_layout_cache is not None else {}
        self._current_bgm_key: str | None = None   # V1.0.5.10 当前播放的楼层BGM key（去重用）

        self._init_floor()

    def _init_floor(self) -> None:
        self.floor_type = get_floor_type(self.current_floor)

        # 同步玩家当前楼层
        self.player.current_floor = self.current_floor

        # 清除战斗 buff（力量/隐身/迅捷进新楼层失效）
        for key in list(self.player.buffs.keys()):
            if key != "heal_over_time":
                del self.player.buffs[key]

        # 重置武器冷却和过热计数
        self.player.attack_cooldown = 0.0
        self.player.ranged_cooldown = 0.0
        if hasattr(self.player, '_overheat_cnt'): self.player._overheat_cnt = 0
        if hasattr(self.player, '_ranged_overheat_cnt'): self.player._ranged_overheat_cnt = 0

        # HP 自动回满
        self.player.heal_full()

        # V1.0.5 根据楼层类型生成地图
        # V1.0.5.6：BOSS楼层同为多房间架构（出生点+分支），统一走多房间生成
        if self.current_floor in self._floor_layout_cache:
            # V1.0.5.17: 仅保留地图结构（布局/陷阱格），房间清怪状态全部重置刷新——
            # 中途返回主菜单再继续（或同楼层复活重建场景）时，怪物/宝箱/刷怪笼/掉落
            # 全部重新生成，不再恢复旧的 room_cleared（修复出生点房倒计时结束不刷怪 BUG26）
            self.floor_layout, _ = self._floor_layout_cache[self.current_floor]
            self.room_cleared = {}
            self._floor_layout_cache[self.current_floor] = (self.floor_layout, self.room_cleared)
        else:
            self.floor_layout = generate_floor(self.current_floor, difficulty=self.difficulty)
            self.room_cleared = {}
            self._floor_layout_cache[self.current_floor] = (self.floor_layout, self.room_cleared)

        self.current_room = self.floor_layout.current_room
        self.grid = self.current_room.grid
        self.spawn_pos = self.current_room.spawn_pos

        # 初始化房间怪物状态
        self.room_monsters = {}
        self._room_spawned = {}
        for room in self.floor_layout.rooms:
            self.room_monsters[room.room_idx] = []
            self._room_spawned[room.room_idx] = False

        self.portal_active = False
        self._floor_clearing = False
        self._floor_clear_toast_shown = False
        self._trap_timer = 0.0

        # 出生点
        self.in_spawn_zone = True
        self.spawn_timer = -1.0

        self.player.x = self.spawn_pos[0] * TILE_SIZE + TILE_SIZE // 2
        self.player.y = self.spawn_pos[1] * TILE_SIZE + TILE_SIZE // 2
        self.player.facing_angle = 0.0

        # 延迟刷新：怪物先不生成
        self.monsters = []
        self.drops.clear()
        self.projectiles.clear()

        # V1.0.5 传送门状态重置
        self._portal_timer = -1.0
        self._portal_target = None
        self._portal_proximity_sound_playing = False
        self._floor_portal_timer = -1.0
        self._unlock_block_travel = False

        # V1.0.5 地狱陷阱（进入对应房间时布置; V1.0.5.14: 修复传送后陷阱不生效）
        self._ensure_traps_for_room(self.current_room)

        # V1.0.5.10 按楼层切换 BGM
        self._update_floor_bgm()

    def _ensure_traps_for_room(self, room) -> None:
        """V1.0.5 地狱陷阱：地狱主题(21-29层)房间首次进入时布置
        （10% 可行走地砖置为值4; 幂等——已布置过的房间不重复布置）
        V1.0.5.14 修复: 原仅在 _init_floor 调用一次，传送进入战斗房间时陷阱从未放置
        V1.0.5.16: 副本房间/宝藏室/特殊宝藏室不生成陷阱
        """
        if (room is None or self.current_floor < 21
                or self.floor_type in ("boss", "final_boss")):
            return
        if room.room_type in (RoomType.DUNGEON, RoomType.TREASURE,
                              RoomType.SPECIAL_TREASURE):
            return
        if getattr(room, '_traps_placed', False):
            return
        place_traps(room)
        room._traps_placed = True

    def _current_floor_bgm_key(self) -> str | None:
        """V1.0.5.11 音乐播放规则: BOSS楼层非BOSS房间→boss_floor,
        头目BOSS房间→head_boss_room, 首领BOSS房间→final_boss_room, 其余按主题"""
        if self.floor_type == 'final_boss':
            if self.current_room and self.current_room.room_type == RoomType.BOSS_BATTLE:
                return 'final_boss_room'
            return 'boss_floor'
        if self.floor_type == 'boss':
            if self.current_room and self.current_room.room_type == RoomType.BOSS_BATTLE:
                return 'head_boss_room'
            return 'boss_floor'
        return get_theme(self.current_floor)

    def _update_floor_bgm(self) -> None:
        """V1.0.5.10: 按楼层切换 BGM（播放/停止, 同 key 去重不重复触发）"""
        if not self.audio:
            return
        bgm_key = self._current_floor_bgm_key()
        if bgm_key == self._current_bgm_key:
            return
        self._current_bgm_key = bgm_key
        if bgm_key is not None:
            self.audio.play_floor_bgm(bgm_key)
        else:
            self.audio.stop_bgm()

    def _spawn_monsters_for_current_room(self) -> None:
        """为当前房间生成怪物"""
        if not self.current_room:
            return
        room_idx = self.current_room.room_idx

        # 副本房间：生成试炼刷怪笼（V1.0.5.18 起高楼层可多个）
        if self.current_room.room_type == RoomType.DUNGEON:
            if not self.room_cleared.get(room_idx, False):
                spawners = spawn_trial_spawners(self.current_room, self.current_floor,
                                                difficulty=self.difficulty)
                if spawners:
                    self.room_monsters[room_idx] = spawners
                    self.monsters = list(spawners)
                    for sp in spawners:
                        sp.skill_cd = 0.0
            return

        # 宝藏室与特殊宝藏室：生成宝箱 + 地面物品
        if self.current_room.room_type in (RoomType.TREASURE, RoomType.SPECIAL_TREASURE):
            if not self.room_cleared.get(room_idx, False):
                chests = spawn_chests(self.current_room)
                self.room_monsters[room_idx] = chests
                self.monsters = list(chests)
                for c in chests:
                    c.skill_cd = 0.0
                self._spawn_treasure_ground_items(self.current_room)
            return

        from config import DIFFICULTY_MODIFIERS
        mod = DIFFICULTY_MODIFIERS.get(self.difficulty, {})

        room_idx = self.current_room.room_idx
        if self.current_room.room_type == RoomType.BOSS_BATTLE:
            # V1.0.5.6 BOSS战房间：头目楼层2名BOSS / 首领楼层高塔之主
            if not self.room_cleared.get(room_idx, False):
                monsters = spawn_monsters_boss(
                    self.current_room,
                    self.floor_type, self.current_floor,
                    difficulty=self.difficulty,
                )
                self.room_monsters[room_idx] = monsters
                self.monsters = list(monsters)
                # BOSS 登场音效
                if self.audio:
                    self.audio.play_boss_appear()
        elif not self.room_cleared.get(room_idx, False):
            # V1.0.5.8 为当前房间生成怪物（平衡性重做）
            # V1.0.5.17: room_cleared 在场景重建时已全部重置（_init_floor），此处恢复原始判定
            monsters = spawn_monsters_for_room(
                self.current_room,
                self.current_floor, difficulty=self.difficulty,
            )
            self.room_monsters[room_idx] = monsters
            self.monsters = list(monsters)

        # V1.0.5.8: 难度修饰已在 floor_manager 中处理（怪物生成时应用缩放）
        # 仅保留旧代码兼容：skill_cd 初始化
        for m in self.monsters:
            m.skill_cd = 0.0

    # ================================================================
    # 事件
    # ================================================================

    def handle_event(self, event: pygame.event.Event) -> str | None:
        # 暂停菜单事件处理（V1.0.4 P3）
        if self._paused:
            return self._handle_pause_event(event)

        # 楼层重置倒计时期间，禁止ESC退出（V1.0.4 P3）
        if self._reset_countdown > 0:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # ESC防抖：0.3秒内不重复触发
                now = pygame.time.get_ticks() / 1000.0
                if now - self._last_esc_time < 0.3:
                    return None
                self._last_esc_time = now
                # 打开暂停菜单
                self._paused = True
                self._pause_confirm_reset = False
                return None
            if event.key == pygame.K_b:
                return "backpack"
            if event.key == pygame.K_e:
                self._pickup_item()
            # 快捷键 1-5: 快速使用消耗品
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                self._quick_use(event.key)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._attack_held = True  # V1.0.5.12 连击&战斗特效: 长按左键自动连续近战攻击
                result = self._player_attack()
                if result:
                    return result
            elif event.button == 3:
                self._player_ranged_fire()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._attack_held = False

        return None

    def _handle_pause_event(self, event: pygame.event.Event) -> str | None:
        """暂停菜单事件处理"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # ESC防抖：0.3秒内不重复触发
                now = pygame.time.get_ticks() / 1000.0
                if now - self._last_esc_time < 0.3:
                    return None
                self._last_esc_time = now
                # ESC关闭暂停菜单
                self._paused = False
                self._pause_confirm_reset = False
                return None

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            screen_center_x = 960 // 2

            if self._pause_confirm_reset:
                # 确认弹窗按钮
                btn_y_yes = 400
                btn_y_no = 460
                btn_width = 200
                btn_height = 40

                # 是按钮
                if (screen_center_x - btn_width // 2 <= mx <= screen_center_x + btn_width // 2
                    and btn_y_yes <= my <= btn_y_yes + btn_height):
                    # 确认楼层重置
                    self._paused = False
                    self._pause_confirm_reset = False
                    self._reset_countdown = 3.0  # 开始3秒倒计时
                    # 消耗一条生命（对应复活次数）
                    if self.revive_system.revive_count > 0:
                        self.revive_system.revive_count -= 1
                    return None

                # 否按钮
                if (screen_center_x - btn_width // 2 <= mx <= screen_center_x + btn_width // 2
                    and btn_y_no <= my <= btn_y_no + btn_height):
                    self._pause_confirm_reset = False
                    return None
            else:
                # 暂停菜单按钮
                btn_y_return = 300
                btn_y_reset = 370
                btn_y_continue = 440
                btn_width = 250
                btn_height = 50

                # 返回主菜单
                if (screen_center_x - btn_width // 2 <= mx <= screen_center_x + btn_width // 2
                    and btn_y_return <= my <= btn_y_return + btn_height):
                    self._paused = False
                    save_game(self.player, self.backpack, self.revive_system,
                              self.current_floor, self.monsters_killed,
                              auto_destroy=getattr(self, 'auto_destroy', False),
                              difficulty=self.difficulty)
                    return "menu"

                # 楼层重置
                if (screen_center_x - btn_width // 2 <= mx <= screen_center_x + btn_width // 2
                    and btn_y_reset <= my <= btn_y_reset + btn_height):
                    self._pause_confirm_reset = True
                    return None

                # 继续游戏
                if (screen_center_x - btn_width // 2 <= mx <= screen_center_x + btn_width // 2
                    and btn_y_continue <= my <= btn_y_continue + btn_height):
                    self._paused = False
                    return None

        return None

    def _player_attack(self) -> str | None:
        """左键攻击，自动朝向鼠标方向; 击杀高塔之主时返回 "victory" """
        # 更新朝向为鼠标方向
        mx, my = pygame.mouse.get_pos()
        self.player.facing_angle = math.atan2(my - self.player.y, mx - self.player.x)
        if self.player.melee_weapon:
            return self._do_melee_attack()
        elif self.player.ranged_weapon:
            self._player_ranged_fire()
        return None

    def _do_melee_attack(self) -> str | None:
        """近战攻击; 击杀高塔之主时返回 "victory"（V1.0.5.9 即时通关）
        V1.0.5.12 连击&战斗特效: 剑/斧/矛/匕首走连击段表（三叉戟沿用矛机制）;
        机械链锯维持过热机制, 每次攻击附加 90° 金色弧形剑气
        """
        _w = self.player.melee_weapon
        if (_w is not None and _w.category == "melee"
                and _w.weapon_type in COMBO_TABLES
                and getattr(_w, "overheat_count", 0) == 0):
            return self._do_combo_attack(_w.weapon_type)
        # 过热武器（机械链锯）及其他近战: 原攻击路径 + 弧形剑气
        _w = self.player.melee_weapon
        if (_w is not None and _w.category == "melee"
                and self.player.attack_cooldown <= 0
                and self.player.total_melee_attack() > 0):
            if getattr(_w, "overheat_count", 0) > 0:
                _fx_kind, _fx_color, _fx_span = CHAINSAW_FX  # 链锯: 90°金色剑气
            else:
                _fx_kind, _fx_color, _fx_span = "arc", (255, 255, 255), 120
            _reach = (_w.attack_range * TILE_SIZE) if getattr(_w, "attack_range", 0) else TILE_SIZE * 1.5
            self.slash_effects.append({
                'x': self.player.x, 'y': self.player.y,
                'angle': self.player.facing_angle,
                'radius': max(TILE_SIZE, _reach * 0.85),
                'span_deg': _fx_span,
                'color': _fx_color,
                't': 0.0,
            })
            # 有效出招即刷新近战计时（含机械链锯：过热计数器 3 秒未攻击自动清零）
            self._melee_last_used_time = 0.0
        hit_monsters = player_melee_attack(self.player, self.monsters)
        # 机械链锯过热提示（_overheat_msg 由近战过热分支置位, 出招后立即消费）
        if getattr(self.player, '_overheat_msg', False):
            self.toasts.append(make_toast('锯刃过热！'))
            self.player._overheat_msg = False
        if not hit_monsters:
            return None
        # 更新近战最后使用时间（V1.0.4 P3 连击归零）
        self._melee_last_used_time = 0.0
        return self._process_melee_hits(hit_monsters)

    def _trigger_shake_flash(self) -> None:
        """V1.0.5.12 连击&战斗特效: 触发屏幕抖动 + 轻微闪烁
        （连击最终段 / 任意暴击 / 幻术师之弓多重箭 / 杀戮之弩斩杀）
        """
        self._shake_timer = SHAKE_DURATION
        self._shake_power = SHAKE_POWER
        self._flash_timer = FLASH_DURATION

    def _process_melee_hits(self, hit_monsters: list, mult: float = 1.0) -> str | None:
        """近战命中处理: 暴击(触发屏抖/闪烁)/吸血/音效/击杀
        击杀高塔之主时返回 "victory"（V1.0.5.9 即时通关）
        """
        armor = self.player.armor
        crit_mult = 1.0
        if armor and armor.crit_chance > 0 and random.random() < armor.crit_chance:
            crit_mult = armor.crit_mult
            self.toasts.append(make_toast('暴击！'))
            self._trigger_shake_flash()  # V1.0.5.12 连击&战斗特效: 任意暴击触发
            if self.audio: self.audio.play_crit()
        lifesteal = armor.lifesteal if armor else 0
        for monster in hit_monsters:
            if crit_mult > 1.0:
                extra_dmg = round(self.player.total_melee_attack() * mult * (crit_mult - 1))
                monster.take_damage(extra_dmg)
            if lifesteal > 0 and self.player.can_heal():
                dmg = self.player.total_melee_attack() * mult * crit_mult
                heal = round(dmg * lifesteal)
                if heal > 0:
                    self.player.current_hp = min(self.player.total_max_hp(),
                                                  self.player.current_hp + heal)
            self._play_hit_sound(monster)
            if not monster.is_alive():
                result = self._on_monster_killed(monster)
                if result:
                    return result
        return None

    def _do_combo_attack(self, table_key: str) -> str | None:
        """V1.0.5.12 连击&战斗特效: 近战武器连击系统（剑/斧/矛/匕首 通用）
        按 COMBO_TABLES[table_key] 段表依次出招:
        - 每段: 伤害 = 等级基础伤害 × 段倍率; 判定范围/角度按段表
        - fx "arc": 原地弧形剑气; fx "v": V形剑气沿攻击方向向前飞行（开口朝向玩家）
        - 段间冷却 interval; 最终段: 屏幕抖动+轻微闪烁, 段数归零,
          矛/匕首等有 final_cd 的武器进入最终冷却
        - 间隔 COMBO_RESET_SECONDS(3秒) 不攻击, 段数自动重置
        """
        table = COMBO_TABLES[table_key]
        if self.player.attack_cooldown > 0:
            return None
        if self.player.total_melee_attack() <= 0:
            return None

        stages = table["stages"]
        n = len(stages)
        # 当前段数（1..N；0或越界视为第1段）
        stage = self.player.melee_stage if 1 <= self.player.melee_stage <= n else 1
        spec = stages[stage - 1]

        # 更新朝向为鼠标方向
        mx, my = pygame.mouse.get_pos()
        self.player.facing_angle = math.atan2(my - self.player.y, mx - self.player.x)

        fx_kind, fx_color, fx_span = spec["fx"]
        if fx_kind == "v":
            # V形剑气: 沿攻击方向向前飞行, 飞行时长随射程缩放
            reach_px = spec["range"] * TILE_SIZE
            self.v_slashes.append({
                "x": self.player.x, "y": self.player.y,
                "vx": math.cos(self.player.facing_angle),
                "vy": math.sin(self.player.facing_angle),
                "angle": self.player.facing_angle,
                "t": 0.0,
                "span_deg": fx_span,
                "color": fx_color,
                "dur": max(0.1, reach_px / V_SLASH_SPEED),
            })
        else:
            # 弧形剑气（原地挥砍, 快速淡出）
            reach = spec["range"] * TILE_SIZE
            self.slash_effects.append({
                'x': self.player.x, 'y': self.player.y,
                'angle': self.player.facing_angle,
                'radius': max(TILE_SIZE, reach * 0.85),
                'span_deg': fx_span,
                'color': fx_color,
                't': 0.0,
            })

        hit_monsters = player_melee_attack(
            self.player, self.monsters,
            stage_mult=spec["mult"],
            override_range=spec["range"],
            fan_angle_deg=spec["angle"],
            manage_cooldown=False,
        )

        # 段间冷却 / 最终段冷却; 最终段触发屏抖闪烁并归零段数
        if stage == n:
            self._trigger_shake_flash()
            self.player.melee_stage = 0
            self.player.attack_cooldown = (table["final_cd"]
                                           if table["final_cd"] > 0
                                           else table["interval"])
        else:
            self.player.melee_stage = stage + 1
            self.player.attack_cooldown = table["interval"]
        self._melee_last_used_time = 0.0

        if not hit_monsters:
            return None
        return self._process_melee_hits(hit_monsters, spec["mult"])

    def _player_ranged_fire(self) -> None:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        projs = player_ranged_attack(self.player, mouse_x, mouse_y)
        if projs:
            # 实际发射即刷新远程计时（机械弩过热计数器 3 秒未攻击自动清零）
            self._ranged_last_used_time = 0.0
            for proj in projs:
                self.projectiles.append(proj)
            # 多重箭提示（幻术师之弓）: 触发屏幕抖动+轻微闪烁 + 暴击音效
            if len(projs) > 1:
                self.toasts.append(make_toast('多重箭！'))
                self._trigger_shake_flash()
            if self.audio:
                self.audio.play_projectile('骷髅')
            # 机械弩过热提示（机械链锯提示在近战出招后消费）
            if getattr(self.player, '_ranged_overheat_msg', False):
                self.toasts.append(make_toast('机械弩过热！'))
                self.player._ranged_overheat_msg = False

    def _play_hit_sound(self, monster: Monster) -> None:
        if self.audio:
            self.audio.play_hit(monster.name)

    def _play_death_sound(self, monster: Monster) -> None:
        if self.audio:
            self.audio.play_death(monster.name)

    # ================================================================
    # 更新
    # ================================================================

    def update(self, dt: float) -> str | None:
        # 暂停菜单期间不更新游戏逻辑（V1.0.4 P3）
        if self._paused:
            return None

        # 楼层重置倒计时（V1.0.4 P3）
        if self._reset_countdown > 0:
            self._reset_countdown -= dt
            if self._reset_countdown <= 0:
                self._reset_countdown = -1.0
                # 手动重置时清除当前楼层缓存，重新生成地图
                if self.current_floor in self._floor_layout_cache:
                    del self._floor_layout_cache[self.current_floor]
                self._init_floor()
                self.toasts.append(make_toast("楼层已刷新！"))
            return None

        # 循伤索敌计时器更新（V1.0.4 P3）
        for m in self.monsters:
            if m.is_alive():
                m.track_attacker_timer = max(0, m.track_attacker_timer - dt)
                m.speed_boost_timer = max(0, m.speed_boost_timer - dt)

        # 冷却（秒）
        if self.player.attack_cooldown > 0:
            self.player.attack_cooldown = max(0, self.player.attack_cooldown - dt)
        if self.player.ranged_cooldown > 0:
            self.player.ranged_cooldown = max(0, self.player.ranged_cooldown - dt)
        for m in self.monsters:
            if m.cooldown_remaining > 0:
                m.cooldown_remaining = max(0, m.cooldown_remaining - dt)

        # 连击/过热计数归零（V1.0.4 P3 / V1.0.5.12）: 3秒未攻击自动重置
        # - 近战：连击段数（剑/斧/矛/匕首）、combo_counter、机械链锯过热计数 _overheat_cnt
        # - 远程：机械弩过热计数 _ranged_overheat_cnt
        self._melee_last_used_time += dt
        self._ranged_last_used_time += dt
        if self._melee_last_used_time >= COMBO_RESET_SECONDS:
            if self.player.combo_counter > 0:
                self.player.combo_counter = 0
            # V1.0.5.12 连击&战斗特效: 3秒未攻击连击段数自动重置（剑/斧/矛/匕首）
            if getattr(self.player, 'melee_stage', 0) > 0:
                self.player.melee_stage = 0
            # 机械链锯过热计数清零
            if getattr(self.player, '_overheat_cnt', 0):
                self.player._overheat_cnt = 0
        if self._ranged_last_used_time >= COMBO_RESET_SECONDS:
            # 机械弩过热计数清零
            if getattr(self.player, '_ranged_overheat_cnt', 0):
                self.player._ranged_overheat_cnt = 0

        # Buff
        self._update_buffs(dt)

        # 陷阱（地狱主题）
        self._update_traps(dt)

        # Toasts 倒计时
        for t in self.toasts:
            t["timer"] -= dt
        self.toasts = [t for t in self.toasts if t["timer"] > 0]

        # 移动
        self._handle_movement(dt)

        # 出生点
        self._check_spawn_zone(dt)

        # V1.0.5.12 连击&战斗特效: 长按左键自动连续近战攻击
        # （远程为右键单发, 无按住连射; 松开/失焦自动停止; 冷却由连击系统节流）
        if self._attack_held:
            if not pygame.mouse.get_pressed()[0]:
                self._attack_held = False
            elif self.player.melee_weapon:
                result = self._player_attack()
                if result:
                    return result

        # 投射物（V1.0.5.9: 击杀高塔之主即时通关）
        result = self._update_projectiles()
        if result:
            return result

        # V1.0.5.11 近战剑气特效
        self._update_slash_effects(dt)

        # V1.0.5.12 补丁: V形剑气 / 屏幕抖动 / 轻微闪烁
        self._update_sword_slashes(dt)
        self._shake_timer = max(0.0, self._shake_timer - dt)
        self._flash_timer = max(0.0, self._flash_timer - dt)

        # 怪物
        self._update_monsters(dt)

        # 传送门（V1.0.5.6：BOSS楼层同为多房间架构，统一走多房间传送门系统）
        result = self._update_portals(dt)
        if result:
            return result

        if not self.player.is_alive():
            return "death"
        return None

    def _update_buffs(self, dt: float) -> None:
        # 面包 HoT（凋零期间不生效）
        hot = self.player.buffs.get("heal_over_time", 0)
        if hot > 0 and self.player.can_heal():
            max_hp = self.player.total_max_hp(self.current_floor)
            if self.player.current_hp < max_hp:
                self._heal_frac += max_hp * BREAD_HEAL_PER_SEC * dt
                whole = int(self._heal_frac)
                if whole > 0:
                    self._heal_frac -= whole
                    self.player.current_hp = min(max_hp, self.player.current_hp + whole)
        else:
            self._heal_frac = 0.0

        # 燃烧 DOT（分数累加器）V1.0.5.8: 使用等级系统
        burn = self.player.status_effects.get("burn", 0)
        if burn > 0:
            burn_dmg = self.player.get_burn_damage()  # V1.0.5.8: 按等级计算伤害
            self._burn_frac += burn_dmg * dt
            whole = int(self._burn_frac)
            if whole > 0:
                self._burn_frac -= whole
                self.player.current_hp = max(0, self.player.current_hp - whole)
            # 燃烧音效每秒一次
            self._burn_audio_timer = round(getattr(self, '_burn_audio_timer', 0) + dt, 2)
            if self._burn_audio_timer >= 1.0:
                self._burn_audio_timer = 0
                if self.audio: self.audio.play_player_burn_tick()
        else:
            self._burn_audio_timer = 0

        self.player.update_buffs(dt)

    def _update_traps(self, dt: float) -> None:
        """地狱陷阱：踩上每秒扣 5 点固定生命（无视减伤），每秒播放一次燃烧音效"""
        col, row = pixel_to_grid(self.player.x, self.player.y)
        on_trap = (0 <= row < len(self.grid) and 0 <= col < len(self.grid[0])
                   and self.grid[row][col] == 4)
        if not on_trap or not self.player.is_alive():
            self._trap_timer = 0.0
            return
        self._trap_timer += dt
        if self._trap_timer >= 1.0:
            self._trap_timer -= 1.0
            self.player.current_hp = max(0, self.player.current_hp - 5)
            # V1.0.5.16: 踩陷阱每秒播放一次燃烧音效（燃烧buff生效时由 _update_buffs 统一播放，避免重叠）
            if self.audio and not self.player.has_status('burn'):
                self.audio.play_player_burn_tick()

    def _update_portals(self, dt: float) -> str | None:
        """V1.0.5 更新传送门交互逻辑（房间间传送）"""
        if not self.floor_layout or not self.current_room:
            return None

        # 检查玩家是否紧靠传送门
        col, row = pixel_to_grid(self.player.x, self.player.y)
        nearby_portal = self._check_portal_proximity(col, row)

        # 检查是否站在传送门上（自动检测F键）
        standing_on_portal = None
        for portal in self.current_room.portals:
            if portal.is_floor_portal:
                continue
            px, py = self.current_room._portal_grid_pos(portal)
            if (col, row) == (px, py):
                standing_on_portal = portal
                break

        active_portal = nearby_portal or standing_on_portal

        # 解锁阻断：F键松开时清除（解锁当帧不允许按住F直接传送）
        if not pygame.key.get_pressed()[pygame.K_f]:
            self._unlock_block_travel = False

        # V1.0.5.6 传送门准入检查（宝藏室/BOSS战房间封印、特殊宝藏室上锁）
        if active_portal:
            target_room = self.floor_layout.get_room_by_idx(active_portal.target_room_idx)
            if target_room and target_room.room_type == RoomType.TREASURE:
                # 检查当前房间是否已清理
                if not self.room_cleared.get(self.current_room.room_idx, False):
                    # 未完成战斗，宝藏室传送门被封印
                    self._portal_hint = make_toast("传送门已被封印！", color=(255, 60, 60))
                    self._block_portal_use()
                    return None
            elif target_room and target_room.room_type == RoomType.BOSS_BATTLE:
                # 需清空出生点与全部增强战斗房间，方可进入BOSS战房间
                if not self._boss_room_reachable():
                    self._portal_hint = make_toast("传送门已被封印！", color=(255, 60, 60))
                    self._block_portal_use()
                    return None
            elif (target_room and target_room.room_type == RoomType.SPECIAL_TREASURE
                    and not target_room.unlocked):
                # 特殊宝藏室：需BOSS战掉落的钥匙解锁
                has_key = any(isinstance(s, KeyItem) for s in self.backpack)
                if has_key:
                    self._portal_hint = make_toast("按F键解锁", color=(200, 100, 255))
                    if pygame.key.get_pressed()[pygame.K_f]:
                        self._unlock_special_treasure(target_room)
                    return None
                self._portal_hint = make_toast("传送门已上锁！", color=(255, 60, 60))
                self._block_portal_use()
                return None

        # 显示传送门提示（普通传送门和已解锁的宝藏室传送门都可交互）
        if active_portal and not active_portal.is_floor_portal:
            if self._portal_timer < 0:
                # 显示紫色提示"按F键传送"
                self._portal_hint = make_toast("按F键传送", color=(200, 100, 255))
            else:
                # 显示绿色传送倒计时
                sec = max(1, int(PORTAL_TRAVEL_DELAY) - int(self._portal_timer))
                self._portal_hint = make_toast(f"{sec} 秒后传送......", color=(100, 255, 100))
        else:
            self._portal_hint = None

        if active_portal:
            if not self._portal_proximity_sound_playing and self.audio:
                self.audio.play_portal_proximity()
                self._portal_proximity_sound_playing = True
        else:
            self._portal_proximity_sound_playing = False
            if self._portal_timer >= 0:
                self._portal_timer = -1.0
                self._portal_target = None
                self._portal_countdown = None

        # 处理F键传送（房间间传送门，包括已解锁的宝藏室/特殊宝藏室传送门）
        if (active_portal and not active_portal.is_floor_portal
                and not self._unlock_block_travel
                and pygame.key.get_pressed()[pygame.K_f]):
            if self._portal_timer < 0:
                self._portal_timer = 0.0
                self._portal_target = active_portal
                if self.audio:
                    self.audio.play_portal_trigger()

        # 更新传送倒计时
        if self._portal_timer >= 0 and self._portal_target:
            self._portal_timer += dt

            if self._portal_timer >= PORTAL_TRAVEL_DELAY:
                # 先完成传送，再重置状态
                self._complete_portal_travel()
                self._portal_timer = -1.0
                self._portal_target = None
                self._portal_hint = None
                self._portal_countdown = None

        # 检查通往下一楼层的传送门（需要站在上面+楼层已清）
        if (self.floor_layout and self.floor_layout.floor_portal_pos is not None
                and self.floor_layout.floor_portal_room_idx is not None
                and self.current_room is not None
                and self.current_room.room_idx == self.floor_layout.floor_portal_room_idx
                and not self._floor_clearing):
            if self._is_floor_cleared():
                # 通关后传送门常开（不再因玩家离开而关闭）
                self.portal_active = True

                fpx, fpy = self.floor_layout.floor_portal_pos
                dist = math.sqrt((self.player.x - (fpx * TILE_SIZE + TILE_SIZE // 2))**2 +
                               (self.player.y - (fpy * TILE_SIZE + TILE_SIZE // 2))**2)
                if dist < TILE_SIZE * 1.5:
                    empty = sum(1 for s in self.backpack if s is None)
                    if empty <= 1:
                        msg = "背包已满，无法传送！" if empty == 0 else "背包将满，无法传送！"
                        self._portal_toast = make_toast(msg)
                        self._floor_portal_timer = -1
                    else:
                        self._portal_toast = None
                        if self._floor_portal_timer < 0:
                            self._floor_portal_timer = 0.0
                        self._floor_portal_timer = round(self._floor_portal_timer + dt, 2)
                        sec = max(1, int(FLOOR_PORTAL_TRAVEL_DELAY) - int(self._floor_portal_timer))
                        self._portal_countdown = make_toast(f"{sec} 秒后传送至下一楼层......")
                        if self._floor_portal_timer >= FLOOR_PORTAL_TRAVEL_DELAY:
                            self._floor_portal_timer = -1
                            self._portal_countdown = None
                            self._floor_clearing = True
                            result = self._on_floor_clear()
                            return result
                else:
                    self._floor_portal_timer = -1
                    self._portal_countdown = None
            else:
                self.portal_active = False

        return None

    def _block_portal_use(self) -> None:
        """封印/上锁传送门：中断进行中的传送并停止接近音效"""
        self._portal_proximity_sound_playing = False
        if self._portal_timer > 0:
            self._portal_timer = -1.0
            self._portal_target = None
            self._portal_countdown = None

    def _boss_room_reachable(self) -> bool:
        """V1.0.5.6 BOSS战房间解锁条件：出生点与全部增强战斗房间已清空"""
        if not self.floor_layout:
            return False
        for room in self.floor_layout.rooms:
            if room.room_type in (RoomType.SPAWN, RoomType.ENHANCED_BATTLE):
                if not self.room_cleared.get(room.room_idx, False):
                    return False
        return True

    def _unlock_special_treasure(self, room: Room) -> None:
        """V1.0.5.6 消耗钥匙解锁特殊宝藏房间（解锁后与普通传送门同一套音效和交互）"""
        if room.unlocked:
            return
        if not consume_item(self.backpack, TREASURE_KEY):
            return
        room.unlocked = True
        self._unlock_block_travel = True
        self._portal_hint = None
        if self.audio:
            self.audio.play_unlock()  # V1.0.5.12 补丁: 解锁专属音效
        t = make_toast("特殊宝藏房间已解锁！", color=(255, 215, 0), duration=3.0)
        self.toasts.append(t)

    def _check_portal_proximity(self, col: int, row: int):
        """检查玩家是否紧靠传送门，返回最近的Portal对象"""
        if not self.current_room:
            return None

        for portal in self.current_room.portals:
            if portal.is_floor_portal:
                continue
            px, py = self.current_room._portal_grid_pos(portal)
            if abs(col - px) <= 1 and abs(row - py) <= 1:
                return portal
        return None

    def _complete_portal_travel(self) -> None:
        """完成房间间传送"""
        if not self._portal_target or not self.floor_layout:
            return

        target_room_idx = self._portal_target.target_room_idx
        target_room = self.floor_layout.get_room_by_idx(target_room_idx)
        if not target_room:
            return

        target_side = self._portal_target.target_side
        target_offset = self._portal_target.target_offset

        # 计算目标位置：在目标房间传送门旁边的可行走格
        if target_side == "left":
            tx = 1 * TILE_SIZE + TILE_SIZE // 2
            ty = (1 + target_offset) * TILE_SIZE + TILE_SIZE // 2
        elif target_side == "right":
            tx = (MAP_COLS - 2) * TILE_SIZE + TILE_SIZE // 2
            ty = (1 + target_offset) * TILE_SIZE + TILE_SIZE // 2
        elif target_side == "top":
            tx = (1 + target_offset) * TILE_SIZE + TILE_SIZE // 2
            ty = 1 * TILE_SIZE + TILE_SIZE // 2
        else:
            tx = (1 + target_offset) * TILE_SIZE + TILE_SIZE // 2
            ty = (MAP_ROWS - 2) * TILE_SIZE + TILE_SIZE // 2

        self.player.x = float(tx)
        self.player.y = float(ty)

        # 切换当前房间和网格
        self.current_room = target_room
        self.grid = target_room.grid
        self.monsters = self.room_monsters.get(target_room.room_idx, [])

        # V1.0.5.14 修复: 地狱主题房间首次进入时布置陷阱（原仅楼层初始化时放置, 传送后无效）
        self._ensure_traps_for_room(target_room)

        # 播放传送音效
        if self.audio:
            self.audio.play_portal_travel()

        # 重置传送状态
        self._portal_timer = -1.0
        self._portal_target = None
        self._portal_countdown = None
        self._portal_proximity_sound_playing = False

        # V1.0.5.13 修复: 副本/宝藏/特殊宝藏房间首次进入时生成刷怪笼/宝箱
        # （已通关的房间不再生成；self.monsters 非空则不重复生成）
        if (target_room.room_type in (RoomType.BATTLE, RoomType.ENHANCED_BATTLE,
                                      RoomType.BOSS_BATTLE, RoomType.DUNGEON,
                                      RoomType.TREASURE, RoomType.SPECIAL_TREASURE)
                and not self.room_cleared.get(target_room.room_idx, False)):
            if not self.monsters:
                self._spawn_monsters_for_current_room()

        # V1.0.5.10 房间切换后更新 BGM
        self._update_floor_bgm()

    def _is_floor_cleared(self) -> bool:
        """V1.0.5 检查楼层是否已通关（战斗类房间全部清空；副本/宝藏/特殊宝藏不参与判定）"""
        if not self.floor_layout:
            return False

        for room in self.floor_layout.rooms:
            # 副本房间、宝藏室与特殊宝藏室不参与通关判定
            if room.room_type in (RoomType.DUNGEON, RoomType.TREASURE,
                                  RoomType.SPECIAL_TREASURE):
                continue
            if room.room_type in (RoomType.SPAWN, RoomType.BATTLE,
                                  RoomType.ENHANCED_BATTLE, RoomType.BOSS_BATTLE):
                if not self.room_cleared.get(room.room_idx, False):
                    return False
        return True

    def _check_spawn_zone(self, dt: float) -> None:
        """V1.0.5 安全区：离开后立即消失，不再重生
        V1.0.5.6：BOSS楼层同为多房间架构，统一走多房间逻辑
        """
        if self.current_room and self.current_room.room_type == RoomType.SPAWN:
            room_idx = self.current_room.room_idx
            if self._room_spawned.get(room_idx, False):
                self.in_spawn_zone = False
                return

            sx = self.spawn_pos[0] * TILE_SIZE + TILE_SIZE // 2
            sy = self.spawn_pos[1] * TILE_SIZE + TILE_SIZE // 2
            dist = math.sqrt((self.player.x - sx)**2 + (self.player.y - sy)**2)

            if dist >= TILE_SIZE * 2:
                self.in_spawn_zone = False
                if self.spawn_timer < 0:
                    self.spawn_timer = SPAWN_DELAY_SEC
                else:
                    self.spawn_timer = round(self.spawn_timer - dt, 2)
                    sec = max(1, int(self.spawn_timer) + 1)
                    self._spawn_toast = make_toast(f"怪物将在 {sec} 秒后出现")
                    if self.spawn_timer <= 0:
                        self._spawn_monsters_for_current_room()
                        self._room_spawned[room_idx] = True
                        self.spawn_timer = -1
                        self._spawn_toast = None
            else:
                self.in_spawn_zone = True

    def _update_projectiles(self) -> str | None:
        """更新投射物; 击杀高塔之主时返回 "victory"（V1.0.5.9 即时通关）"""
        to_remove = []
        for i, proj in enumerate(self.projectiles):
            proj['x'] += proj['vx']
            proj['y'] += proj['vy']
            proj['traveled'] += proj.get('speed', PROJECTILE_SPEED)
            if proj['traveled'] > proj.get('range', PROJECTILE_RANGE) or self._collides_wall(proj['x'], proj['y']):
                to_remove.append(i)
                continue

            hit = False
            shooter_id = proj.get('shooter')

            # 敌方投射物 → 检测玩家碰撞
            if shooter_id is not None:
                dx = self.player.x - proj['x']
                dy = self.player.y - proj['y']
                if math.sqrt(dx*dx+dy*dy) < TILE_SIZE // 2:
                    self.player.take_damage(proj['damage'])
                    # V1.0.5.11 弹射物附加BUFF机制: 火球/冰弹→时长刷新(refresh);
                    # 冰焰弹→时长叠加(stack); 其余(箭矢等)→取最大(max)
                    _pt = proj.get('proj_type', 'arrow')
                    if _pt == 'ice_fireball':
                        _buff_mode = "stack"
                    elif _pt in ('fireball', 'ice_bomb'):
                        _buff_mode = "refresh"
                    else:
                        _buff_mode = "max"
                    if proj.get('burn'):
                        burn_level = proj.get('burn_level', 2)
                        self.player.add_status("burn", proj['burn'], proj.get('burn_dmg', 7),
                                               level=burn_level, mode=_buff_mode)
                    if proj.get('frost'):
                        frost_level = proj.get('frost_level', 1)
                        self.player.add_status("frost", proj['frost'],
                                               level=frost_level, mode=_buff_mode)
                    # V1.0.5.9: 定身（冰弹命中 1.5s 无法移动）
                    if proj.get('root'):
                        self.player._root_timer = max(self.player._root_timer, float(proj['root']))
                    # V1.0.5.9: 首领被动生命窃取（每次造成伤害 60% 概率回复等量HP）
                    shooter = next((m for m in self.monsters if id(m) == shooter_id), None)
                    if (shooter is not None and shooter.monster_type == "final_boss"
                            and random.random() < 0.6):
                        shooter.hp = min(shooter.max_hp, shooter.hp + max(1, int(proj['damage'])))
                    if self.audio:
                        self.audio.play_player_hit()
                    if not self.player.is_alive():
                        if self.audio:
                            self.audio.play_player_death()
                    hit = True
            else:
                # 玩家投射物 → 检测怪物碰撞
                for monster in self.monsters:
                    if not monster.is_alive():
                        continue
                    if shooter_id is not None and id(monster) == shooter_id:
                        continue
                    dx = monster.x - proj['x']
                    dy = monster.y - proj['y']
                    if math.sqrt(dx*dx+dy*dy) < TILE_SIZE // 2:
                        if projectile_hit_monster(proj, monster, self.player):
                            self._play_hit_sound(monster)
                            weapon = proj.get('weapon')
                            # 循伤索敌（V1.0.5.11）：受远程攻击且玩家不在索敌范围内时,
                            # 索敌范围+50%（×1.5）, 持续3秒
                            # 循伤索敌（V1.0.5.11）：隐身时依然生效——怪物向受伤来源方向移动但不锁定玩家
                            if monster.is_alive():
                                if not is_in_range(monster.x, monster.y, self.player.x,
                                                   self.player.y,
                                                   monster.get_current_detect_range()):
                                    monster.set_track_attacker(self.player.x, self.player.y, 3.0)
                            # 精英之弓暴击提示: 触发屏幕抖动+轻微闪烁
                            if proj.get('crit_triggered'):
                                self.toasts.append(make_toast('暴击！'))
                                proj['crit_triggered'] = False
                                self._trigger_shake_flash()
                                if self.audio: self.audio.play_crit()
                            if not monster.is_alive():
                                # 杀戮之弩斩杀提示: 触发屏幕抖动+轻微闪烁 + 专属斩杀音效
                                if weapon and weapon.instakill:
                                    self.toasts.append(make_toast('斩杀！'))
                                    self._trigger_shake_flash()
                                result = self._on_monster_killed(monster)
                                if result:
                                    return result
                        hit = True
                        break
            if hit:
                to_remove.append(i)
        for i in reversed(to_remove):
            self.projectiles.pop(i)

    def _update_slash_effects(self, dt: float) -> None:
        """V1.0.5.11: 更新近战剑气特效（0.18s 淡出）"""
        for s in self.slash_effects:
            s['t'] += dt
        self.slash_effects = [s for s in self.slash_effects if s['t'] < 0.18]

    def _update_sword_slashes(self, dt: float) -> None:
        """V1.0.5.12 连击&战斗特效: 更新V形剑气（沿攻击方向向前飞行, 时长按射程缩放）"""
        for s in self.v_slashes:
            s['t'] += dt
            s['x'] += s.get('vx', 0.0) * V_SLASH_SPEED * dt
            s['y'] += s.get('vy', 0.0) * V_SLASH_SPEED * dt
        self.v_slashes = [s for s in self.v_slashes
                          if s['t'] < s.get('dur', V_SLASH_DURATION)]

    def _update_monsters(self, dt: float) -> None:
        for monster in self.monsters:
            if not monster.is_alive():
                continue

            if monster.check_phase_transition():
                self.toasts.append(make_toast(f"{monster.name} 进入新阶段！"))

            # V1.0.5.12 不可移动实体（宝箱/试炼刷怪笼）
            if getattr(monster, 'immobile', False):
                if monster.monster_type == "trial_spawner":
                    if not hasattr(monster, 'spawn_timer'): monster.spawn_timer = 0.0
                    if not hasattr(monster, 'spawn_interval'): monster.spawn_interval = 10.0
                    monster.spawn_timer -= dt
                    if not hasattr(monster, 'ambient_timer'): monster.ambient_timer = 0.0
                    monster.ambient_timer -= dt
                    dist_to_player = math.sqrt((self.player.x - monster.x) ** 2 + (self.player.y - monster.y) ** 2)
                    if dist_to_player <= TILE_SIZE * 6 and monster.ambient_timer <= 0:
                        if self.audio:
                            self.audio.play_ambient(monster.name, id(monster))
                        monster.ambient_timer = 5.0
                    in_range = is_in_range(monster.x, monster.y, self.player.x, self.player.y, monster.detect_range)
                    if in_range and monster.spawn_timer <= 0:
                        self._trial_spawner_summon(monster)
                        monster.spawn_timer = monster.spawn_interval
                continue

            # 最终BOSS技能系统（V1.0.5.9）
            # 隐身药水（安全区外）：BOSS 同样无法锁定玩家，技能/弹幕暂停
            if monster.monster_type == "final_boss" and not (not self.in_spawn_zone and self.player.is_invisible()):
                if getattr(monster, 'locked', False):
                    minions = getattr(monster, '_ultimate_minions', [])
                    if minions and all(not m.is_alive() for m in minions):
                        monster.locked = False
                        monster._output_mult = 1.0
                        self.toasts.append(make_toast('高塔之主的锁血已解除！', color=(255, 215, 0)))
                if not hasattr(monster, 'skill_cd'): monster.skill_cd = 0.0
                if monster.skill_cd > 0:
                    monster.skill_cd -= dt
                self._update_boss_barrage(monster, dt)
                if monster.skill_cd <= 0:
                    if getattr(monster, '_rooted', False):
                        pass
                    elif monster.hp < monster.max_hp and monster.phase >= 3 and not getattr(monster, '_ultimate_used', False):
                        self._boss_ultimate(monster)
                        monster.skill_cd = 12.0
                    elif monster.phase == 1:
                        if self._boss_summon_allowed():
                            self._boss_summon(monster)
                            if self.audio:
                                self.audio.play_boss_summon()
                        monster.skill_cd = 15.0
                    else:
                        # 弹幕与额外号令均为 50% 概率触发（号令还需满足发动条件）
                        if random.random() < 0.5:
                            self._boss_barrage(monster)
                            if self._boss_summon_allowed():
                                self._boss_summon(monster)
                                if self.audio:
                                    self.audio.play_boss_summon()
                        monster.skill_cd = 15.0 if monster.phase == 2 else 12.0

            # 索敌范围
            detect_range = monster.get_current_detect_range()
            in_range = is_in_range(monster.x, monster.y, self.player.x, self.player.y, detect_range)
            dist_to_player = math.sqrt((self.player.x - monster.x) ** 2 + (self.player.y - monster.y) ** 2)

            # 隐身药水（安全区外）：怪物无法锁定玩家
            hidden = (not self.in_spawn_zone) and self.player.is_invisible()

            # 玩家离开索敌范围（×1.25 容差）或隐身时解除锁定（不解除循伤索敌：隐身时怪物仍会循伤向玩家方向移动）
            if monster.aggro and (hidden or not is_in_range(monster.x, monster.y, self.player.x, self.player.y, monster.get_current_detect_range() * 1.25)):
                monster.aggro = False
                monster._path = None

            if in_range and not monster.aggro and not hidden:
                monster.aggro = True
                monster._path = None

            # 移动
            current_speed = monster.get_current_speed()
            if monster.is_tracking_attacker():
                track_grid = pixel_to_grid(monster.track_attacker_x, monster.track_attacker_y)
                self._move_with_astar(monster, track_grid, current_speed, dt)
            elif not monster.aggro:
                if not hasattr(monster, '_wander_accum'): monster._wander_accum = 0.0
                monster._wander_accum += monster.speed * 0.6 * dt * 60
                wsteps = int(monster._wander_accum)
                if wsteps > 0:
                    monster._wander_accum -= wsteps
                    self._move_with_astar(monster, None, wsteps, dt)
            else:
                self._move_with_astar(monster, pixel_to_grid(self.player.x, self.player.y), current_speed, dt)

            # 玩家在索敌范围内：靠近音效（3格内）；隐身时怪物无目标、不播音效
            if in_range and not hidden:
                if self.audio and dist_to_player <= TILE_SIZE * 3:
                    self.audio.play_ambient(monster.name, id(monster))
            # 隐身药水（安全区外）：无法锁定玩家，跳过技能/攻击/远程走位
            if hidden:
                continue

            # 技能触发
            can_skill = monster.hp < monster.max_hp
            if can_skill and '精英僵尸' in monster.name and monster.skill_cd <= 0:
                # 仅在血量首次低于 50% 时自愈一次（治疗 30%~50% 最大生命）
                first_time = not getattr(monster, '_healed_once', False)
                if first_time and monster.hp < monster.max_hp * 0.5:
                    heal = int(monster.max_hp * random.uniform(0.3, 0.5))
                    monster.hp = min(monster.max_hp, monster.hp + heal)
                    monster._healed_once = True
                    monster.skill_cd = 20.0
                    self.toasts.append(make_toast(f"{monster.name}发动了自我痊愈技能！"))
            elif can_skill and '冰霜僵尸' in monster.name and monster.skill_cd <= 0 and dist_to_player > TILE_SIZE * 4:
                self._fire_ice_bomb(monster)
                monster.skill_cd = 10.0
                self.toasts.append(make_toast(f"{monster.name}发动了投掷冰弹技能！"))
            elif can_skill and '精英骷髅' in monster.name and monster.skill_cd <= 0 and dist_to_player > TILE_SIZE * 4:
                self._fire_snipe(monster)
                monster.skill_cd = 10.0
                self.toasts.append(make_toast(f"{monster.name}发动了精确狙击技能！"))
            elif can_skill and '流髑' in monster.name and monster.skill_cd <= 0:
                self._fire_multishot(monster)
                monster.skill_cd = 20.0
                self.toasts.append(make_toast(f"{monster.name}发动了多重射击技能！"))
            elif can_skill and '暗影骑士' in monster.name and '暗黑' not in monster.name and monster.skill_cd <= 0 and dist_to_player < TILE_SIZE * 6:
                monster.speed *= 2.0
                monster._dash_timer = 1.5
                monster._dash_dmg_mult = 2.5
                monster.skill_cd = 20.0
                self.toasts.append(make_toast(f"{monster.name}发动了闪击技能！"))
            elif can_skill and '烈焰使者' in monster.name and monster.skill_cd <= 0:
                r = random.random()
                if r < 0.3:
                    cnt, child = 2, '中型岩浆史莱姆'
                elif r < 0.5:
                    cnt, child = 1, '中型岩浆史莱姆'
                elif r < 0.8:
                    cnt, child = 4, '小型岩浆史莱姆'
                else:
                    cnt, child = 3, '小型岩浆史莱姆'
                for _ in range(cnt):
                    self._spawn_slime_child(child, monster)
                monster.skill_cd = 20.0
                self.toasts.append(make_toast(f"{monster.name}发动了召唤术式技能！"))
            elif can_skill and '卫道士' in monster.name and monster.skill_cd <= 0 and dist_to_player <= monster.attack_range * TILE_SIZE:
                monster._fury_timer = 2.0
                monster._fury_atk_mult = 1.5
                monster._fury_cd_mult = 0.5
                monster.skill_cd = 15.0
                self.toasts.append(make_toast(f"{monster.name}发动了狂怒技能！"))
            elif can_skill and '掠夺者' in monster.name and monster.skill_cd <= 0:
                monster._rain_shots = 10
                monster._rain_timer = 0.0
                monster._rooted = True
                monster.skill_cd = 15.0
                self.toasts.append(make_toast(f"{monster.name}发动了箭雨技能！"))
            elif can_skill and '暗黑骑士' in monster.name and monster.skill_cd <= 0 and dist_to_player < TILE_SIZE * 10:
                for _ in range(20):
                    a = random.uniform(0, 2 * math.pi)
                    d = TILE_SIZE * 1.5
                    tx = self.player.x + math.cos(a) * d
                    ty = self.player.y + math.sin(a) * d
                    if not self._collides_wall(tx, ty):
                        monster.x = tx
                        monster.y = ty
                        break
                monster._assault_timer = 2.0
                monster._assault_dmg_mult = 2.0
                monster.speed *= 1.5
                monster.skill_cd = 15.0
                self.toasts.append(make_toast(f"{monster.name}发动了暗影突袭技能！"))
            elif can_skill and '炎魔' in monster.name and monster.skill_cd <= 0 and dist_to_player < TILE_SIZE * 10:
                monster._flame_waves = 3
                monster._flame_timer = 0.0
                monster._rooted = True
                for _ in range(3):
                    self._spawn_slime_child('中型岩浆史莱姆', monster, TILE_SIZE * 1.5)
                monster.skill_cd = 15.0
                self.toasts.append(make_toast(f"{monster.name}发动了浴火焚身技能！"))

            self._update_skill_states(monster, dt)
            # 攻击（与原版攻击块 L1431–L1539 逐行对齐）
            if monster.ranged_attacker:
                # ── 原版 L1432–L1469：远程怪走位 + 骷髅视线 ──
                atk_px = monster.attack_range * TILE_SIZE
                dist_p = math.sqrt((self.player.x - monster.x) ** 2 + (self.player.y - monster.y) ** 2)
                is_skeleton = ('骷髅' in monster.name or '流髑' in monster.name)
                has_line_of_sight = True
                if is_skeleton:
                    monster_grid = pixel_to_grid(monster.x, monster.y)
                    player_grid = pixel_to_grid(self.player.x, self.player.y)
                    from systems.pathfinding import _line_clear
                    has_line_of_sight = _line_clear(self.grid, monster_grid, player_grid)
                flee_px = max(TILE_SIZE * 1.2, atk_px * 0.6)
                if dist_p > atk_px * 0.9:
                    nx, ny = move_toward(monster.x, monster.y, self.player.x, self.player.y, monster.speed)
                    if not self._collides_wall(nx, monster.y): monster.x = nx
                    if not self._collides_wall(monster.x, ny): monster.y = ny
                elif dist_p < flee_px:
                    if monster.monster_type != 'final_boss':
                        flee_spd = max(1.0, monster.speed * 0.5)
                        nx, ny = move_toward(monster.x, monster.y, self.player.x, self.player.y, -flee_spd)
                        if not self._collides_wall(nx, monster.y): monster.x = nx
                        if not self._collides_wall(monster.x, ny): monster.y = ny
                if dist_p < TILE_SIZE * 1 and monster.monster_type != 'final_boss':
                    continue
                if is_skeleton and not has_line_of_sight:
                    self._move_with_astar(monster, pixel_to_grid(self.player.x, self.player.y), monster.speed, dt)
                    continue
                # ── 原版 L1470–L1517：远程开火 ──
                if monster.cooldown_remaining <= 0:
                    dx = self.player.x - monster.x
                    dy = self.player.y - monster.y
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > 0:
                        is_fireball = ('烈焰使者' in monster.name) or ('炎魔' in monster.name)
                        is_ice_bomb = ('冰弹' in monster.name) or ('冰霜僵尸' in monster.name)
                        count = 3 if is_fireball else 1
                        base_angle = math.atan2(dy, dx)
                        if is_fireball:
                            proj_speed = FIREBALL_SPEED
                            proj_range = FIREBALL_RANGE
                        elif is_ice_bomb:
                            proj_speed = ICE_BOMB_SPEED
                            proj_range = ICE_BOMB_RANGE
                        else:
                            proj_speed = ENEMY_ARROW_SPEED
                            proj_range = ENEMY_ARROW_RANGE
                        for j in range(count):
                            spread = (j - 1) * 0.1 if count > 1 else 0
                            a = base_angle + spread
                            vx = math.cos(a) * proj_speed * ENEMY_PROJECTILE_SPEED_MULT
                            vy = math.sin(a) * proj_speed * ENEMY_PROJECTILE_SPEED_MULT
                            proj = {
                                'x': monster.x, 'y': monster.y,
                                'vx': vx, 'vy': vy, 'damage': monster.attack,
                                'traveled': 0.0, 'weapon': None, 'shooter': id(monster),
                                'speed': proj_speed * ENEMY_PROJECTILE_SPEED_MULT, 'range': proj_range,
                                'proj_type': 'fireball' if is_fireball else ('ice_bomb' if is_ice_bomb else 'arrow'),
                            }
                            if '烈焰使者' in monster.name:
                                proj['burn'] = 4.0; proj['burn_dmg'] = 7; proj['damage'] = 5; proj['burn_level'] = 2
                            elif '炎魔' in monster.name:
                                proj['burn'] = 5.0; proj['burn_dmg'] = 9; proj['damage'] = 8; proj['burn_level'] = 3
                            if '流髑' in monster.name:
                                proj['frost'] = 5.0
                                proj['frost_level'] = 1
                            self.projectiles.append(proj)
                        cd = 5.0 if ('烈焰使者' in monster.name or '炎魔' in monster.name) else 1.2
                        monster.cooldown_remaining = cd
                        if self.audio:
                            self.audio.play_projectile(monster.name)
            else:
                # ── 原版 L1518–L1539：近战攻击 ──
                if monster_attack_player(monster, self.player):
                    if '中型岩浆史莱姆' in monster.name:
                        self.player.add_status('burn', 3.0, 7, level=2)
                    elif '小型岩浆史莱姆' in monster.name:
                        self.player.add_status('burn', 3.0, 5, level=1)
                    if '暗影骑士' in monster.name:
                        self.player.add_status('wither', 4.0)
                        self.player.buffs.pop('heal_over_time', None)
                    elif '暗黑骑士' in monster.name:
                        self.player.add_status('wither', 6.0)
                        self.player.buffs.pop('heal_over_time', None)
                    if '冰霜僵尸' in monster.name:
                        self.player.add_status('frost', 5.0, level=1)
                    if self.audio:
                        self.audio.play_player_hit()
                    if not self.player.is_alive():
                        if self.audio:
                            self.audio.play_player_death()
                        return

    def _move_with_astar(self, monster, goal_grid, speed, dt):
        """统一的 A* 移动：有路径沿路径走，无路径则规划。goal_grid=None 表示徘徊"""
        speed *= GLOBAL_SPEED_MULT
        path = getattr(monster, '_path', None)
        recalc = getattr(monster, '_recalc', 0)
        retry = getattr(monster, '_retry', 0)

        # 需要重新规划？
        # path=None 时立即规划（刚到达/首次），已有路径时仅定时刷新
        need_replan = (path is None) or (recalc <= 0)
        if need_replan:
            monster._recalc = 1.0 + random.uniform(-0.2, 0.2)
            sc, sr = pixel_to_grid(monster.x, monster.y)
            if 0 <= sc < MAP_COLS and 0 <= sr < MAP_ROWS and self.grid[sr][sc] != 1:
                target = goal_grid if goal_grid else random_walkable(self.grid)
                if target:
                    raw = astar(self.grid, (sc, sr), target)
                    monster._path = simplify_path(self.grid, raw) if raw else None
        else:
            monster._recalc = recalc - dt

        # 沿路径移动
        path = getattr(monster, '_path', None)
        if path:
            tx, ty = grid_to_pixel(path[0][0], path[0][1])
            dx, dy = tx - monster.x, ty - monster.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < speed + 3:
                monster.x, monster.y = tx, ty
                path.pop(0)
                if not path:
                    monster._path = None  # 到达终点
                    return
                tx, ty = grid_to_pixel(path[0][0], path[0][1])
                dx, dy = tx - monster.x, ty - monster.y
                dist = math.sqrt(dx*dx + dy*dy) if (dx or dy) else 1
            if dist > 0:
                nx = monster.x + (dx/dist) * speed
                ny = monster.y + (dy/dist) * speed
                if not self._collides_wall(nx, monster.y): monster.x = nx
                if not self._collides_wall(monster.x, ny): monster.y = ny
        else:
            # 无路径（A* 失败）：强制下次重试
            monster._recalc = 0

    def _boss_summon_allowed(self) -> bool:
        """V1.0.5.11 首领号令发动条件: 全场存活精英数量<4 且 普通怪物数量<6。
        任意条件不满足则技能发动失败（仍进入冷却）; 首领被动不受影响。"""
        elites = sum(1 for m in self.monsters if m.is_alive() and m.monster_type == 'elite')
        normals = sum(1 for m in self.monsters if m.is_alive() and m.monster_type == 'normal')
        return elites < 4 and normals < 6

    def _boss_summon(self, boss: Monster) -> None:
        """首领号令（V1.0.5.9）: 概率表召唤, 怪物强度与29层一致
        10% 3精英 / 20% 1精英 / 30% 2精英 / 30% 2普通 / 20% 3普通
        """
        r = random.random()
        if r < 0.1:
            specs = [('elite', 3)]
        elif r < 0.3:
            specs = [('elite', 1)]
        elif r < 0.6:
            specs = [('elite', 2)]
        elif r < 0.9:
            specs = [('normal', 2)]
        else:
            specs = [('normal', 3)]
        g_summon = DIFFICULTY_MODIFIERS.get(self.difficulty, DIFFICULTY_MODIFIERS['easy'])
        hp_mult = 1.0 + g_summon['hp_scale_per_floor'] * 28
        atk_mult = 1.0 + g_summon['atk_scale_per_floor'] * 28
        pools = {
            'normal': [m for m in NORMAL_MONSTERS if m['name'] in NATURAL_NORMAL],
            'elite': ELITE_MONSTERS + SNOW_ELITE_MONSTERS,
        }
        for mtype, count in specs:
            for _ in range(count):
                mdef = random.choice(pools[mtype])
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(TILE_SIZE * 1.5, TILE_SIZE * 3)
                sx = boss.x + math.cos(angle) * dist
                sy = boss.y + math.sin(angle) * dist
                if self._collides_wall(sx, sy):
                    continue
                hp = int(mdef['hp'] * hp_mult)
                m = Monster(name=mdef['name'], monster_type=mtype,
                            hp=hp, max_hp=hp,
                            attack=int(mdef['atk'] * atk_mult),
                            attack_range=mdef['range'], attack_cooldown=mdef['cd'],
                            ranged_attacker=mdef.get('ranged', False),
                            speed=mdef['speed'] * MONSTER_SPEED_SCALE,
                            x=sx, y=sy, aggro=True)
                # V1.0.5.19 修复：首领号令召唤怪必须初始化 skill_cd，
                # 否则技能判断 monster.skill_cd 访问未定义属性导致 AttributeError 崩溃
                m.skill_cd = 0.0
                self.monsters.append(m)
        self.toasts.append(make_toast(f"{boss.name}发动了首领号令技能！"))

    def _fire_monster_projectile(self, monster, angle, speed, damage, proj_type='arrow',
                                 burn=0, burn_dmg=0, burn_level=0,
                                 frost=0, frost_level=0, root=0):
        """V1.0.5.10: 统一敌方投射物发射（实际位移/记账 = speed×全局系数, 射程字段按弹种文档值）"""
        range_map = {'arrow': ENEMY_ARROW_RANGE, 'fireball': FIREBALL_RANGE,
                     'ice_bomb': ICE_BOMB_RANGE, 'ice_fireball': ICE_FIREBALL_RANGE}
        eff_speed = speed * ENEMY_PROJECTILE_SPEED_MULT
        proj = {
            'x': monster.x, 'y': monster.y,
            'vx': math.cos(angle) * eff_speed, 'vy': math.sin(angle) * eff_speed,
            'damage': damage, 'traveled': 0.0, 'weapon': None,
            'shooter': id(monster), 'speed': eff_speed,
            'range': range_map.get(proj_type, ENEMY_ARROW_RANGE), 'proj_type': proj_type,
        }
        if burn > 0:
            proj['burn'] = burn
            proj['burn_dmg'] = burn_dmg
            proj['burn_level'] = burn_level
        if frost > 0:
            proj['frost'] = frost
            proj['frost_level'] = frost_level
        if root > 0:
            proj['root'] = root
        self.projectiles.append(proj)

    def _fire_ice_bomb(self, monster):
        """投掷冰弹（冰霜僵尸）: 命中 5S霜冻II + 1.5S定身"""
        angle = math.atan2(self.player.y - monster.y, self.player.x - monster.x)
        self._fire_monster_projectile(monster, angle, ICE_BOMB_SPEED, monster.attack,
                                      'ice_bomb', frost=5.0, frost_level=2, root=1.5)

    def _fire_snipe(self, monster):
        """精确狙击（精英骷髅）: 箭矢速度×200% 伤害×200%"""
        angle = math.atan2(self.player.y - monster.y, self.player.x - monster.x)
        self._fire_monster_projectile(monster, angle, ENEMY_ARROW_SPEED * 2.0,
                                      max(1, int(monster.attack * 2.0)), 'arrow')

    def _fire_multishot(self, monster):
        """多重射击（流髑）: 三箭 速度×120%"""
        base = math.atan2(self.player.y - monster.y, self.player.x - monster.x)
        for j in range(3):
            self._fire_monster_projectile(monster, base + (j - 1) * 0.15,
                                          ENEMY_ARROW_SPEED * 1.2, monster.attack, 'arrow')

    def _update_skill_states(self, monster, dt):
        """V1.0.5.9: 技能持续状态计时（闪击/暗影突袭/狂怒/箭雨/浴火焚身）"""
        if getattr(monster, '_dash_timer', 0) > 0:
            monster._dash_timer -= dt
            if monster._dash_timer <= 0:
                monster.speed /= 2.0
                monster._dash_dmg_mult = 1.0
        if getattr(monster, '_assault_timer', 0) > 0:
            monster._assault_timer -= dt
            if monster._assault_timer <= 0:
                monster.speed /= 1.5
                monster._assault_dmg_mult = 1.0
        if getattr(monster, '_fury_timer', 0) > 0:
            monster._fury_timer -= dt
            if monster._fury_timer <= 0:
                monster._fury_atk_mult = 1.0
                monster._fury_cd_mult = 1.0
        if getattr(monster, '_rain_shots', 0) > 0:
            monster._rain_timer += dt
            while monster._rain_timer >= 0.1 and monster._rain_shots > 0:
                monster._rain_timer -= 0.1
                monster._rain_shots -= 1
                angle = math.atan2(self.player.y - monster.y, self.player.x - monster.x)
                self._fire_monster_projectile(monster, angle, ENEMY_ARROW_SPEED * 1.2,
                                              max(1, int(monster.attack * 1.2)), 'arrow')
            if monster._rain_shots <= 0:
                monster._rooted = False
        if getattr(monster, '_flame_waves', 0) > 0:
            monster._flame_timer += dt
            if monster._flame_timer >= 0.5:
                monster._flame_timer = 0.0
                monster._flame_waves -= 1
                base = math.atan2(self.player.y - monster.y, self.player.x - monster.x)
                for j in range(6):
                    self._fire_monster_projectile(monster, base + (j - 2.5) * 0.12,
                                                  FIREBALL_SPEED, 8, 'fireball',
                                                  burn=5.0, burn_dmg=9, burn_level=3)
                if monster._flame_waves <= 0:
                    monster._rooted = False

    def _boss_barrage(self, boss):
        """冰焰弹幕（V1.0.5.9）: 两形态随机发动其一, 施放期间原地定身
        形态一: 360°均匀三轮各18枚（0.6s间隔）
        形态二: 朝玩家五轮每轮5枚（0.3s间隔）
        冰焰弹: 命中 3S燃烧II + 3S霜冻II
        """
        if random.random() < 0.5:
            boss._barrage_mode = 'circle'
            boss._barrage_waves = 3
            boss._barrage_per_wave = 18
            boss._barrage_interval = 0.6
        else:
            boss._barrage_mode = 'aimed'
            boss._barrage_waves = 5
            boss._barrage_per_wave = 5
            boss._barrage_interval = 0.3
        boss._barrage_timer = 0.0
        boss._rooted = True
        self.toasts.append(make_toast(f"{boss.name}发动了冰焰弹幕技能！"))

    def _update_boss_barrage(self, boss, dt):
        """冰焰弹幕逐轮发射处理"""
        if getattr(boss, '_barrage_waves', 0) <= 0:
            return
        boss._barrage_timer += dt
        if boss._barrage_timer < boss._barrage_interval:
            return
        boss._barrage_timer = 0.0
        boss._barrage_waves -= 1
        if self.audio:
            self.audio.play_boss_ice_fireball()
        if boss._barrage_mode == 'circle':
            for j in range(boss._barrage_per_wave):
                a = j * (2 * math.pi / boss._barrage_per_wave)
                self._fire_monster_projectile(boss, a, ICE_FIREBALL_SPEED, boss.attack,
                                              'ice_fireball', burn=3.0, burn_dmg=7, burn_level=2,
                                              frost=3.0, frost_level=2)
        else:
            base = math.atan2(self.player.y - boss.y, self.player.x - boss.x)
            for j in range(boss._barrage_per_wave):
                spread = (j - (boss._barrage_per_wave - 1) / 2) * 0.12
                self._fire_monster_projectile(boss, base + spread, ICE_FIREBALL_SPEED, boss.attack,
                                              'ice_fireball', burn=3.0, burn_dmg=7, burn_level=2,
                                              frost=3.0, frost_level=2)
        if boss._barrage_waves <= 0:
            boss._rooted = False

    def _boss_ultimate(self, boss):
        """起死回生（V1.0.5.9 终极技能, 仅一次）:
        召唤两名头目(1近战+1远程), 被击败前首领锁血且对玩家伤害-60%
        """
        diff_mod = DIFFICULTY_MODIFIERS.get(self.difficulty, DIFFICULTY_MODIFIERS['easy'])
        minions = []
        for mdef in (random.choice(HEAD_BOSS_MELEE), random.choice(HEAD_BOSS_RANGED)):
            angle = random.uniform(0, 2 * math.pi)
            sx = boss.x + math.cos(angle) * TILE_SIZE * 2.5
            sy = boss.y + math.sin(angle) * TILE_SIZE * 2.5
            if self._collides_wall(sx, sy):
                sx, sy = boss.x, boss.y
            floor_boost = head_boss_floor_boost(self.current_floor, self.difficulty)
            hp = int(mdef['hp'] * diff_mod['boss_hp_mult'] * floor_boost)
            m = Monster(name=mdef['name'], monster_type='head_boss',
                        hp=hp, max_hp=hp,
                        attack=int(mdef['atk'] * diff_mod['boss_atk_mult'] * floor_boost),
                        attack_range=mdef['range'],
                        attack_cooldown=mdef['cd'] * diff_mod['boss_cd_mult'],
                        ranged_attacker=mdef.get('ranged', False),
                        speed=mdef['speed'] * MONSTER_SPEED_SCALE,
                        x=sx, y=sy, aggro=True,
                        detect_range=mdef.get('detect', 600),
                        dr_ranged=mdef.get('dr_ranged', 0.0), dr_melee=mdef.get('dr_melee', 0.0))
            minions.append(m)
            self.monsters.append(m)
        boss._ultimate_minions = minions
        boss.locked = True
        boss._output_mult = 0.4
        boss._ultimate_used = True
        self.toasts.append(make_toast(f"{boss.name}发动了起死回生技能！"))

    # ================================================================
    # 移动
    # ================================================================

    def _handle_movement(self, dt: float) -> None:
        # V1.0.5.9: 定身（冰弹命中 1.5s 无法移动）
        if self.player._root_timer > 0:
            self.player._root_timer = round(self.player._root_timer - dt, 2)
            return
        keys = pygame.key.get_pressed()
        dx, dy = 0.0, 0.0
        spd = self.player.total_speed() * GLOBAL_SPEED_MULT
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= spd
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += spd
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= spd
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += spd

        if dx == 0 and dy == 0:
            return

        self.player.facing_angle = math.atan2(dy, dx)
        nx = self.player.x + dx
        ny = self.player.y + dy
        if not self._collides_wall(nx, self.player.y):
            self.player.x = nx
        if not self._collides_wall(self.player.x, ny):
            self.player.y = ny

    def _collides_wall(self, px: float, py: float) -> bool:
        half = TILE_SIZE // 3
        for cx, cy in [(px-half, py-half), (px+half, py-half),
                       (px-half, py+half), (px+half, py+half)]:
            col, row = int(cx // TILE_SIZE), int(cy // TILE_SIZE)
            if 0 <= row < len(self.grid) and 0 <= col < len(self.grid[0]):
                if self.grid[row][col] in (1, 5):
                    return True
        return False

    # ================================================================
    # 掉落 & 击杀
    # ================================================================

    def _on_monster_killed(self, monster: Monster) -> str | None:
        """处理怪物死亡; 击杀高塔之主立即通关返回 "victory"（V1.0.5.9）"""
        self.monsters_killed += 1
        self._play_death_sound(monster)

        if monster.monster_type == "head_boss":
            self.player.boss_kills += 1
        elif monster.monster_type == "elite":
            self.player.elite_kills += 1

        # 史莱姆分裂
        self._handle_slime_split(monster)

        # 幻影长袍效果
        if self.player.armor:
            if self.player.armor.on_kill_invis:
                self.player.add_buff("invisible", 5.0)
            if self.player.armor.on_kill_speed:
                self.player.add_buff("swift", 5.0)

        self._roll_drops(monster)

        # V1.0.5.9 击杀高塔之主立即通关
        if self.floor_type == 'final_boss' and monster.monster_type == 'final_boss':
            self._floor_clearing = True
            if self.audio:
                self.audio.play_victory()
            return 'victory'

        # V1.0.5 检查当前房间怪物是否全部死亡
        if self.current_room and self.floor_layout:
            alive = [m for m in self.monsters if m.is_alive()]
            if not alive:
                self.room_cleared[self.current_room.room_idx] = True
                # 楼层通关提示：任意房间完成战斗时检查全楼层
                if not self._floor_clear_toast_shown and self._is_floor_cleared():
                    self._floor_clear_toast_shown = True
                    if self.floor_type != 'final_boss':
                        self.toasts.append(make_toast(
                            "当前楼层已完成，传送门已开启",
                            color=(255, 215, 0), duration=3.0))
                        if self.audio:
                            self.audio.play_portal_appear()
        return None

    def _handle_slime_split(self, monster: Monster) -> None:
        """史莱姆死亡分裂"""
        if "大型史莱姆" in monster.name:
            r = random.random()
            if r < 0.4:
                for _ in range(2): self._spawn_slime_child("中型史莱姆", monster)
            elif r < 0.8:
                for _ in range(4): self._spawn_slime_child("小型史莱姆", monster)
        elif "中型史莱姆" in monster.name:
            r = random.random()
            if r < 0.4:
                for _ in range(2): self._spawn_slime_child("小型史莱姆", monster)
            elif r < 0.6:
                for _ in range(3): self._spawn_slime_child("小型史莱姆", monster)

    def _spawn_slime_child(self, name: str, parent: Monster, spawn_dist: float = 0) -> None:
        """生成史莱姆子体，spawn_dist=0时随机10-40px（属性按楼层缩放，与原版一致）"""
        from data.monsters import NORMAL_MONSTERS
        mdef = next((m for m in NORMAL_MONSTERS if m["name"] == name), None)
        if mdef is None: return
        diff_mod = DIFFICULTY_MODIFIERS.get(self.difficulty, DIFFICULTY_MODIFIERS['easy'])
        hp_mult = 1.0 + diff_mod['hp_scale_per_floor'] * (self.current_floor - 1)
        atk_mult = 1.0 + diff_mod['atk_scale_per_floor'] * (self.current_floor - 1)
        for _ in range(10):
            angle = random.uniform(0, 2*math.pi)
            dist = spawn_dist if spawn_dist > 0 else random.uniform(10, 40)
            sx = parent.x + math.cos(angle)*dist
            sy = parent.y + math.sin(angle)*dist
            if not self._collides_wall(sx, sy):
                child = Monster(name=mdef["name"], monster_type="normal",
                                hp=int(mdef["hp"] * hp_mult), max_hp=int(mdef["hp"] * hp_mult),
                                attack=int(mdef["atk"] * atk_mult),
                                attack_range=mdef["range"], attack_cooldown=mdef["cd"],
                                ranged_attacker=mdef.get("ranged", False),
                                speed=mdef["speed"] * MONSTER_SPEED_SCALE,
                                x=sx, y=sy, aggro=True)
                self.monsters.append(child)
                return

    def _roll_drops(self, monster: Monster) -> None:
        mtype = monster.monster_type
        mx, my = monster.x, monster.y
        room_idx = self.current_room.room_idx if self.current_room else 0

        if mtype == "normal":
            r = random.random()
            if r < DROP_NORMAL_BREAD:
                self._add_drop(room_idx, (BREAD, mx, my))
            elif r < DROP_NORMAL_BREAD + DROP_NORMAL_POTION:
                self._add_drop(room_idx, (random.choice(POTION_POOL), mx + 10, my))

        elif mtype == "elite":
            dropped = 0
            if random.random() < DROP_ELITE_BREAD and dropped < 2:
                self._add_drop(room_idx, (BREAD, mx, my))
                dropped += 1
            if random.random() < DROP_ELITE_POTION and dropped < 2:
                self._add_drop(room_idx, (random.choice(POTION_POOL), mx + 10, my))

        elif mtype == "head_boss":
            self._drop_better_equip(monster)
            # V1.0.5.6 头目楼层BOSS战必掉一把藏宝室钥匙（两名BOSS仅掉落一次）
            if self.floor_type == "boss":
                key_dropped = any(isinstance(it, KeyItem) for it, _, _ in self.drops.get(room_idx, []))
                has_key = any(isinstance(s, KeyItem) for s in self.backpack)
                if not key_dropped and not has_key:
                    self._add_drop(room_idx, (TREASURE_KEY, mx, my + 15))
            if random.random() < DROP_BOSS_BREAD:
                self._add_drop(room_idx, (BREAD, mx + 5, my + 5))
            if random.random() < DROP_BOSS_POTION:
                self._add_drop(room_idx, (random.choice(POTION_POOL), mx - 5, my + 5))

        elif mtype == "chest":
            self._chest_drop(monster)
            return
        elif mtype == "trial_spawner":
            self._trial_spawner_drop(monster)
            return

    def _drop_better_equip(self, monster: Monster) -> None:
        """头目掉落：玩家同类型装备满级或特殊时，掉落必为特殊（V1.0.4 P2）"""
        choice = random.choice(["melee_weapon", "ranged_weapon", "armor"])
        current_tier = 0
        is_special = False

        if choice == "melee_weapon" and self.player.melee_weapon:
            current_tier = self.player.melee_weapon.tier
            is_special = (current_tier >= 5)
        elif choice == "ranged_weapon" and self.player.ranged_weapon:
            current_tier = self.player.ranged_weapon.tier
            is_special = (current_tier >= 5)
        elif choice == "armor" and self.player.armor:
            current_tier = self.player.armor.tier
            is_special = (current_tier >= 5 or self.player.armor.armor_type == "special")

        new_tier = min(5, current_tier + 1)

        if choice == "melee_weapon":
            if is_special:
                item = random.choice([WEAPON_BY_NAME["三叉戟"], WEAPON_BY_NAME["机械链锯"]])
            else:
                wtypes = ["sword", "axe", "spear", "dagger"]
                item = WEAPON_BY_TYPE_TIER.get((random.choice(wtypes), new_tier))
        elif choice == "ranged_weapon":
            if is_special:
                specials = ["精英之弓", "杀戮之弩", "机械弩", "幻术师之弓"]
                item = WEAPON_BY_NAME.get(random.choice(specials))
            else:
                wtypes = ["bow", "crossbow"]
                item = WEAPON_BY_TYPE_TIER.get((random.choice(wtypes), new_tier))
        else:
            if is_special:
                from data.armor import SPECIAL_ARMORS
                item = random.choice(SPECIAL_ARMORS)
            else:
                pool = ARMOR_BY_TIER.get(new_tier, [])
                item = random.choice(pool) if pool else None

        if item:
            room_idx = self.current_room.room_idx if self.current_room else 0
            self._add_drop(room_idx, (item, monster.x, monster.y - 10))

    def _trial_spawner_summon(self, spawner):
        """V1.0.5.12 试炼刷怪笼召唤怪物
        召唤概率表：20% 3精英 / 20% 2精英 / 30% 4普通 / 30% 3普通
        怪物属性与所在楼层刷出的怪物一致
        """
        roll = random.random()
        cumulative = 0
        count = 3
        monster_type = 'normal'
        for weight, cnt, mtype in TRIAL_SPAWN_WEIGHTS:
            cumulative += weight
            if roll < cumulative:
                count = cnt
                monster_type = mtype
                break

        diff_mod = DIFFICULTY_MODIFIERS.get(self.difficulty, DIFFICULTY_MODIFIERS['easy'])
        hp_scale = diff_mod['hp_scale_per_floor']
        atk_scale = diff_mod['atk_scale_per_floor']
        hp_mult = 1.0 + hp_scale * (self.current_floor - 1)
        atk_mult = 1.0 + atk_scale * (self.current_floor - 1)

        if monster_type == 'elite':
            if self.current_floor <= 9:
                pool = [e for e in ELITE_MONSTERS if e['name'] in ('精英僵尸', '精英骷髅')]
            elif self.current_floor <= 19:
                pool = SNOW_ELITE_MONSTERS
            else:
                snow_names = {e['name'] for e in SNOW_ELITE_MONSTERS}
                pool = [e for e in ELITE_MONSTERS if e['name'] not in snow_names]
        else:
            pool = [m for m in NORMAL_MONSTERS if m['name'] in NATURAL_NORMAL]

        if not pool:
            return

        rows = len(self.grid)
        cols = len(self.grid[0]) if rows else 0
        # 合法生成范围：留 1 格墙 padding，避免召唤怪越出房间网格（V1.0.5.18 角落刷怪笼朝外偏移会越界）
        min_x, max_x = TILE_SIZE * 1.5, TILE_SIZE * (cols - 1.5)
        min_y, max_y = TILE_SIZE * 1.5, TILE_SIZE * (rows - 1.5)

        def _clamp_px(xx, yy):
            if cols > 3:
                xx = max(min_x, min(max_x, xx))
            if rows > 3:
                yy = max(min_y, min(max_y, yy))
            return xx, yy

        for _ in range(count):
            mdef = random.choice(pool)
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(TILE_SIZE * 2, TILE_SIZE * 4)
            px = spawner.x + math.cos(angle) * dist
            py = spawner.y + math.sin(angle) * dist
            if self._collides_wall(px, py):
                px = spawner.x + random.uniform(-TILE_SIZE * 3, TILE_SIZE * 3)
                py = spawner.y + random.uniform(-TILE_SIZE * 3, TILE_SIZE * 3)
            # 钳制到房间网格内，防止角落刷怪笼朝外召唤导致怪物越界
            px, py = _clamp_px(px, py)
            hp = int(mdef['hp'] * hp_mult)
            atk = int(mdef['atk'] * atk_mult)
            m = Monster(
                name=mdef['name'], monster_type=monster_type,
                hp=hp, max_hp=hp, attack=atk,
                attack_range=mdef['range'], attack_cooldown=mdef['cd'],
                ranged_attacker=mdef.get('ranged', False),
                speed=mdef['speed'] * MONSTER_SPEED_SCALE,
                x=float(px), y=float(py),
                wither=mdef.get('wither', 0.0),
                frost=mdef.get('frost', 0.0),
                burn=mdef.get('burn', 0.0), burn_dmg=mdef.get('burn_dmg', 0),
                fireball=mdef.get('fireball', 0), fire_interval=mdef.get('fire_interval', 0.0),
                detect_range=mdef.get('detect', 480),
            )
            m.skill_cd = 0.0
            self.monsters.append(m)
            room_idx = self.current_room.room_idx if self.current_room else 0
            if room_idx not in self.room_monsters:
                self.room_monsters[room_idx] = []
            self.room_monsters[room_idx].append(m)
        if self.audio:
            self.audio.play_ambient(spawner.name, id(spawner))

    def _chest_drop(self, chest):
        """V1.0.5.12 宝箱死亡掉落
        1件随机武器或装备（5%独特，10%T5，15%T4，20% T3，25% T2，25% T1）
        +随机药水（50%0个，30%1个，20%2个）
        +面包（50%0个，30%1个，20%2个）
        """
        mx, my = chest.x, chest.y
        room_idx = self.current_room.room_idx if self.current_room else 0

        roll = random.random()
        cumulative = 0
        selected_tier = 1
        is_unique = False
        for tier_name, weight in CHEST_DROP_EQUIP_WEIGHTS.items():
            cumulative += weight
            if roll < cumulative:
                if tier_name == 'unique':
                    is_unique = True
                else:
                    selected_tier = int(tier_name[1])
                break

        equip_type = random.choice(['melee_weapon', 'ranged_weapon', 'armor'])
        if is_unique:
            if equip_type == 'melee_weapon':
                item = random.choice([WEAPON_BY_NAME.get('三叉戟'), WEAPON_BY_NAME.get('机械链锯')])
            elif equip_type == 'ranged_weapon':
                specials = ['精英之弓', '杀戮之弩', '机械弩', '幻术师之弓']
                item = WEAPON_BY_NAME.get(random.choice(specials))
            else:
                from data.armor import SPECIAL_ARMORS
                item = random.choice(SPECIAL_ARMORS)
        else:
            if equip_type == 'melee_weapon':
                wtypes = ['sword', 'axe', 'spear', 'dagger']
                item = WEAPON_BY_TYPE_TIER.get((random.choice(wtypes), selected_tier))
            elif equip_type == 'ranged_weapon':
                wtypes = ['bow', 'crossbow']
                item = WEAPON_BY_TYPE_TIER.get((random.choice(wtypes), selected_tier))
            else:
                pool = ARMOR_BY_TIER.get(selected_tier, [])
                item = random.choice(pool) if pool else None
        if item:
            self._add_drop(room_idx, (item, mx, my))

        potion_count = self._weighted_random(CHEST_DROP_POTION_WEIGHTS)
        for _ in range(potion_count):
            self._add_drop(room_idx, (random.choice(POTION_POOL), mx + 10, my))

        bread_count = self._weighted_random(CHEST_DROP_BREAD_WEIGHTS)
        for _ in range(bread_count):
            self._add_drop(room_idx, (BREAD, mx - 10, my))
        if self.audio:
            self.audio.play_ambient(chest.name, id(chest))

    def _trial_spawner_drop(self, spawner):
        """V1.0.5.12 试炼刷怪笼死亡掉落
        必掉一件特殊装备（或武器）和两瓶随机药水
        """
        mx, my = spawner.x, spawner.y
        room_idx = self.current_room.room_idx if self.current_room else 0

        equip_type = random.choice(['melee_weapon', 'ranged_weapon', 'armor'])
        if equip_type == 'melee_weapon':
            item = random.choice([WEAPON_BY_NAME.get('三叉戟'), WEAPON_BY_NAME.get('机械链锯')])
        elif equip_type == 'ranged_weapon':
            specials = ['精英之弓', '杀戮之弩', '机械弩', '幻术师之弓']
            item = WEAPON_BY_NAME.get(random.choice(specials))
        else:
            from data.armor import SPECIAL_ARMORS
            item = random.choice(SPECIAL_ARMORS)
        if item:
            self._add_drop(room_idx, (item, mx, my))

        for _ in range(TRIAL_SPAWNER_DROP_POTIONS):
            self._add_drop(room_idx, (random.choice(POTION_POOL), mx + 10, my))
        if self.audio:
            self.audio.play_ambient(spawner.name, id(spawner))

    def _weighted_random(self, weights: dict):
        """按权重随机选择一个键"""
        roll = random.random()
        cumulative = 0
        for value, weight in weights.items():
            cumulative += weight
            if roll < cumulative:
                return value
        return list(weights.keys())[-1]

    def _spawn_treasure_ground_items(self, room: Room) -> None:
        """V1.0.5.12 补丁: 宝藏室/特殊宝藏房间地面刷新消耗品+装备"""
        room_idx = room.room_idx
        # 防重复生成
        if self.drops.get(room_idx):
            return
        is_special = room.room_type == RoomType.SPECIAL_TREASURE
        if is_special:
            potion_limit = SPECIAL_TREASURE_ROOM_MIN_POTIONS
        else:
            potion_limit = TREASURE_ROOM_MAX_POTIONS

        # 消耗品：前 potion_limit 个位置随机药水，其余面包
        for i, (col, row) in enumerate(room.consumable_positions):
            px = col * TILE_SIZE + TILE_SIZE // 2
            py = row * TILE_SIZE + TILE_SIZE // 2
            if i < potion_limit:
                item = random.choice(POTION_POOL)
            else:
                item = BREAD
            self._add_drop(room_idx, (item, px, py))

        # 装备：宝藏室 T1~T5 普通；特殊宝藏室 T5 及以上（独特装备）
        for col, row in room.equip_positions:
            if is_special:
                item = self._roll_treasure_equip(5, allow_unique=True)
            else:
                tier = random.randint(1, TREASURE_ROOM_EQUIP_MAX_TIER)
                item = self._roll_treasure_equip(tier, allow_unique=False)
            if item:
                px = col * TILE_SIZE + TILE_SIZE // 2
                py = row * TILE_SIZE + TILE_SIZE // 2
                self._add_drop(room_idx, (item, px, py))

    def _roll_treasure_equip(self, tier: int, allow_unique: bool = False):
        """V1.0.5.12 补丁: 宝藏室地面装备随机生成"""
        equip_type = random.choice(['melee_weapon', 'ranged_weapon', 'armor'])
        if allow_unique and random.random() < 0.5:
            if equip_type == 'melee_weapon':
                item = random.choice([WEAPON_BY_NAME.get('三叉戟'), WEAPON_BY_NAME.get('机械链锯')])
            elif equip_type == 'ranged_weapon':
                item = WEAPON_BY_NAME.get(random.choice(['精英之弓', '杀戮之弩', '机械弩', '幻术师之弓']))
            else:
                from data.armor import SPECIAL_ARMORS
                item = random.choice(SPECIAL_ARMORS)
        else:
            if equip_type == 'melee_weapon':
                item = WEAPON_BY_TYPE_TIER.get((random.choice(['sword', 'axe', 'spear', 'dagger']), tier))
            elif equip_type == 'ranged_weapon':
                item = WEAPON_BY_TYPE_TIER.get((random.choice(['bow', 'crossbow']), tier))
            else:
                pool = ARMOR_BY_TIER.get(tier, [])
                item = random.choice(pool) if pool else None
        return item

    def _quick_use(self, key: int) -> None:
        """快捷键快速使用消耗品"""
        key_map = {pygame.K_1: ("heal_50", "面包"),
                    pygame.K_2: ("heal_100", "生命药水"),
                    pygame.K_3: ("strength_boost", "力量药水"),
                    pygame.K_4: ("swift", "迅捷药水"),
                    pygame.K_5: ("invis", "隐身药水")}
        item_type, item_name = key_map.get(key, (None, None))
        if item_type is None: return
        from systems.inventory import find_item, count_item, use_item
        slot = find_item(self.backpack, item_type)
        if slot is None:
            t = make_toast(f"背包内无{item_name}！")
            t["color"] = (255, 60, 60)
            self.toasts.append(t)
            return
        use_item(self.player, self.backpack, slot)
        count = count_item(self.backpack, item_type)
        if count >= 3: clr = (100, 255, 100)
        elif count == 2: clr = (255, 255, 60)
        else: clr = (255, 60, 60)
        t = make_toast(f"剩余 {item_name}: {count} 个")
        t["color"] = clr
        self.toasts.append(t)

    def _pickup_item(self) -> None:
        room_idx = self.current_room.room_idx if self.current_room else 0
        room_drops = self.drops.get(room_idx, [])
        if not room_drops:
            return
        closest_idx = 0
        closest_dist = float("inf")
        for i, (_, px, py) in enumerate(room_drops):
            d = (self.player.x - px)**2 + (self.player.y - py)**2
            if d < closest_dist:
                closest_dist = d
                closest_idx = i
        if closest_dist > (TILE_SIZE * 1.5)**2:
            return
        item = room_drops[closest_idx][0]
        if add_item(self.backpack, item):
            room_drops.pop(closest_idx)
            # V1.0.5.12 补丁: 拾取提示「您捡起了XXX」（物品名称按颜色）
            name_color = self._pickup_color(item)
            t = make_toast('', duration=2.0,
                           segments=[('您捡起了', (80, 80, 80)), (item.name, name_color)])
            self.toasts.append(t)
            # V1.0.5.6 钥匙拾取提示
            if isinstance(item, KeyItem):
                t = make_toast("获得 藏宝室钥匙！", color=(255, 215, 0), duration=3.0)
                self.toasts.append(t)

    def _add_drop(self, room_idx: int, drop: tuple) -> None:
        """向指定房间添加掉落物"""
        if room_idx not in self.drops:
            self.drops[room_idx] = []
        self.drops[room_idx].append(drop)

    def _pickup_color(self, item) -> tuple:
        """V1.0.5.12 补丁: 拾取提示物品名称颜色"""
        if isinstance(item, Consumable):
            if item.name == '面包':
                return (139, 90, 43)
            if item.name == '力量药水':
                return (255, 0, 255)
            if item.name == '迅捷药水':
                return (135, 206, 250)
            if item.name == '生命药水':
                return (255, 60, 60)
            if item.name == '隐身药水':
                return (160, 160, 220)
            return (220, 220, 220)
        if isinstance(item, Weapon):
            if item.name in UNIQUE_WEAPON_NAMES:
                return (255, 140, 0)
            if item.tier >= 5:
                return (144, 238, 144)
            return (255, 255, 255)
        if isinstance(item, Armor):
            if item.armor_type == 'special':
                return (255, 140, 0)
            if item.tier >= 5:
                return (144, 238, 144)
            return (255, 255, 255)
        if isinstance(item, KeyItem):
            return (255, 215, 0)
        return (220, 220, 220)

    # ================================================================
    # 楼层通关
    # ================================================================

    def _on_floor_clear(self) -> str | None:
        """V1.0.5 楼层通关"""
        if self.floor_type == 'final_boss':
            return "victory"

        # 通关提示已在 _on_monster_killed 中显示（持续3秒）

        # 清除全部 Buff
        self.player.buffs.clear()
        self.player.status_effects.clear()
        self.player._burn_dmg = 0
        self.current_floor += 1
        save_game(self.player, self.backpack, self.revive_system,
                  self.current_floor, self.monsters_killed,
                  auto_destroy=getattr(self, 'auto_destroy', False),
                  difficulty=self.difficulty)
        return "reward"

    # ================================================================
    # 绘制
    # ================================================================

    def draw(self, screen: pygame.Surface) -> None:
        # V1.0.5.12 补丁: 屏幕抖动 + 轻微闪烁
        if self._shake_timer > 0 and self._shake_power > 0:
            render = pygame.Surface(screen.get_size())
            self._draw_world(render)
            screen.fill(COLOR_BG)
            ox = int(random.uniform(-self._shake_power, self._shake_power))
            oy = int(random.uniform(-self._shake_power, self._shake_power))
            screen.blit(render, (ox, oy))
        else:
            self._draw_world(screen)

        if self._flash_timer > 0:
            flash = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            alpha = int(160 * min(1.0, self._flash_timer / FLASH_DURATION))
            if alpha > 0:
                flash.fill((255, 255, 255, alpha))
                screen.blit(flash, (0, 0))

    def _draw_world(self, render: pygame.Surface) -> None:
        render.fill(COLOR_BG)
        draw_map(render, self.grid, self.spawn_pos, self.portal_pos,
                 self.portal_active, self.in_spawn_zone,
                 get_theme(self.current_floor),
                 self.floor_layout, self.current_room)
        draw_drops(render, self.drops.get(self.current_room.room_idx, []) if self.current_room else [])
        for monster in self.monsters:
            if monster.is_alive():
                draw_monster(render, monster)
        self._draw_projectiles(render)
        # V1.0.5.11 近战弧形剑气 / V1.0.5.12 V形剑气
        draw_slash_effects(render, self.slash_effects)
        draw_v_slashes(render, self.v_slashes)
        draw_player(render, self.player)
        draw_hud(render, self.player, self.current_floor,
                 self.revive_system.revives_remaining, get_bold_hud_font())
        # HUD 测试: 顶部BOSS血条（高塔之主 + 头目; 仅BOSS战斗房间且BOSS存活时显示）
        is_boss_room = False
        if (self.current_room is not None
                and self.current_room.room_type == RoomType.BOSS_BATTLE):
            is_boss_room = True
        fb = next((m for m in self.monsters if m.monster_type == 'final_boss'), None)
        hbs = [m for m in self.monsters if m.monster_type == 'head_boss']
        if is_boss_room and (fb is not None or hbs):
            draw_boss_hp_bar(render, final_boss=fb, head_bosses=hbs,
                             font=get_bold_hud_font())
        # 倒计时 toast
        offset = 0
        if self._spawn_toast:
            draw_toast(render, self._spawn_toast, get_bold_hud_font(), offset=0)
            offset = 1
        # 传送门提示（紫色或绿色）
        if self._portal_hint:
            draw_toast(render, self._portal_hint, get_bold_hud_font(), offset=offset)
            offset += 1
        # 传送门倒计时（绿色）
        if self._portal_countdown:
            draw_toast(render, self._portal_countdown, get_bold_hud_font(), offset=offset, color=(100, 220, 100))
            offset += 1
        # 传送门背包警告（黄色）
        if self._portal_toast:
            draw_toast(render, self._portal_toast, get_bold_hud_font(), offset=offset, color=(255, 220, 60))
            offset += 1
        # 技能 toast
        for i, t in enumerate(self.toasts):
            draw_toast(render, t, get_bold_hud_font(), offset=offset + i)

        # 楼层重置倒计时提示（V1.0.4 P3）
        if self._reset_countdown > 0:
            sec = max(1, int(self._reset_countdown) + 1)
            reset_text = f"{sec}秒后楼层将刷新"
            font = get_bold_hud_font()
            text_surface = font.render(reset_text, True, (255, 80, 80))
            text_rect = text_surface.get_rect(center=(960 // 2, 720 // 2))
            # 半透明背景
            bg_surface = pygame.Surface((text_rect.width + 40, text_rect.height + 20), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 180))
            render.blit(bg_surface, (text_rect.x - 20, text_rect.y - 10))
            render.blit(text_surface, text_rect)

        # 暂停菜单（V1.0.4 P3）
        if self._paused:
            self._draw_pause_menu(render)

    def _draw_pause_menu(self, screen: pygame.Surface) -> None:
        """绘制暂停菜单"""
        # 半透明黑色遮罩
        overlay = pygame.Surface((960, 720), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        font_title = get_bold_hud_font()
        font_btn = get_bold_font(24)

        screen_center_x = 960 // 2

        # 标题：游戏暂停（金色加粗中号字体）
        title_surface = font_title.render("游戏暂停", True, (255, 215, 0))
        title_rect = title_surface.get_rect(center=(screen_center_x, 200))
        screen.blit(title_surface, title_rect)

        if self._pause_confirm_reset:
            # 楼层重置确认弹窗
            confirm_text = "重置楼层将会消耗一条生命，是否继续？"
            confirm_surface = font_btn.render(confirm_text, True, (255, 255, 255))
            confirm_rect = confirm_surface.get_rect(center=(screen_center_x, 330))
            screen.blit(confirm_surface, confirm_rect)

            # 是按钮
            btn_width = 200
            btn_height = 40
            btn_y_yes = 400
            pygame.draw.rect(screen, (80, 160, 80),
                           (screen_center_x - btn_width // 2, btn_y_yes, btn_width, btn_height))
            yes_surface = font_btn.render("是", True, (255, 255, 255))
            yes_rect = yes_surface.get_rect(center=(screen_center_x, btn_y_yes + btn_height // 2))
            screen.blit(yes_surface, yes_rect)

            # 否按钮
            btn_y_no = 460
            pygame.draw.rect(screen, (160, 80, 80),
                           (screen_center_x - btn_width // 2, btn_y_no, btn_width, btn_height))
            no_surface = font_btn.render("否", True, (255, 255, 255))
            no_rect = no_surface.get_rect(center=(screen_center_x, btn_y_no + btn_height // 2))
            screen.blit(no_surface, no_rect)
        else:
            # 暂停菜单按钮（灰色）
            btn_width = 250
            btn_height = 50
            btn_color = (100, 100, 100)

            # 返回主菜单
            btn_y_return = 300
            pygame.draw.rect(screen, btn_color,
                           (screen_center_x - btn_width // 2, btn_y_return, btn_width, btn_height))
            return_surface = font_btn.render("返回主菜单", True, (255, 255, 255))
            return_rect = return_surface.get_rect(center=(screen_center_x, btn_y_return + btn_height // 2))
            screen.blit(return_surface, return_rect)

            # 楼层重置
            btn_y_reset = 370
            pygame.draw.rect(screen, btn_color,
                           (screen_center_x - btn_width // 2, btn_y_reset, btn_width, btn_height))
            reset_surface = font_btn.render("楼层重置", True, (255, 255, 255))
            reset_rect = reset_surface.get_rect(center=(screen_center_x, btn_y_reset + btn_height // 2))
            screen.blit(reset_surface, reset_rect)

            # 继续游戏
            btn_y_continue = 440
            pygame.draw.rect(screen, btn_color,
                           (screen_center_x - btn_width // 2, btn_y_continue, btn_width, btn_height))
            continue_surface = font_btn.render("继续游戏", True, (255, 255, 255))
            continue_rect = continue_surface.get_rect(center=(screen_center_x, btn_y_continue + btn_height // 2))
            screen.blit(continue_surface, continue_rect)

    def _draw_projectiles(self, screen: pygame.Surface) -> None:
        import os
        from utils import resource_path
        for proj in self.projectiles:
            px, py = int(proj['x']), int(proj['y'])
            proj_type = proj.get('proj_type')
            is_fire = proj.get('burn') is not None
            # 加载图标（缓存）
            if proj_type == 'ice_fireball':
                icon_key = 'ice_fireball'
                fname = 'icon/Dragon_Fireball_JE2.png'
            elif proj_type == 'ice_bomb':
                icon_key = 'ice_bomb'
                fname = 'icon/64px-Ice_Bomb.png'
            elif is_fire:
                icon_key = 'fireball'
                fname = 'icon/EntitySprite_fire-charge.webp'
            else:
                icon_key = 'arrow'
                fname = 'icon/EntitySprite_arrow.webp'
            if not hasattr(self, '_proj_icons'): self._proj_icons = {}
            if icon_key not in self._proj_icons:
                try:
                    path = resource_path(fname)
                    if os.path.exists(path):
                        img = pygame.image.load(path)
                        img = pygame.transform.scale(img, (PROJECTILE_SIZE*3, PROJECTILE_SIZE*3))
                        self._proj_icons[icon_key] = img
                    else:
                        self._proj_icons[icon_key] = None
                except Exception:
                    self._proj_icons[icon_key] = None
            icon = self._proj_icons.get(icon_key)
            if icon:
                # 火球/冰弹/冰焰弹图标直接绘制（不旋转）；箭矢按飞行方向旋转
                if not is_fire and proj_type not in ('ice_fireball', 'ice_bomb'):
                    angle = math.degrees(math.atan2(proj['vy'], proj['vx']))
                    rotated = pygame.transform.rotate(icon, -angle)
                    rw, rh = rotated.get_size()
                    screen.blit(rotated, (px - rw//2, py - rh//2))
                else:
                    screen.blit(icon, (px - PROJECTILE_SIZE*3//2, py - PROJECTILE_SIZE*3//2))
            else:
                color = (255, 60, 30) if is_fire else COLOR_PROJECTILE
                pygame.draw.circle(screen, color, (px, py), PROJECTILE_SIZE)
                tail_x = int(px - proj['vx'] * 2)
                tail_y = int(py - proj['vy'] * 2)
                tail_color = (200, 40, 20) if is_fire else (80, 160, 220)
                pygame.draw.line(screen, tail_color, (px, py), (tail_x, tail_y), 3)
