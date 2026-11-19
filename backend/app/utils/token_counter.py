import tiktoken

def estimate_tokens(text: str) -> int:

    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return max(1,len(text.split())*2) if text.strip() else 0
