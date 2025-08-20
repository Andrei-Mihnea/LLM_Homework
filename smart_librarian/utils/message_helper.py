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

import re

def sanitize_ctx_messages(messages: list[dict]) -> list[dict]:
    """
    Remove <audio>…</audio> tags and any base64-like blobs from the message contents,
    so they don't get sent back to the LLM.

    Args:
        messages: list of {"role": str, "content": str}

    Returns:
        A sanitized copy of messages.
    """
    cleaned = []
    for m in messages:
        if not isinstance(m.get("content"), str):
            cleaned.append(m)
            continue

        text = m["content"]

        # remove <audio>…</audio> tags completely
        text = re.sub(r"<audio>.*?</audio>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # remove very long base64-like strings (just in case)
        # (looks like a long run of A–Z, a–z, 0–9, +, / with optional padding =)
        text = re.sub(r"[A-Za-z0-9+/=]{100,}", "[[base64 removed]]", text)

        cleaned.append({"role": m["role"], "content": text.strip()})

    return cleaned
