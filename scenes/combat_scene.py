"""
Dungeon Warriors v2.0 — 战斗场景（核心玩法）
延迟刷新、Buff计时器、武器类型系统、BOSS阶段、掉落&奖励
"""

import math
import random
import pygame
from config import (
    TILE_SIZE, MAP_COLS, MAP_ROWS, FPS, SPAWN_DELAY_SEC,
    PLAYER_BASE_SPEED,
    PROJECTILE_SPEED, PROJECTILE_RANGE, PROJECTILE_SIZE,
    MONSTER_DETECT_RANGE, MONSTER_SPEED,
    MONSTER_FINAL_BOSS_SUMMON_INTERVAL, MONSTER_FINAL_BOSS_SUMMON_CHANCE,
    DROP_NORMAL_POTION, DROP_NORMAL_BREAD,
    DROP_ELITE_POTION, DROP_ELITE_BREAD,
    DROP_BOSS_EQUIP, DROP_BOSS_BREAD, DROP_BOSS_POTION,
    BREAD_HEAL_PER_SEC, BREAD_HEAL_DURATION,
    COLOR_BG, COLOR_PROJECTILE,
)
from entities.player import Player
from entities.monster import Monster
from entities.item import Weapon, Armor, Consumable
from systems.combat import (
    player_melee_attack, player_ranged_attack,
    projectile_hit_monster, move_toward, is_in_range, monster_attack_player,
)
from systems.inventory import add_item
from systems.floor_manager import (
    generate_map, find_spawn_point, spawn_monsters, get_floor_type,
    get_theme, place_traps,
)
from systems.pathfinding import astar, simplify_path, pixel_to_grid, grid_to_pixel, random_walkable
from systems.save_system import save_game
from systems.revive_system import ReviveSystem
from systems.audio_manager import AudioManager
from rendering.renderer import (
    draw_map, draw_player, draw_monster, draw_drops, draw_hud, draw_toast,
    get_bold_font,
    get_bold_hud_font,
)
from rendering.pixel_style import make_toast
from data.weapons import WEAPON_BY_NAME, WEAPON_BY_TYPE_TIER
from data.armor import ARMOR_BY_TIER
from data.consumables import BREAD, POTION_POOL


