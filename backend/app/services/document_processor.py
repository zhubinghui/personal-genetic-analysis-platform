"""
文档解析与分块服务

支持格式：PDF（PyMuPDF）、DOCX（python-docx）、TXT/MD
分块策略：按字符数滑动窗口切分，尽量在段落边界处截断。
"""

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 分块参数
CHUNK_SIZE = 1000       # 每块最大字符数
CHUNK_OVERLAP = 200     # 相邻块重叠字符数


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    page_number: int | None = None


def _split_into_chunks(text: str, page_number: int | None = None) -> list[TextChunk]:
    """将文本按滑动窗口切分为 TextChunk 列表。"""
    chunks: list[TextChunk] = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + CHUNK_SIZE

        # 尝试在段落或句子边界处截断
        if end < len(text):
            for sep in ("\n\n", "\n", "。", ". ", "! ", "? "):
                pos = text.rfind(sep, start, end)
                if pos != -1 and pos > start + CHUNK_SIZE // 2:
                    end = pos + len(sep)
                    break

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(TextChunk(
                text=chunk_text,
                chunk_index=idx,
                page_number=page_number,
            ))
            idx += 1

        start = end - CHUNK_OVERLAP
        if start >= len(text):
            break

    return chunks


@dataclass
class PDFMetadata:
    title: str | None = None
    authors: str | None = None
    subject: str | None = None
    keywords: str | None = None


def extract_pdf_metadata(file_bytes: bytes) -> PDFMetadata:
    """从 PDF 元数据中提取标题、作者、关键词。"""
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        meta = doc.metadata or {}
        doc.close()
        return PDFMetadata(
            title=meta.get("title") or None,
            authors=meta.get("author") or None,
            subject=meta.get("subject") or None,
            keywords=meta.get("keywords") or None,
        )
    except Exception:
        return PDFMetadata()


def parse_pdf(file_bytes: bytes) -> list[TextChunk]:
    """解析 PDF 文件，按页提取文本并切分。"""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_chunks: list[TextChunk] = []
        global_idx = 0

        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text").strip()
            if not page_text:
                continue
            for chunk in _split_into_chunks(page_text, page_number=page_num):
                chunk.chunk_index = global_idx
                global_idx += 1
                all_chunks.append(chunk)

        doc.close()
        logger.info("PDF 解析完成，共 %d 个文本块", len(all_chunks))
        return all_chunks

    except Exception as e:
        logger.error("PDF 解析失败: %s", e)
        raise ValueError(f"PDF 解析失败: {e}") from e


def parse_docx(file_bytes: bytes) -> list[TextChunk]:
    """解析 DOCX 文件，提取段落文本并切分。"""
    try:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)

        chunks = _split_into_chunks(full_text)
        logger.info("DOCX 解析完成，共 %d 个文本块", len(chunks))
        return chunks

    except Exception as e:
        logger.error("DOCX 解析失败: %s", e)
        raise ValueError(f"DOCX 解析失败: {e}") from e


def parse_txt(file_bytes: bytes) -> list[TextChunk]:
    """解析纯文本文件（UTF-8 / GBK 自动检测）。"""
    for encoding in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            text = file_bytes.decode(encoding)
            chunks = _split_into_chunks(text)
            logger.info("TXT 解析完成，共 %d 个文本块", len(chunks))
            return chunks
        except UnicodeDecodeError:
            continue
    raise ValueError("无法解码文本文件，请确保文件编码为 UTF-8 或 GBK")


def parse_document(file_bytes: bytes, file_type: str) -> list[TextChunk]:
    """根据文件类型分发到对应解析器。"""
    t = file_type.lower().lstrip(".")
    if t == "pdf":
        return parse_pdf(file_bytes)
    elif t == "docx":
        return parse_docx(file_bytes)
    elif t in ("txt", "md", "text"):
        return parse_txt(file_bytes)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}，支持 PDF / DOCX / TXT")
