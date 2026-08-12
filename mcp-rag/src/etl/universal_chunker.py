"""Universal schema-driven markdown chunker."""

import re

from dataclasses import dataclass
from typing import Any

from src.etl.chunking_schema import CategoryPolicyBinding, ChunkingPolicy, ChunkingSchemaV3, SchemaCategory
from src.etl.faq_regex import build_faq_pair_regex
from src.etl.hashing import content_hash
from src.etl.types import ChunkDraft


def _slug(value: str, *, limit: int = 40) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9а-яА-Я_]+", "_", value.strip().lower()).strip("_")
    return cleaned[:limit] or "untitled"


def _compile_heading_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.MULTILINE)


def _title_from_match(match: re.Match[str]) -> str:
    groups = match.groupdict()

    if "title" in groups and groups["title"] is not None:
        return groups["title"].strip()

    if match.lastindex and match.lastindex >= 1:
        return match.group(1).strip()

    return match.group(0).strip()


@dataclass(frozen=True, slots=True)
class HeadingBlock:
    """
    One heading section block in markdown.
    """

    title: str
    body: str
    index: int
    section_number: str | None


class UniversalChunker:
    """
    Execute schema-driven classification and chunking strategies.
    """

    def __init__(self, schema: ChunkingSchemaV3) -> None:
        self.schema = schema
        hp = schema.document.heading_patterns
        self._h1_re = _compile_heading_pattern(hp.h1_regex)
        self._h2_re = _compile_heading_pattern(hp.h2_regex)
        self._h3_re = _compile_heading_pattern(hp.h3_regex)
        self._section_num_re = re.compile(hp.section_number_regex)
        self._category_by_id: dict[str, SchemaCategory] = {item.id: item for item in schema.categories}
        self._policy_by_id: dict[str, ChunkingPolicy] = {item.id: item for item in schema.chunking_policies}
        self._binding_by_category: dict[str, CategoryPolicyBinding] = {
            item.category_id: item for item in schema.category_policy_bindings
        }

    def _section_number(self, title: str) -> str | None:
        match = self._section_num_re.match(title.strip())

        if match is None:
            return None

        if "number" in match.groupdict() and match.group("number") is not None:
            return match.group("number")

        return match.group(1)

    @staticmethod
    def _split_by_heading(text: str, pattern: re.Pattern[str]) -> list[tuple[str, str]]:
        matches = list(pattern.finditer(text))
        if not matches:
            return [("", text.strip())] if text.strip() else []

        parts: list[tuple[str, str]] = []

        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            title = _title_from_match(match)
            body = text[match.end() : end].strip()
            parts.append((title, body))

        return parts

    def split_h1_blocks(self, text: str) -> list[HeadingBlock]:
        """
        Split document into top-level H1 blocks.
        """

        matches = list(self._h1_re.finditer(text))
        if not matches:
            return []

        blocks: list[HeadingBlock] = []

        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            title = _title_from_match(match)
            body = text[match.end() : end].strip()
            blocks.append(
                HeadingBlock(
                    title=title,
                    body=body,
                    index=index,
                    section_number=self._section_number(title),
                )
            )

        return blocks

    @staticmethod
    def _matches_rule(block: HeadingBlock, matcher: Any) -> bool:
        section_numbers = set(matcher.section_number_in)
        if section_numbers and block.section_number in section_numbers:
            return True

        title = block.title
        lowered = title.lower()

        if matcher.title_keywords_any and any(keyword.lower() in lowered for keyword in matcher.title_keywords_any):
            return True

        if matcher.title_regex:
            if re.search(matcher.title_regex, title):
                return True

        if matcher.path_regex:
            if re.search(matcher.path_regex, title):
                return True

        return False

    def classify_block(self, block: HeadingBlock) -> str:
        """
        Classify H1 block into a category id.
        """

        for rule in sorted(self.schema.classification_rules, key=lambda item: item.priority):
            if self._matches_rule(block, rule.match):
                return rule.target_category_id

        return self.schema.default_category_id

    @staticmethod
    def _estimate_tokens(text: str, *, chars_per_token: int = 4) -> int:
        return max(1, len(text) // max(chars_per_token, 1))

    @staticmethod
    def _prefix(category: SchemaCategory, *, section: str, title: str, body: str) -> str:
        labels = category.labels
        return (
            f"[{labels.section}: {section} > {title}]\n"
            f"[{labels.type}: {category.id}]\n"
            f"{body.strip()}"
        )

    @staticmethod
    def _faq_prefix(category: SchemaCategory, *, source_section: str, body: str) -> str:
        labels = category.labels
        return (
            f"[{labels.section}: {source_section} > FAQ]\n"
            f"[{labels.source}: {source_section}]\n"
            f"[{labels.type}: {category.id}]\n"
            f"{body.strip()}"
        )

    @staticmethod
    def _token_window_split(text: str, *, chunk_size: int, overlap: int, chars_per_token: int) -> list[str]:
        if not text.strip():
            return []

        window_chars = max(1, chunk_size * chars_per_token)
        step_chars = max(1, (chunk_size - overlap) * chars_per_token)
        chunks: list[str] = []

        for start in range(0, len(text), step_chars):
            end = start + window_chars
            part = text[start:end].strip()

            if part:
                chunks.append(part)

            if end >= len(text):
                break

        return chunks

    def _faq_pairs_from_text(
        self,
        category: SchemaCategory,
        *,
        text: str,
        source_section: str,
        node_base_id: str,
        question_marker: str,
        answer_marker: str,
    ) -> list[ChunkDraft]:
        pattern = build_faq_pair_regex(question_marker, answer_marker)
        chunks: list[ChunkDraft] = []

        for index, match in enumerate(pattern.finditer(text)):
            question = match.group("question").strip()
            answer = match.group("answer").strip()
            body = f"{question_marker} {question}\n{answer_marker} {answer}"
            content = self._faq_prefix(category, source_section=source_section, body=body)
            chunks.append(
                ChunkDraft(
                    content=content,
                    content_type=category.id,
                    section=source_section,
                    title=question[:120],
                    node_id=f"{node_base_id}.faq.{index}",
                    token_count=self._estimate_tokens(content),
                )
            )

        return chunks

    @staticmethod
    def _extract_embedded_faq(
        binding: CategoryPolicyBinding,
        *,
        section_body: str,
    ) -> tuple[str, str | None]:
        regex_value = binding.extras.get("embedded_faq_block_regex")

        if not isinstance(regex_value, str) or not regex_value.strip():
            return section_body.strip(), None

        match = re.search(regex_value, section_body, re.MULTILINE)
        if not match:
            return section_body.strip(), None

        sop_body = section_body[: match.start()].strip()
        faq_body = section_body[match.end() :].strip()

        return sop_body, faq_body or None

    def _apply_regex_split(
        self,
        category: SchemaCategory,
        policy: ChunkingPolicy,
        block: HeadingBlock,
        *,
        node_prefix: str,
    ) -> list[ChunkDraft]:
        regex = str(policy.params.get("split_regex", "")).strip()

        if not regex:
            return []

        capture_group = int(policy.params.get("title_capture_group", 1))
        pattern = re.compile(regex, re.MULTILINE)
        matches = list(pattern.finditer(block.body))

        if not matches:
            content = self._prefix(category, section=block.title, title=block.title, body=block.body)
            return [
                ChunkDraft(
                    content=content,
                    content_type=category.id,
                    section=block.title,
                    title=block.title,
                    node_id=node_prefix,
                    token_count=self._estimate_tokens(content),
                )
            ]

        chunks: list[ChunkDraft] = []

        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(block.body)
            title = (match.group(capture_group) or "").strip()
            part = block.body[match.end() : end].strip()
            content = self._prefix(category, section=block.title, title=title or block.title, body=part)
            chunks.append(
                ChunkDraft(
                    content=content,
                    content_type=category.id,
                    section=block.title,
                    title=title or block.title,
                    node_id=f"{node_prefix}.part.{index}",
                    token_count=self._estimate_tokens(content),
                )
            )

        return chunks

    def _apply_by_subheading(
        self,
        category: SchemaCategory,
        policy: ChunkingPolicy,
        block: HeadingBlock,
        *,
        node_prefix: str,
        binding: CategoryPolicyBinding,
    ) -> list[ChunkDraft]:
        heading_level = int(policy.params.get("heading_level", 2))
        max_tokens = int(policy.params.get("max_tokens", 800))
        chars_per_token = int(policy.params.get("chars_per_token", 4))
        overflow_split_level = int(policy.params.get("overflow_split_level", heading_level + 1))
        overflow_overlap = int(policy.params.get("overflow_overlap", 0))
        pattern = self._h2_re if heading_level == 2 else self._h3_re
        overflow_pattern = self._h3_re if overflow_split_level == 3 else self._h2_re

        section_body, embedded_faq = self._extract_embedded_faq(binding, section_body=block.body)
        parts = self._split_by_heading(section_body, pattern)

        if not parts:
            parts = [("", section_body)]

        chunks: list[ChunkDraft] = []

        for index, (title, body) in enumerate(parts):
            if not body.strip():
                continue

            part_title = title or block.title
            content = self._prefix(category, section=block.title, title=part_title, body=body)

            if self._estimate_tokens(content, chars_per_token=chars_per_token) <= max_tokens:
                chunks.append(
                    ChunkDraft(
                        content=content,
                        content_type=category.id,
                        section=block.title,
                        title=part_title,
                        node_id=f"{node_prefix}.h{heading_level}.{index}",
                        token_count=self._estimate_tokens(content, chars_per_token=chars_per_token),
                    )
                )
                continue

            overflow_parts = self._split_by_heading(body, overflow_pattern)
            if overflow_parts:
                parent_idx: int | None = None

                for inner_index, (inner_title, inner_body) in enumerate(overflow_parts):
                    if not inner_body.strip():
                        continue

                    combined_title = f"{part_title} > {inner_title}" if inner_title else part_title
                    prefixed = self._prefix(category, section=block.title, title=combined_title, body=inner_body)
                    draft = ChunkDraft(
                        content=prefixed,
                        content_type=category.id,
                        section=block.title,
                        title=inner_title or part_title,
                        node_id=f"{node_prefix}.h{overflow_split_level}.{index}.{inner_index}",
                        parent_chunk_index=parent_idx,
                        token_count=self._estimate_tokens(prefixed, chars_per_token=chars_per_token),
                    )

                    if parent_idx is None:
                        parent_idx = len(chunks)

                    chunks.append(draft)

                continue

            token_window_parts = self._token_window_split(
                body,
                chunk_size=max_tokens,
                overlap=overflow_overlap,
                chars_per_token=chars_per_token,
            )

            if token_window_parts:
                for tw_index, tw_part in enumerate(token_window_parts):
                    tw_content = self._prefix(
                        category,
                        section=block.title,
                        title=f"{part_title} (part {tw_index + 1})",
                        body=tw_part,
                    )
                    chunks.append(
                        ChunkDraft(
                            content=tw_content,
                            content_type=category.id,
                            section=block.title,
                            title=part_title,
                            node_id=f"{node_prefix}.tw.{index}.{tw_index}",
                            token_count=self._estimate_tokens(tw_content, chars_per_token=chars_per_token),
                        )
                    )
                continue

            chunks.append(
                ChunkDraft(
                    content=content,
                    content_type=category.id,
                    section=block.title,
                    title=part_title,
                    node_id=f"{node_prefix}.h{heading_level}.{index}",
                    token_count=self._estimate_tokens(content, chars_per_token=chars_per_token),
                )
            )

        if embedded_faq:
            chunks.extend(
                self._chunk_embedded_faq(
                    binding,
                    text=embedded_faq,
                    source_section=block.title,
                    node_base_id=f"{node_prefix}.embedded",
                )
            )

        return chunks

    def _chunk_embedded_faq(
        self,
        binding: CategoryPolicyBinding,
        *,
        text: str,
        source_section: str,
        node_base_id: str,
    ) -> list[ChunkDraft]:
        """
        Chunk an embedded FAQ block under the category declared in binding extras.
        """

        faq_policy_id = binding.extras.get("embedded_faq_policy_id")
        if not isinstance(faq_policy_id, str) or faq_policy_id not in self._policy_by_id:
            return []

        faq_policy = self._policy_by_id[faq_policy_id]
        if faq_policy.strategy != "qa_pairs":
            return []

        faq_category_id = binding.extras.get("embedded_faq_category_id")
        if not isinstance(faq_category_id, str) or not faq_category_id.strip():
            return []

        faq_category = self._category_by_id.get(faq_category_id)
        if faq_category is None:
            return []

        question_marker = str(faq_policy.params.get("question_marker", "**Question:**"))
        answer_marker = str(faq_policy.params.get("answer_marker", "**Answer:**"))

        return self._faq_pairs_from_text(
            faq_category,
            text=text,
            source_section=source_section,
            node_base_id=node_base_id,
            question_marker=question_marker,
            answer_marker=answer_marker,
        )

    def _apply_qa_pairs(
        self,
        category: SchemaCategory,
        policy: ChunkingPolicy,
        block: HeadingBlock,
        *,
        node_prefix: str,
    ) -> list[ChunkDraft]:
        question_marker = str(policy.params.get("question_marker", "")).strip()
        answer_marker = str(policy.params.get("answer_marker", "")).strip()

        if not question_marker or not answer_marker:
            return []

        chunks = self._faq_pairs_from_text(
            category,
            text=block.body,
            source_section=block.title,
            node_base_id=node_prefix,
            question_marker=question_marker,
            answer_marker=answer_marker,
        )

        if chunks:
            return chunks

        content = self._faq_prefix(category, source_section=block.title, body=block.body)

        return [
            ChunkDraft(
                content=content,
                content_type=category.id,
                section=block.title,
                title=block.title,
                node_id=node_prefix,
                token_count=self._estimate_tokens(content),
            )
        ]

    def _apply_qa_by_heading_prefix(
        self,
        category: SchemaCategory,
        policy: ChunkingPolicy,
        block: HeadingBlock,
        *,
        node_prefix: str,
    ) -> list[ChunkDraft]:
        heading_level = int(policy.params.get("heading_level", 2))
        prefixes = [str(item).strip().lower() for item in policy.params.get("question_prefixes", [])]
        question_marker = str(policy.params.get("question_marker", "**Question:**"))
        answer_marker = str(policy.params.get("answer_marker", "**Answer:**"))

        if not prefixes:
            prefixes = ["question:", "вопрос:"]

        pattern = self._h2_re if heading_level == 2 else self._h3_re
        parts = self._split_by_heading(block.body, pattern)
        chunks: list[ChunkDraft] = []

        for index, (title, body) in enumerate(parts):
            lowered = title.lower()
            matched_prefix = next((prefix for prefix in prefixes if lowered.startswith(prefix)), None)

            if matched_prefix is None:
                continue

            question = title[len(matched_prefix) :].strip(" :—-") or title
            qa_body = f"{question_marker} {question}\n{answer_marker} {body.strip()}"
            content = self._faq_prefix(category, source_section=block.title, body=qa_body)
            chunks.append(
                ChunkDraft(
                    content=content,
                    content_type=category.id,
                    section=block.title,
                    title=question[:120],
                    node_id=f"{node_prefix}.qa_h.{index}",
                    token_count=self._estimate_tokens(content),
                )
            )

        if chunks:
            return chunks

        return self._apply_whole_section(category, policy, block, node_prefix=node_prefix)

    def _apply_token_window(
        self,
        category: SchemaCategory,
        policy: ChunkingPolicy,
        block: HeadingBlock,
        *,
        node_prefix: str,
    ) -> list[ChunkDraft]:
        chunk_size = int(policy.params.get("chunk_size", 800))
        overlap = int(policy.params.get("overlap", 0))
        chars_per_token = int(policy.params.get("chars_per_token", 4))
        parts = self._token_window_split(
            block.body,
            chunk_size=chunk_size,
            overlap=overlap,
            chars_per_token=chars_per_token,
        )
        chunks: list[ChunkDraft] = []

        for index, part in enumerate(parts):
            content = self._prefix(category, section=block.title, title=f"{block.title} (part {index + 1})", body=part)
            chunks.append(
                ChunkDraft(
                    content=content,
                    content_type=category.id,
                    section=block.title,
                    title=block.title,
                    node_id=f"{node_prefix}.tw.{index}",
                    token_count=self._estimate_tokens(content, chars_per_token=chars_per_token),
                )
            )

        return chunks

    def _apply_whole_section(
        self,
        category: SchemaCategory,
        policy: ChunkingPolicy,
        block: HeadingBlock,
        *,
        node_prefix: str,
    ) -> list[ChunkDraft]:
        emit_chunks = bool(policy.params.get("emit_chunks", True))

        if not emit_chunks:
            return []

        if not block.body.strip():
            return []

        content = self._prefix(category, section=block.title, title=block.title, body=block.body)

        return [
            ChunkDraft(
                content=content,
                content_type=category.id,
                section=block.title,
                title=block.title,
                node_id=node_prefix,
                token_count=self._estimate_tokens(content),
            )
        ]

    def _apply_policy(
        self,
        category: SchemaCategory,
        binding: CategoryPolicyBinding,
        policy: ChunkingPolicy,
        block: HeadingBlock,
        *,
        node_prefix: str,
    ) -> list[ChunkDraft]:
        if policy.strategy == "whole_section":
            return self._apply_whole_section(category, policy, block, node_prefix=node_prefix)

        if policy.strategy == "by_subheading":
            return self._apply_by_subheading(category, policy, block, node_prefix=node_prefix, binding=binding)

        if policy.strategy == "regex_split":
            return self._apply_regex_split(category, policy, block, node_prefix=node_prefix)

        if policy.strategy == "qa_pairs":
            return self._apply_qa_pairs(category, policy, block, node_prefix=node_prefix)

        if policy.strategy == "qa_by_heading_prefix":
            return self._apply_qa_by_heading_prefix(category, policy, block, node_prefix=node_prefix)

        if policy.strategy == "token_window":
            return self._apply_token_window(category, policy, block, node_prefix=node_prefix)

        return []

    def chunk_document(self, text: str, *, source_path: str = "") -> list[ChunkDraft]:
        """
        Build chunks according to schema-defined categories and policies.
        """

        blocks = self.split_h1_blocks(text)
        chunks: list[ChunkDraft] = []

        for block in blocks:
            category_id = self.classify_block(block)
            category = self._category_by_id.get(category_id)

            if category is None:
                continue

            binding = self._binding_by_category.get(category_id)

            if binding is None:
                continue

            policy = self._policy_by_id.get(binding.policy_id)

            if policy is None:
                continue

            node_prefix = f"h1_{block.index:03d}.{_slug(category_id)}.{_slug(block.title, limit=24)}"
            built = self._apply_policy(category, binding, policy, block, node_prefix=node_prefix)

            for chunk in built:
                chunk.source_path = source_path
                chunk.content_hash = content_hash(chunk.content)

            chunks.extend(built)

        return chunks
