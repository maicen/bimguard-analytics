"""
Rule extraction pipeline — Module 1 → OpenAI → rules list.

Step  Description                         Status
────  ──────────────────────────────────  ──────────────────────────────────────
  1   Docling + pypdf (parallel)          Active — Docling primary, pypdf standby
  2   Table Builder (no LLM)              Active
  3   Section Chunker (13 OBC sections)   Active
  4   Keyword Filter                      Optional — active when spaCy installed
  5   TF-IDF Keyword Discovery            Optional — active when spaCy installed
  6   Dependency Parser                   Optional — active when spaCy installed
  7   Confidence Scorer                   Optional — active when spaCy installed
 7b   Module 1-b NLP Annotator           Optional — deontic/condition/crossref/
                                                    dimension/dependency/IFC hints
  8   BERT Classifier                     Optional — active when transformers +
                                                    fine-tuned model both present
  9   OpenAI LLM extraction               Active
 10   Deduplication                       Active

Docling is the primary extractor. pypdf runs in parallel as a hot standby.
If Docling fails, pypdf result is used immediately and a warning is surfaced.
"""

import asyncio
import os
import tempfile
from pathlib import Path

from app.modules.module1_doc_parser import Module1_DocReader
from app.modules.module1_doc_parser.section_chunker import SectionChunker
from app.services.openai_rule_extractor import OpenAIRuleExtractor, RuleExtractionProvider

# ── Optional module flags ─────────────────────────────────────────────────────

try:
    from app.modules.module1_doc_parser.docling_extractor import DoclingExtractor

    _DOCLING_AVAILABLE = True
except ImportError:
    _DOCLING_AVAILABLE = False

try:
    from app.modules.module1_doc_parser.table_rule_builder import TableRuleBuilder

    _TABLE_BUILDER_AVAILABLE = True
except ImportError:
    _TABLE_BUILDER_AVAILABLE = False

# Steps 4–7: spaCy-powered filtering (optional)
try:
    from app.modules.module1_doc_parser.keyword_filter import KeywordFilter
    from app.modules.module1_doc_parser.dependency_parser import DependencyParser
    from app.modules.module1_doc_parser.confidence_scorer import ConfidenceScorer

    _SPACY_AVAILABLE = True
except (ImportError, OSError):
    _SPACY_AVAILABLE = False

# TF-IDF keyword discovery (optional — needs scikit-learn)
try:
    from app.modules.module1_doc_parser.tfidf_analyzer import TFIDFAnalyzer

    _TFIDF_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    _TFIDF_AVAILABLE = False

# Module 1-b: NLP annotation layer (optional — pure Python, no extra deps)
try:
    from app.modules.module1b_nlp_annotator import Module1b_NLPAnnotator

    _NLP_ANNOTATOR_AVAILABLE = True
except Exception:
    _NLP_ANNOTATOR_AVAILABLE = False

# Step 8: BERT classifier (optional — requires transformers + fine-tuned model)
_BERT_MODEL_PATH = Path("models/bert_obc_classifier")
try:
    from app.modules.module1_doc_parser.bert_classifier import BERTClassifier

    _BERT_INSTALLED = True
    _BERT_AVAILABLE = _BERT_MODEL_PATH.exists()
except (ImportError, OSError):
    _BERT_INSTALLED = False
    _BERT_AVAILABLE = False


class ExtractionResult:
    """Holds the rules list and any non-fatal warnings from the pipeline."""

    def __init__(self, rules: list[dict], warnings: list[str]):
        self.rules = rules
        self.warnings = warnings


