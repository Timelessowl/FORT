import re


def sanitize_mermaid_code(mermaid_code: str) -> str:
    def clean_block(block: str) -> str:
        # Удаляем HTML и JS
        block = re.sub(r"<script.*?>.*?</script>", "", block, flags=re.DOTALL)
        block = re.sub(r"<[^>]+>", "", block)

        # Удаляем однострочные комментарии // ...
        block = re.sub(r"^\s*//.*$", "", block, flags=re.MULTILINE)

        # Удаляем кавычки внутри стрелок и по краям
        block = block.replace('"', '')

        # Очищаем пустые и явно невалидные строки
        lines = []
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            # Пропускаем строки, не содержащие хотя бы один признак синтаксиса
            if not re.search(r"(-->|\-\-|\[\[|\]\]|\(\)|\(|\)|{|\}|:)", line) and not re.match(
                    r'^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|journey|pie)\b',
                    line):
                continue
            lines.append(line)

        return '\n'.join(lines)

    # Ищем все ```mermaid блоки
    mermaid_blocks = re.findall(r"```mermaid\s*(.*?)\s*```", mermaid_code, flags=re.DOTALL)
    if not mermaid_blocks:
        # Вдруг это просто текст с `graph TD` и без markdown — тогда ищем по ключевым словам
        keywords = [
            "graph TD", "graph LR", "graph RL", "graph BT",
            "flowchart TB", "flowchart TD", "sequenceDiagram",
            "classDiagram", "stateDiagram", "erDiagram",
            "gantt", "journey", "pie"
        ]
        for keyword in keywords:
            pattern = rf"({re.escape(keyword)}[\s\S]+?)(?=\n\S|\Z)"
            match = re.search(pattern, mermaid_code)
            if match:
                return clean_block(match.group(1))

        return ""

    # Берём первый валидный блок
    for raw_block in mermaid_blocks:
        cleaned = clean_block(raw_block)
        if cleaned.strip():
            return cleaned

    return ""


