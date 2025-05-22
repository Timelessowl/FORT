import re


def sanitize_mermaid_code_2(mermaid_code: str) -> str:
    start_marker = "```mermaid\n"
    end_marker = "```"

    start_index = mermaid_code.find(start_marker) + len(start_marker)
    end_index = mermaid_code.rfind(end_marker)

    if start_index == -1 or end_index == -1 or start_index >= end_index:
        return ""

    return mermaid_code[start_index:end_index].strip()
