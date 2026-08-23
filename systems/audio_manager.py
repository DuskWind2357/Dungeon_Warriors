"""
Dungeon Warriors V1.0.2 — 音效系统
每怪物类型: 环境音/受击/死亡/弹射物 + BOSS特殊音效
"""

import random
import os
import pygame
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
        if "骷髅" in name and "精英" not in name: return "skeleton"
        if "精英骷髅" in name: return "skeleton"
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
        }
        for key, dname in dir_map.items():
            dp = os.path.join(base, dname)
            if not os.path.exists(dp): continue
            self._sounds[key] = {}
            # 子目录
            for sub in ["环境音","受击","死亡"]:
                sp = os.path.join(dp, sub)
                if os.path.exists(sp):
                    self._sounds[key][sub] = self._load_files(sp)
            # 根目录文件
            self._sounds[key]["_root"] = self._load_files(dp)
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
        if now - last < 3.0: return          # 每3秒
        if random.random() > 0.5: return     # 50%概率
        self._ambient_timers[monster_id] = now
        self._play_pool(key, "环境音", f"amb_{key}")

    def play_projectile(self, monster_name: str):
        key = self._monster_key(monster_name)
        if key in ("skeleton",):
            self._play_root("skeleton", "射箭", f"arrow")
        elif key in ("flame_envoy", "flame_demon", "tower_master"):
            self._play_root(key, "发射火球", f"fireball")

    def play_boss_appear(self):
        self._play_root("tower_master", "BOSS出现", "boss_appear")

    def play_boss_summon(self):
        self._play_root("tower_master", "召唤", "boss_summon")

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
        self._play_pool(key, "杀", "instakill")

    def set_volume(self, v): self._volume = max(0, min(1, v))
    @property
    def is_enabled(self): return self._enabled
