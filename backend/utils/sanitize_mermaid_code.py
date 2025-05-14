import re


def sanitize_mermaid_code(mermaid_code: str) -> str:
    code = re.sub(r'^\s*```mermaid\s*|\s*```\s*$', '', mermaid_code.strip(), flags=re.IGNORECASE)

    valid_lines = []
    mermaid_keywords = {
        "graph", "subgraph", "end",
        "sequenceDiagram", "gantt", "pie",
        "classDiagram", "stateDiagram", "gitGraph",
        "journey", "erDiagram", "requirementDiagram",
        "direction", "%%", "-->", "->", "==>", "-.->",
        "style", "click", "link", "classDef", "applyClass"
    }

    for line in code.split('\n'):
        stripped_line = line.strip()
        if not stripped_line:
            continue

        is_valid = any(
            stripped_line.startswith(keyword) or
            f" {keyword}" in stripped_line or
            f"\t{keyword}" in stripped_line
            for keyword in mermaid_keywords
        )

        if is_valid:
            clean_line = line.replace('"', '')
            valid_lines.append(clean_line)
        else:
            if valid_lines:
                break

    return '\n'.join(valid_lines).strip()


if __name__ == "__main__":
    invalid_mermaid = """
        graph TD
            Process((Принятие заявки)) -->|Присвоение статуса "В работе"| DB[[ERP]]
            <script>alert('XSS')</script>
        """

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)

    invalid_mermaid = """
     graph TD

    User[User] -->|Заявки на ремонт| Process(Обработка заявок)
    Process(Обработка заявок) -->|Статус заявки| DB[[База данных]]
    DB[[База данных]] -->|Отчеты| Process(Аналитика)
    Process(Аналитика) -->|Эффективность| User[Руководитель]
    
    Администратор системы имеет доступ к следующим элементам:
    
    Process(Настройка прав доступа) -->|Роли пользователей| User[Администратор]
    Process(Мониторинг активности)|User[Администратор]
    Process(Управление учетными записями)|User[Администратор]
    Process(Интеграция с другими системами)|User[Администратор]
    """

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)
