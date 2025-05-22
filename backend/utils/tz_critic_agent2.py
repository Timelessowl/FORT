import os

import requests
import uuid
import base64
from langchain_gigachat.chat_models import GigaChat
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


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

    def clarify_or_generate(self, previous: str, user_input: str,
                            llm_callable, token: str) -> str:
        """
        Сначала проверяем, нужно ли уточнить информацию или можно сразу сгенерировать.
        Если LLM возвращает текст, заканчивающийся на '?', считаем это уточняющим вопросом.
        Иначе — это готовый раздел.
        """
        prompt = f"""
            Ты — эксперт по разделу «{self.name}».
            У тебя на входе — предыдущий текст (если был) и пользовательский ввод:
            {user_input}
            
            1) Если данных недостаточно для полноценного раздела — задай один уточняющий вопрос.
            2) Иначе — сразу сгенерируй раздел по шаблону.
            """
        return llm_callable(prompt.strip(), token).strip()


# === Агент-критик ===
class TzCriticAgent:
    def __init__(
            self,
            word_doc_path: str,
            embedding_model,
            llm,
            chunk_size: int = 1000,
            chunk_overlap: int = 200,
            retriever_k: int = 5
    ):
        # 1) Загружаем Word и разбиваем на чанки
        docs = UnstructuredWordDocumentLoader(word_doc_path).load()
        chunks = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        ).split_documents(docs)

        # 2) FAISS + GigaChatEmbedddings
        vs = FAISS.from_documents(chunks, embedding_model)
        retriever = vs.as_retriever(search_kwargs={"k": retriever_k})

        # 3) Шаблон RAG-промпта
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
                Контекст (рекомендации по ТЗ):
                {context}
                
                Задача: улучшить блок ТЗ по критериям:
                1. Логичность структуры и полнота
                2. Конкретность формулировок
                3. Удалить избыточное
                4. Добавить недостающее (название, цели, роли, use-case, безопасность…)
                
                Текст блока:
                {question}
                
                Верните только итоговый улучшённый текст без инструкций модели.
                """.strip())

        # 4) Собираем RAG-цепочку через RetrievalQA
        self.rag_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt},
        )

    def review(self, tz_block: str) -> str:
        return self.rag_chain.run(query=tz_block)


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
            В ответе выдай ТОЛЬКО готовый раздел ТЗ без инструкций, подсказок или комментариев.
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
            Верни только конечный текст раздела «Цели проекта», без шаблонных указаний
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
            Введи ответ  без инструкций модели.
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
            Введите в ответ ТОЛЬКО готовый список требований, без инструкций модели.
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
            "model": "GigaChat-Pro",
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


class UseCaseDiagramAgent:
    def __init__(self):
        self.name = "Use Case Diagram Generator"
        self.prompt_template = '''
                Ты — помощник по генерированию UML Use Case Diagram в формате Mermaid.js.
                На входе — полное текстовое техническое задание проекта.
                Твоя задача:
                1. Выделить всех основных и вспомогательных акторов (пользователи, внешние системы).
                2. Определить ключевые прецеденты (use cases): что делает каждый актор.
                3. Показывать связи:
                   - ассоциации (Actor — UseCase),
                   - «include» (UseCase -->|<<include>>| OtherUseCase),
                   - «extend» (UseCase -->|<<extend>>| OtherUseCase).
                4. Группировать прецеденты в границы системы (с помощью `rectangle System { ... }`).
                5. Использовать синтаксис Mermaid:
                      %%{ init: {'theme': 'default'} }%%
                        graph TD
                          C[Customer] --> Login
                          Login --> Authenticate
                          subgraph MySystem
                            Login
                            Purchase
                          end
                Верни только mermaid-код без пояснений.
                '''

    def generate(self, tz_text: str, token: str) -> str:
        prompt = self.prompt_template
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4())
        }
        payload = {
            "model": "GigaChat-Pro",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "stream": False
        }
        response = requests.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers=headers, json=payload, verify=False
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class ActivityDiagramAgent:
    def __init__(self):
        self.name = "Activity Diagram Generator"
        self.prompt_template = '''
            Ты — помощник, генерирующий подробный Activity Diagram (BPMN-like) в формате Mermaid.js, синтаксис flowchart TB.
            На входе — полный текст технического задания.
            Твоя задача:
            1. Определить начальную ноду (`start`).
            2. Выделить ключевые действия и соединить их стрелками (`-->`).
            3. Моделировать точки принятия решений (`decision`) с исходами (`-->|label|`).
            4. Отметить параллельные потоки (`fork` / `join`).
            5. Обозначить конечную ноду (`endNode`).
            6. Показать циклические ветки при необходимости.
            Пример:
                flowchart TB
                    start([Start])
                    task1["Получить запрос от пользователя"]
                    decision{"Валидны ли данные?"}
                    task2["Сохранить в БД"]
                    task3["Вернуть ошибку"]
                    endNode([End])
                    
                    start --> task1 --> decision
                    decision -- Yes --> task2 --> endNode
                    decision -- No --> task3 --> endNode
            Верни только mermaid-фрагмент.
            '''

    def generate(self, tz_text: str, token: str) -> str:
        prompt = self.prompt_template
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json",
                   "RqUID": str(uuid.uuid4())}
        payload = {"model": "GigaChat-Pro", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7,
                   "stream": False}
        response = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions", headers=headers,
                                 json=payload, verify=False)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class C4ContextDiagramAgent:
    def __init__(self):
        self.name = "C4 Context Diagram Generator"
        self.prompt_template = '''
            Ты — помощник по генерации C4-модели (уровень Context) в формате Mermaid.js с использованием C4 plugin.
            На входе — полный текст технического задания.
            Твоя задача:
            1. Обозначить основную систему: System_Boundary(alias, "System Name") { }.
            2. Выделить внешних участников: Person(alias, "Name").
            3. Показать внешние системы: System_Ext(alias, "External System").
            4. Провести зависимости: Rel(source, target, "Описание", "Протокол").
            Пример:
            
            C4Context
              Person(customer, "Customer")
              System_Boundary(OnlineStore, "Online Store") {
                System(webApp, "Web Application")
              }
              System_Ext(paymentSvc, "Payment Gateway")
            
              Rel(customer, webApp, "Places orders via web UI")
              Rel(webApp, paymentSvc, "Requests payment", "REST/JSON")
            Верни только mermaid-код.
            '''

    def generate(self, tz_text: str, token: str) -> str:
        prompt = self.prompt_template
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                   "Accept": "application/json", "RqUID": str(uuid.uuid4())}
        payload = {"model": "GigaChat-Pro", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7,
                   "stream": False}
        response = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions", headers=headers,
                                 json=payload, verify=False)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class ERDiagramAgent:
    def __init__(self):
        self.name = "ER Diagram Generator"
        self.prompt_template = '''
                Ты — помощник, генерирующий ER-диаграмму в формате Mermaid.js, синтаксис erDiagram.
                На входе — текстовые блоки ТЗ.
                Твоя задача:
                1. Выделить сущности и атрибуты.
                2. Указать PK/ FK: Table { id INT PK }.
                3. Определить связи с кардинальностями: Entity1 ||--o{ Entity2 : "has many".
                Пример:
                      erDiagram
                        Customer {
                            id INT PK
                            name VARCHAR
                            email VARCHAR
                        }
                        Order {
                            id INT PK
                            customerId INT FK
                            orderDate DATE
                        }
                        Customer ||--o{ Order : "places"
                    Верни только mermaid-описание.
                    '''

    def generate(self, tz_text: str, token: str) -> str:
        prompt = self.prompt_template
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                   "Accept": "application/json", "RqUID": str(uuid.uuid4())}
        payload = {"model": "GigaChat-Pro", "messages": [{"role": "user", "content": prompt}],
                   "temperature": 0.7, "stream": False}
        response = requests.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                                 headers=headers, json=payload, verify=False)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


# === Контроллер пайплайна ===
class TzPipeline:
    def __init__(self, llm_callable, embedding_model, llm):
        self.llm = llm_callable
        self.agents = {
            "description": DescriptionAgent(),
            "goals": GoalsAgent(),
            "users": UsersAgent(),
            "requirements": RequirementsAgent()
        }
        self.critic = TzCriticAgent(
            word_doc_path="tz_guidelines.docx",
            embedding_model=embedding_model,
            llm=llm
        )
        self.diagram_agents = {
            "DFD": MermaidDiagramAgent(),
            "Use Case": UseCaseDiagramAgent(),
            "Activity": ActivityDiagramAgent(),
            "C4 Context": C4ContextDiagramAgent(),
            "ER Diagram": ERDiagramAgent(),
        }

    def run_agent(self, agent_key: str, last_response: str, user_comment: str, token: str) -> str:
        agent = self.agents[agent_key]

        # Фаза уточнений
        resp = agent.clarify_or_generate(last_response, user_comment, self.llm, token)
        if resp.endswith("?"):
            return resp

        # Фаза критики
        improved_output = self.critic.review(resp)

        agent.last_response = improved_output
        return improved_output


    def get_all_responses(self) -> dict:
        return {key: agent.last_response for key, agent in self.agents.items()}

    def get_full_text(self) -> str:
        return "\n\n".join(agent.last_response for agent in self.agents.values())

    def generate_all_diagrams(self, full_text: str, token: str, diagram_types: list[str]) -> dict:
        # full_text = self.get_full_text()
        outputs = {}
        for title, agent in self.diagram_agents.items():
            if title in diagram_types:
                outputs[title] = agent.generate(full_text, token)
        return outputs


# === CLI-запуск ===
if __name__ == "__main__":

    client_id = ""
    client_secret = ""

    # Получение токена
    token = get_access_token(client_id, client_secret)

    basic_creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    # 2) (Опционально) Через переменную окружения
    os.environ["GIGACHAT_CREDENTIALS"] = basic_creds

    # 3) Инициализируем LLM и эмбеддинги
    llm = GigaChat(
        # либо просто GigaChat(), если задали GIGACHAT_CREDENTIALS
        credentials=basic_creds,
        auth_url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        base_url="https://gigachat.devices.sberbank.ru/api/v1",
        scope="GIGACHAT_API_PERS",
        verify_ssl_certs=False,
    )

    model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    model_kwargs = {"device": "cpu"}
    encode_kwargs = {"normalize_embeddings": False}

    local_embedding = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

    # Инициализация пайплайна
    pipeline = TzPipeline(llm_callable=call_gigachat, embedding_model=local_embedding, llm=llm)

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

    print("\n📊 Генерация всех диаграмм по техническому заданию…")
    all_diags = pipeline.generate_all_diagrams(token)
    for title, code in all_diags.items():
        print(f"\n🔧 {title} диаграмма:\n")
        print("```mermaid")
        print(code.strip())
