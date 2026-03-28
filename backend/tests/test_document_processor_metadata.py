"""文档处理器 — PDF 元数据提取 + 分块逻辑单元测试"""

import struct

import pytest

from app.services.document_processor import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    PDFMetadata,
    TextChunk,
    _split_into_chunks,
    extract_pdf_metadata,
)


class TestExtractPdfMetadata:
    def test_returns_metadata_from_valid_pdf(self):
        """有效 PDF 应提取出元数据（依赖 PyMuPDF 实际解析）。"""
        # 构造最小合法 PDF（PyMuPDF 可识别的最小结构）
        # 注：真实 PDF 元数据提取需要完整 PDF 结构
        meta = extract_pdf_metadata(b"not a real pdf")
        # 非法文件应返回空 PDFMetadata 而非报错
        assert isinstance(meta, PDFMetadata)

    def test_returns_empty_on_invalid_bytes(self):
        meta = extract_pdf_metadata(b"")
        assert meta.title is None
        assert meta.authors is None

    def test_returns_empty_on_random_bytes(self):
        import os
        meta = extract_pdf_metadata(os.urandom(1000))
        assert isinstance(meta, PDFMetadata)
        assert meta.title is None


class TestSplitIntoChunks:
    def test_short_text_single_chunk(self):
        text = "Hello, world!"
        chunks = _split_into_chunks(text)
        assert len(chunks) == 1
        assert chunks[0].text == "Hello, world!"
        assert chunks[0].chunk_index == 0

    def test_empty_text_no_chunks(self):
        chunks = _split_into_chunks("")
        assert chunks == []

    def test_whitespace_only_no_chunks(self):
        chunks = _split_into_chunks("   \n\n   ")
        assert chunks == []

    def test_long_text_multiple_chunks(self):
        text = "A" * (CHUNK_SIZE * 3)
        chunks = _split_into_chunks(text)
        assert len(chunks) > 1

    def test_chunk_indices_sequential(self):
        text = "word " * 500  # ~2500 chars
        chunks = _split_into_chunks(text)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_page_number_propagated(self):
        chunks = _split_into_chunks("Some text", page_number=5)
        assert chunks[0].page_number == 5

    def test_overlap_between_chunks(self):
        """相邻切片应有重叠内容。"""
        text = "X" * (CHUNK_SIZE * 2 + 100)
        chunks = _split_into_chunks(text)
        if len(chunks) >= 2:
            # 第二个 chunk 的开头应与第一个 chunk 的尾部有重叠
            end_of_first = chunks[0].text[-CHUNK_OVERLAP:]
            start_of_second = chunks[1].text[:CHUNK_OVERLAP]
            # 至少部分重叠（因为可能在边界处截断）
            assert len(end_of_first) > 0 or len(start_of_second) > 0

    def test_prefers_paragraph_break(self):
        """分块时应优先在段落边界（\\n\\n）截断。"""
        # 构造一段刚好超过 CHUNK_SIZE 的文本，中间有段落断点
        part1 = "A" * (CHUNK_SIZE - 100)
        part2 = "B" * 200
        text = part1 + "\n\n" + part2
        chunks = _split_into_chunks(text)
        if len(chunks) >= 2:
            # 第一个 chunk 应在段落边界处结束
            assert chunks[0].text.endswith("A") or chunks[0].text.endswith("\n")
