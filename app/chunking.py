def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    """Splits the text into segments up to `size` characters long.

    Subsequent segments overlap by approximately `overlap` characters so that a sentence split
    at the boundary is not lost. The split occurs at a space, not in the middle of a word
    (provided there is a space in the window).
    """
    if size <= 0 or overlap < 0 or size <= overlap:
        raise ValueError("Size must be greater than 0 and overlab must be equal greater than 0")

    text = " ".join(text.split()) # Replace multiple white characters with a single space
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + size, len(text))

        if end < len(text):
            cut = text.rfind(" ", start + size // 2, end)
            if cut != -1:
                end = cut

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        next_start = max(end - overlap, start + 1)
        space = text.find(" ", next_start, end)
        if space != -1:
            next_start = space + 1  # The next part begins at the start of the word
        start = next_start

    return chunks