from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging
import uuid
import environ
import base64
import torch
import os
from langchain_gigachat.chat_models import GigaChat
from langchain_huggingface import HuggingFaceEmbeddings

from chat.models import AgentResponse
from chat.serializer import ChatResponseSerializer, ErrorResponseSerializer
from sentence_transformers import SentenceTransformer
from utils.tz_critic_agent2 import get_access_token, TzPipeline, call_gigachat

logger = logging.getLogger(__name__)


class ChatAPIView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        env = environ.Env()
        client_id = env('CLIENT_ID')
        client_secret = env('CLIENT_SECRET')

        self.access_token: str = get_access_token(client_id, client_secret)
        basic_creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        # 2) (Опционально) Через переменную окружения
        os.environ["GIGACHAT_CREDENTIALS"] = basic_creds
        # 3) Инициализируем LLM и эмбеддинги
        self.llm = GigaChat(
            # либо просто GigaChat(), если задали GIGACHAT_CREDENTIALS
            credentials=basic_creds,
            auth_url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            base_url="https://gigachat.devices.sberbank.ru/api/v1",
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
        )
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        model_kwargs = {"device": device}
        encode_kwargs = {"normalize_embeddings": False}

        try:
            model = SentenceTransformer(model_name_or_path=model_name, device=device)
        except Exception as e:
            logger.exception(f"Error loading embedding model: {e}")

        self.local_embedding = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )

    @extend_schema(
        summary='Генерация ТЗ через чат с ИИ агентом',
        description="""
        Этот эндпоинт позволяет пользователю начать или продолжить чат с ИИ-агентом для создания технического задания (ТЗ).
        Номер агента указывается в URL.
        
        Пользователь отправляет текст сообщения и, при необходимости, токен (уникальный идентификатор чата).
        Если токен отсутствует (например, при первом сообщении), он генерируется автоматически. 
        Ответ всегда содержит токен для продолжения диалога и текст (вопрос или ТЗ).
        """,
        operation_id='chat_generate_tz',
        parameters=[
            OpenApiParameter(
                name='agent_id',
                type=int,
                location=OpenApiParameter.PATH,
                description='Номер ИИ-агента, с которым нужно взаимодействовать (от 1 до 4, 6 по порядку)',
                required=True,
                examples=[
                    OpenApiExample(
                        'Пример 1',
                        summary='Агент 1 для получения общих сведений о ТЗ',
                        value=1
                    ),
                    OpenApiExample(
                        'Пример 2',
                        summary='Агент 2 для уточнения цели и задачи проекта',
                        value=2
                    ),
                ],
            ),
        ],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'token': {
                        'type': 'string',
                        'description': 'Уникальный идентификатор чата. Необязателен для первого сообщения.',
                        'example': '550e8400-e29b-41d4-a716-446655440000'
                    },
                    'text': {
                        'type': 'string',
                        'description': 'Текст сообщения от пользователя для обработки ИИ-агентом.',
                        'example': 'Напиши ТЗ для сайта интернет-магазина'
                    }
                },
                'required': ['text']
            }
        },
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=ChatResponseSerializer,
                description='Успешный ответ с токеном и текстом от ИИ-агента',
                examples=[
                    OpenApiExample(
                        'Пример направляющего вопроса',
                        summary='ИИ задает уточняющий вопрос',
                        value={
                            'token': '550e8400-e29b-41d4-a716-446655440000',
                            'text': 'Какой функционал должен быть у интернет-магазина? Укажите ключевые требования.'
                        }
                    ),
                    OpenApiExample(
                        'Пример готового ТЗ',
                        summary='ИИ возвращает сгенерированное ТЗ',
                        value={
                            'token': '550e8400-e29b-41d4-a716-446655440000',
                            'text': 'ТЗ для интернет-магазина: 1. Каталог товаров с фильтрами; 2. Корзина; 3. Оформление заказа...'
                        }
                    )
                ]
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Ошибка ИИ-агента или запроса',
                examples=[
                    OpenApiExample(
                        name='Пример ошибки запроса',
                        value={
                            'error': 'The "text" field is required'
                        }
                    ),
                    OpenApiExample(
                        name='Пример ошибки ИИ-агента',
                        value={
                            'error': 'Agent error'
                        }
                    ),
                    OpenApiExample(
                        name='Пример несуществующего агента',
                        value={
                            'error': 'Agent with id 99 not found'
                        }
                    )
                ]
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Внутренняя ошибка сервера',
                examples=[
                    OpenApiExample(
                        name='Внутренняя ошибка сервера',
                        value={
                            'error': 'Отсутствует подключение к ИИ-агенту'
                        }
                    )
                ]
            )
        }
    )
    def post(self, request, agent_id):
        try:
            if agent_id not in {1, 2, 3, 4, 6}:
                return Response({'error': f'Agent with id {agent_id} not found. Available agents: 1, 2, 3, 4, 6'}, status=status.HTTP_400_BAD_REQUEST)

            token = request.data.get('token')
            text = request.data.get('text')

            if not text and agent_id != 6:
                return Response({'error': 'The \'text\' field is required'}, status=status.HTTP_400_BAD_REQUEST)

            if not token:
                token = str(uuid.uuid4())
            else:
                try:
                    uuid.UUID(token)
                except ValueError:
                    return Response({'error': 'Invalid token format'}, status=status.HTTP_400_BAD_REQUEST)

            last_response = ""
            if agent_id == 1:
                prev_response = AgentResponse.objects.filter(token=token, agent_id=agent_id).order_by('-created_at').first()
                if prev_response:
                    last_response = prev_response.response
            else:
                current_agent_response = AgentResponse.objects.filter(token=token, agent_id=agent_id).order_by('-created_at').first()

                if current_agent_response:
                    last_response = current_agent_response.response
                else:
                    prev_agent_response = AgentResponse.objects.filter(token=token, agent_id=agent_id - 1).order_by('-created_at').first()
                    if prev_agent_response:
                        last_response = prev_agent_response.response
            # ============================================== Вызов агента ==============================================
            response_agent = 'error'

            pipeline = TzPipeline(llm_callable=call_gigachat, embedding_model=self.local_embedding, llm=self.llm)

            if agent_id == 1:
                # Агент 1: Общее описание
                response_agent = pipeline.run_agent("description", last_response, text, self.access_token)
            elif agent_id == 2:
                # Агент 2: Цели проекта
                response_agent = pipeline.run_agent("goals", last_response, text, self.access_token)
            elif agent_id == 3:
                # Агент 3: Пользовательские группы
                response_agent = pipeline.run_agent("users", last_response, text, self.access_token)
            elif agent_id == 4:
                # Агент 4: Требования
                response_agent = pipeline.run_agent("requirements", last_response, text, self.access_token)

            elif agent_id == 6:
                all_responses = AgentResponse.objects.filter(
                    token=token,
                    agent_id__in=[1, 2, 3, 4]
                ).order_by('agent_id', '-created_at').distinct('agent_id')

                structured_response = "Собранное техническое задание:\n\n"

                for resp in all_responses:
                    if resp.agent_id == 1:
                        section = "1. Общее описание проекта:\n\n"
                    elif resp.agent_id == 2:
                        section = "2. Цели и задачи проекта:\n\n"
                    elif resp.agent_id == 3:
                        section = "3. Пользовательские группы:\n\n"
                    elif resp.agent_id == 4:
                        section = "4. Требования и функционал:\n\n"

                    structured_response += f"{section}{resp.response}\n\n"

                AgentResponse.objects.create(token=token, agent_id=agent_id, response=structured_response)

                return Response({'token': token, 'text': structured_response}, status=status.HTTP_200_OK)
            # ============================================== Вызов агента ==============================================

            if agent_id != 6:
                if response_agent.endswith("?"):
                    pass
                else:
                    AgentResponse.objects.create(token=token, agent_id=agent_id, response=response_agent)

            return Response({'token': token, 'text': response_agent}, status=status.HTTP_200_OK)

        except ValueError as ve:
            logger.warning(f'Agent error: {ve}')
            return Response({'error': 'Agent error'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f'Error contacting agent: {e}')
            return Response({'error': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
