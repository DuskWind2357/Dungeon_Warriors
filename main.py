"""
Dungeon Warriors — 主入口
游戏主循环、状态机调度
"""

import sys
import os
import random
import traceback
import datetime
import pygame
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, COLOR_BG,
    MAX_REVIVES, REVIVE_COUNTDOWN_SEC, GAME_OVER_DELAY_SEC,
    AUTO_DESTROY_LOW_LEVEL_GEAR,
)
from entities.player import Player
from systems.revive_system import ReviveSystem
from systems.inventory import create_empty_backpack
from systems.save_system import save_game, load_game, save_exists, delete_save
from systems.audio_manager import AudioManager
from rendering.renderer import get_title_font, get_button_font, get_hud_font


class Game:
    """游戏主类 — 状态机调度"""

    def __init__(self) -> None:
        pygame.init()
        # 禁用中文输入法 (IME)，防止 WASD 被 IME 拦截
        pygame.key.stop_text_input()
        # 使用 SDL 提示彻底禁用 IME
        pygame.event.set_blocked(pygame.TEXTEDITING)
        pygame.event.set_blocked(pygame.TEXTINPUT)
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Dungeon Warriors")
        self.clock = pygame.time.Clock()
        self.running = True

        # 字体
        self.title_font = get_title_font()
        self.button_font = get_button_font()
        self.hud_font = get_hud_font()

        # 音效
        self.audio = AudioManager()
        self.audio.initialize()

        # 游戏状态
        self.scene: str = "menu"
        self.prev_scene: str = ""  # 用于从背包返回

        # 游戏数据
        self.player: Player | None = None
        self.backpack: list = []
        self.revive_system = ReviveSystem()
        self.current_floor: int = 1
        self.monsters_killed: int = 0
        self.difficulty: str = "easy"  # 默认难度
        self.auto_destroy: bool = AUTO_DESTROY_LOW_LEVEL_GEAR  # 低级装备自动销毁开关

        # V1.0.5 楼层布局缓存（跨场景持久化，解决地图锁定问题）
        self.floor_layout_cache: dict[int, tuple] = {}

        # 场景对象
        self.menu_scene = None
        self.combat_scene = None
        self.backpack_scene = None
        self.reward_scene = None
        self.death_scene = None
        self.victory_scene = None
        self.game_over_scene = None
        self.settings_scene = None

        self._init_menu()

    # ================================================================
    # 菜单 / 新游戏 / 继续
    # ================================================================

    def _init_menu(self) -> None:
        """初始化菜单场景"""
        from scenes.menu_scene import MenuScene
        self.menu_scene = MenuScene()
        self.menu_scene.refresh_labels(save_exists())
        # 每次进入菜单从头循环播放BGM
        self.audio.play_menu_bgm()

    def _new_game(self) -> None:
        """开始新游戏"""
        if save_exists():
            delete_save()
        self.player = Player()
        from data.weapons import WEAPON_BY_NAME
        from data.armor import ARMOR_BY_NAME
        self.player.melee_weapon = WEAPON_BY_NAME["铜剑"]     # 初始近战武器
        self.player.ranged_weapon = WEAPON_BY_NAME["弩（普通）"]  # 初始远程武器
        # 初始护甲：T1五选一
        self.player.armor = random.choice([
            ARMOR_BY_NAME["战袍 (T1)"],
            ARMOR_BY_NAME["猎人之甲 (T1)"],
            ARMOR_BY_NAME["弓箭手之甲 (T1)"],
            ARMOR_BY_NAME["冷酷战甲 (T1)"],
            ARMOR_BY_NAME["窃贼之甲 (T1)"],
        ])
        self.player.heal_full()
        self.backpack = create_empty_backpack()
        self.revive_system.reset()
        self.current_floor = 1
        self.monsters_killed = 0
        self._start_combat()

    def _continue_game(self) -> None:
        """继续游戏（加载存档）"""
        from data.weapons import WEAPON_BY_NAME
        data = load_game()
        if data:
            self.player = data["player"]
            self.backpack = data["backpack"]
            self.revive_system = data["revive_system"]
            self.current_floor = data["current_floor"]
            self.monsters_killed = data["monsters_killed"]
            self.auto_destroy = data.get("auto_destroy", AUTO_DESTROY_LOW_LEVEL_GEAR)
            # 确保玩家有武器
            if self.player.melee_weapon is None:
                self.player.melee_weapon = WEAPON_BY_NAME["铜剑"]
            if self.player.ranged_weapon is None:
                self.player.ranged_weapon = WEAPON_BY_NAME["弩（普通）"]
            # 检查是否在奖励选择界面退出
            if data.get("scene_state") == "reward":
                from scenes.reward_scene import RewardScene
                self.reward_scene = RewardScene(
                    self.player, self.backpack, self.revive_system,
                    self.current_floor, self.auto_destroy
                )
                self.scene = "reward"
                return
        else:
            self._new_game()
            return
        self._start_combat()

    def _start_combat(self) -> None:
        """启动战斗场景"""
        self.audio.fadeout_bgm()  # 离开菜单，淡出BGM
        from scenes.combat_scene import CombatScene
        self.combat_scene = CombatScene(
            self.player, self.backpack, self.revive_system,
            self.current_floor, self.monsters_killed,
            audio_manager=self.audio,
            difficulty=self.difficulty,
            floor_layout_cache=self.floor_layout_cache,
        )
        self.scene = "combat"

    # ================================================================
    # 死亡 / 复活 / 胜利
    # ================================================================

    def _on_player_death(self) -> None:
        """玩家死亡处理"""
        # 清除全部 Buff 和状态效果
        self.player.buffs.clear()
        self.player.status_effects.clear()
        self.player._burn_dmg = 0
        # 清除楼层布局缓存（死亡后重新生成地图）
        self.floor_layout_cache.clear()
        if self.revive_system.consume_revive():
            self.scene = "death"
        else:
            delete_save()
            self.scene = "game_over"

    def _revive_player(self) -> None:
        """复活玩家：HP 回满，装备保留，楼层重置"""
        if self.combat_scene:
            self.player.current_hp = self.player.total_max_hp()
            # 复活时清除楼层缓存，重新生成地图
            self.floor_layout_cache.clear()
            self.combat_scene._floor_layout_cache = self.floor_layout_cache
            self.combat_scene._init_floor()
        self.scene = "combat"

    def _on_victory(self) -> None:
        """通关胜利"""
        delete_save()
        self.scene = "victory"

    # ================================================================
    # 主循环
    # ================================================================

    def run(self) -> None:
        """主游戏循环"""
        frame_count = 0
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 1000.0
                frame_count += 1

                # 每 60 帧打印一次状态
                if frame_count % 60 == 0:
                    print(f"[DEBUG] frame={frame_count} scene={self.scene} fps={self.clock.get_fps():.0f}")

                # ---- 事件 ----
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        print(f"[DEBUG] QUIT event received, exiting")
                        self.running = False
                        break
                    # 记录所有事件类型
                    print(f"[DEBUG] Event: {pygame.event.event_name(event.type)} scene={self.scene}")
                    self._dispatch_event(event)

                if not self.running:
                    break

                # ---- 更新 ----
                self._dispatch_update(dt)

                # ---- 绘制 ----
                self._dispatch_draw(self.screen)
                pygame.display.flip()
        except Exception as e:
            print(f"[ERROR] {e}")
            traceback.print_exc()
        finally:
            print(f"[DEBUG] Game loop ended. Total frames: {frame_count}")
            pygame.quit()
            sys.exit()

    def _dispatch_event(self, event: pygame.event.Event) -> None:
        """分发事件到当前场景"""
        if self.scene == "menu" and self.menu_scene:
            result = self.menu_scene.handle_event(event)
            if result == "continue_or_start":
                if save_exists():
                    self._continue_game()
                else:
                    self._new_game()
            elif result == "new_game":
                self._new_game()
            elif result == "quit":
                self.running = False
            elif result == "settings":
                from scenes.settings_scene import SettingsScene
                self.settings_scene = SettingsScene(self.difficulty)
                self.scene = "settings"

        elif self.scene == "settings" and self.settings_scene:
            result = self.settings_scene.handle_event(event)
            if result == "menu":
                self.difficulty = self.settings_scene.get_difficulty()
                self.auto_destroy = self.settings_scene.get_auto_destroy()
                self._init_menu()
                self.scene = "menu"

        elif self.scene == "combat" and self.combat_scene:
            result = self.combat_scene.handle_event(event)
            if result == "menu":
                self._init_menu()
                self.scene = "menu"
            elif result == "backpack":
                self.prev_scene = "combat"
                from scenes.backpack_scene import BackpackScene
                self.backpack_scene = BackpackScene(
                    self.player, self.backpack, self.audio
                )
                self.scene = "backpack"

        elif self.scene == "backpack" and self.backpack_scene:
            result = self.backpack_scene.handle_event(event)
            if result == "close":
                if self.combat_scene:
                    self.combat_scene.backpack = self.backpack
                self.scene = self.prev_scene

        elif self.scene == "reward" and self.reward_scene:
            result = self.reward_scene.handle_event(event)
            if result == "combat":
                self._start_combat()
            # 不再直接从 handle_event 返回 combat（由 update 延迟返回）

        elif self.scene == "victory" and self.victory_scene:
            result = self.victory_scene.handle_event(event)
            if result == "menu":
                self._init_menu()
                self.scene = "menu"

        elif self.scene == "game_over" and self.game_over_scene:
            result = self.game_over_scene.handle_event(event)
            if result == "menu":
                self._init_menu()
                self.scene = "menu"

    def _dispatch_update(self, dt: float) -> None:
        """分发更新到当前场景"""
        if self.scene == "combat" and self.combat_scene:
            result = self.combat_scene.update(dt)
            if result == "death":
                self._on_player_death()
                if self.scene == "death":
                    from scenes.death_scene import DeathScene
                    self.death_scene = DeathScene(
                        self.revive_system, REVIVE_COUNTDOWN_SEC
                    )
                elif self.scene == "game_over":
                    from scenes.game_over_scene import GameOverScene
                    self.game_over_scene = GameOverScene()
            elif result == "victory":
                from scenes.victory_scene import VictoryScene
                self.victory_scene = VictoryScene()
                self._on_victory()
            elif result == "reward":
                # 同步楼层号并保存奖励状态
                self.current_floor = self.combat_scene.current_floor
                save_game(self.player, self.backpack, self.revive_system,
                          self.current_floor, self.monsters_killed,
                          scene_state="reward", auto_destroy=self.auto_destroy)
                from scenes.reward_scene import RewardScene
                self.reward_scene = RewardScene(
                    self.player, self.backpack, self.revive_system,
                    self.current_floor, self.auto_destroy
                )
                self.scene = "reward"

        elif self.scene == "death" and self.death_scene:
            result = self.death_scene.update(dt)
            if result == "revive":
                self._revive_player()
            elif result == "game_over":
                from scenes.game_over_scene import GameOverScene
                self.game_over_scene = GameOverScene()
                self.scene = "game_over"

        elif self.scene == "victory" and self.victory_scene:
            result = self.victory_scene.update(dt)
            if result == "menu":
                self._init_menu()
                self.scene = "menu"

        elif self.scene == "reward" and self.reward_scene:
            result = self.reward_scene.update(dt)
            if result == "combat":
                self._start_combat()

        elif self.scene == "game_over" and self.game_over_scene:
            result = self.game_over_scene.update(dt)
            if result == "menu":
                self._init_menu()
                self.scene = "menu"

    def _dispatch_draw(self, screen: pygame.Surface) -> None:
        """分发绘制到当前场景"""
        if self.scene == "menu" and self.menu_scene:
            self.menu_scene.draw(screen)

        elif self.scene == "settings" and self.settings_scene:
            self.settings_scene.draw(screen)

        elif self.scene == "combat" and self.combat_scene:
            self.combat_scene.draw(screen)

        elif self.scene == "backpack" and self.backpack_scene:
            if self.combat_scene:
                self.combat_scene.draw(screen)
            self.backpack_scene.draw(screen)

        elif self.scene == "reward" and self.reward_scene:
            if self.combat_scene:
                self.combat_scene.draw(screen)
            self.reward_scene.draw(screen)

        elif self.scene == "death" and self.death_scene:
            if self.combat_scene:
                self.combat_scene.draw(screen)
            self.death_scene.draw(screen)

        elif self.scene == "victory" and self.victory_scene:
            if self.combat_scene:
                self.combat_scene.draw(screen)
            self.victory_scene.draw(screen)

        elif self.scene == "game_over" and self.game_over_scene:
            if self.combat_scene:
                self.combat_scene.draw(screen)
            self.game_over_scene.draw(screen)


def setup_debug_log():
    """将 stdout/stderr 重定向到日志文件"""
    log_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    log_path = os.path.join(log_dir, 'debug.log')
    try:
        log_file = open(log_path, 'w', encoding='utf-8', buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
        print(f'[{datetime.datetime.now()}] Debug log started (frozen={getattr(sys, "frozen", False)})')
        return True
    except Exception as e:
        print(f'Log setup failed: {e}')
        return False


def main():
    # 在初始化 pygame 之前设置 SDL 环境变量，禁用 IME
    os.environ['SDL_IME_INPUT_ENABLED'] = '0'
    os.environ['SDL_HINT_IME_INTERNAL_EDITING'] = '0'
    setup_debug_log()
    print("[DEBUG] Starting Dungeon Warriors (IME disabled)...")
    game = Game()
    print("[DEBUG] Game initialized, starting loop...")
    game.run()


if __name__ == "__main__":
    main()
