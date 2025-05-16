from django.http import HttpResponse
import os
from django.conf import settings
from django.http import JsonResponse
import base64
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
        summary='[MOCK] Тестовый эндпоинт для набора Mermaid-диаграмм с возможностью симуляции ошибок',
        description="""
                Mock-эндпоинт, возвращающий массив фиксированных изображений Mermaid-диаграмм в формате PNG
                без вызова ИИ-агента и сложных вычислений. Используется для тестирования фронтенда.

                Mock-эндпоинт принимает массив названий диаграмм и возвращает:
                - Массив фиксированных изображений диаграмм (по умолчанию)
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
        operation_id='generate_or_update_mermaid_diagrams_mock',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'token': {
                        'type': 'string',
                        'description': 'Уникальный идентификатор чата (игнорируется в mock)',
                        'example': '550e8400-e29b-41d4-a716-446655440000'
                    },
                    'diagram_names': {
                        'type': 'array',
                        'items': {
                            'type': 'string'
                        },
                        'description': 'Массив названий диаграмм для генерации',
                        'example': ['Main Flow', 'User Authentication', 'Data Processing']
                    }
                },
                'required': ['diagram_names']
            }
        },
        responses={
            (status.HTTP_200_OK, 'application/json'): OpenApiResponse(
                description='Успешный ответ с массивом фиксированных тестовых изображений',
                response={
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'format': 'binary'
                    }
                },
                examples=[
                    OpenApiExample(
                        name='Пример набора диаграмм',
                        summary='Генерация нескольких тестовых диаграмм',
                        description='Mock-эндпоинт создал набор фиксированных диаграмм',
                        value=['[Binary PNG data]', '[Binary PNG data]']
                    )
                ]
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Симуляция ошибки валидации или рендеринга',
                examples=[
                    OpenApiExample(
                        name='Симуляция ошибки валидации',
                        value={'error': '[MOCK] Ошибка валидации: отсутствует или неверный массив названий'}
                    ),
                    OpenApiExample(
                        name='Симуляция ошибки рендеринга',
                        value={'error': '[MOCK] Ошибка рендеринга Mermaid'}
                    )
                ]
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Симуляция внутренней ошибки сервера',
                examples=[
                    OpenApiExample(
                        name='Внутренняя ошибка сервера',
                        value={'error': '[MOCK] Внутренняя ошибка сервера'}
                    )
                ]
            )
        }
    )
    def post(self, request):
        try:
            error_type = request.query_params.get('error')
            diagram_names = request.data.get('diagram_names')

            # Симуляция ошибок
            if error_type == 'validation':
                return Response({'error': '[MOCK] Ошибка валидации: отсутствует или неверный массив названий'},
                                status=status.HTTP_400_BAD_REQUEST)
            elif error_type == 'server':
                return Response({'error': '[MOCK] Внутренняя ошибка сервера'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif error_type == 'render':
                return Response({'error': '[MOCK] Ошибка рендеринга Mermaid'}, status=status.HTTP_400_BAD_REQUEST)

            # Стандартный ответ с фиксированной диаграммой
            # mock_mermaid = """
            #     graph TD
            #         A[Пользователь] -->|Загружает| B(Сервер)
            #         B --> C{Обработка}
            #         C -->|Успех| D[База данных]
            #         C -->|Ошибка| E[Логи]
            #     """
            #
            # png_bytes: bytes = render_mermaid_to_png(mock_mermaid)
            #
            # return HttpResponse(png_bytes, status=status.HTTP_200_OK, content_type='image/png')
            payload = request.data
            texts = payload.get("texts") or ([payload.get("text")] if payload.get("text") else [])
            if not isinstance(texts, list):
                return JsonResponse({"error": "`texts` must be an array of strings"},
                                    status=status.HTTP_400_BAD_REQUEST)

            images_b64: list[str] = []
            file_path = os.path.join(settings.BASE_DIR, 'test.png')
            with open(file_path, 'rb') as f:
                data = f.read()

            for _ in texts:
                images_b64.append(base64.b64encode(data).decode())

            return JsonResponse({"images": images_b64}, status=status.HTTP_200_OK)
            # return HttpResponse(data, status=status.HTTP_200_OK, content_type='image/png')
        except SystemExit as se:
            logger.warning(f'Agent error: {se}')
            return Response({'error': 'Agent error'}, status=status.HTTP_400_BAD_REQUEST)

        except MermaidRenderError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f'Error contacting agent: {e}')
            return Response({'error': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
