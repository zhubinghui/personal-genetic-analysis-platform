"""
伪名化工具

核心规则：分析层只能使用 pseudonym_id，永不使用 users.id。
所有需要 pseudonym_id 的代码应调用此模块，便于 code review 审计。
"""

import uuid

from app.models.user import User


def get_pseudonym_id(user: User) -> uuid.UUID:
    """
    返回用户的 pseudonym_id，这是分析数据中唯一允许出现的用户标识符。
    永远不要在分析相关代码中直接访问 user.id。
    """
    return user.pseudonym_id


def make_object_key(pseudonym_id: uuid.UUID, sample_id: uuid.UUID, filename: str) -> str:
    """
    构建 MinIO 对象键，前缀使用 pseudonym_id 而非 user_id。
    格式：{pseudonym_id}/{sample_id}/{filename}.enc
    """
    return f"{pseudonym_id}/{sample_id}/{filename}.enc"