class CombatScene:
    """战斗场景 v2.0"""

    def __init__(self, player: Player, backpack: list,
                 revive_system: ReviveSystem,
                 current_floor: int,
                 monsters_killed: int = 0,
                 audio_manager: AudioManager | None = None,
                 difficulty: str = "easy") -> None:
        self.player = player
        self.backpack = backpack
        self.revive_system = revive_system
        self.current_floor = current_floor
        self.monsters_killed = monsters_killed
        self.audio = audio_manager
        self.difficulty = difficulty

        # 楼层数据
        self.grid: list[list[int]] = []
        self.spawn_pos: tuple[int, int] = (0, 0)
        self.portal_pos: tuple[int, int] = (MAP_COLS // 2, MAP_ROWS // 2)
        self.portal_active: bool = False
        self.in_spawn_zone: bool = True
        self.spawn_timer: float = -1.0
        self.monsters: list[Monster] = []
        self.drops: list[tuple[object, float, float]] = []
        self.projectiles: list[dict] = []

        # 战斗状态
        self.toasts: list[dict] = []
        self._spawn_toast: dict | None = None
        self._portal_timer: float = -1
        self._portal_countdown: dict | None = None
        self._portal_toast: dict | None = None
        self.floor_type: str = "battle"
        self._heal_frac: float = 0.0  # 面包 HoT 分数累加器
        self._burn_frac: float = 0.0  # 燃烧 DoT 分数累加器

        # 暂停菜单状态（V1.0.4 P3）
        self._paused: bool = False
        self._pause_confirm_reset: bool = False  # 是否显示楼层重置确认弹窗
        self._reset_countdown: float = -1.0       # 楼层重置倒计时
        self._melee_last_used_time: float = 0.0   # 近战武器最后使用时间（连击归零用）
        self._last_esc_time: float = 0.0          # ESC防抖计时器

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

        # 生成地图
        self.grid = generate_map(MAP_COLS, MAP_ROWS)
        self.spawn_pos = find_spawn_point(self.grid, MAP_COLS, MAP_ROWS)
        if get_theme(self.current_floor) == "hell":
            place_traps(self.grid, MAP_COLS, MAP_ROWS, self.spawn_pos)
        self.portal_pos = (MAP_COLS // 2, MAP_ROWS // 2)
        self.portal_active = False
        self._trap_timer = 0.0  # 陷阱伤害计时器

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

    def _spawn_monsters_now(self) -> None:
        from config import DIFFICULTY_MODIFIERS
        mod = DIFFICULTY_MODIFIERS.get(self.difficulty, {})
        spawn_mult = mod.get("spawn_mult", 1.0)
        self.monsters = spawn_monsters(
            self.grid, MAP_COLS, MAP_ROWS,
            self.spawn_pos, self.floor_type, self.current_floor,
            spawn_mult=spawn_mult,
        )
        # BOSS 登场音效
        if self.floor_type == "final_boss" and self.audio:
            self.audio.play_boss_appear()
        # 应用难度修饰（移速、冷却）
        spd_mul = mod.get("speed_mult", 1.0)
        cd_mul = mod.get("cd_mult", 1.0)
        for m in self.monsters:
            m.speed = int(m.speed * spd_mul)
            m.attack_cooldown = m.attack_cooldown * cd_mul
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
                self._player_attack()
            elif event.button == 3:
                self._player_ranged_fire()

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
                              self.current_floor, self.monsters_killed)
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

    def _player_attack(self) -> None:
        """左键攻击，自动朝向鼠标方向"""
        # 更新朝向为鼠标方向
        mx, my = pygame.mouse.get_pos()
        self.player.facing_angle = math.atan2(my - self.player.y, mx - self.player.x)
        if self.player.melee_weapon:
            self._do_melee_attack()
        elif self.player.ranged_weapon:
            self._player_ranged_fire()

    def _do_melee_attack(self) -> None:
        hit_monsters = player_melee_attack(self.player, self.monsters)
        if not hit_monsters:
            return
        # 更新近战最后使用时间（V1.0.4 P3 连击归零）
        self._melee_last_used_time = 0.0
        armor = self.player.armor
        crit_mult = 1.0
        if armor and armor.crit_chance > 0 and random.random() < armor.crit_chance:
            crit_mult = armor.crit_mult
            self.toasts.append(make_toast('暴击！'))
            if self.audio: self.audio.play_crit()
        lifesteal = armor.lifesteal if armor else 0
        for monster in hit_monsters:
            if crit_mult > 1.0:
                extra_dmg = round(self.player.total_melee_attack() * (crit_mult - 1))
                monster.take_damage(extra_dmg)
            if lifesteal > 0 and self.player.can_heal():
                dmg = self.player.total_melee_attack() * crit_mult
                heal = round(dmg * lifesteal)
                if heal > 0:
                    self.player.current_hp = min(self.player.total_max_hp(),
                                                  self.player.current_hp + heal)
            self._play_hit_sound(monster)
            if not monster.is_alive():
                self._on_monster_killed(monster)

    def _player_ranged_fire(self) -> None:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        projs = player_ranged_attack(self.player, mouse_x, mouse_y)
        if projs:
            for proj in projs:
                self.projectiles.append(proj)
            # 多重箭提示
            if len(projs) > 1:
                self.toasts.append(make_toast('多重箭！'))
            if self.audio:
                self.audio.play_projectile('骷髅')
            # 过热提示
            if getattr(self.player, '_overheat_msg', False):
                self.toasts.append(make_toast('锯刃过热！'))
                self.player._overheat_msg = False
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
                self._init_floor()
                self.toasts.append(make_toast("楼层已刷新！"))
            return None

        # 定身计时器更新（V1.0.4 P3）
        self.player.stagger_timer = max(0, self.player.stagger_timer - dt)
        self.player.stagger_immune_timer = max(0, self.player.stagger_immune_timer - dt)
        for m in self.monsters:
            if m.is_alive():
                m.stagger_timer = max(0, m.stagger_timer - dt)
                m.stagger_immune_timer = max(0, m.stagger_immune_timer - dt)
                m.track_attacker_timer = max(0, m.track_attacker_timer - dt)

        # 玩家定身期间不处理移动和攻击
        if self.player.is_staggered():
            # 仅更新冷却和buff
            if self.player.attack_cooldown > 0:
                self.player.attack_cooldown = max(0, self.player.attack_cooldown - dt)
            if self.player.ranged_cooldown > 0:
                self.player.ranged_cooldown = max(0, self.player.ranged_cooldown - dt)
            for m in self.monsters:
                if m.cooldown_remaining > 0:
                    m.cooldown_remaining = max(0, m.cooldown_remaining - dt)
            self._update_buffs(dt)
            self._update_traps(dt)
            # Toasts 倒计时
            for t in self.toasts:
                t["timer"] -= dt
            self.toasts = [t for t in self.toasts if t["timer"] > 0]
            # 投射物继续移动
            self._update_projectiles()
            # 怪物继续行动
            self._update_monsters(dt)
            return None

        # 冷却（秒）
        if self.player.attack_cooldown > 0:
            self.player.attack_cooldown = max(0, self.player.attack_cooldown - dt)
        if self.player.ranged_cooldown > 0:
            self.player.ranged_cooldown = max(0, self.player.ranged_cooldown - dt)
        for m in self.monsters:
            if m.cooldown_remaining > 0:
                m.cooldown_remaining = max(0, m.cooldown_remaining - dt)

        # 连击冷却归零（V1.0.4 P3）：3秒未使用近战武器时连击计数器归零
        self._melee_last_used_time += dt
        if self._melee_last_used_time >= 3.0 and self.player.combo_counter > 0:
            self.player.combo_counter = 0

        # Buff
        self._update_buffs(dt)

        # 陷阱（地狱主题）
        self._update_traps(dt)

        # Toasts 倒计时
        for t in self.toasts:
            t["timer"] -= dt
        self.toasts = [t for t in self.toasts if t["timer"] > 0]

        # 移动
        self._handle_movement()

        # 出生点
        self._check_spawn_zone(dt)

        # 投射物
        self._update_projectiles()

        # 怪物
        self._update_monsters(dt)

        # 传送门
        if self.monsters:
            alive = [m for m in self.monsters if m.is_alive()]
            if not alive:
                if not self.portal_active and self.audio:
                    self.audio.play_portal_appear()
                self.portal_active = True

        if self.portal_active:
            px = self.portal_pos[0] * TILE_SIZE + TILE_SIZE // 2
            py = self.portal_pos[1] * TILE_SIZE + TILE_SIZE // 2
            in_portal = math.sqrt((self.player.x - px)**2 + (self.player.y - py)**2) < TILE_SIZE
            if in_portal:
                # 背包空格校验（V1.0.4 P2 文案）
                empty = sum(1 for s in self.backpack if s is None)
                if empty <= 1:
                    msg = "背包已满，无法传送！" if empty == 0 else "背包将满，无法传送！"
                    self._portal_toast = make_toast(msg)
                    self._portal_timer = -1  # 重置倒计时，取消传送进程
                else:
                    self._portal_toast = None
                    if not hasattr(self, '_portal_timer'): self._portal_timer = 0.0
                    if self._portal_timer < 0: self._portal_timer = 0.0
                    self._portal_timer = round(self._portal_timer + dt, 2)
                    sec = max(1, 3 - int(self._portal_timer))
                    self._portal_countdown = make_toast(f"{sec} 秒后传送至下一楼层......")
                    if self._portal_timer >= 3.0:
                        self._portal_timer = -1
                        self._portal_countdown = None
                        return self._on_floor_clear()
            else:
                self._portal_timer = -1
                self._portal_countdown = None
                self._portal_toast = None

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

        # 燃烧 DOT（分数累加器）
        burn = self.player.status_effects.get("burn", 0)
        if burn > 0:
            self._burn_frac += self.player._burn_dmg * dt
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
                   and self.grid[row][col] == 2)
        if not on_trap or not self.player.is_alive():
            self._trap_timer = 0.0
            return
        self._trap_timer += dt
        if self._trap_timer >= 1.0:
            self._trap_timer -= 1.0
            self.player.current_hp = max(0, self.player.current_hp - 5)
            if self.audio:
                self.audio.play_player_burn_tick()

    def _check_spawn_zone(self, dt: float) -> None:
        """安全区：离开后立即消失，不再重生"""
        if self.monsters:
            self.in_spawn_zone = False
            return

        sx = self.spawn_pos[0] * TILE_SIZE + TILE_SIZE // 2
        sy = self.spawn_pos[1] * TILE_SIZE + TILE_SIZE // 2
        dist = math.sqrt((self.player.x - sx)**2 + (self.player.y - sy)**2)

        if dist >= TILE_SIZE * 2:
            # 离开安全区 → 倒计时后怪物出现，安全区永久消失
            self.in_spawn_zone = False
            if self.spawn_timer < 0:
                self.spawn_timer = SPAWN_DELAY_SEC
            else:
                self.spawn_timer = round(self.spawn_timer - dt, 2)
                sec = max(1, int(self.spawn_timer) + 1)
                # 更新倒计时 toast（不重复叠加）
                self._spawn_toast = make_toast(f"怪物将在 {sec} 秒后出现")
                if self.spawn_timer <= 0:
                    self._spawn_monsters_now()
                    self.spawn_timer = -1
                    self._spawn_toast = None
        else:
            self.in_spawn_zone = True

    def _update_projectiles(self) -> None:
        to_remove = []
        for i, proj in enumerate(self.projectiles):
            proj['x'] += proj['vx']
            proj['y'] += proj['vy']
            proj['traveled'] += PROJECTILE_SPEED
            if proj['traveled'] > PROJECTILE_RANGE or self._collides_wall(proj['x'], proj['y']):
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
                    # 燃烧效果（火球）
                    if proj.get('burn'):
                        self.player.add_status("burn", proj['burn'], proj.get('burn_dmg', 7))
                    # 霜冻效果（流髑箭矢）
                    if proj.get('frost'):
                        self.player.add_status("frost", proj['frost'])
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
                            # 循伤索敌（V1.0.4 P3）：怪物遭受远程攻击后向玩家方向移动
                            if monster.is_alive():
                                monster.set_track_attacker(self.player.x, self.player.y, 1.0)
                            # 精英之弓暴击提示
                            if proj.get('crit_triggered'):
                                self.toasts.append(make_toast('暴击！'))
                                proj['crit_triggered'] = False
                                if self.audio: self.audio.play_crit()
                            if not monster.is_alive():
                                # 杀戮之弩斩杀提示
                                if weapon and weapon.instakill:
                                    self.toasts.append(make_toast('斩杀！'))
                                self._on_monster_killed(monster)
                        hit = True
                        break
            if hit:
                to_remove.append(i)
        for i in reversed(to_remove):
            self.projectiles.pop(i)

    def _update_monsters(self, dt: float) -> None:
        for monster in self.monsters:
            if not monster.is_alive():
                continue

            # 定身期间怪物不行动（V1.0.4 P3）
            if monster.is_staggered():
                continue

            if monster.check_phase_transition():
                self.toasts.append(make_toast(f"{monster.name} 进入新阶段！"))

            if monster.monster_type == "final_boss":
                monster.summon_timer += dt
                # P2 360 deg 18 fireballs every 10s
                if monster.phase >= 2 and not hasattr(monster, '_p2_fb_timer'): monster._p2_fb_timer = 0.0
                if monster.phase >= 2:
                    monster._p2_fb_timer = round(getattr(monster, '_p2_fb_timer', 0) + dt, 2)
                    from data.monsters import FINAL_BOSS
                    if monster._p2_fb_timer >= FINAL_BOSS.get('p2_fireball_interval', 10.0):
                        monster._p2_fb_timer = 0.0
                        for j in range(18):
                            a = j * (2 * math.pi / 18)
                            vx = math.cos(a) * PROJECTILE_SPEED * 0.5
                            vy = math.sin(a) * PROJECTILE_SPEED * 0.5
                            self.projectiles.append({
                                'x': monster.x, 'y': monster.y,
                                'vx': vx, 'vy': vy, 'damage': 8,
                                'traveled': 0.0, 'weapon': None, 'shooter': id(monster),
                                'burn': 5.0, 'burn_dmg': 9,
                            })
                if monster.summon_timer >= MONSTER_FINAL_BOSS_SUMMON_INTERVAL:
                    monster.summon_timer = 0
                    if random.random() < MONSTER_FINAL_BOSS_SUMMON_CHANCE:
                        self._boss_summon(monster)
                    if self.audio:
                        self.audio.play_boss_summon()

            # 使用动态索敌范围（V1.0.4 P3 循伤索敌期间×1.5）
            detect_range = monster.get_current_detect_range()
            in_range = is_in_range(monster.x, monster.y,
                                   self.player.x, self.player.y,
                                   detect_range)

            # 玩家离开索敌范围后重置 aggro，怪物恢复徘徊
            if not in_range and monster.aggro:
                monster.aggro = False
                monster._path = None  # 清空旧追击路径，重新选徘徊目标

            if in_range and not monster.aggro and not self.in_spawn_zone and not self.player.is_invisible():
                monster.aggro = True
                monster._path = None  # 清空徘徊路径，开始追击

            # === 移动：A* 寻路（追击/循伤/徘徊） ===
            if monster.is_tracking_attacker():
                # 循伤索敌：向攻击来源方向移动（V1.0.4 P3）
                track_grid = pixel_to_grid(monster.track_attacker_x, monster.track_attacker_y)
                self._move_with_astar(monster, track_grid, monster.speed, dt)
            elif not monster.aggro:
                # 徘徊：走向随机目的地
                # 徘徊 0.5 px/f（分数累加器）
                if not hasattr(monster, '_wander_accum'): monster._wander_accum = 0.0
                monster._wander_accum += 0.5 * dt * 60  # 每帧 +0.5
                wsteps = int(monster._wander_accum)
                if wsteps > 0:
                    monster._wander_accum -= wsteps
                    self._move_with_astar(monster, None, wsteps, dt)
            else:
                # 追击：走向玩家
                self._move_with_astar(monster,
                    pixel_to_grid(self.player.x, self.player.y),
                    monster.speed, dt)

            # 环境音（3格内每3秒50%概率）
            if in_range and self.audio:
                dist_to_player = math.sqrt((self.player.x-monster.x)**2+(self.player.y-monster.y)**2)
                if dist_to_player <= TILE_SIZE * 3:
                    self.audio.play_ambient(monster.name, id(monster))

            if not in_range or self.in_spawn_zone or self.player.is_invisible():
                continue

            # === 技能系统 ===
            dist_to_player = math.sqrt((self.player.x-monster.x)**2+(self.player.y-monster.y)**2)
            if not hasattr(monster, 'skill_cd'): monster.skill_cd = 0.0
            if monster.skill_cd > 0: monster.skill_cd -= dt

            # 精英僵尸/冰霜僵尸: >3格且HP<50% → 回复50%（不满足则不进冷却）
            if ('精英僵尸' in monster.name or '冰霜僵尸' in monster.name) and monster.skill_cd <= 0 and dist_to_player > TILE_SIZE*3 and monster.hp < monster.max_hp * 0.5:
                monster.hp = min(monster.max_hp, monster.hp + monster.max_hp//2)
                monster.skill_cd = 20.0; self.toasts.append(make_toast(f'{monster.name} 回复生命！'))
            # 精英骷髅/流髑: >3格 → 三连箭
            elif ('精英骷髅' in monster.name or '流髑' in monster.name) and monster.skill_cd <= 0 and dist_to_player > TILE_SIZE*3:
                for j in range(3):
                    a = math.atan2(self.player.y-monster.y, self.player.x-monster.x) + (j-1)*0.08
                    vx = math.cos(a)*PROJECTILE_SPEED*0.75; vy = math.sin(a)*PROJECTILE_SPEED*0.75
                    self.projectiles.append({'x':monster.x,'y':monster.y,'vx':vx,'vy':vy,'damage':monster.attack,'traveled':0,'weapon':None,'shooter':id(monster),'frost': 3.0} if '流髑' in monster.name else {'x':monster.x,'y':monster.y,'vx':vx,'vy':vy,'damage':monster.attack,'traveled':0,'weapon':None,'shooter':id(monster)})
                monster.skill_cd = 20.0; self.toasts.append(make_toast(f'{monster.name} 三连箭！'))
            # 暗影骑士: >3格 → 冲刺(1秒×2速)
            elif '暗影骑士' in monster.name and '暗黑' not in monster.name and monster.skill_cd <= 0 and dist_to_player > TILE_SIZE*3:
                monster._orig_spd = monster.speed; monster.speed = int(monster.speed*2)
                monster.skill_cd = 20.0; monster._dash_timer = 1.0
                self.toasts.append(make_toast('暗影骑士 冲刺！'))
            # 冲刺恢复
            if hasattr(monster, '_dash_timer') and monster._dash_timer > 0:
                monster._dash_timer -= dt
                if monster._dash_timer <= 0:
                    monster.speed = monster._orig_spd
                    delattr(monster, '_dash_timer'); delattr(monster, '_orig_spd')
            # 烈焰使者: >3格 → 召唤2小岩浆史莱姆
            if '烈焰使者' in monster.name and monster.skill_cd <= 0 and dist_to_player > TILE_SIZE*3:
                self._spawn_slime_child('小型岩浆史莱姆', self.player, TILE_SIZE)
                self._spawn_slime_child('小型岩浆史莱姆', self.player, TILE_SIZE)
                monster.skill_cd = 20.0; self.toasts.append(make_toast('烈焰使者 召唤！'))
            # 暗黑骑士: >4格 → 瞬移至1.5格处
            if '暗黑骑士' in monster.name and monster.skill_cd <= 0 and dist_to_player > TILE_SIZE*4:
                for _ in range(20):
                    a = random.uniform(0, 2*math.pi); d = TILE_SIZE*1.5
                    tx = self.player.x+math.cos(a)*d; ty = self.player.y+math.sin(a)*d
                    if not self._collides_wall(tx, ty): monster.x=tx; monster.y=ty; break
                monster.skill_cd = 20.0; self.toasts.append(make_toast('暗黑骑士 瞬移！'))
            # 炎魔: >4格 → 召唤3中岩浆史莱姆
            if '炎魔' in monster.name and monster.skill_cd <= 0 and dist_to_player > TILE_SIZE*4:
                for _ in range(3): self._spawn_slime_child('中型岩浆史莱姆', self.player, TILE_SIZE*1.5)
                monster.skill_cd = 25.0; self.toasts.append(make_toast('炎魔 召唤！'))

            # 远程怪物 AI：发射投射物，保持距离
            if monster.ranged_attacker:
                atk_px = monster.attack_range * TILE_SIZE
                dist_p = math.sqrt((self.player.x-monster.x)**2 + (self.player.y-monster.y)**2)

                # 骷髅障碍物检测（V1.0.4 P3）：直线上有障碍物时主动寻路靠近而非射击
                is_skeleton = '骷髅' in monster.name or '流髑' in monster.name
                has_line_of_sight = True
                if is_skeleton:
                    # 检测与玩家直线上是否有障碍物
                    monster_grid = pixel_to_grid(monster.x, monster.y)
                    player_grid = pixel_to_grid(self.player.x, self.player.y)
                    from systems.pathfinding import _line_clear
                    has_line_of_sight = _line_clear(self.grid, monster_grid, player_grid)

                if dist_p > atk_px * 0.8:
                    nx, ny = move_toward(monster.x, monster.y,
                                         self.player.x, self.player.y, monster.speed)
                    if not self._collides_wall(nx, monster.y): monster.x = nx
                    if not self._collides_wall(monster.x, ny): monster.y = ny
                # 玩家距离<2格时以50%速度远离（除首领外）
                if dist_p < TILE_SIZE * 2 and monster.monster_type != 'final_boss':
                    flee_spd = max(1, int(monster.speed * 0.5))
                    nx, ny = move_toward(monster.x, monster.y,
                                         self.player.x, self.player.y, -flee_spd)
                    if not self._collides_wall(nx, monster.y): monster.x = nx
                    if not self._collides_wall(monster.x, ny): monster.y = ny
                # 距离<1格时优先逃逸，不攻击
                if dist_p < TILE_SIZE * 1 and monster.monster_type != 'final_boss':
                    continue
                # 骷髅无障碍物时不射击，主动寻路靠近（V1.0.4 P3）
                if is_skeleton and not has_line_of_sight:
                    # 主动寻路靠近玩家
                    self._move_with_astar(monster,
                        pixel_to_grid(self.player.x, self.player.y),
                        monster.speed, dt)
                    continue
                if monster.cooldown_remaining <= 0:
                    dx = self.player.x - monster.x
                    dy = self.player.y - monster.y
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist > 0:
                        is_fireball = ('烈焰使者' in monster.name or '炎魔' in monster.name)
                        count = 3 if is_fireball else 1
                        base_angle = math.atan2(dy, dx)
                        for j in range(count):
                            spread = (j - 1) * 0.10 if count > 1 else 0
                            a = base_angle + spread
                            vx = math.cos(a) * PROJECTILE_SPEED * 0.5
                            vy = math.sin(a) * PROJECTILE_SPEED * 0.5
                            proj = {
                                'x': monster.x, 'y': monster.y,
                                'vx': vx, 'vy': vy, 'damage': monster.attack,
                                'traveled': 0.0, 'weapon': None, 'shooter': id(monster),
                            }
                            if '烈焰使者' in monster.name:
                                proj['burn'] = 3.0; proj['burn_dmg'] = 7; proj['damage'] = 5
                            elif '炎魔' in monster.name:
                                proj['burn'] = 5.0; proj['burn_dmg'] = 8; proj['damage'] = 8
                            # 流髑箭矢附加霜冻（V1.0.4）
                            if '流髑' in monster.name:
                                proj['frost'] = 3.0
                            self.projectiles.append(proj)
                        cd = 5.0 if '烈焰使者' in monster.name else (6.0 if '炎魔' in monster.name else 1.2)
                        monster.cooldown_remaining = cd
                        if self.audio:
                            self.audio.play_projectile(monster.name)
            elif monster_attack_player(monster, self.player):
                # 岩浆史莱姆燃烧
                if '岩浆史莱姆' in monster.name:
                    self.player.add_status('burn', 3.0, 5)
                # 头目暴击（卫道士/掠夺者每3次攻击60%×2）
                if '卫道士' in monster.name or '掠夺者' in monster.name:
                    if not hasattr(monster, '_atk_cnt'): monster._atk_cnt = 0
                    monster._atk_cnt += 1
                    if monster._atk_cnt >= 3:
                        monster._atk_cnt = 0
                        if random.random() < 0.6:
                            self.player.take_damage(monster.attack)
                            self.toasts.append(make_toast('暴击！'))
                # 凋零效果
                if "暗影骑士" in monster.name:
                    self.player.add_status("wither", 3.0)
                    self.player.buffs.pop("heal_over_time", None)  # 打断回血
                elif "暗黑骑士" in monster.name:
                    self.player.add_status("wither", 5.0)
                    self.player.buffs.pop("heal_over_time", None)
                # 霜冻攻击（V1.0.4 冰霜僵尸）
                if '冰霜僵尸' in monster.name:
                    self.player.add_status("frost", 4.0)
                if self.audio:
                    self.audio.play_player_hit()
                if not self.player.is_alive():
                    if self.audio:
                        self.audio.play_player_death()
                    return
            elif monster.cooldown_remaining <= 0:
                pass  # 移动由 _move_with_astar 统一处理

    def _move_with_astar(self, monster, goal_grid, speed, dt):
        """统一的 A* 移动：有路径沿路径走，无路径则规划。goal_grid=None 表示徘徊"""
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

    def _boss_summon(self, boss: Monster) -> None:
        r_summon = random.random()
        if r_summon < 0.5: summon_specs = [("elite", 1)]
        elif r_summon < 0.8: summon_specs = [("normal", 2)]
        else: summon_specs = [("normal", 3)]
        from data.monsters import MONSTER_BASE_STATS, MONSTER_NAMES
        for mtype, count in summon_specs:
            for _ in range(count):
                stats = MONSTER_BASE_STATS.get(mtype, {"hp":30,"attack":5,"attack_range":1.5,"attack_cooldown":0.5})
                name = random.choice(MONSTER_NAMES.get(mtype, ["怪物"]))
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(TILE_SIZE * 1.5, TILE_SIZE * 3)
                sx = boss.x + math.cos(angle) * dist
                sy = boss.y + math.sin(angle) * dist
                if not self._collides_wall(sx, sy):
                    m = Monster(name=name, monster_type=mtype,
                               hp=stats["hp"], max_hp=stats["hp"],
                               attack=stats["attack"],
                               attack_range=stats["attack_range"],
                               attack_cooldown=stats["attack_cooldown"],
                               x=sx, y=sy, aggro=True)
                    self.monsters.append(m)

    # ================================================================
    # 移动
    # ================================================================

    def _handle_movement(self) -> None:
        keys = pygame.key.get_pressed()
        dx, dy = 0.0, 0.0
        spd = self.player.total_speed()
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
                if self.grid[row][col] == 1:
                    return True
        return False

    # ================================================================
    # 掉落 & 击杀
    # ================================================================

    def _on_monster_killed(self, monster: Monster) -> None:
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
        """生成史莱姆子体，spawn_dist=0时随机10-40px"""
        from data.monsters import NORMAL_MONSTERS
        mdef = next((m for m in NORMAL_MONSTERS if m["name"] == name), None)
        if mdef is None: return
        for _ in range(10):
            angle = random.uniform(0, 2*math.pi)
            dist = spawn_dist if spawn_dist > 0 else random.uniform(10, 40)
            sx = parent.x + math.cos(angle)*dist
            sy = parent.y + math.sin(angle)*dist
            if not self._collides_wall(sx, sy):
                child = Monster(name=mdef["name"], monster_type="normal",
                                hp=mdef["hp"], max_hp=mdef["hp"],
                                attack=mdef["atk"], attack_range=mdef["range"],
                                attack_cooldown=mdef["cd"],
                                ranged_attacker=mdef.get("ranged", False),
                                speed=mdef["speed"], x=sx, y=sy, aggro=True)
                self.monsters.append(child)
                return

    def _roll_drops(self, monster: Monster) -> None:
        mtype = monster.monster_type
        mx, my = monster.x, monster.y

        if mtype == "normal":
            r = random.random()
            if r < DROP_NORMAL_BREAD:
                self.drops.append((BREAD, mx, my))
            elif r < DROP_NORMAL_BREAD + DROP_NORMAL_POTION:
                self.drops.append((random.choice(POTION_POOL), mx + 10, my))

        elif mtype == "elite":
            dropped = 0
            if random.random() < DROP_ELITE_BREAD and dropped < 2:
                self.drops.append((BREAD, mx, my))
                dropped += 1
            if random.random() < DROP_ELITE_POTION and dropped < 2:
                self.drops.append((random.choice(POTION_POOL), mx + 10, my))

        elif mtype == "head_boss":
            self._drop_better_equip(monster)
            if random.random() < DROP_BOSS_BREAD:
                self.drops.append((BREAD, mx + 5, my + 5))
            if random.random() < DROP_BOSS_POTION:
                self.drops.append((random.choice(POTION_POOL), mx - 5, my + 5))

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
            self.drops.append((item, monster.x, monster.y - 10))

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
        if not self.drops:
            return
        closest_idx = 0
        closest_dist = float("inf")
        for i, (_, px, py) in enumerate(self.drops):
            d = (self.player.x - px)**2 + (self.player.y - py)**2
            if d < closest_dist:
                closest_dist = d
                closest_idx = i
        if closest_dist > (TILE_SIZE * 1.5)**2:
            return
        item = self.drops[closest_idx][0]
        if add_item(self.backpack, item):
            self.drops.pop(closest_idx)

    # ================================================================
    # 楼层通关
    # ================================================================

    def _on_floor_clear(self) -> str | None:
        if self.current_floor >= 30:
            return "victory"
        # 清除全部 Buff
        self.player.buffs.clear()
        self.player.status_effects.clear()
        self.player._burn_dmg = 0
        self.current_floor += 1
        save_game(self.player, self.backpack, self.revive_system,
                  self.current_floor, self.monsters_killed)
        return "reward"

    # ================================================================
    # 绘制
    # ================================================================

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_BG)
        draw_map(screen, self.grid, self.spawn_pos, self.portal_pos,
                 self.portal_active, self.in_spawn_zone,
                 get_theme(self.current_floor))
        draw_drops(screen, self.drops)
        for monster in self.monsters:
            if monster.is_alive():
                draw_monster(screen, monster)
        self._draw_projectiles(screen)
        draw_player(screen, self.player)
        draw_hud(screen, self.player, self.current_floor,
                 self.revive_system.revives_remaining, get_bold_hud_font())
        # 倒计时 toast
        offset = 0
        if self._spawn_toast:
            draw_toast(screen, self._spawn_toast, get_bold_hud_font(), offset=0)
            offset = 1
        # 传送门倒计时（绿色）
        if self._portal_countdown:
            draw_toast(screen, self._portal_countdown, get_bold_hud_font(), offset=offset, color=(100, 220, 100))
            offset += 1
        # 传送门背包警告（黄色）
        if self._portal_toast:
            draw_toast(screen, self._portal_toast, get_bold_hud_font(), offset=offset, color=(255, 220, 60))
            offset += 1
        # 技能 toast
        for i, t in enumerate(self.toasts):
            draw_toast(screen, t, get_bold_hud_font(), offset=offset + i)

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
            screen.blit(bg_surface, (text_rect.x - 20, text_rect.y - 10))
            screen.blit(text_surface, text_rect)

        # 暂停菜单（V1.0.4 P3）
        if self._paused:
            self._draw_pause_menu(screen)

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
            is_fire = proj.get('burn') is not None
            # 加载图标（缓存）
            icon_key = 'fireball' if is_fire else 'arrow'
            if not hasattr(self, '_proj_icons'): self._proj_icons = {}
            if icon_key not in self._proj_icons:
                fname = 'icon/EntitySprite_fire-charge.webp' if is_fire else 'icon/EntitySprite_arrow.webp'
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
                if is_fire:
                    screen.blit(icon, (px - PROJECTILE_SIZE*3//2, py - PROJECTILE_SIZE*3//2))
                else:
                    # 箭矢：计算旋转角度（默认向右=0°）
                    angle = math.degrees(math.atan2(proj['vy'], proj['vx']))
                    rotated = pygame.transform.rotate(icon, -angle)
                    rw, rh = rotated.get_size()
                    screen.blit(rotated, (px - rw//2, py - rh//2))
            else:
                color = (255, 60, 30) if is_fire else COLOR_PROJECTILE
                pygame.draw.circle(screen, color, (px, py), PROJECTILE_SIZE)
                tail_x = int(px - proj['vx'] * 2)
                tail_y = int(py - proj['vy'] * 2)
                tail_color = (200, 40, 20) if is_fire else (80, 160, 220)
                pygame.draw.line(screen, tail_color, (px, py), (tail_x, tail_y), 3)
