"""
Dungeon Warriors v2.0 — 战斗系统
武器类型分发、连击、暴击、秒杀、移动限制、伤害减免
"""

import math
import random
from config import MONSTER_DETECT_RANGE, TILE_SIZE
from entities.player import Player
from entities.monster import Monster


def player_melee_attack(player: Player, monsters: list[Monster]) -> list[Monster]:
    """
    玩家近战攻击：根据武器类型执行不同逻辑。
    返回被击中的怪物列表。
    """
    weapon = player.melee_weapon
    if not weapon or weapon.category != "melee":
        return []
    if player.attack_cooldown > 0:
        return []

    atk = player.total_melee_attack()
    if atk <= 0:
        return []

    # 连击系统
    if weapon.combo_count > 1:
        player.combo_counter += 1
        if player.combo_counter >= weapon.combo_count:
            player.attack_cooldown = weapon.cooldown
            player.combo_counter = 0
    elif weapon.overheat_count > 0:
        # 过热机制
        if not hasattr(player, '_overheat_cnt'): player._overheat_cnt = 0
        player._overheat_cnt += 1
        if player._overheat_cnt >= weapon.overheat_count:
            player.attack_cooldown = weapon.overheat_cd
            player._overheat_cnt = 0
            player._overheat_msg = True
        # 未过热时不设冷却
    else:
        player.attack_cooldown = weapon.cooldown

    # 范围判定
    attack_range_px = weapon.attack_range * TILE_SIZE

    # 朝向向量
    dx = math.cos(player.facing_angle)
    dy = math.sin(player.facing_angle)

    hit_monsters: list[Monster] = []

    for monster in monsters:
        if not monster.is_alive():
            continue

        mx = monster.x - player.x
        my = monster.y - player.y
        dist = math.sqrt(mx * mx + my * my)

        if dist > attack_range_px + TILE_SIZE // 3:
            continue

        # 扇形判定（dot product）
        if dist > 0:
            dot = (mx / dist) * dx + (my / dist) * dy
            if dot < 0.3:
                continue

        _deal_damage_to_monster(player, monster, atk, hit_monsters)

    return hit_monsters


def player_ranged_attack(player: Player,
                         mouse_x: float, mouse_y: float) -> list[dict] | None:
    """
    玩家远程攻击：返回投射物数据 dict 或 None。
    移动中不能攻击的武器在此检查。
    """
    weapon = player.ranged_weapon
    if not weapon or weapon.category != "ranged":
        return None
    if player.ranged_cooldown > 0:
        return None

    # 移动限制（弓）
    if weapon.move_restricted:
        import pygame
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]:
            return None

    atk = player.total_ranged_attack()
    if atk <= 0:
        return None

    # 过热机制（机械弩）
    if weapon.overheat_count > 0:
        if not hasattr(player, '_ranged_overheat_cnt'): player._ranged_overheat_cnt = 0
        player._ranged_overheat_cnt += 1
        if player._ranged_overheat_cnt >= weapon.overheat_count:
            player.ranged_cooldown = weapon.overheat_cd
            player._ranged_overheat_cnt = 0
            player._ranged_overheat_msg = True
        # 未过热不设冷却
    else:
        player.ranged_cooldown = weapon.cooldown

    # 三重射击（幻术师弓 60%）
    count = 3 if (weapon.triple_shot_chance > 0 and random.random() < weapon.triple_shot_chance) else 1

    # 投射方向
    dx = mouse_x - player.x
    dy = mouse_y - player.y
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 1:
        dx, dy = 1.0, 0.0
        dist = 1.0

    from config import PROJECTILE_SPEED
    vx = (dx / dist) * PROJECTILE_SPEED
    vy = (dy / dist) * PROJECTILE_SPEED

    # 更新朝向
    player.facing_angle = math.atan2(dy, dx)

    projectiles = []
    for j in range(count):
        spread = (j - 1) * 0.08 if count > 1 else 0
        a = math.atan2(dy, dx) + spread
        vx_j = math.cos(a) * PROJECTILE_SPEED
        vy_j = math.sin(a) * PROJECTILE_SPEED
        projectiles.append({
            'x': player.x, 'y': player.y,
            'vx': vx_j, 'vy': vy_j,
            'damage': atk,
            'traveled': 0.0,
            'weapon': weapon,
        })
    return projectiles


def projectile_hit_monster(projectile: dict, monster: Monster,
                            player: Player) -> bool:
    """
    投射物命中怪物，处理暴击/秒杀/远程免疫。
    返回 True 表示投射物应被销毁。
    """
    weapon = projectile.get('weapon')
    damage = projectile['damage']

    # BOSS 远程免疫
    if monster.ranged_immune:
        return False  # 穿透不销毁

    # 秒杀判定（杀戮之弩）
    if weapon and weapon.instakill:
        rate = weapon.instakill.get(monster.monster_type, 0)
        # 首领只有在 HP>30% 时才可能被秒杀
        if monster.monster_type == "final_boss" and monster.hp_ratio <= 0.30:
            rate = 0
        if rate > 0 and random.random() < rate:
            monster.hp = 0
            monster.alive = False
            # 杀戮之弩彩蛋音效
            from systems.audio_manager import AudioManager
            AudioManager().play_instakill_easter_egg()
            return True

    # 暴击判定（力量弓/精英之弓）
    if weapon and weapon.crit_chance > 0:
        if random.random() < weapon.crit_chance:
            damage = int(damage * weapon.crit_mult)
            projectile['crit_triggered'] = True

    monster.take_damage(damage)

    return True


def _deal_damage_to_monster(player: Player, monster: Monster,
                            damage: int, hit_list: list) -> None:
    """对怪物造成伤害并加入命中列表"""
    # 秒杀判定
    weapon = player.melee_weapon
    if weapon and weapon.instakill:
        rate = weapon.instakill.get(monster.monster_type, 0)
        if monster.monster_type == "final_boss" and monster.hp_ratio <= 0.30:
            rate = 0
        if rate > 0 and random.random() < rate:
            monster.hp = 0
            monster.alive = False
            hit_list.append(monster)
            return

    monster.take_damage(damage)
    hit_list.append(monster)


# ================================================================
# 怪物 AI 辅助
# ================================================================

def monster_attack_player(monster: Monster, player: Player) -> bool:
    """怪物攻击玩家，返回是否命中"""
    if monster.cooldown_remaining > 0:
        return False
    if not monster.is_alive():
        return False

    attack_range_px = monster.attack_range * TILE_SIZE
    dx = player.x - monster.x
    dy = player.y - monster.y
    dist = math.sqrt(dx * dx + dy * dy)

    if dist > attack_range_px + 5:
        return False

    player.take_damage(monster.attack)
    monster.cooldown_remaining = monster.attack_cooldown

    return True


def is_in_range(x1: float, y1: float, x2: float, y2: float,
                detect_range: float) -> bool:
    dx = x2 - x1
    dy = y2 - y1
    return (dx * dx + dy * dy) <= detect_range * detect_range


def move_toward(ex: float, ey: float, tx: float, ty: float,
                speed: float) -> tuple[float, float]:
    dx = tx - ex
    dy = ty - ey
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 2:
        return ex, ey
    return ex + (dx / dist) * speed, ey + (dy / dist) * speed
