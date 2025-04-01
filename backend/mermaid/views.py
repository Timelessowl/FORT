from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging

from utils.mermaid_renderer import render_mermaid_to_png, MermaidRenderError
from mermaid.serializer import MermaidRequestSerializer, ErrorResponseSerializer

logger = logging.getLogger(__name__)


class MermaidAPIView(APIView):
    @extend_schema(
        summary='Генерация или изменение Mermaid-диаграммы через ИИ-агента',
        description="""
            Этот эндпоинт позволяет пользователю получить изображение Mermaid-диаграммы в формате PNG, сгенерированное или измененное ИИ-агентом. 
            Пользователь отправляет обязательный токен (уникальный идентификатор чата) и необязательный текст. 
            - Если текст не передан (например, первое обращение), ИИ-агент генерирует начальный Mermaid-код на основе предыдущего контекста, связанного с токеном.
            - Если текст передан, он интерпретируется как инструкция для изменения существующей диаграммы, и ИИ-агент обновляет Mermaid-код.
            Сервер рендерит полученный Mermaid-код в изображение PNG и возвращает его клиенту в теле ответа.
            """,
        operation_id='generate_or_update_mermaid_diagram',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'token': {
                        'type': 'string',
                        'description': 'Уникальный идентификатор чата',
                        'example': '550e8400-e29b-41d4-a716-446655440000'
                    },
                    'text': {
                        'type': 'string',
                        'description': 'Что изменить в текущей диаграмме',
                        'example': 'Добавь дополнительный блок'
                    }
                },
                'required': ['token']
            }
        },
        responses={
            (status.HTTP_200_OK, 'image/png'): OpenApiResponse(
                description='Успешный ответ с изображением Mermaid-диаграммы',
                response={
                    'type': 'string',
                    'format': 'binary'
                },
                examples=[
                    OpenApiExample(
                        name='Пример начальной диаграммы',
                        summary='Генерация новой диаграммы',
                        description='ИИ-агент создал начальную диаграмму по токену без текста',
                        value='[Binary PNG data]'
                    ),
                    OpenApiExample(
                        'Пример измененной диаграммы',
                        summary='Обновление диаграммы по тексту',
                        description='ИИ-агент обновил диаграмму на основе текста',
                        value='[Binary PNG data]'
                    )
                ]
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Ошибка в запросе или обработке',
                examples=[
                    OpenApiExample(
                        name='Отсутствует токен',
                        value={'error': 'The "token" field is required'}
                    ),
                    OpenApiExample(
                        name='Ошибка рендеринга',
                        value={'error': 'Invalid Mermaid syntax'}
                    )
                ]
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Внутренняя ошибка сервера',
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
            token = request.data.get('token')
            text = request.data.get('text')

            if not token:
                return Response({'error': 'The "token" field is required'}, status=status.HTTP_400_BAD_REQUEST)

            # ============================================== Вызов агента ==============================================
            mermaid_code: str = f'await call_agent({token}, {text})'
            # ============================================== Вызов агента ==============================================

            png_bytes: bytes = render_mermaid_to_png(mermaid_code)

            return HttpResponse(png_bytes, status=status.HTTP_200_OK, content_type='image/png')

        except ValueError as ve:
            logger.warning(f'Agent error: {ve}')
            return Response({'error': 'Agent error'}, status=status.HTTP_400_BAD_REQUEST)

        except MermaidRenderError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f'Error contacting agent: {e}')
            return Response({'error': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
