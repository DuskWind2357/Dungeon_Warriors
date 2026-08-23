"""
Dungeon Warriors v2.0 — 消耗品定义 (frame.txt)
面包 / 生命药水 / 力量药水 / 隐身药水 / 迅捷药水
"""

from entities.item import Consumable

BREAD = Consumable(name="面包", item_type="heal_50")
HEALTH_POTION = Consumable(name="生命药水", item_type="heal_100")
STRENGTH_POTION = Consumable(name="力量药水", item_type="strength_boost")
INVIS_POTION = Consumable(name="隐身药水", item_type="invis")
SWIFT_POTION = Consumable(name="迅捷药水", item_type="swift")

CONSUMABLES: list[Consumable] = [
    BREAD, HEALTH_POTION, STRENGTH_POTION, INVIS_POTION, SWIFT_POTION,
]
CONSUMABLE_BY_NAME: dict[str, Consumable] = {c.name: c for c in CONSUMABLES}

# 药水类（4选1等概率的池）
POTION_POOL: list[Consumable] = [
    HEALTH_POTION, STRENGTH_POTION, INVIS_POTION, SWIFT_POTION,
]
