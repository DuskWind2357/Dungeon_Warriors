"""
Dungeon Warriors V1.0.5.12 — 音效系统
每怪物类型: 环境音/受击/死亡/弹射物 + BOSS特殊音效
"""

import random
import os
import pygame
from config import MUSIC_ENABLED
from utils import resource_path


class AudioManager:
    """音效管理器（单例）"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init = False
        return cls._instance

    def __init__(self):
        if self._init: return
        self._init = True
        self._enabled = False
        self._sounds: dict[str, dict[str, list[pygame.mixer.Sound]]] = {}
        self._last_play: dict[str, float] = {}
        self._volume: float = 0.7
        # 环境音计时器（按怪物个体）
        self._ambient_timers: dict[int, float] = {}
        # BGM 状态（与音效独立，便于后续扩展）
        self._bgm_enabled: bool = MUSIC_ENABLED
        self._bgm_volume: float = 0.5
        self._current_bgm: str = ""  # 当前播放的BGM文件路径

    def initialize(self):
        try:
            pygame.mixer.init()
            self._enabled = True
        except pygame.error:
            print("[Audio] init failed, silent mode")
            self._enabled = False
            return
        pygame.mixer.set_num_channels(24)
        self._load_all()
        self._load_player_sounds()
        print(f"[Audio] loaded, enabled={self._enabled}")

    # ================================================================
    # 怪物名 → 内部 key 映射
    # ================================================================
    def _monster_key(self, name: str) -> str:
        if "僵尸" in name and "精英" not in name: return "zombie"
        if "精英僵尸" in name: return "zombie"
        if "冰霜僵尸" in name: return "zombie"
        if "骷髅" in name and "精英" not in name: return "skeleton"
        if "精英骷髅" in name: return "skeleton"
        if "流髑" in name: return "skeleton"
        if "史莱姆" in name: return "slime"
        if "蜘蛛" in name: return "spider"
        if "蝙蝠" in name: return "bat"
        if "暗影骑士" in name: return "shadow_knight"
        if "暗黑骑士" in name: return "shadow_knight"
        if "烈焰使者" in name: return "flame_envoy"
        if "炎魔" in name: return "flame_demon"
        if "卫道士" in name: return "vindicator"
        if "掠夺者" in name: return "pillager"
        if "高塔之主" in name: return "tower_master"
        # V1.0.5.12 新增特殊实体音效映射
        if "试炼刷怪笼" in name: return "trial_spawner"
        if "宝箱" in name: return "chest"
        return ""

    # ================================================================
    # 加载所有音效
    # ================================================================
    def _load_all(self):
        base = resource_path("sounds")
        dir_map = {
            "zombie":       "僵尸&精英僵尸",
            "skeleton":     "骷髅&精英骷髅",
            "slime":        "史莱姆",
            "spider":       "蜘蛛",
            "bat":          "蝙蝠",
            "shadow_knight":"暗影骑士&暗黑骑士",
            "flame_envoy":  "烈焰使者&炎魔",
            "flame_demon":  "烈焰使者&炎魔",
            "vindicator":   "卫道士突袭队长",
            "pillager":     "掠夺者突袭队长",
            "tower_master": "高塔之主",
            # V1.0.5.12 新增特殊实体音效目录
            "trial_spawner": "试炼刷怪笼",
            "chest":        "宝箱",
        }
        for key, dname in dir_map.items():
            dp = os.path.join(base, dname)
            if not os.path.exists(dp): continue
            self._sounds[key] = {}
            # 子目录
            for sub in ["环境音","受击","死亡","召唤"]:
                sp = os.path.join(dp, sub)
                if os.path.exists(sp):
                    self._sounds[key][sub] = self._load_files(sp)
            # 根目录文件
            self._sounds[key]["_root"] = self._load_files(dp)

        # V1.0.5 传送门音效
        portal_dir = os.path.join(base, "portal")
        if os.path.exists(portal_dir):
            self._sounds["portal"] = {"_root": self._load_files(portal_dir)}

        # V1.0.5.12 补丁: 特殊宝藏房间解锁音效（sounds/unlock 随机）
        unlock_dir = os.path.join(base, "unlock")
        if os.path.exists(unlock_dir):
            self._sounds["unlock"] = {"_root": self._load_files(unlock_dir)}

        print(f"[Audio] {sum(len(v) for k in self._sounds for v in self._sounds[k].values())} sounds")

    def _load_files(self, path):
        """返回 [(filename, sound), ...] 列表，保留文件名用于后续筛选"""
        sounds = []
        for f in sorted(os.listdir(path)):
            fp = os.path.join(path, f)
            if os.path.isfile(fp) and f.endswith(('.ogg','.mp3','.wav')):
                try:
                    s = pygame.mixer.Sound(fp)
                    s.set_volume(self._volume)
                    sounds.append((f, s))
                except pygame.error: pass
        return sounds

    # ================================================================
    # 播放接口
    # ================================================================
    def _play_pool(self, key, category, cd_tag=None):
        if not self._enabled: return
        pool = self._sounds.get(key, {}).get(category, [])
        if not pool: return
        if cd_tag:
            now = pygame.time.get_ticks()/1000.0
            if now - self._last_play.get(cd_tag, -9) < 0.05: return
            self._last_play[cd_tag] = now
        random.choice(pool)[1].play()

    def _play_root(self, key, prefix, cd_tag=None):
        """播放根目录中文件名以 prefix 开头的音效"""
        if not self._enabled: return
        pool = self._sounds.get(key, {}).get("_root", [])
        matching = [s for fname, s in pool if fname.startswith(prefix)]
        if not matching: return
        if cd_tag:
            now = pygame.time.get_ticks()/1000.0
            if now - self._last_play.get(cd_tag, -9) < 0.05: return
            self._last_play[cd_tag] = now
        random.choice(matching).play()

    # -------- 公开 API --------
    def play_hit(self, monster_name: str):
        key = self._monster_key(monster_name)
        self._play_pool(key, "受击", f"hit_{key}")

    def play_death(self, monster_name: str):
        key = self._monster_key(monster_name)
        # 特殊死亡音效
        if "烈焰使者" in monster_name:
            self._play_root("flame_envoy", "烈焰使者死亡音效")
        elif "炎魔" in monster_name:
            self._play_root("flame_demon", "炎魔死亡音效")
        else:
            self._play_pool(key, "死亡", f"death_{key}")
            if not self._sounds.get(key,{}).get("死亡"):
                self._play_root(key, "", f"death_root_{key}")

    def play_ambient(self, monster_name: str, monster_id: int):
        key = self._monster_key(monster_name)
        now = pygame.time.get_ticks()/1000.0
        last = self._ambient_timers.get(monster_id, 0)
        # V1.0.5.12 试炼刷怪笼环境音间隔5秒，其他怪物3秒
        interval = 5.0 if "试炼刷怪笼" in monster_name else 3.0
        if now - last < interval: return
        if random.random() > 0.5: return     # 50%概率
        self._ambient_timers[monster_id] = now
        self._play_pool(key, "环境音", f"amb_{key}")

    def play_projectile(self, monster_name: str):
        key = self._monster_key(monster_name)
        if key in ("skeleton",):
            self._play_root("skeleton", "射箭", f"arrow")
        elif key == "pillager":
            # V1.0.4 P2：掠夺者突袭队长射箭音效（复用骷髅射箭.ogg）
            self._play_root("skeleton", "射箭", "arrow")
        elif key in ("flame_envoy", "flame_demon", "tower_master"):
            self._play_root(key, "发射火球", f"fireball")

    def play_boss_appear(self):
        self._play_root("tower_master", "BOSS出现", "boss_appear")

    def play_boss_summon(self):
        self._play_root("tower_master", "召唤", "boss_summon")

    def play_boss_ice_fireball(self):
        """V1.0.5.11: 高塔之主发射冰焰弹音效"""
        self._play_root("tower_master", "发射冰焰弹", "boss_ice_fireball")

    def play_reward_bgm(self):
        """V1.0.5.11: 奖励选择界面BGM（循环播放）"""
        self._play_bgm("music/奖励.mp3")

    # ================================================================
    # 玩家音效
    # ================================================================
    def _load_player_sounds(self):
        """加载玩家音效目录"""
        key = "player"
        dp = resource_path(os.path.join("sounds", "玩家"))
        if not os.path.exists(dp): return
        self._sounds[key] = {}
        for sub in ["受击", "燃烧buff"]:
            sp = os.path.join(dp, sub)
            if os.path.exists(sp):
                self._sounds[key][sub] = self._load_files(sp)
        self._sounds[key]["_root"] = self._load_files(dp)

    def play_player_hit(self):
        self._play_pool("player", "受击", "player_hit")

    def play_player_burn_tick(self):
        self._play_pool("player", "燃烧buff", "player_burn")

    def play_player_death(self):
        self._play_root("player", "死亡", "player_death")

    def play_portal_appear(self):
        self._play_root("player", "通关", "portal")

    def play_victory(self):
        """通关胜利音效（V1.0.5.9: 击败高塔之主即时通关）"""
        self._play_root("player", "通关", "victory")

    def play_eat(self):
        self._play_root("player", "eat", "eat_sound")

    def play_drink(self):
        self._play_root("player", "drink", "drink_sound")

    def play_crit(self):
        self._play_root("player", "暴击", "crit_sound")

    def play_instakill_easter_egg(self):
        key = "instakill"
        if key not in self._sounds:
            dp = resource_path(os.path.join("sounds", "玩家", "杀"))
            if os.path.exists(dp):
                self._sounds[key] = {"杀": self._load_files(dp)}
        # BUG 修复: 移除 0.05s 冷却(cd_tag) —— 杀戮之弩一次射击多枚/多目标连续斩杀时,
        # 冷却会吞掉后续斩杀音效, 导致"有时不播放"; 斩杀死目标每次都播放
        self._play_pool(key, "杀")

    def set_volume(self, v): self._volume = max(0, min(1, v))
    @property
    def is_enabled(self): return self._enabled

    # ================================================================
    # V1.0.5 传送门音效
    # ================================================================
    def play_portal_proximity(self):
        """传送门靠近音效"""
        self._play_root("portal", "portal", "portal_proximity")

    def play_portal_trigger(self):
        """传送触发音效"""
        self._play_root("portal", "trigger", "portal_trigger")

    def play_portal_travel(self):
        """传送完成音效"""
        self._play_root("portal", "travel", "portal_travel")

    def play_unlock(self):
        """V1.0.5.12 补丁: 使用钥匙解锁特殊宝藏房间音效（sounds/unlock 随机播放）"""
        self._play_root("unlock", "", "unlock")

    # ================================================================
    # BGM 背景音乐（使用 pygame.mixer.music，与音效互不干扰）
    # ================================================================

    # 楼层 → BGM 映射（V1.0.5.11 音乐添加及播放规则）
    # 值为文件 → 直接循环播放; 值为目录 → 随机取其中一首循环播放
    FLOOR_BGM_MAP: dict[str, str] = {
        "dungeon":         "music/地牢.mp3",      # 1-9 层
        "snow":            "music/雪地",          # 11-19 层（目录随机）
        "hell":            "music/地狱",          # 21-29 层（目录随机）
        "boss_floor":      "music/BOSS.mp3",      # 10/20/30 层（不含BOSS房间）
        "head_boss_room":  "music/头目.mp3",      # 头目BOSS房间（10/20层BOSS战）
        "final_boss_room": "music/高塔之主.mp3",  # 首领BOSS房间（30层BOSS战）
    }

    def _play_bgm(self, relative_path: str) -> None:
        """通用 BGM 播放器（循环播放, 从头开始）"""
        if not self._enabled or not self._bgm_enabled:
            return
        bgm_path = resource_path(relative_path)
        if not os.path.exists(bgm_path):
            print(f"[Audio] BGM not found: {bgm_path}")
            return
        try:
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.set_volume(self._bgm_volume)
            pygame.mixer.music.play(-1)  # -1 = 无限循环
            self._current_bgm = bgm_path
        except pygame.error as e:
            print(f"[Audio] BGM load failed: {e}")

    def play_menu_bgm(self) -> None:
        """播放主菜单BGM（循环播放，从头开始）"""
        self._play_bgm("music/大厅BGM.mp3")

    def play_floor_bgm(self, bgm_key: str) -> None:
        """播放楼层BGM（V1.0.5.11）。目录映射 → 随机取一首循环播放。
        key 未映射或文件缺失时静默停止。"""
        rel = self.FLOOR_BGM_MAP.get(bgm_key)
        if not rel:
            self.stop_bgm()
            return
        path = resource_path(rel)
        if os.path.isdir(path):
            tracks = [f for f in sorted(os.listdir(path))
                      if f.endswith(('.mp3', '.ogg', '.wav'))]
            if not tracks:
                self.stop_bgm()
                return
            self._play_bgm(os.path.join(rel, random.choice(tracks)))
            return
        if not os.path.exists(path):
            self.stop_bgm()
            return
        self._play_bgm(rel)

    def stop_bgm(self) -> None:
        """立即停止BGM"""
        pygame.mixer.music.stop()
        self._current_bgm = ""

    def ensure_menu_bgm(self) -> None:
        """确保主菜单BGM在播放；若已在播放则保持原进度，不从头开始"""
        if not self._enabled or not self._bgm_enabled:
            return
        if pygame.mixer.music.get_busy():
            return
        self.play_menu_bgm()

    def fadeout_bgm(self, ms: int = 1000) -> None:
        """淡出停止BGM（默认1秒过渡）"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(ms)
        self._current_bgm = ""

    def set_bgm_volume(self, v: float) -> None:
        """设置BGM音量（0.0~1.0）"""
        self._bgm_volume = max(0.0, min(1.0, v))
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(self._bgm_volume)

    def toggle_bgm(self) -> None:
        """切换BGM开关"""
        self._bgm_enabled = not self._bgm_enabled
        if not self._bgm_enabled:
            self.stop_bgm()

    def set_bgm_enabled(self, enabled: bool) -> None:
        """设置BGM开关；关闭时立即停止当前音乐"""
        self._bgm_enabled = bool(enabled)
        if not self._bgm_enabled:
            self.stop_bgm()

    @property
    def bgm_enabled(self) -> bool:
        return self._bgm_enabled
