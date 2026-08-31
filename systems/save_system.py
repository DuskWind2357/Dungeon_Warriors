"""
Dungeon Warriors — 存档系统
JSON 格式存档/读档
"""

import json
import os
import sys
from pathlib import Path
from entities.player import Player
from entities.item import Weapon, Armor, Consumable, KeyItem
from systems.revive_system import ReviveSystem
from data.weapons import WEAPON_BY_NAME
from data.armor import ARMOR_BY_NAME
from data.consumables import CONSUMABLE_BY_NAME
from data.keys import KEY_BY_NAME
from config import INVENTORY_SIZE

SAVE_FILE = "save.json"
SAVE_VERSION = 2


def get_save_path() -> Path:
    """获取存档文件完整路径（兼容 dev 和 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包：存档放在 exe 所在目录
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent
    return base_dir / SAVE_FILE


def save_exists() -> bool:
    """检查存档文件是否存在"""
    return get_save_path().exists()


def delete_save() -> None:
    """删除存档文件"""
    path = get_save_path()
    if path.exists():
        path.unlink()


def mark_game_completed() -> None:
    """通关后清除进度并存档已通关标记（V1.0.5.9 重新应用）

    save.json 将只保留 {"version", "game_completed"} 字段,
    load_game() 读到该标记时返回 None（视为无有效进度）。
    """
    data = {
        "version": SAVE_VERSION,
        "game_completed": True,
    }
    try:
        path = get_save_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # 写档失败不阻断胜利流程


def is_game_completed() -> bool:
    """检查存档是否为已通关标记; 文件缺失/损坏时返回 False"""
    path = get_save_path()
    if not path.exists():
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("game_completed", False))
    except (json.JSONDecodeError, OSError, ValueError, AttributeError):
        return False


def save_game(player: Player, backpack: list,
              revive_system: ReviveSystem,
              current_floor: int,
              monsters_killed: int,
              scene_state: str = "combat",
              auto_destroy: bool = False,
              music_enabled: bool = True,
              difficulty: str = "easy") -> None:
    """保存游戏到 JSON 文件（V1.0.5.10: 增加难度字段）"""
    data = {
        "version": SAVE_VERSION,
        "current_floor": current_floor,
        "monsters_killed": monsters_killed,
        "scene_state": scene_state,
        "auto_destroy": auto_destroy,
        "music_enabled": music_enabled,
        "difficulty": difficulty,
        "revive": revive_system.to_dict(),
        "player": _serialize_player(player),
        "backpack": _serialize_backpack(backpack),
    }

    path = get_save_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_game() -> dict | None:
    """从 JSON 文件加载游戏数据，失败返回 None"""
    path = get_save_path()
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # V1.0.5.9 已通关标记存档: 无有效进度, 视为无存档
        if data.get("game_completed", False):
            return None

        version = data.get("version", 0)
        if not isinstance(version, (int, float)) or version < 1:
            return None

        # 重建 Player
        player = _deserialize_player(data.get("player", {}))

        # 重建背包
        backpack = _deserialize_backpack(data.get("backpack", []))

        # 重建复活系统
        revive_system = ReviveSystem.from_dict(data.get("revive", {}))

        return {
            "player": player,
            "backpack": backpack,
            "revive_system": revive_system,
            "current_floor": data.get("current_floor", 1),
            "monsters_killed": data.get("monsters_killed", 0),
            "scene_state": data.get("scene_state", "combat"),
            "auto_destroy": data.get("auto_destroy", False),
            "music_enabled": data.get("music_enabled", True),
            "difficulty": data.get("difficulty", "easy"),
        }
    except (json.JSONDecodeError, KeyError, TypeError,
            ValueError, AttributeError, OSError):
        return None


def _serialize_player(player: Player) -> dict:
    """序列化玩家数据"""
    return {
        "current_hp": player.current_hp,
        "difficulty": player.difficulty,
        "boss_kills": player.boss_kills,
        "elite_kills": player.elite_kills,
        "_burn_dmg": player._burn_dmg,
        "_burn_level": player._burn_level,
        "status_levels": dict(player.status_levels),
        "buffs": dict(player.buffs),
        "status_effects": dict(player.status_effects),
        "melee_weapon": player.melee_weapon.name if player.melee_weapon else None,
        "ranged_weapon": player.ranged_weapon.name if player.ranged_weapon else None,
        "armor": player.armor.name if player.armor else None,
    }


def _deserialize_player(data: dict) -> Player:
    """反序列化玩家数据（防御式：字段缺失/类型错误/空值均回退默认）"""
    player = Player()

    hp = data.get("current_hp")
    player.current_hp = int(hp) if isinstance(hp, (int, float)) else player.base_hp

    # V1.0.5.10: 玩家难度（成长参数取值依据；缺失/非法时回退默认）
    saved_difficulty = data.get("difficulty")
    if isinstance(saved_difficulty, str) and saved_difficulty:
        player.difficulty = saved_difficulty

    bk = data.get("boss_kills")
    player.boss_kills = int(bk) if isinstance(bk, (int, float)) else 0

    ek = data.get("elite_kills")
    player.elite_kills = int(ek) if isinstance(ek, (int, float)) else 0

    bd = data.get("_burn_dmg")
    player._burn_dmg = float(bd) if isinstance(bd, (int, float)) else 7.0

    # buffs/status_effects 必须是 dict 且值均为数值，否则整体回退为空
    raw_buffs = data.get("buffs")
    player.buffs = ({k: float(v) for k, v in raw_buffs.items()
                     if isinstance(v, (int, float))}
                    if isinstance(raw_buffs, dict) else {})

    raw_se = data.get("status_effects")
    player.status_effects = ({k: float(v) for k, v in raw_se.items()
                              if isinstance(v, (int, float))}
                             if isinstance(raw_se, dict) else {})

    # V1.0.5.9: 状态等级（防御式：仅接受正整数等级）
    raw_sl = data.get("status_levels")
    player.status_levels = ({k: int(v) for k, v in raw_sl.items()
                             if isinstance(k, str) and isinstance(v, (int, float)) and v > 0}
                            if isinstance(raw_sl, dict) else {})
    bl = data.get("_burn_level")
    player._burn_level = int(bl) if isinstance(bl, (int, float)) and bl > 0 else 2

    melee_name = data.get("melee_weapon")
    ranged_name = data.get("ranged_weapon")
    if isinstance(melee_name, str) and melee_name in WEAPON_BY_NAME:
        player.melee_weapon = WEAPON_BY_NAME[melee_name]
    if isinstance(ranged_name, str) and ranged_name in WEAPON_BY_NAME:
        player.ranged_weapon = WEAPON_BY_NAME[ranged_name]

    armor_name = data.get("armor")
    if isinstance(armor_name, str) and armor_name in ARMOR_BY_NAME:
        player.armor = ARMOR_BY_NAME[armor_name]

    return player


def _serialize_backpack(backpack: list) -> list:
    """序列化背包"""
    result = []
    for item in backpack:
        if item is None:
            result.append(None)
        elif isinstance(item, Weapon):
            result.append({"type": "weapon", "name": item.name})
        elif isinstance(item, Armor):
            result.append({"type": "armor", "name": item.name})
        elif isinstance(item, Consumable):
            result.append({"type": "consumable", "name": item.name})
        elif isinstance(item, KeyItem):
            result.append({"type": "key", "name": item.name})
        else:
            result.append(None)
    return result


def _deserialize_backpack(data: list) -> list:
    """反序列化背包（补齐至标准容量，防止旧档/损坏档导致索引越界）"""
    backpack = []
    for entry in (data if isinstance(data, list) else []):
        if entry is None:
            backpack.append(None)
        elif isinstance(entry, dict):
            item_type = entry.get("type")
            name = entry.get("name", "")
            if item_type == "weapon" and isinstance(name, str) and name in WEAPON_BY_NAME:
                backpack.append(WEAPON_BY_NAME[name])
            elif item_type == "armor" and isinstance(name, str) and name in ARMOR_BY_NAME:
                backpack.append(ARMOR_BY_NAME[name])
            elif item_type == "consumable" and isinstance(name, str) and name in CONSUMABLE_BY_NAME:
                backpack.append(CONSUMABLE_BY_NAME[name])
            elif item_type == "key" and isinstance(name, str) and name in KEY_BY_NAME:
                backpack.append(KEY_BY_NAME[name])
            else:
                backpack.append(None)
        else:
            backpack.append(None)
    while len(backpack) < INVENTORY_SIZE:
        backpack.append(None)
    return backpack
