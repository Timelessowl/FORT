import requests
import uuid
import base64


# === Получение токена доступа ===
def get_access_token(client_id: str, client_secret: str) -> str:
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
        "RqUID": str(uuid.uuid4())
    }

    data = {
        "scope": "GIGACHAT_API_PERS"
    }

    response = requests.post(url, headers=headers, data=data, verify=False)
    response.raise_for_status()
    return response.json()["access_token"]


# === Вызов GigaChat ===
def call_gigachat(prompt: str, access_token: str) -> str:
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4())
    }

    payload = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "stream": False
    }

    response = requests.post(url, headers=headers, json=payload, verify=False)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# === Базовый класс агента ===
class BaseAgent:
    def __init__(self, name: str, prompt_template: str):
        self.name = name
        self.prompt_template = prompt_template
        self.last_response = ""

    def build_prompt(self, user_input: str) -> str:
        return self.prompt_template.format(previous_response_and_comment=user_input)

    def call_model(self, prompt: str, llm_callable, token: str) -> str:
        response = llm_callable(prompt, token)
        self.last_response = response
        return response

    def run(self, previous: str, user_comment: str, llm_callable, token: str) -> str:
        merged_input = previous.strip() + "\n\nКомментарий пользователя:\n" + user_comment.strip()
        prompt = self.build_prompt(merged_input)
        return self.call_model(prompt, llm_callable, token)


# === Агент-критик ===
class TzCriticAgent:
    def __init__(self):
        self.name = "Критикатор ТЗ"
        self.prompt_template = """
Ты — эксперт по технической документации. Проверь и при необходимости улучши следующий текст по следующим критериям:

1. Логичность структуры и полнота информации
2. Конкретность формулировок
3. Удаление избыточных или расплывчатых фраз
4. Добавление недостающих важных блоков (название, цели, роли, use-case, безопасность и т.д.)

Если всё хорошо — отформатируй текст и сохрани.

Текст:
{tz_block}
"""

    def review(self, block_text: str, llm_callable, token: str) -> str:
        prompt = self.prompt_template.format(tz_block=block_text.strip())
        return llm_callable(prompt, token)


# === Специализированные агенты ===
class DescriptionAgent(BaseAgent):
    def __init__(self):
        prompt = """
Ты — профессиональный аналитик. На основе пользовательского ввода подготовь краткое, но структурированное описание проекта, включающее:

1. Название проекта (если есть)
2. Общее назначение и цели проекта
3. Какая проблема решается?
4. Для кого предназначен продукт (целевая аудитория)?
5. Контекст и предпосылки для разработки (обоснование необходимости)
6. Планируемое взаимодействие с другими системами, если применимо
7. Словарь терминов и сокращений, упомянутых в тексте

Обнови описание с учетом комментариев пользователя.

Входной текст:
{previous_response_and_comment}
"""
        super().__init__("Описание проекта", prompt)


class GoalsAgent(BaseAgent):
    def __init__(self):
        prompt = """
Ты — аналитик по бизнес-требованиям. На основе входного текста уточни цели проекта и структурируй их:

1. Бизнес-цели
2. Пользовательские цели
3. Как реализация этих целей поможет достичь бизнес-показателей?
4. Тип задач: разработка с нуля, доработка, миграция и т.п.
Учитывай пользовательские правки при обновлении целей.

Входной текст:
{previous_response_and_comment}
"""
        super().__init__("Цели проекта", prompt)


class UsersAgent(BaseAgent):
    def __init__(self):
        prompt = """
Ты — системный аналитик. На основе ввода пользователя определи:

1. Основные пользовательские группы (например: клиенты, сотрудники, администраторы)
2. Роли и уровни доступа
3. Сценарии использования системой (use cases)
4. Действия пользователей и взаимодействие с системой

Обнови блок, учитывая комментарии.

Входной текст:
{previous_response_and_comment}
"""
        super().__init__("Пользователи и роли", prompt)


class RequirementsAgent(BaseAgent):
    def __init__(self):
        prompt = """
Ты — инженер по требованиям. На основе текста выдели и структурируй:

1. Функциональные требования
2. Нефункциональные требования
3. Требования к интерфейсу
4. Требования к интеграции
5. Требования к безопасности
6. Требования к качеству и надежности
7. Требования к разработке
8. Пользовательские сценарии

Обнови список требований с учётом входного текста и комментариев.

Входной текст:
{previous_response_and_comment}
"""
        super().__init__("Требования", prompt)


