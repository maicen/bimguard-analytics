"""
module1_doc_parser
------------------
Public interface for Module 1 — PDF → structured text pipeline.

Exports
-------
Module1_DocReader
    Basic pypdf-based reader. Used as a fallback in the web pipeline
    and for plain text / markdown uploads.

run_module1_pipeline(pdf_path, **kwargs) -> dict
    Full enhanced pipeline (Docling + TF-IDF + optional BERT).
    Works both from the web app and as a CLI call.
    Returns the same summary dict as the CLI would print.
"""

import re
from io import BytesIO

from pypdf import PdfReader


class Module1_DocReader:
    """
    Basic PDF reader (pypdf).
    Used as the pypdf fallback when Docling is unavailable or fails.
    """

    def parse_pdf(self, file_content: bytes) -> str:
        """Parse PDF document bytes and return extracted text."""
        if not file_content:
            return ""
        try:
            reader = PdfReader(BytesIO(file_content))
        except Exception:
            return ""

        parts = []
        for page in reader.pages:
            page_text = (page.extract_text() or "").strip()
            if page_text:
                parts.append(page_text)
        return "\n\n".join(parts)

    def extract_text_sections(self, raw_text: str) -> list[str]:
        """Extract normalized, size-bounded text chunks from parsed document text."""
        normalized_text = self._normalize_text(raw_text)
        if not normalized_text:
            return []
        blocks = self._split_into_blocks(normalized_text)
        return self._chunk_blocks(blocks)

    def _normalize_text(self, raw_text: str) -> str:
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
        normalized_lines = []
        previous_blank = False
        for line in lines:
            if not line:
                if not previous_blank:
                    normalized_lines.append("")
                previous_blank = True
                continue
            normalized_lines.append(line)
            previous_blank = False
        return "\n".join(normalized_lines).strip()

    def _split_into_blocks(self, normalized_text: str) -> list[str]:
        blocks = []
        current_lines = []
        for line in normalized_text.split("\n"):
            if not line:
                if current_lines:
                    blocks.append(" ".join(current_lines).strip())
                    current_lines = []
                continue
            if current_lines and self._starts_new_block(line):
                blocks.append(" ".join(current_lines).strip())
                current_lines = [line]
                continue
            current_lines.append(line)
        if current_lines:
            blocks.append(" ".join(current_lines).strip())
        return blocks or [normalized_text]

    def _starts_new_block(self, line: str) -> bool:
        return bool(
            re.match(r"^(?:[-*•]\s+|\d+(?:\.\d+)*[.)]\s+)", line)
            or (len(line) <= 100 and (line.isupper() or line.endswith(":")))
        )

    def _chunk_blocks(self, blocks: list[str], max_chars: int = 3500) -> list[str]:
        chunks = []
        current = []
        current_size = 0
        for block in blocks:
            oversized_blocks = self._split_large_block(block, max_chars)
            for piece in oversized_blocks:
                piece_size = len(piece)
                separator_size = 2 if current else 0
                if current and current_size + separator_size + piece_size > max_chars:
                    chunks.append("\n\n".join(current).strip())
                    current = [piece]
                    current_size = piece_size
                    continue
                current.append(piece)
                current_size += separator_size + piece_size
        if current:
            chunks.append("\n\n".join(current).strip())
        return [chunk for chunk in chunks if chunk]

    def _split_large_block(self, block: str, max_chars: int) -> list[str]:
        if len(block) <= max_chars:
            return [block]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", block) if s.strip()]
        if len(sentences) <= 1:
            sentences = [segment.strip() for segment in block.split(" ") if segment.strip()]
        chunks = []
        current = []
        current_size = 0
        for sentence in sentences:
            sentence_size = len(sentence)
            separator_size = 1 if current else 0
            if current and current_size + separator_size + sentence_size > max_chars:
                chunks.append(" ".join(current).strip())
                current = [sentence]
                current_size = sentence_size
                continue
            current.append(sentence)
            current_size += separator_size + sentence_size
        if current:
            chunks.append(" ".join(current).strip())
        return chunks


def run_module1_pipeline(pdf_path: str, **kwargs) -> dict:
    """
    Run the full enhanced Module 1 pipeline from the web app or CLI.

    This is the same pipeline as `enhanced_orchestrator.run_enhanced_pipeline()`
    but callable without needing to manage import paths.

    Args:
        pdf_path (str): path to the PDF file on disk
        **kwargs: forwarded to run_enhanced_pipeline()
                  e.g. use_bert=True, discover_keywords=False

    Returns:
        dict: pipeline summary (table_rules, prose_rules, total_rules, ...)
    """
    from app.modules.module1_doc_parser.enhanced_orchestrator import run_enhanced_pipeline

    return run_enhanced_pipeline(pdf_path, **kwargs)