class RuleExtractionService:
    """Module 1 rule extraction pipeline with parallel PDF extraction."""

    def __init__(
        self,
        *,
        doc_reader: Module1_DocReader | None = None,
        provider: RuleExtractionProvider | None = None,
    ):
        """Initialize document parser and extraction provider dependencies."""
        self._doc_reader = doc_reader or Module1_DocReader()
        self._provider = provider or OpenAIRuleExtractor()

    # ── Public API ────────────────────────────────────────────────────────────

    async def extract_rules(self, file_content: bytes) -> ExtractionResult:
        if not file_content:
            return ExtractionResult(rules=[], warnings=[])

        # ── Step 1: Docling + pypdf in parallel ────────────────────────────
        text, tables, warnings = await self._extract_simultaneously(file_content)

        if not text.strip():
            raise RuntimeError(
                "No text could be extracted from this PDF. "
                "The file may be scanned (image-only) or encrypted."
            )

        # ── Step 2: Table Builder — direct rules, no LLM ──────────────────
        table_rules: list[dict] = []
        if tables and _TABLE_BUILDER_AVAILABLE:
            table_rules = TableRuleBuilder().extract_all_as_dicts(tables)

        # ── Step 3: Section Chunker ────────────────────────────────────────
        obc_chunks = SectionChunker().chunk(text)
        if obc_chunks:
            chunks_to_process = obc_chunks
        else:
            generic = self._doc_reader.extract_text_sections(text)
            chunks_to_process = [
                {
                    "section_number": str(i + 1),
                    "section_name": f"Section {i + 1}",
                    "text": t,
                    "char_count": len(t),
                }
                for i, t in enumerate(generic)
            ]

        if not chunks_to_process:
            raise RuntimeError(
                "Could not split the document into processable sections. "
                "Make sure the document contains readable text."
            )

        # ── Steps 4–7: optional spaCy filtering pipeline ──────────────────
        text_key = "text"
        sendable = chunks_to_process
        bert_chunks = None

        if _SPACY_AVAILABLE:
            try:
                # Step 4: keyword scoring HIGH / MEDIUM / LOW
                filtered_chunks = KeywordFilter().score_chunks(chunks_to_process)

                # Step 5: TF-IDF keyword discovery (reporting only, no routing change)
                if _TFIDF_AVAILABLE:
                    try:
                        TFIDFAnalyzer(top_n=20).discover(filtered_chunks)
                    except Exception:
                        pass

                # Step 6: dependency parser upgrades missed obligations
                dep_chunks = DependencyParser().analyse_chunks(filtered_chunks)

                # Step 8: BERT classifier — only if fine-tuned model exists on disk
                if _BERT_AVAILABLE:
                    try:
                        bert_chunks = BERTClassifier(
                            mode="fine_tuned",
                            model_path=str(_BERT_MODEL_PATH),
                        ).classify_chunks(filtered_chunks)
                    except Exception:
                        bert_chunks = None
                elif _BERT_INSTALLED:
                    warnings.append(
                        "BERT classifier installed but no fine-tuned model found at "
                        f"{_BERT_MODEL_PATH}. "
                        "Run BERTClassifier().train() to enable it."
                    )

                # Step 7: combine all signals → SEND / SKIP per paragraph
                final_chunks = ConfidenceScorer().combine(
                    filtered_chunks=filtered_chunks,
                    dep_chunks=dep_chunks,
                    bert_chunks=bert_chunks,
                )

                # Step 7b: Module 1-b NLP annotation (deontic, conditions,
                # cross-refs, dependencies, dimensions, IFC hints)
                if _NLP_ANNOTATOR_AVAILABLE:
                    try:
                        final_chunks = Module1b_NLPAnnotator().annotate(final_chunks)
                    except Exception:
                        pass  # annotation failure must never break extraction

                sendable = [c for c in final_chunks if c.get("filtered_text", "").strip()]
                text_key = "filtered_text"

            except (ImportError, OSError):
                pass  # spaCy model not downloaded — skip all filtering

        # ── Step 9: OpenAI LLM ────────────────────────────────────────────
        prose_rules: list[dict] = []
        total = len(sendable)

        for idx, chunk in enumerate(sendable, start=1):
            chunk_text = chunk.get(text_key, "").strip()
            if not chunk_text:
                continue
            chunk_rules = await self._provider.extract_rules_from_text(
                chunk_text,
                chunk_index=idx,
                total_chunks=total,
            )
            prose_rules.extend(chunk_rules)

        # ── Step 10: Deduplication ────────────────────────────────────────
        rules = self._deduplicate(table_rules + prose_rules)
        return ExtractionResult(rules=rules, warnings=warnings)

    # ── Private: parallel extraction ──────────────────────────────────────────

    async def _extract_simultaneously(self, file_content: bytes) -> tuple[str, list, list[str]]:
        """
        Run Docling and pypdf in parallel threads.
        Docling is primary: if it succeeds its text + tables are used.
        pypdf runs as a hot standby: used instantly if Docling fails, at no
        extra time cost because both were already running in parallel.
        """
        warnings: list[str] = []

        pypdf_coro = asyncio.to_thread(self._run_pypdf, file_content)
        docling_coro = (
            asyncio.to_thread(self._run_docling, file_content) if _DOCLING_AVAILABLE else None
        )

        if docling_coro:
            docling_result, pypdf_result = await asyncio.gather(
                docling_coro, pypdf_coro, return_exceptions=True
            )
        else:
            warnings.append(
                "Docling is not installed — using pypdf "
                "(install docling for structured text and table extraction)."
            )
            pypdf_result = await pypdf_coro
            docling_result = None

        # Use Docling if extraction succeeded and returned text
        if (
            isinstance(docling_result, tuple)
            and isinstance(docling_result[0], str)
            and docling_result[0].strip()
        ):
            return docling_result[0], docling_result[1], warnings

        # Docling failed — surface a warning, fall through to pypdf
        if _DOCLING_AVAILABLE:
            err = str(docling_result) if isinstance(docling_result, Exception) else "empty output"
            warnings.append(
                f"Docling extraction failed ({err}). "
                "Switched to pypdf — table detection unavailable for this document."
            )

        if isinstance(pypdf_result, str) and pypdf_result.strip():
            return pypdf_result, [], warnings

        if isinstance(pypdf_result, Exception):
            raise RuntimeError(f"Both extractors failed: {pypdf_result}") from pypdf_result

        raise RuntimeError(
            "No text could be extracted from this PDF. "
            "The file may be scanned (image-only) or encrypted."
        )

    def _run_docling(self, file_content: bytes) -> tuple[str, list]:
        """Blocking Docling extraction — called in a thread pool."""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            return DoclingExtractor().extract(tmp_path)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _run_pypdf(self, file_content: bytes) -> str:
        """Blocking pypdf extraction — called in a thread pool."""
        return self._doc_reader.parse_pdf(file_content)

    # ── Private: deduplication ────────────────────────────────────────────────

    def _deduplicate(self, rules: list[dict]) -> list[dict]:
        deduplicated: list[dict] = []
        seen: set[tuple] = set()

        for rule in rules:
            desc = str(rule.get("desc") or "").strip()
            target = str(rule.get("target") or "Unspecified").strip()
            if not desc:
                continue

            key = (desc.casefold(), target.casefold())
            if key in seen:
                continue
            seen.add(key)

            ref = str(rule.get("ref") or "").strip()
            deduplicated.append(
                {
                    **rule,
                    "ref": ref or f"REQ-AI-{len(deduplicated) + 1:03d}",
                    "target": target,
                }
            )

        return deduplicated
