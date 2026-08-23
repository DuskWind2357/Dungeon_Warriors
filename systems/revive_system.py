"""
Dungeon Warriors — 复活系统
管理复活计数器、死亡/游戏结束状态转换
"""

from config import MAX_REVIVES


class ReviveSystem:
    """复活状态管理器"""

    def __init__(self) -> None:
        self.revive_count: int = MAX_REVIVES  # 剩余复活次数

    @property
    def revives_remaining(self) -> int:
        return self.revive_count

    @property
    def is_game_over(self) -> bool:
        """是否已用完所有复活机会"""
        return self.revive_count <= 0

    def consume_revive(self) -> bool:
        """
        消耗一次复活机会。
        返回 True 表示复活成功，False 表示无复活机会（游戏结束）。
        """
        if self.revive_count > 0:
            self.revive_count -= 1
            return True
        return False

    def reset(self) -> None:
        """重置复活计数（新游戏时）"""
        self.revive_count = MAX_REVIVES

    def to_dict(self) -> dict:
        return {"revive_count": self.revive_count}

    @classmethod
    def from_dict(cls, data: dict) -> "ReviveSystem":
        rs = cls()
        rs.revive_count = data.get("revive_count", MAX_REVIVES)
        return rs
