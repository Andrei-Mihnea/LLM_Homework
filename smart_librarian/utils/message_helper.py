import base64
import re

# Compile once at module import time
AUDIO_TAG_RE   = re.compile(r"<audio(?:\s+[^>]*)?>.*?</audio>", re.IGNORECASE | re.DOTALL)
IMAGE_TAG_RE   = re.compile(r"<image(?:\s+[^>]*)?>.*?</image>", re.IGNORECASE | re.DOTALL)
# Matches optional data:...;base64, prefix and long base64-looking runs
BASE64_BLOB_RE = re.compile(r"(?:data:[\w/+.\-]+;base64,)?[A-Za-z0-9+/=]{100,}")
def check_profanity(client,message:str) -> bool:
    resp = client.moderations.create(
        model="omni-moderation-latest",
        input=message
    )

    flagged = resp.results[0].flagged
    categories = resp.results[0].categories

    if flagged:
        print("⚠️ Message flagged:", categories)
    return flagged



def sanitize_ctx_messages(messages: list[dict]) -> list[dict]:
    """
    Remove <audio>…</audio>, <image …>…</image> tags, and any long base64-like blobs
    from message contents before sending history back to the LLM.

    Args:
        messages: list of {"role": str, "content": Any, ...}

    Returns:
        A sanitized, shallow-copied list of messages. Only 'content' is modified.
    """
    cleaned: list[dict] = []
    for m in messages:
        # Shallow copy to avoid mutating caller's objects
        out = dict(m)

        content = out.get("content")
        if isinstance(content, str) and content:
            text = content

            # 1) Strip custom media tags completely (ignore case, span newlines)
            text = AUDIO_TAG_RE.sub("", text)
            text = IMAGE_TAG_RE.sub("", text)

            # 2) Replace very long base64-like blobs with a placeholder
            text = BASE64_BLOB_RE.sub("[[media removed]]", text)

            out["content"] = text.strip()

        # Non-string contents (e.g., tool calls) are left as-is
        cleaned.append(out)

    return cleaned

def to_b64(maybe_bytes):
    if not maybe_bytes:
        return None
    return base64.b64encode(maybe_bytes).decode("ascii")