if __name__ == "__main__":
    invalid_mermaid = """
 ```mermaid
graph TD
    Client[Client] --> |Create Repair Request| ServiceEngineer((Service Engineer))
    ServiceEngineer --> |Assign Task| Technician((Technician))
    Technician --> |Perform Repair| Equipment[Equipment]
    Equipment --> |Update Status| Database[[Database]]
    Database --> |Generate Report| DepartmentManager(Department Manager)
    DepartmentManager --> |Approve Expenses| FinanceDepartment(Finance Department)
    FinanceDepartment --> |Analyze Costs| ITSupportTeam(IT Support Team)
    ITSupportTeam --> |Monitor System| SystemAdministrator(System Administrator)
    SystemAdministrator --> |Manage Access Rights| Client
```
        """

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)

    invalid_mermaid = """Конечно! Вот пример того, как можно создать диаграмму активности в формате Mermaid.js для вашего технического задания: 

mermaid
flowchart TB
    start([Начало])
    task1["Обработка запроса пользователя"]
    decision{"Запрос корректен?"}
    task2["Проверка данных"]
    task3["Сохранение в базу данных"]
    task4["Отправка уведомления"]
    fork1{Параллельная обработка}
    join1{Объединение потоков}
    task5["Формирование отчета"]
    end1([Конец])

    start --> task1
    task1 --> decision
    decision -- Да --> task2
    decision -- Нет --> task3
    task2 --> fork1
    fork1 --> task4 & task5
    task4 --> join1
    task5 --> join1
    join1 --> end1


Этот код создает диаграмму активности, которая включает в себя обработку запроса пользователя, проверку его корректности, сохранение данных в базе, отправку уведомления и формирование отчета. Параллельное выполнение задач показано через использование операторов fork и join."""

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)

    invalid_mermaid = """
      ```mermaid
        graph TD
        
        // Внешние сущности
        User[User]
        Client[Client]
        
        // Процессы
        Process(Создание заявки на ремонт)
        Process(Отслеживание статуса заявки)
        Process(Выполнение ремонтных работ)
        Process(Закрытие заявки)
        Process(Аналитика и отчетность)
        
        // Хранилища данных
        DB[[База данных]]
        
        // Потоки данных
        User -->|Заявка на ремонт| Client
        Client -->|Статус заявки| Process
        Client -->|Информация о ремонте| Process
        Client -->|Уведомление об окончании ремонта| Process
        Client -->|Отчеты| Process
        
        // Стрелки
        A -->|Данные| B
        ```
    """

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)

    invalid_mermaid = """
         ```mermaid
            usecaseDiagram
                actor Customer as C
                Customer — (Login)
                (Login) --›|(includes authentication)| (Authenticate)
                rectangle MySystem { (Login) (Purchase) }
        ```
    """

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)

    invalid_mermaid = """
         Конечно! Вот пример реализации твоего запроса:
        
        ```mermaid
        flowchart TB
          start[Начало]
        
          task1["Получить запрос от пользователя"]
          decision{"Проверить валидность данных?"}
        
          task2["Обработать запрос"]
          task3["Отправить ответ пользователю"]
        
          join[Завершение]
        
          start --> task1 --> decision
          decision -- Валидно --> task2 --> task3 --> join
          decision -- Невалидно --> task1 --> end
        
          end[Конец]
        ```
        
        Этот код создаст диаграмму деятельности в стиле BPMN с начальной и конечной точками, а также с действиями для обработки запроса.
    """

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)

    invalid_mermaid = """
         Для того чтобы создать C4-модель в формате Mermaid.js на основе предоставленного тобой текста технического задания, нужно выделить основные элементы модели и их взаимосвязи. Вот как это может выглядеть:
        
        ```mermaid
        C4Context
          Person(customer, "Customer")
          System_Boundary(OnlineStore, "Online Store") {
            System(webApp, "Web Application")
          }
          System_Ext(paymentSvc, "Payment Gateway")
        
          Rel(customer, webApp, "Places orders via web UI")
          Rel(webApp, paymentSvc, "Requests payment", "REST/JSON")
        ```
        
        Этот код создаёт основную систему `OnlineStore`, включает в неё подсистему `webApp` и указывает на внешнюю систему `paymentSvc`. Также он показывает связь между `customer` (внешний участник) и `webApp` через размещение заказов (`Places orders via web UI`). Кроме того, указывается взаимодействие между `webApp` и `paymentSvc` для запроса оплаты через REST/JSON протокол.
    """

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)

    invalid_mermaid = """
        Для того чтобы сгенерировать ER-диаграмму в формате Mermaid.js, необходимо следовать следующим шагам:
        
        1. **Выделение сущностей и атрибутов**:
           - **Customer**:
             - `PK id INT`
             - `name VARCHAR`
             - `email VARCHAR`
           - **Order**:
             - `PK id INT`
             - `FK customerId INT`
             - `orderDate DATE`
        
        2. **Определение связей с кардинальностями**:
           - Связь между `Customer` и `Order`: `Customer ||--o{ Order : "places"` (где `places` означает, что один клиент может разместить много заказов).
        
        Вот как это будет выглядеть в виде кода для Mermaid.js:
        
        ```mermaid
        erDiagram
          Customer {
            PK id INT,
            name VARCHAR,
            email VARCHAR
          }
          Order {
            PK id INT,
            FK customerId INT,
            orderDate DATE
          }
          Customer ||--o{ Order : "places"
        ```
        
        Этот код создаст следующую ER-диаграмму:
        
        ```mermaid
        Customer
          * PK id INT
          * name VARCHAR
          * email VARCHAR
        Order
          * PK id INT
          * FK customerId INT
          * orderDate DATE
        Customer --o{ Order : "places"
        ```
    """

    clean_mermaid = sanitize_mermaid_code(invalid_mermaid)
    print(clean_mermaid)
