from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging
import uuid

from chat.serializer import ErrorResponseSerializer, ChatResponseSerializer

logger = logging.getLogger(__name__)


class ChatMockAPIView(APIView):
    @extend_schema(
        summary='[MOCK] Тестовый эндпоинт для генерации ТЗ через чат с возможностью симуляции ошибок',
        description="""
            МОК-эндпоинт для тестирования. Имитирует работу чата с ИИ-агентом.
            Возвращает предопределенные ответы в зависимости от номера агента.
            Не выполняет реальных вызовов к ИИ-агенту, только эмулирует поведение.
            
            Mock-эндпоинт, возвращающий:
            - Фиксированные ответы в зависимости от <agent_id>
            - Ошибку 400 при ?error=validation
            - Ошибку 500 при ?error=server
            """,
        operation_id='mock_chat_generate_tz',
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
            OpenApiParameter(
                name='error',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Тип симулируемой ошибки (validation | server)',
                required=False,
                enum=['validation', 'server']
            )
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
                description='Успешный mock-ответ с токеном и текстом',
                examples=[
                    OpenApiExample(
                        'Агент 1 - Ответ',
                        value={
                            'token': '550e8400-e29b-41d4-a716-446655440000',
                            'text': '[MOCK Агент 1] На основе вашего запроса сгенерировано ТЗ: 1. Главная страница...'
                        }
                    )
                ]
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Mock ошибки',
                examples=[
                    OpenApiExample(
                        'Неверный агент',
                        value={'error': 'Agent with id 99 not found. Available agents: 1, 2, 3, 4'}
                    ),
                    OpenApiExample(
                        'Отсутствует текст',
                        value={'error': 'The \'text\' field is required'}
                    )
                ]
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Симуляция внутренней ошибки сервера',
                examples=[
                    OpenApiExample(
                        name='Внутренняя ошибка сервера',
                        value={'error': 'Internal Server Error'}
                    )
                ]
            )
        }
    )
    def post(self, request, agent_id):
        try:
            error_type = request.query_params.get('error')

            # Симуляция ошибок
            if error_type == 'validation':
                return Response({'error': '[MOCK] Ошибка валидации: неверный токен или текст'},
                                status=status.HTTP_400_BAD_REQUEST)
            elif error_type == 'server':
                return Response({'error': '[MOCK] Внутренняя ошибка сервера'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Проверка допустимых агентов
            if agent_id not in {1, 2, 3, 4}:
                return Response({'error': f'Agent with id {agent_id} not found. Available agents: 1, 2, 3, 4'},
                                status=status.HTTP_400_BAD_REQUEST)

            token = request.data.get('token', str(uuid.uuid4()))
            text = request.data.get('text')

            # Mock-ответы для каждого агента
            mock_responses = {
                1: f'[MOCK Агент 1] На основе вашего запроса "{text}" сгенерировано ТЗ: 1. Главная страница с каталогом товаров 2. Корзина с возможностью оформления 3. Личный кабинет пользователя',
                2: f'[MOCK Агент 2] Проанализированы требования: "{text}". Выявлены ключевые точки: UX, безопасность платежей, адаптивный дизайн',
                3: f'[MOCK Агент 3] Техническое решение для "{text}": Бэкенд - Django, фронтенд - React, БД - PostgreSQL, развертывание - Docker',
                4: f'[MOCK Агент 4] Креативные идеи для "{text}": 1. Геймификация процесса покупок 2. Виртуальная примерка товаров 3. Персонализированные рекомендации'
            }

            return Response({'token': token, 'text': mock_responses[agent_id]}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f'Mock error: {e}')
            return Response({'error': 'Mock Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
