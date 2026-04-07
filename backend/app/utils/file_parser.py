"""
文件解析工具
支持 PDF / Markdown / TXT 的文本提取，以及首次附件阶段的可选 Vision 增强解析。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..config import Config
from .llm_client import LLMClient


TEXT_ONLY_MODE = "text_only"
TEXT_PLUS_VISION_MODE = "text_plus_vision"

TEXT_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALL_INPUT_EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS

PDF_VISION_MAX_PAGES = 8
PDF_DRAWING_CANDIDATE_THRESHOLD = 25

IMAGE_VISION_SYSTEM_PROMPT = """你是一个附件内容解析助手。
请直接提取这张图片中的有效信息，重点关注：
1. 图片中可见的文字
2. 表格、图表、曲线、柱状图、流程图、示意图中的关键数据和关系
3. 对理解文档有价值的视觉信息

输出要求：
- 只输出纯文本，不要使用 Markdown 代码块
- 先给出简短标题，再分点列出信息
- 如果图片几乎没有有效信息，回复 EXACTLY: NO_VISUAL_CONTENT
"""

PDF_VISION_SYSTEM_PROMPT = """你是一个 PDF 视觉补充解析助手。
当前任务是补充 PDF 页面中“文本层可能无法完整表达”的视觉信息。

只关注：
1. 表格中的关键列、行、数值、结论
2. 图表（柱状图、折线图、饼图、热力图等）中的关键趋势、对比、峰值/低值
3. 图片、海报、截图、信息图中的重要文字与结论
4. 流程图、关系图、架构图中的结构关系

不要重复抄写普通正文段落；只输出视觉补充信息。

