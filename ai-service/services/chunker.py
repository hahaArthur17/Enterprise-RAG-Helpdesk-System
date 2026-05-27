import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger("ai-service")

# Parent splitter: large window for full context
PARENT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", ".", " ", ""],
)

# Child splitter: small window for precise retrieval
CHILD_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20,
    separators=["\n\n", "\n", ".", " ", ""],
)


def split_parent_child(
    text: str,
    source_filename: str,
    section_title: str | None = None,
    page_number: int | None = None,
) -> list[dict]:
    """
    Split text into parent-child chunk hierarchy.

    Returns a list of parent dicts, each containing child chunks:
    [
        {
            "parent_content": "...",
            "source_filename": "report.pdf",
            "section_title": "Chapter 1",
            "page_number": 3,
            "children": [
                {"content": "...", "chunk_index": 0, "page_number": 3},
                ...
            ]
        },
        ...
    ]
    """
    parent_chunks = PARENT_SPLITTER.split_text(text)
    result = []

    for parent_text in parent_chunks:
        child_chunks = CHILD_SPLITTER.split_text(parent_text)
        result.append(
            {
                "parent_content": parent_text,
                "source_filename": source_filename,
                "section_title": section_title,
                "page_number": page_number,
                "children": [
                    {
                        "content": child,
                        "chunk_index": i,
                        "page_number": page_number,
                    }
                    for i, child in enumerate(child_chunks)
                ],
            }
        )

    logger.info(
        f"Split into {len(result)} parent chunks, "
        f"{sum(len(p['children']) for p in result)} child chunks total"
    )
    return result
