"""
文件解析工具
支持PDF、Markdown、TXT文件的文本提取
"""

import os
import imghdr
from pathlib import Path
from typing import List, Optional

# PDF 文件魔数（%PDF）
_PDF_MAGIC = b'%PDF'
# 常见可执行文件/二进制魔数（拒绝上传）
_BLOCKED_MAGIC_PREFIXES = (
    b'MZ',                    # Windows PE 可执行
    b'\x7fELF',               # Linux ELF 可执行
    b'\xca\xfe\xba\xbe',      # Mach-O 可执行
    b'PK\x03\x04',            # ZIP / docx / jar
)
# 最大允许文件大小（50MB，与 Flask MAX_CONTENT_LENGTH 一致）
_MAX_FILE_SIZE = 50 * 1024 * 1024


def _validate_file(file_path: str, expected_suffix: str) -> None:
    """
    根据文件内容验证上传文件的合法性，防止扩展名欺骗攻击。

    Args:
        file_path: 文件路径
        expected_suffix: 期望的扩展名（如 '.pdf'）

    Raises:
        OSError: 文件超过大小限制
        ValueError: 文件内容与扩展名不符，或包含被拒绝的内容类型
    """
    path = Path(file_path)
    size = path.stat().st_size
    if size > _MAX_FILE_SIZE:
        raise OSError(
            f"文件超过最大限制 {_MAX_FILE_SIZE // (1024 * 1024)}MB: {size} bytes"
        )

    header = path.read_bytes()[:8]

    # 拒绝已知的可执行/压缩格式
    for magic in _BLOCKED_MAGIC_PREFIXES:
        if header.startswith(magic):
            raise ValueError(f"不允许上传的文件类型（可执行/压缩格式）: {file_path}")

    # 对 PDF 严格验证魔数
    if expected_suffix == '.pdf':
        if not header.startswith(_PDF_MAGIC):
            raise ValueError(
                f"文件内容与 .pdf 扩展名不符（缺少 %PDF 魔数）: {file_path}"
            )

    # 拒绝伪装成文本的图片
    if imghdr.what(file_path) is not None:
        raise ValueError(f"不允许上传图片文件: {file_path}")


def _read_text_with_fallback(file_path: str) -> str:
    """
    读取文本文件，UTF-8失败时自动探测编码。
    
    采用多级回退策略：
    1. 首先尝试 UTF-8 解码
    2. 使用 charset_normalizer 检测编码
    3. 回退到 chardet 检测编码
    4. 最终使用 UTF-8 + errors='replace' 兜底
    
    Args:
        file_path: 文件路径
        
    Returns:
        解码后的文本内容
    """
    data = Path(file_path).read_bytes()
    
    # 首先尝试 UTF-8
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        pass
    
    # 尝试使用 charset_normalizer 检测编码
    encoding = None
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data).best()
        if best and best.encoding:
            encoding = best.encoding
    except Exception:
        pass
    
    # 回退到 chardet
    if not encoding:
        try:
            import chardet
            result = chardet.detect(data)
            encoding = result.get('encoding') if result else None
        except Exception:
            pass
    
    # 最终兜底：使用 UTF-8 + replace
    if not encoding:
        encoding = 'utf-8'
    
    return data.decode(encoding, errors='replace')


class FileParser:
    """文件解析器"""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.md', '.markdown', '.txt'}
    
    @classmethod
    def extract_text(cls, file_path: str) -> str:
        """
        从文件中提取文本
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的文本内容
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()

        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {suffix}")

        # 验证文件内容与扩展名一致，拒绝扩展名欺骗
        _validate_file(file_path, suffix)

        if suffix == '.pdf':
            return cls._extract_from_pdf(file_path)
        elif suffix in {'.md', '.markdown'}:
            return cls._extract_from_md(file_path)
        elif suffix == '.txt':
            return cls._extract_from_txt(file_path)
        
        raise ValueError(f"无法处理的文件格式: {suffix}")
    
    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """从PDF提取文本"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("需要安装PyMuPDF: pip install PyMuPDF")
        
        text_parts = []
        with fitz.open(file_path) as doc:
            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    @staticmethod
    def _extract_from_md(file_path: str) -> str:
        """从Markdown提取文本，支持自动编码检测"""
        return _read_text_with_fallback(file_path)
    
    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """从TXT提取文本，支持自动编码检测"""
        return _read_text_with_fallback(file_path)
    
    @classmethod
    def extract_from_multiple(cls, file_paths: List[str]) -> str:
        """
        从多个文件提取文本并合并
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            合并后的文本
        """
        all_texts = []
        
        for i, file_path in enumerate(file_paths, 1):
            try:
                text = cls.extract_text(file_path)
                filename = Path(file_path).name
                all_texts.append(f"=== 文档 {i}: {filename} ===\n{text}")
            except Exception as e:
                all_texts.append(f"=== 文档 {i}: {file_path} (提取失败: {str(e)}) ===")
        
        return "\n\n".join(all_texts)


def split_text_into_chunks(
    text: str, 
    chunk_size: int = 500, 
    overlap: int = 50
) -> List[str]:
    """
    将文本分割成小块
    
    Args:
        text: 原始文本
        chunk_size: 每块的字符数
        overlap: 重叠字符数
        
    Returns:
        文本块列表
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # 尝试在句子边界处分割
        if end < len(text):
            # 查找最近的句子结束符
            for sep in ['。', '！', '？', '.\n', '!\n', '?\n', '\n\n', '. ', '! ', '? ']:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1 and last_sep > chunk_size * 0.3:
                    end = start + last_sep + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # 下一个块从重叠位置开始
        start = end - overlap if end < len(text) else len(text)
    
    return chunks

