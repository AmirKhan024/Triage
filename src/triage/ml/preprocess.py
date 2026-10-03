"""Issue text preprocessing pipeline for ML classification.

Section 6.3 specifications:
- Text = title + newline + body.
- Remove HTML comments.
- Replace code blocks, URLs, and stack traces with placeholder tokens:
  <CODE>, <URL>, <TRACE>.
- Truncate bodies longer than MAX_BODY_CHARS, preserving head and tail.
"""

import re

# Regex patterns
HTML_COMMENT_PATTERN = re.compile(r"<!--[\s\S]*?-->")
CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")

# Stack trace patterns (Python, JavaScript, Java/C++)
STACK_TRACE_PATTERNS = [
    re.compile(
        r"(?:Traceback \(most recent call last\):[\s\S]*?(?:\w+Error|\w+Exception):[^\n]+)",
        re.MULTILINE,
    ),
    re.compile(r"(?:^\s*at\s+[\w\.\<\>\$]+\s*(?:\([^)]*\)|[^\n]*)\s*)+", re.MULTILINE),
    re.compile(
        r"(?:^\s*(?:Caused by:|\bException in thread\b)[^\n]+(?:\n\s+at\s+[^\n]+)+)", re.MULTILINE
    ),
]


def remove_html_comments(text: str) -> str:
    """Remove HTML comments embedded from GitHub issue templates."""
    return HTML_COMMENT_PATTERN.sub("", text)


def replace_code_blocks(text: str) -> str:
    """Replace fenced code blocks with <CODE> placeholder."""
    return CODE_BLOCK_PATTERN.sub(" <CODE> ", text)


def replace_urls(text: str) -> str:
    """Replace web URLs with <URL> placeholder."""
    return URL_PATTERN.sub(" <URL> ", text)


def replace_stack_traces(text: str) -> str:
    """Replace stack traces with <TRACE> placeholder."""
    processed = text
    for pattern in STACK_TRACE_PATTERNS:
        processed = pattern.sub(" <TRACE> ", processed)
    return processed


def truncate_body(body: str, max_chars: int = 6000) -> str:
    """Truncate very long bodies to max_chars, keeping the start and the end."""
    if len(body) <= max_chars:
        return body
    half = max_chars // 2
    return body[:half] + "\n...\n" + body[-half:]


def preprocess_text(title: str, body: str, max_chars: int = 6000) -> str:
    """Clean and combine issue title and body for classification.

    Preserves original text for rules layer while preparing normalized
    representation for feature extraction.
    """
    clean_title = (title or "").strip()
    clean_body = (body or "").strip()

    # Truncate body if exceeding threshold
    clean_body = truncate_body(clean_body, max_chars=max_chars)

    # Combine title and body
    combined = f"{clean_title}\n{clean_body}"

    # Apply sanitization and token replacements
    combined = remove_html_comments(combined)
    combined = replace_code_blocks(combined)
    combined = replace_stack_traces(combined)
    combined = replace_urls(combined)

    # Collapse multiple whitespaces
    combined = re.sub(r"[ \t]+", " ", combined)
    combined = re.sub(r"\n{3,}", "\n\n", combined)

    return combined.strip()
