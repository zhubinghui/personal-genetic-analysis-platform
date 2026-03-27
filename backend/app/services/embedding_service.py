"""
本地嵌入服务

使用 fastembed（ONNX Runtime）运行本地嵌入模型，无需外部 API。
默认模型：BAAI/bge-small-en-v1.5（384 维，~33 MB）

fastembed 在首次使用时自动下载并缓存模型。
生产部署时建议将 FASTEMBED_CACHE_PATH 挂载为 Docker Volume 以避免重复下载。
"""

import asyncio
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _get_model():
    """懒加载并缓存嵌入模型（进程内单例）。"""
    try:
        from fastembed import TextEmbedding
        logger.info("正在加载嵌入模型: %s", EMBEDDING_MODEL)
        model = TextEmbedding(EMBEDDING_MODEL)
        logger.info("嵌入模型加载完成")
        return model
    except Exception as e:
        logger.error("嵌入模型加载失败: %s", e)
        raise


def embed_texts_sync(texts: list[str]) -> list[list[float]]:
    """同步生成批量文本嵌入向量。"""
    model = _get_model()
    embeddings = list(model.embed(texts))
    return [emb.tolist() for emb in embeddings]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """异步生成批量文本嵌入向量（在线程池中运行以免阻塞事件循环）。"""
    return await asyncio.to_thread(embed_texts_sync, texts)


async def embed_query(text: str) -> list[float]:
    """生成单条查询的嵌入向量。"""
    results = await embed_texts([text])
    return results[0]
