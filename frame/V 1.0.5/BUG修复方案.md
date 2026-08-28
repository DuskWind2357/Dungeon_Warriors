# V1.0.5 BUG修复方案

---

## 一、BUG清单与修复计划

### BUG1: 通关奖励自动装备 + 低级装备自动销毁

**问题描述**：
- 通关后选择的武器或护甲需要自动装备
- 被替换下来的装备，如果等级 < 奖励等级，则自动销毁
- T5和特殊装备视为同级
- 功能可手动设置开关

**修复方案**：
1. **修改 `reward_scene.py`**：
   - 在选择武器/护甲奖励时，检查玩家当前装备等级
   - 如果奖励等级 > 当前装备等级，自动装备
   - 如果奖励等级 < 当前装备等级，检查设置开关
   - 开关开启时，销毁低级装备

2. **修改 `settings_scene.py`**：
   - 添加"低级装备自动销毁"开关（ON/OFF）
   - 默认值：OFF

3. **修改 `config.py`**：
   - 添加配置项 `AUTO_DESTROY_LOW_LEVEL_GEAR = False`

4. **修改 `save_system.py`**：
   - 保存设置开关状态

**涉及文件**：
- `scenes/reward_scene.py`
- `scenes/settings_scene.py`
- `config.py`
- `systems/save_system.py`

---

### BUG2: 传送门贴图显示问题

**问题描述**：
- 传送门所处位置的方块贴图未正常生成，显示为黑色空位

**修复方案**：
1. **修改 `rendering/renderer.py`**：
   - 检查 `draw_map` 函数中传送门位置的绘制逻辑
   - 确保传送门位置先绘制地板贴图，再绘制传送门贴图
   - 修复传送门位置的渲染顺序

**涉及文件**：
- `rendering/renderer.py`

---

### BUG3: 文案提示系统优化

**问题描述**：
- 玩家进入跨房间传送门区域时，需要持续提示紫色"按F键传送"
- 完成楼层战斗时（非BOSS层），需要弹出金色字体提示

**修复方案**：
1. **修改 `scenes/combat_scene.py`**：
   - 在 `_update_portals` 函数中添加传送区域检测
   - 检测玩家是否在传送门附近，显示紫色提示
   - 按F后切换为绿色传送倒计时
   - 在 `_on_floor_clear` 函数中添加金色提示

2. **修改 `rendering/renderer.py`**：
   - 添加提示文字渲染方法

**涉及文件**：
- `scenes/combat_scene.py`
- `rendering/renderer.py`

---

### BUG4: 副本卡顿问题

**问题描述**：
- 玩家进入副本后，游戏变得异常卡顿

**修复方案**：
1. **检查 `systems/floor_manager.py`**：
   - 检查副本房间的怪物生成逻辑
   - 检查副本房间的地图生成逻辑
   - 确认副本不刷新怪物

2. **检查 `scenes/combat_scene.py`**：
   - 检查副本房间的更新逻辑
   - 检查副本房间的渲染逻辑
   - 排除性能瓶颈

3. **检查 `rendering/renderer.py`**：
   - 检查副本房间的渲染逻辑
   - 排除渲染性能问题

**涉及文件**：
- `systems/floor_manager.py`
- `scenes/combat_scene.py`
- `rendering/renderer.py`

---

### BUG5: 宝藏室地图架构优化

**问题描述**：
- 宝藏室为战斗房间或副本额外连通的房间
- 通向宝藏室的传送门必须位于不相邻的墙壁上
- 未完成战斗时，靠近宝藏室传送门提示"传送门已被封印"
- 完成战斗后，传送门正常开启

**修复方案**：
1. **修改 `systems/floor_manager.py`**：
   - 添加宝藏室生成逻辑
   - 确保传送门位置不相邻
   - 副本宝藏室刷新概率100%
   - 战斗房间宝藏室刷新概率90%

2. **修改 `scenes/combat_scene.py`**：
   - 添加宝藏室传送门检测逻辑
   - 未完成战斗时显示"传送门已被封印"
   - 完成战斗后正常开启

