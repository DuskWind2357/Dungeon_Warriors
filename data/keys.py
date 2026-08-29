"""
Dungeon Warriors V1.0.5.6 — 钥匙道具定义
藏宝室钥匙：头目BOSS战掉落，用于解锁特殊宝藏房间
"""

from entities.item import KeyItem

TREASURE_KEY = KeyItem(name="藏宝室钥匙")

KEY_BY_NAME: dict[str, KeyItem] = {TREASURE_KEY.name: TREASURE_KEY}
