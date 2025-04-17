import requests
import uuid
import base64
import environ


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
        "model": "GigaChat-Pro",
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


# === Агенты с промтами ===
class DescriptionAgent(BaseAgent):
    def __init__(self):
        prompt = """
Ты — профессиональный аналитик. Составь краткое описание проекта, включая:
1. Название (если есть)
2. Что делает продукт?
3. Какую проблему решает?
4. Для кого предназначен?
5. Контекст и предпосылки

Обнови описание, учитывая правки.

Входной текст:
{previous_response_and_comment}
"""
        super().__init__("Описание проекта", prompt)


class GoalsAgent(BaseAgent):
    def __init__(self):
        prompt = """
Ты — аналитик, специализирующийся на целях проекта. Раздели цели на:
1. Бизнес-цели
2. Пользовательские цели

Обнови цели с учётом правок пользователя.

Входной текст:
{previous_response_and_comment}
"""
        super().__init__("Цели проекта", prompt)


class UsersAgent(BaseAgent):
    def __init__(self):
        prompt = """
Ты — системный аналитик. Определи:
- Пользовательские группы
- Их действия в системе
- Роли / уровни доступа

Учти комментарии и уточнения пользователя.

Входной текст:
{previous_response_and_comment}
"""
        super().__init__("Пользователи и роли", prompt)


class RequirementsAgent(BaseAgent):
    def __init__(self):
        prompt = """
Ты — инженер по требованиям. Составь:
1. Функциональные требования
2. Нефункциональные требования

Обнови требования по входному тексту с учётом правок.

Входной текст:
{previous_response_and_comment}
"""
        super().__init__("Требования", prompt)


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

    def run_agent(self, agent_key: str, last_response: str, user_comment: str, token: str) -> str:
        agent = self.agents[agent_key]
        # return agent.run(agent.last_response, user_comment, self.llm, token)
        return agent.run(last_response, user_comment, self.llm, token)

    def get_all_responses(self) -> dict:
        return {key: agent.last_response for key, agent in self.agents.items()}


# === CLI-запуск ===
# if __name__ == "__main__":
#     env = environ.Env()
#
#     client_id = env('CLIENT_ID')
#     client_secret = env('CLIENT_SECRET')
#     token = get_access_token(client_id, client_secret)
#
#     pipeline = TzPipeline(llm_callable=call_gigachat)
#
#     print(" Агент 1: Общее описание")
#     text = input("Введите описание или уточнение: ")
#     print(pipeline.run_agent("description", text, token))
#
#     print(" Агент 2: Цели проекта")
#     text = input("Опишите бизнес и пользовательские цели: ")
#     print(pipeline.run_agent("goals", text, token))
#
#     print(" Агент 3: Пользовательские группы")
#     text = input("Опишите пользователей и их роли: ")
#     print(pipeline.run_agent("users", text, token))
#
#     print(" Агент 4: Требования")
#     text = input("Опишите функциональные и нефункциональные требования: ")
#     print(pipeline.run_agent("requirements", text, token))
#
#     print("Итоговое ТЗ по всем агентам:")
#     all_blocks = pipeline.get_all_responses()
#     for k, v in all_blocks.items():
#         print(f" {k.upper()}\n{v}\n")