3. **修改 `rendering/renderer.py`**：
   - 宝藏室传送门使用特殊贴图
   - 通向副本的传送门使用 `BlockSprite_end-gateway.webp`

**涉及文件**：
- `systems/floor_manager.py`
- `scenes/combat_scene.py`
- `rendering/renderer.py`

---

## 二、执行顺序

### 阶段1: 基础修复（优先级高）
1. 创建fix分支
2. 修复BUG2: 传送门贴图显示问题
3. 修复BUG4: 副本卡顿问题

### 阶段2: 功能优化（优先级中）
4. 修复BUG1: 通关奖励自动装备 + 低级装备自动销毁
5. 更新设置菜单添加低级装备自动销毁开关
6. 优化BUG3: 文案提示系统

### 阶段3: 架构优化（优先级中）
7. 优化BUG5: 宝藏室地图架构

### 阶段4: 收尾工作
8. 打包测试
9. 更新markdown文档

---

## 三、技术细节

### BUG1 技术细节

```python
# reward_scene.py 选择奖励时的逻辑
def _select_reward(self, index):
    reward = self.options[index]
    if reward["type"] in ("melee", "ranged", "armor"):
        # 获取当前装备等级
        if reward["type"] == "melee":
            current_level = self.player.melee_level
            current_tier = self.player.melee_tier
        elif reward["type"] == "ranged":
            current_level = self.player.ranged_level
            current_tier = self.player.ranged_tier
        else:
            current_level = self.player.armor_level
            current_tier = self.player.armor_tier
        
        # 比较等级
        new_level = reward["level"]
        new_tier = reward["tier"]
        
        # T5和特殊视为同级
        if current_tier == 5 or current_tier == 99:
            current_level = 5
        if new_tier == 5 or new_tier == 99:
            new_level = 5
        
        # 自动装备
        if new_level > current_level:
            self._equip_reward(reward)
            # 检查设置开关
            if config.AUTO_DESTROY_LOW_LEVEL_GEAR:
                self._destroy_low_level_gear(reward["type"])
```

### BUG4 技术细节

副本卡顿可能原因：
1. 副本房间怪物生成逻辑异常
2. 副本房间地图渲染复杂度过高
3. 副本房间更新逻辑存在无限循环

检查点：
- `floor_manager.py` 中 `spawn_monsters_for_room` 函数
- `combat_scene.py` 中副本房间的更新逻辑
- `renderer.py` 中副本房间的渲染逻辑

### BUG5 技术细节

传送门位置不相邻算法：
```python
def _is_adjacent(self, side1, offset1, side2, offset2):
    """检查两个传送门位置是否相邻"""
    # 同一墙壁上的传送门
    if side1 == side2:
        return abs(offset1 - offset2) <= 1
    
    # 相邻墙壁
    adjacent_walls = {
        "left": ["top", "bottom"],
        "right": ["top", "bottom"],
        "top": ["left", "right"],
        "bottom": ["left", "right"]
    }
    
    if side2 in adjacent_walls.get(side1, []):
        # 检查角落位置
        if side1 == "left" and side2 == "top":
            return offset1 == 0 and offset2 == 0
        # ... 其他角落情况
    
    return False
```

---

## 四、V1.0.5.3 BUG修复方案（2026年8月28日追加）

### BUG6: 地图结构锁定机制失效

**根本原因**：
- `_floor_layout_cache` 是 `CombatScene` 的实例变量
- 每次调用 `_start_combat()` 都会创建新的 `CombatScene` 实例
- 新实例的缓存为空，导致地图每次都重新生成

**修复方案**：
1. **修改 `main.py`**：
   - 将 `floor_layout_cache` 从 `CombatScene` 实例变量迁移至 `Game` 类实例变量
   - 缓存格式: `dict[int, tuple[FloorLayout, dict[int, bool]]]`
   - `_start_combat()` 创建 `CombatScene` 时传入缓存引用
   - `_on_player_death()` 清除 `Game.floor_layout_cache`
   - `_revive_player()` 重新传递缓存引用

