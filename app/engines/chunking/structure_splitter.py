"""
structure_splitter.py — Structure-aware text splitter prioritizing semantic boundaries.
Hierarchical boundary priority:
1. Heading boundaries (Markdown #, ##, numbered sections e.g. 1., 1.1)
2. Paragraph boundaries (\n\n)
3. Sentence boundaries (.!?)
4. Safe fallback splitting (word / character sliding window)
"""
import re
from typing import List
from app.core.exceptions import InvalidChunkConfigurationError


class StructureSplitter:
    """
    Splits document text into ordered, semantically coherent chunks
    based on headings, paragraphs, sentences, and safe fallback logic.
    """

    # Heading patterns: Markdown headings or numbered sections (e.g., "1. Overview", "2.1 Scope")
    HEADING_PATTERN = re.compile(
        r"^(?:#{1,6}\s+.+|\d+(?:\.\d+)*\.?\s+[A-Z].+)$",
        re.MULTILINE
    )

    # Sentence boundary pattern: whitespace following ., !, or ? (fixed width look-behind for Python re)
    SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self._validate_config(chunk_size, chunk_overlap)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def _validate_config(chunk_size: int, chunk_overlap: int) -> None:
        """Validate splitter configuration parameters."""
        if chunk_size <= 0:
            raise InvalidChunkConfigurationError(
                f"chunk_size must be greater than 0, got {chunk_size}"
            )
        if chunk_overlap < 0:
            raise InvalidChunkConfigurationError(
                f"chunk_overlap must be non-negative, got {chunk_overlap}"
            )
        if chunk_overlap >= chunk_size:
            raise InvalidChunkConfigurationError(
                f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})"
            )

    def split_text(self, text: str) -> List[str]:
        """
        Split input text into ordered chunks respecting structural hierarchy.
        Returns empty list if input is empty or whitespace-only.
        """
        if not text or not text.strip():
            return []

        cleaned_text = text.strip()
        if len(cleaned_text) <= self.chunk_size and not self.HEADING_PATTERN.search(cleaned_text):
            return [cleaned_text]

        # 1. Break text into structural blocks (sections / paragraphs)
        blocks = self._split_into_blocks(cleaned_text)

        # 2. Decompose oversized blocks into sentence or word-level units
        fine_units = []
        for block, is_heading in blocks:
            if len(block) <= self.chunk_size:
                fine_units.append((block, is_heading))
            else:
                sub_units = self._decompose_oversized_block(block)
                for unit in sub_units:
                    fine_units.append((unit, False))

        # 3. Assemble units into chunks respecting chunk_size and chunk_overlap
        chunks = self._assemble_chunks(fine_units)

        # Filter out empty or whitespace-only chunks
        return [c.strip() for c in chunks if c and c.strip()]

    def _split_into_blocks(self, text: str) -> List[tuple[str, bool]]:
        """
        Split document into blocks by headings and paragraph boundaries.
        Returns list of (block_text, is_heading).
        """
        # Split by double newline first to preserve paragraph structure
        raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        blocks: List[tuple[str, bool]] = []

        for p in raw_paragraphs:
            lines = p.split("\n")
            current_group: List[str] = []

            for line in lines:
                stripped_line = line.strip()
                if self.HEADING_PATTERN.match(stripped_line):
                    # Flush any accumulated lines
                    if current_group:
                        blocks.append(("\n".join(current_group), False))
                        current_group = []
                    # Heading block
                    blocks.append((stripped_line, True))
                else:
                    current_group.append(stripped_line)

            if current_group:
                blocks.append(("\n".join(current_group), False))

        return blocks

    def _decompose_oversized_block(self, block: str) -> List[str]:
        """Decompose a block exceeding chunk_size into sentence or fallback units."""
        # Split into sentences
        sentences = self.SENTENCE_SPLIT_PATTERN.split(block)
        units: List[str] = []

        for sent in sentences:
            sent_clean = sent.strip()
            if not sent_clean:
                continue

            if len(sent_clean) <= self.chunk_size:
                units.append(sent_clean)
            else:
                # Sentence itself exceeds chunk_size — fallback to word-level / sliding window
                words = sent_clean.split(" ")
                current_sub: List[str] = []
                current_len = 0

                for word in words:
                    # Single word exceeds chunk_size — character slice fallback
                    if len(word) > self.chunk_size:
                        if current_sub:
                            units.append(" ".join(current_sub))
                            current_sub = []
                            current_len = 0
                        # Slice word
                        step = max(1, self.chunk_size - self.chunk_overlap)
                        for i in range(0, len(word), step):
                            units.append(word[i : i + self.chunk_size])
                        continue

                    needed = len(word) + (1 if current_sub else 0)
                    if current_len + needed <= self.chunk_size:
                        current_sub.append(word)
                        current_len += needed
                    else:
                        if current_sub:
                            units.append(" ".join(current_sub))
                        current_sub = [word]
                        current_len = len(word)

                if current_sub:
                    units.append(" ".join(current_sub))

        return units

    def _assemble_chunks(self, units: List[tuple[str, bool]]) -> List[str]:
        """
        Assemble fine units into chunks up to chunk_size, applying chunk_overlap
        and respecting heading boundaries.
        """
        if not units:
            return []

        chunks: List[str] = []
        current_pieces: List[str] = []
        current_len = 0

        for unit_text, is_heading in units:
            if not unit_text.strip():
                continue

            piece_len = len(unit_text)
            sep_len = 2 if is_heading else 1  # use newline or space separator
            additional_len = piece_len + (sep_len if current_pieces else 0)

            # Check if adding this unit exceeds chunk_size
            # Also: if this unit is a heading and the current chunk already has substantial content (> 50% chunk_size),
            # split early to let the heading start a new chunk
            heading_split_condition = is_heading and current_len >= (self.chunk_size * 0.5)

            if (current_len + additional_len > self.chunk_size) or heading_split_condition:
                if current_pieces:
                    chunk_str = "\n\n".join(current_pieces) if any("\n" in p for p in current_pieces) else " ".join(current_pieces)
                    chunks.append(chunk_str)

                    # Compute overlap pieces to seed next chunk
                    overlap_pieces = self._compute_overlap_pieces(current_pieces)
                    current_pieces = list(overlap_pieces)
                    current_len = sum(len(p) for p in current_pieces) + max(0, len(current_pieces) - 1)

            current_pieces.append(unit_text)
            current_len += piece_len + (1 if len(current_pieces) > 1 else 0)

        if current_pieces:
            chunk_str = "\n\n".join(current_pieces) if any("\n" in p for p in current_pieces) else " ".join(current_pieces)
            chunks.append(chunk_str)

        return chunks

    def _compute_overlap_pieces(self, pieces: List[str]) -> List[str]:
        """Select a suffix of pieces whose cumulative length is <= chunk_overlap."""
        if self.chunk_overlap <= 0 or not pieces:
            return []

        # Do not retain the full piece set to avoid duplicate chunks
        if len(pieces) <= 1:
            return []

        overlap_accum: List[str] = []
        accum_len = 0

        # Traverse backwards from the last piece
        for piece in reversed(pieces):
            needed = len(piece) + (1 if overlap_accum else 0)
            if accum_len + needed <= self.chunk_overlap:
                overlap_accum.insert(0, piece)
                accum_len += needed
            else:
                break

        # If even the last piece is longer than chunk_overlap, we do not retain it
        # to strictly respect chunk_overlap upper bound
        return overlap_accum
