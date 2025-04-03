import requests
import uuid
import base64
import environ


def get_access_token(client_id: str, client_secret: str) -> str:
    """
    Получает OAuth2 access_token от GigaChat API.
    """
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


def generate_mermaid_dfd_from_description(description: str, access_token: str) -> str:
    """
    Отправляет описание в GigaChat API и возвращает сгенерированный Mermaid.js код.
    """
    GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

    prompt = f"""
    Ты — помощник, который генерирует DFD (Data Flow Diagram) диаграммы в формате Mermaid.js.

    Используй только синтаксис Mermaid.js с типом "graph TD". Обозначай:
    - внешние сущности как прямоугольники (например, User[User])
    - процессы — как окружённые скобками (например, Process((Обработка)))
    - хранилища данных — как двойные линии (например, DB[[Database]])
    - потоки данных — стрелками (пример стрелки -->) с  подписями (например, A -->|Данные| B )

    Преобразуй следующее пользовательское описание в корректный Mermaid код для DFD диаграммы:

    "{description}"

    Верни только mermaid код, без пояснений и комментариев.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Accept": "application/json"
    }

    payload = {
        "model": "GigaChat-Pro",
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "stream": False
    }

    try:
        response = requests.post(GIGACHAT_API_URL, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"Ошибка при запросе к GigaChat API: {e}\nОтвет: {getattr(e.response, 'text', 'нет данных')}")


# Пример использования
if __name__ == "__main__":
    env = environ.Env()

    client_id = env('CLIENT_ID')
    client_secret = env('CLIENT_SECRET')

    token = get_access_token(client_id, client_secret)
    description = "Пользователь загружает изображение. Сервер обрабатывает изображение. Результат сохраняется в базу данных."
    mermaid_code = generate_mermaid_dfd_from_description(description, token)
    print("\nMermaid DFD Code:\n")
    print(mermaid_code)