2. **修改 `scenes/combat_scene.py`**：
   - 构造函数新增 `floor_layout_cache` 参数
   - `_init_floor()` 从外部缓存读取/写入布局
   - `room_cleared` 字典与缓存共享引用，修改同步

**涉及文件**：
- `main.py`
- `scenes/combat_scene.py`

---

### BUG7: 通关传送门常开 + 绘制不全

**问题描述**：
- 通关传送门在玩家离开区域后关闭，需要常开
- 通关传送门绘制不全

**修复方案**：
1. **修改 `scenes/combat_scene.py`**：
   - `_is_floor_cleared()` 返回 True 后立即设置 `self.portal_active = True`
   - 移除玩家离开时的 `self.portal_active = False` 逻辑
   - 只在楼层未通关时关闭传送门

2. **修改 `rendering/renderer.py`**：
   - `_draw_floor_portal()` 改用传送门贴图渲染（不再只画圆）
   - 激活后叠加紫色脉冲光效

**涉及文件**：
- `scenes/combat_scene.py`
- `rendering/renderer.py`

---

### BUG8: 副本传送门贴图落实

**问题描述**：
- 通向副本的传送门贴图须使用 `BlockSprite_end-gateway.webp`
- 原实现未区分目标房间类型

**修复方案**：
1. **修改 `rendering/renderer.py`**：
   - `_SPECIAL_ROOM_TEXTURES` 新增 `dungeon_portal` 键
   - `draw_map()` 中 cell==5 路径：查找传送门目标房间类型
   - `_draw_portal_wall()` 新增 `portal_type` 参数，根据类型选贴图

2. **新增导入**：
   - `renderer.py` 导入 `RoomType`

**涉及文件**：
- `rendering/renderer.py`

---

### BUG9: 传送门倒计时结束后不传送

**根本原因**：
- `_complete_portal_travel()` 在 `_portal_target = None` 之后调用
- 导致方法内 `if not self._portal_target: return` 直接退出

**修复方案**：
1. **修改 `scenes/combat_scene.py`**：
   - 先调用 `_complete_portal_travel()`
   - 再重置状态（`_portal_timer`, `_portal_target`, `_portal_hint`, `_portal_countdown`）
   - 修复离开传送门区域时 `_portal_timer == 0` 未重置的边界情况（`> 0` 改为 `>= 0`）

**涉及文件**：
- `scenes/combat_scene.py`

---

### 性能优化: 特殊房间贴图缓存

**问题描述**：
- `_load_special_texture()` 每帧重新加载贴图，导致卡顿

**修复方案**：
1. **修改 `rendering/renderer.py`**：
   - 新增 `_special_texture_cache` 模块级字典
   - `_load_special_texture()` 首次加载后缓存，后续直接返回缓存

**涉及文件**：
- `rendering/renderer.py`

---

## 五、测试计划

### 测试用例

1. **BUG1测试**：
   - 通关后选择武器奖励，验证自动装备
   - 选择低级奖励，验证自动销毁
   - 验证设置开关功能

2. **BUG2测试**：
   - 进入游戏，检查传送门位置贴图
   - 验证所有传送门位置正常显示

3. **BUG3测试**：
   - 靠近传送门，验证紫色提示
   - 按F键，验证绿色倒计时
   - 通关楼层，验证金色提示

4. **BUG4测试**：
   - 进入副本，验证游戏流畅度
   - 检查CPU和内存占用

5. **BUG5测试**：
   - 生成宝藏室，验证传送门位置不相邻
   - 未完成战斗时靠近传送门，验证封印提示
   - 完成战斗后，验证传送门正常开启

---

## 五、风险评估

### 高风险
- BUG4副本卡顿：需要深入排查，可能涉及架构调整

### 中风险
- BUG1自动装备：涉及装备系统逻辑，需要仔细测试
- BUG5宝藏室：涉及地图生成算法，需要确保随机性

### 低风险
- BUG2贴图显示：主要是渲染逻辑调整
- BUG3文案提示：主要是UI逻辑调整

---

**方案制定时间**: 2026年8月28日
**方案制定人**: Dusk_Wind
