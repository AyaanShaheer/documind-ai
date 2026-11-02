
import pytest
import re

from app.services.chunking import (
    chunk_text,
    chunk_pages,
    chunk_pages_by_tokens,
)


def test_short_text_returns_one_chunk():

    text = "DocuMind AI is a document intelligence platform."

    chunks = chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_empty_text_returns_empty_list():

    assert chunk_text("") == []


def test_chunk_size():

    text = " ".join(
        f"word{i}" for i in range(250)
    )

    chunks = chunk_text(
        text,
        chunk_size_words=100,
        overlap_words=20,
    )

    assert len(chunks) == 3

    for chunk in chunks:
        assert len(chunk.split()) <= 100


def test_overlap_is_preserved():

    text = " ".join(
        f"word{i}" for i in range(250)
    )

    chunks = chunk_text(
        text,
        chunk_size_words=100,
        overlap_words=20,
    )

    first = chunks[0].split()
    second = chunks[1].split()

    assert first[-20:] == second[:20]


def test_invalid_chunk_configuration():

    with pytest.raises(ValueError):

        chunk_text(
            "Some text",
            chunk_size_words=100,
            overlap_words=100,
        )


def test_page_numbers_are_preserved():

    pages = [
        {
            "page_number": 1,
            "text": "This is text from page one."
        },
        {
            "page_number": 2,
            "text": "This is text from page two."
        }
    ]

    chunks = chunk_pages(pages)

    assert chunks[0]["page_number"] == 1
    assert chunks[1]["page_number"] == 2

class FakeTokenizer:

    def encode(self, text, **kwargs):
        return text.split()

    def decode(self, token_ids, **kwargs):
        return " ".join(token_ids)


def test_token_aware_chunking_respects_limit():

    tokenizer = FakeOffsetTokenizer()

    pages = [{
        "page_number": 1,
        "text": " ".join(f"word{i}" for i in range(250))
    }]

    chunks = chunk_pages_by_tokens(
        pages,
        tokenizer,
        max_tokens=100,
        overlap_tokens=20,
    )

    assert len(chunks) == 3

    assert all(
        chunk["token_count"] <= 100
        for chunk in chunks
    )


def test_token_chunks_preserve_page_numbers():

    tokenizer = FakeOffsetTokenizer()

    pages = [
        {"page_number": 1, "text": "page one content"},
        {"page_number": 2, "text": "page two content"},
    ]

    chunks = chunk_pages_by_tokens(
        pages,
        tokenizer,
    )

    assert chunks[0]["page_number"] == 1
    assert chunks[1]["page_number"] == 2


class FakeOffsetTokenizer:

    is_fast = True

    def __call__(
        self,
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
        truncation=False,
    ):

        matches = list(re.finditer(r"\S+", text))

        return {
            "input_ids": list(range(len(matches))),
            "offset_mapping": [
                (match.start(), match.end())
                for match in matches
            ],
        }


def test_token_chunking_preserves_original_text():

    tokenizer = FakeOffsetTokenizer()

    original_text = "DocuMind AI Upload Test"

    pages = [{
        "page_number": 1,
        "text": original_text,
    }]

    chunks = chunk_pages_by_tokens(
        pages,
        tokenizer,
    )

    assert chunks[0]["text"] == original_text
