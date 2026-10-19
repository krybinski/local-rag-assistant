import pytest

from app.chunking import chunk_text

def test_empty_text_gives_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\t ") == []

def test_short_text_is_single_chunk():
    assert chunk_text("Tom has a cat.", size = 100, overlap = 10) == ["Tom has a cat."]

def test_chunks_respect_max_size():
    text = "word " * 500
    chunks = chunk_text(text, size = 200, overlap = 40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)

def test_consecutive_chunks_overlap():
    text = "word " * 500
    chunks = chunk_text(text, size = 200, overlap = 40)
    # The beginning of the next part repeats the end of the previous one
    assert chunks[1][:15] in chunks[0]

def test_no_words_are_lost_or_split():
    words = [f"w{i}" for i in range(300)]
    chunks = chunk_text(" ".join(words), size = 120, overlap = 30)
    seen = set(" ".join(chunks).split())
    assert all(w in seen for w in words)

def test_text_without_spaces_is_hard_cut():
    chunks = chunk_text("a" * 1000, size = 300, overlap = 50)
    assert all(len(c) <= 300 for c in chunks)
    assert len(chunks) >= 4

@pytest.mark.parametrize("size,overlap", [(100, 100), (50, 80), (0, 0), (100, -1)])
def test_invalid_parameters_raise(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("sentence", size = size, overlap = overlap)
