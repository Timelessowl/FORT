from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging
import uuid

from chat.serializer import ChatResponseSerializer, ErrorResponseSerializer

logger = logging.getLogger(__name__)


class ChatAPIView(APIView):
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
                description='Номер ИИ-агента, с которым нужно взаимодействовать (от 1 до 4, по порядку)',
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
            if agent_id not in {1, 2, 3, 4}:
                return Response({'error': f'Agent with id {agent_id} not found. Available agents: 1, 2, 3, 4'},
                                status=status.HTTP_400_BAD_REQUEST)

            token = request.data.get('token')
            text = request.data.get('text')

            if not text:
                return Response({'error': 'The \'text\' field is required'}, status=status.HTTP_400_BAD_REQUEST)

            if not token:
                token = str(uuid.uuid4())

            # ============================================== Вызов агента ==============================================
            response_agent = 'error'

            # Заглушки для разных агентов
            if agent_id == 1:
                # Агент для получения общих сведений о проекте
                response_agent = f"[Агент для получения общих сведений о проекте] Получено сообщение: {text}. Токен: {token}"
            elif agent_id == 2:
                # Агент для уточнения цели и задачи проекта
                response_agent = f"[Агент для уточнения цели и задачи проекта] Анализирую требования: {text}. Токен: {token}"
            elif agent_id == 3:
                # Агент для выделения пользовательских групп
                response_agent = f"[Агент для выделения пользовательских групп] Технический ответ на: {text}. Токен: {token}"
            elif agent_id == 4:
                # Агент для формирования основных требований к проекту
                response_agent = f"[Агент для формирования основных требований к проекту] Генерирую идеи по запросу: {text}. Токен: {token}"
            # ============================================== Вызов агента ==============================================

            return Response({'token': token, 'text': response_agent}, status=status.HTTP_200_OK)

        except ValueError as ve:
            logger.warning(f'Agent error: {ve}')
            return Response({'error': 'Agent error'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f'Error contacting agent: {e}')
            return Response({'error': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
