def format_chat_history(messages, max_turns: int = 10) -> str:
    recent = messages[-max_turns*2:]
    lines = []
    for m in recent:
        role = m.get("role", "").upper()
        content = m.get("content", "")
        if not content:
            continue
        lines.append(f"{role}: {content}")
    return "\n".join(lines)