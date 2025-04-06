from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging

from utils.mermaid_renderer import render_mermaid_to_png, MermaidRenderError
from mermaid.serializer import MermaidRequestSerializer, ErrorResponseSerializer

logger = logging.getLogger(__name__)


class MermaidMockAPIView(APIView):
    @extend_schema(
        summary='[MOCK] Тестовый эндпоинт для Mermaid-диаграммы с возможностью симуляции ошибок',
        description="""
            Mock-эндпоинт, возвращающий фиксированное изображение Mermaid-диаграммы
            без вызова ИИ-агента и сложных вычислений. Используется для тестирования фронтенда.
            
            Mock-эндпоинт, возвращающий:
            - Фиксированное изображение диаграммы (по умолчанию)
            - Ошибку 400 при ?error=validation
            - Ошибку 500 при ?error=server
            - Ошибку рендеринга при ?error=render
            """,
        parameters=[
            OpenApiParameter(
                name='error',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Тип симулируемой ошибки (validation | server | render)',
                required=False,
                enum=['validation', 'server', 'render']
            )
        ],
        operation_id='generate_or_update_mermaid_diagram',
        responses={
            (status.HTTP_200_OK, 'image/png'): OpenApiResponse(
                description='Успешный ответ с фиксированным тестовым изображением',
                response={
                    'type': 'string',
                    'format': 'binary'
                }
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Симуляция ошибки валидации или рендеринга',
                examples=[
                    OpenApiExample(
                        name='Симуляция ошибки валидации',
                        value={'error': 'The "token" field is required'}
                    ),
                    OpenApiExample(
                        name='Симуляция ошибки рендеринга',
                        value={'error': 'Invalid Mermaid syntax'}
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
    def post(self, request):
        try:
            error_type = request.query_params.get('error')

            # Симуляция ошибок
            if error_type == 'validation':
                return Response({'error': '[MOCK] Ошибка валидации: неверный токен или текст'},
                                status=status.HTTP_400_BAD_REQUEST)
            elif error_type == 'server':
                return Response({'error': '[MOCK] Внутренняя ошибка сервера'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif error_type == 'render':
                return Response({'error': '[MOCK] Ошибка рендеринга Mermaid'}, status=status.HTTP_400_BAD_REQUEST)

            # Стандартный ответ с фиксированной диаграммой
            mock_mermaid = """
                graph TD
                    A[Пользователь] -->|Загружает| B(Сервер)
                    B --> C{Обработка}
                    C -->|Успех| D[База данных]
                    C -->|Ошибка| E[Логи]
                """

            png_bytes: bytes = render_mermaid_to_png(mock_mermaid)

            return HttpResponse(png_bytes, status=status.HTTP_200_OK, content_type='image/png')

        except SystemExit as se:
            logger.warning(f'Agent error: {se}')
            return Response({'error': 'Agent error'}, status=status.HTTP_400_BAD_REQUEST)

        except MermaidRenderError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f'Error contacting agent: {e}')
            return Response({'error': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