输出要求：
- 只输出纯文本，不要使用 Markdown 代码块
- 以简短摘要开头，再列出关键点
- 如果页面没有值得补充的视觉信息，回复 EXACTLY: NO_VISUAL_ENRICHMENT
"""


def _read_text_with_fallback(file_path: str) -> str:
    """
    读取文本文件，UTF-8失败时自动探测编码。
    """
    data = Path(file_path).read_bytes()

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass

    encoding = None
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data).best()
        if best and best.encoding:
            encoding = best.encoding
    except Exception:
        pass

    if not encoding:
        try:
            import chardet
            result = chardet.detect(data)
            encoding = result.get("encoding") if result else None
        except Exception:
            pass

    if not encoding:
        encoding = "utf-8"

    return data.decode(encoding, errors="replace")


@dataclass
class InputExtractionResult:
    """首次附件解析结果。"""

    text: str = ""
    used_vision: bool = False
    skipped: bool = False
    skip_reason: Optional[str] = None
    vision_pages: List[int] = field(default_factory=list)


class FileParser:
    """文件解析器"""

    SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS
    INPUT_SUPPORTED_EXTENSIONS = ALL_INPUT_EXTENSIONS
    IMAGE_EXTENSIONS = IMAGE_EXTENSIONS

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        """
        从纯文本类文件中提取文本。
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()

        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {suffix}")

        if suffix == ".pdf":
            return cls._extract_from_pdf(file_path)
        if suffix in {".md", ".markdown"}:
            return cls._extract_from_md(file_path)
        if suffix == ".txt":
            return cls._extract_from_txt(file_path)

        raise ValueError(f"无法处理的文件格式: {suffix}")

    @classmethod
    def extract_input_content(
        cls,
        file_path: str,
        parse_mode: str = TEXT_ONLY_MODE,
        input_llm_client: Optional[LLMClient] = None,
    ) -> InputExtractionResult:
        """
        用于“首次附件读取”场景的统一解析入口。
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        if suffix not in cls.INPUT_SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {suffix}")

        if parse_mode not in {TEXT_ONLY_MODE, TEXT_PLUS_VISION_MODE}:
            raise ValueError(f"不支持的解析模式: {parse_mode}")

        if suffix in {".md", ".markdown"}:
            return InputExtractionResult(text=cls._extract_from_md(file_path))

        if suffix == ".txt":
            return InputExtractionResult(text=cls._extract_from_txt(file_path))

        if suffix in cls.IMAGE_EXTENSIONS:
            if parse_mode == TEXT_ONLY_MODE:
                return InputExtractionResult(
                    skipped=True,
                    skip_reason="image_requires_vision",
                )
            if input_llm_client is None:
                raise ValueError("text_plus_vision 模式下缺少输入专用 LLM 客户端")
            image_text = cls._extract_from_image_with_vision(file_path, input_llm_client)
            return InputExtractionResult(text=image_text, used_vision=True)

        if suffix == ".pdf":
            if parse_mode == TEXT_ONLY_MODE:
                return InputExtractionResult(text=cls._extract_from_pdf(file_path))
            if input_llm_client is None:
                raise ValueError("text_plus_vision 模式下缺少输入专用 LLM 客户端")
            pdf_text, vision_pages = cls._extract_from_pdf_with_vision(file_path, input_llm_client)
            return InputExtractionResult(
                text=pdf_text,
                used_vision=bool(vision_pages),
                vision_pages=vision_pages,
            )

        raise ValueError(f"无法处理的文件格式: {suffix}")

    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """从PDF提取文本。"""
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

    @classmethod
    def _extract_from_pdf_with_vision(
        cls,
        file_path: str,
        input_llm_client: LLMClient,
    ) -> tuple[str, List[int]]:
        """从 PDF 提取文本，并对包含视觉信息的页面做 Vision 补充。"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("需要安装PyMuPDF: pip install PyMuPDF")

        text_parts: List[str] = []
        vision_candidates: List[tuple[int, bytes]] = []

        with fitz.open(file_path) as doc:
            for page_index, page in enumerate(doc):
                page_text = page.get_text().strip()
                if page_text:
                    text_parts.append(f"[PDF_PAGE_{page_index + 1}]\n{page_text}")

                if len(vision_candidates) >= PDF_VISION_MAX_PAGES:
                    continue

                if cls._should_use_vision_for_pdf_page(page):
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    vision_candidates.append((page_index + 1, pix.tobytes("png")))

        vision_pages: List[int] = []
        vision_parts: List[str] = []

        for page_number, image_bytes in vision_candidates:
            prompt = (
                f"请分析这个 PDF 的第 {page_number} 页，只补充表格、图片、图表、图形、截图中的关键信息。"
                " 如果页面没有值得补充的视觉信息，请回复 EXACTLY: NO_VISUAL_ENRICHMENT。"
            )
            result = input_llm_client.analyze_image(
                image_bytes=image_bytes,
                mime_type="image/png",
                prompt=prompt,
                system_prompt=PDF_VISION_SYSTEM_PROMPT,
                max_tokens=Config.INPUT_LLM_PDF_VISION_MAX_TOKENS,
                request_label=f"input_pdf_page_{page_number}_vision",
            ).strip()

            if not result or result == "NO_VISUAL_ENRICHMENT":
                continue

            vision_pages.append(page_number)
            vision_parts.append(f"[PDF_VISION_PAGE_{page_number}]\n{result}")

        combined_parts = list(text_parts)
        if vision_parts:
            combined_parts.append("[PDF_VISION_ENRICHMENT]")
            combined_parts.extend(vision_parts)

        return "\n\n".join(part for part in combined_parts if part.strip()), vision_pages

    @classmethod
    def _should_use_vision_for_pdf_page(cls, page) -> bool:
        """根据视觉信号判断页面是否值得做 Vision 补充。"""
        try:
            has_images = bool(page.get_images(full=True))
        except Exception:
            has_images = False

        try:
            drawing_count = len(page.get_drawings())
        except Exception:
            drawing_count = 0

        return has_images or drawing_count >= PDF_DRAWING_CANDIDATE_THRESHOLD

    @staticmethod
    def _extract_from_image_with_vision(file_path: str, input_llm_client: LLMClient) -> str:
        """使用 Vision 模型读取图片附件。"""
        path = Path(file_path)
        mime_type = _guess_image_mime_type(path.suffix.lower())
        prompt = (
            "请读取这张附件图片，提取可见文字，并总结其中的表格、图表、流程图、截图、信息图或关键视觉信息。"
            " 如果没有有效内容，请回复 EXACTLY: NO_VISUAL_CONTENT。"
        )
        result = input_llm_client.analyze_image(
            image_bytes=path.read_bytes(),
            mime_type=mime_type,
            prompt=prompt,
            system_prompt=IMAGE_VISION_SYSTEM_PROMPT,
            max_tokens=Config.INPUT_LLM_IMAGE_MAX_TOKENS,
            request_label=f"input_image_{path.name}",
        ).strip()

        if not result or result == "NO_VISUAL_CONTENT":
            return ""

        return f"[IMAGE_ATTACHMENT]\n{result}"

    @staticmethod
    def _extract_from_md(file_path: str) -> str:
        """从Markdown提取文本，支持自动编码检测。"""
        return _read_text_with_fallback(file_path)

    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """从TXT提取文本，支持自动编码检测。"""
        return _read_text_with_fallback(file_path)

    @classmethod
    def extract_from_multiple(cls, file_paths: List[str]) -> str:
        """
        从多个纯文本类文件提取文本并合并。
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


def _guess_image_mime_type(suffix: str) -> str:
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[str]:
    """
    将文本分割成小块。
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            for sep in ["。", "！", "？", ".\n", "!\n", "?\n", "\n\n", ". ", "! ", "? "]:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1 and last_sep > chunk_size * 0.3:
                    end = start + last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap if end < len(text) else len(text)

    return chunks
