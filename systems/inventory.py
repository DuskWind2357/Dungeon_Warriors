"""
Dungeon Warriors v2.0 — 背包系统
30格（5×6），新消耗品支持（隐身/迅捷/HoT面包）
"""

from entities.item import Weapon, Armor, Consumable, Item
from entities.player import Player
from systems.audio_manager import AudioManager
from config import (
    INVENTORY_SIZE, INVENTORY_COLS, INVENTORY_ROWS,
    STRENGTH_POTION_DURATION, INVIS_POTION_DURATION, SWIFT_POTION_DURATION,
)


def create_empty_backpack() -> list[Item | None]:
    """创建空背包"""
    return [None] * INVENTORY_SIZE


def find_empty_slot(backpack: list[Item | None]) -> int | None:
    """查找第一个空格，返回索引；无空格返回 None"""
    for i, slot in enumerate(backpack):
        if slot is None:
            return i
    return None


def count_empty_slots(backpack: list[Item | None]) -> int:
    """统计空格数量"""
    return sum(1 for s in backpack if s is None)


def is_backpack_full(backpack: list[Item | None]) -> bool:
    """背包是否已满"""
    return find_empty_slot(backpack) is None


def count_item(backpack: list[Item | None], item_type: str) -> int:
    """统计背包中指定类型的消耗品数量"""
    from entities.item import Consumable
    return sum(1 for s in backpack if s is not None and isinstance(s, Consumable) and s.item_type == item_type)


def find_item(backpack: list[Item | None], item_type: str) -> int | None:
    """查找第一个指定类型消耗品的槽位"""
    from entities.item import Consumable
    for i, s in enumerate(backpack):
        if s is not None and isinstance(s, Consumable) and s.item_type == item_type:
            return i
    return None


def add_item(backpack: list[Item | None], item: Item) -> bool:
    """添加物品到背包，成功返回 True，背包满返回 False"""
    slot = find_empty_slot(backpack)
    if slot is None:
        return False
    backpack[slot] = item
    return True


def remove_item(backpack: list[Item | None], slot_index: int) -> Item | None:
    """从指定格子移除物品并返回"""
    if 0 <= slot_index < INVENTORY_SIZE:
        item = backpack[slot_index]
        backpack[slot_index] = None
        return item
    return None


def get_slot_at_position(mouse_x: int, mouse_y: int,
                         grid_x: int, grid_y: int,
                         slot_size: int, gap: int) -> int | None:
    """
    根据鼠标坐标计算点击的是哪个格子。
    返回格子索引（0-19），未命中返回 None。
    """
    col = (mouse_x - grid_x) // (slot_size + gap)
    row = (mouse_y - grid_y) // (slot_size + gap)

    if 0 <= col < INVENTORY_COLS and 0 <= row < INVENTORY_ROWS:
        # 检查是否在格子内部（不在间隙中）
        local_x = mouse_x - grid_x - col * (slot_size + gap)
        local_y = mouse_y - grid_y - row * (slot_size + gap)
        if local_x < slot_size and local_y < slot_size:
            return row * INVENTORY_COLS + col

    return None


def use_item(player: Player, backpack: list[Item | None],
              slot_index: int) -> str:
    """
    使用/装备指定格子的物品。
    返回操作描述字符串（用于 UI 反馈）。
    """
    item = backpack[slot_index]
    if item is None:
        return ""

    if isinstance(item, Consumable):
        return _use_consumable(player, backpack, slot_index, item)
    elif isinstance(item, Weapon):
        return _equip_weapon(player, backpack, slot_index, item)
    elif isinstance(item, Armor):
        return _equip_armor(player, backpack, slot_index, item)

    return ""


def destroy_item(backpack: list[Item | None], slot_index: int) -> str:
    """销毁指定格子的物品，返回物品名称"""
    item = remove_item(backpack, slot_index)
    if item:
        name = item.name
        return f"已销毁 {name}"
    return ""


def pickup_item(player: Player, backpack: list[Item | None],
                item: Item) -> bool:
    """拾取物品到背包，成功返回 True"""
    return add_item(backpack, item)


def _use_consumable(player: Player, backpack: list[Item | None],
                    slot_index: int, item: Consumable) -> str:
    """使用消耗品（v2.0 Buff 计时器 + 5s同种冷却）"""
    import pygame
    now = pygame.time.get_ticks() / 1000.0
    if not player.can_use_consumable(item.item_type, now):
        return f"{item.name} 冷却中，请稍后再试"

    player.mark_consumable_used(item.item_type, now)

    if item.item_type == "heal_50":
        # 面包: 5秒 HoT
        player.add_buff("heal_over_time", 5.0)
        backpack[slot_index] = None
        AudioManager().play_eat()
        return f"使用 {item.name}，5秒内持续回复生命"
    elif item.item_type == "heal_100":
        player.heal_full()
        backpack[slot_index] = None
        AudioManager().play_drink()
        return f"使用 {item.name}，生命回满"
    elif item.item_type == "strength_boost":
        player.add_buff("strength", STRENGTH_POTION_DURATION)
        backpack[slot_index] = None
        AudioManager().play_drink()
        return f"使用 {item.name}，15秒攻击力×2"
    elif item.item_type == "invis":
        player.add_buff("invisible", INVIS_POTION_DURATION)
        backpack[slot_index] = None
        AudioManager().play_drink()
        return f"使用 {item.name}，15秒隐身"
    elif item.item_type == "swift":
        player.add_buff("swift", SWIFT_POTION_DURATION)
        backpack[slot_index] = None
        AudioManager().play_drink()
        return f"使用 {item.name}，15秒移速×2"
    return ""


def _equip_weapon(player: Player, backpack: list[Item | None],
                  slot_index: int, weapon: Weapon) -> str:
    """装备武器到对应槽位（近战→近战槽，远程→远程槽）"""
    if weapon.category == "melee":
        old = player.equip_melee_weapon(weapon)
    else:
        old = player.equip_ranged_weapon(weapon)

    # 如果槽位校验失败（old is None 且武器未装备成功）
    if old is None:
        current = player.melee_weapon if weapon.category == "melee" else player.ranged_weapon
        if current is not weapon:
            return f"无法装备 {weapon.name}：槽位类型不匹配"

    backpack[slot_index] = None
    if old:
        backpack[slot_index] = old
        return f"装备 {weapon.name}（换下 {old.name}）"
    return f"装备 {weapon.name}"


def _equip_armor(player: Player, backpack: list[Item | None],
                 slot_index: int, armor: Armor) -> str:
    """装备护甲，自动交换"""
    old = player.equip_armor(armor)
    backpack[slot_index] = None

    if old:
        backpack[slot_index] = old
        return f"装备 {armor.name}（换下 {old.name}）"
    return f"装备 {armor.name}"
