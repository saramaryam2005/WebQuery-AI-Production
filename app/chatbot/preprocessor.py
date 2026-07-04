import re


def clean_text(text: str) -> str:
    """Clean website text before chunking."""

    # Remove extra blank lines
    text = re.sub(r"\n\s*\n", "\n\n", text)

    # Collapse multiple spaces
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()