class MermaidDiagramAgent:
    def __init__(self):
        self.name = "Генератор диаграммы"

    def generate(self, tz_text: str, token: str) -> str:
        prompt = f"""
Ты — помощник, который генерирует DFD (Data Flow Diagram) диаграммы в формате Mermaid.js.

Используй только синтаксис Mermaid.js с типом "graph TD". Обозначай:
- внешние сущности как прямоугольники (например, User[User])
- процессы — как окружённые скобками (например, Process((Обработка)))
- хранилища данных — как двойные линии (например, DB[[Database]])
- потоки данных — стрелками (пример стрелки -->) с подписями (например, A -->|Данные| B)

Преобразуй следующее техническое задание в корректный Mermaid код для DFD диаграммы:

\"\"\"{tz_text}\"\"\"

Верни только mermaid код, без пояснений и комментариев.
"""

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4())
        }

        payload = {
            "model": "GigaChat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "stream": False
        }

        try:
            response = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                                     headers=headers, json=payload, verify=False)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            raise SystemExit(
                f"Ошибка при запросе к GigaChat API: {e}\nОтвет: {getattr(e.response, 'text', 'нет данных')}")


# === Контроллер пайплайна ===
class TzPipeline:
    def __init__(self, llm_callable):
        self.llm = llm_callable
        self.agents = {
            "description": DescriptionAgent(),
            "goals": GoalsAgent(),
            "users": UsersAgent(),
            "requirements": RequirementsAgent()
        }
        self.critic = TzCriticAgent()
        self.diagram_agent = MermaidDiagramAgent()

    def run_agent(self, agent_key: str, last_response: str, user_comment: str, token: str) -> str:
        agent = self.agents[agent_key]
        # raw_output = agent.run(agent.last_response, user_comment, self.llm, token)
        raw_output = agent.run(last_response, user_comment, self.llm, token)
        improved_output = self.critic.review(raw_output, self.llm, token)

        # print(f"\n📄 Результат от агента «{agent.name}» после критики:\n")
        # print(improved_output)
        # edit = input("\n🛠 Хотите отредактировать вручную? (y/N): ").strip().lower()
        # if edit == "y":
        #     print("\nВведите обновлённый текст. Введите END, чтобы завершить:")
        #     manual_input = []
        #     while True:
        #         line = input()
        #         if line.strip().upper() == "END":
        #             break
        #         manual_input.append(line)
        #     final_output = "\n".join(manual_input).strip()
        #     print(" Ваш текст сохранён.")
        # else:
        #     final_output = improved_output

        final_output = improved_output

        agent.last_response = final_output
        return final_output

    def get_all_responses(self) -> dict:
        return {key: agent.last_response for key, agent in self.agents.items()}

    def get_full_text(self) -> str:
        return "\n\n".join(agent.last_response for agent in self.agents.values())

    def generate_mermaid_diagram(self, full_text: str, token: str) -> str:
        # full_text = self.get_full_text()
        return self.diagram_agent.generate(full_text, token)


# === CLI-запуск ===
if __name__ == "__main__":
    client_id = ""
    client_secret = ""

    # Получение токена
    token = get_access_token(client_id, client_secret)

    # Инициализация пайплайна
    pipeline = TzPipeline(llm_callable=call_gigachat)

    # Работа с агентами
    print("📌 Шаг 1: Общее описание проекта")
    input_text = input("Введите описание или уточнение: ")
    pipeline.run_agent("description", input_text, token)

    print("\n📌 Шаг 2: Цели проекта")
    input_text = input("Опишите бизнес и пользовательские цели: ")
    pipeline.run_agent("goals", input_text, token)

    print("\n📌 Шаг 3: Пользовательские группы и роли")
    input_text = input("Опишите пользователей и их роли: ")
    pipeline.run_agent("users", input_text, token)

    print("\n📌 Шаг 4: Требования к продукту")
    input_text = input("Опишите функциональные и нефункциональные требования: ")
    pipeline.run_agent("requirements", input_text, token)

    # Вывод финального ТЗ
    print("\n✅ Сформированное техническое задание:")
    all_blocks = pipeline.get_all_responses()
    for key, value in all_blocks.items():
        print(f"\n=== {key.upper()} ===\n{value}\n")

    # Генерация диаграммы
    print("📈 Генерация DFD-диаграммы (Mermaid.js)...")
    mermaid_code = pipeline.generate_mermaid_diagram(token)

    print("\n🔧 Mermaid.js диаграмма:")
    print(mermaid_code)
