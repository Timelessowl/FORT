from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging
import environ

from chat.models import AgentResponse
from utils.mermaid_renderer import render_mermaid_to_png, MermaidRenderError
from utils.dfd_generator import get_access_token, generate_mermaid_dfd_from_description
from mermaid.serializer import MermaidRequestSerializer, ErrorResponseSerializer
from utils.tz_critic_agent import TzPipeline, call_gigachat
from utils.sanitize_mermaid_code import sanitize_mermaid_code

logger = logging.getLogger(__name__)


class MermaidAPIView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        env = environ.Env()
        self.client_id = env('CLIENT_ID')
        self.client_secret = env('CLIENT_SECRET')

    @extend_schema(
        summary='Генерация или изменение Mermaid-диаграммы через ИИ-агента',
        description="""
            Этот эндпоинт позволяет пользователю получить изображение Mermaid-диаграммы в формате PNG, сгенерированное или измененное ИИ-агентом. 
            Пользователь отправляет обязательный токен (уникальный идентификатор чата). 
            - На основе токена ИИ-агент обновляет Mermaid-код и генерируется диаграмма.
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
                        description='ИИ-агент создал начальную диаграмму по токену и тексту',
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

            if not token:
                return Response({'error': 'The "token" field is required'}, status=status.HTTP_400_BAD_REQUEST)

            # ============================================== Вызов агента ==============================================
            access_token: str = get_access_token(self.client_id, self.client_secret)
            pipeline = TzPipeline(llm_callable=call_gigachat)

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

            # mermaid_code: str = generate_mermaid_dfd_from_description(text, access_token)
            mermaid_code = pipeline.generate_mermaid_diagram(structured_response, access_token)
            # ============================================== Вызов агента ==============================================

            clear_code: str = sanitize_mermaid_code(mermaid_code)
            png_bytes: bytes = render_mermaid_to_png(clear_code)

            return HttpResponse(png_bytes, status=status.HTTP_200_OK, content_type='image/png')

        except SystemExit as se:
            logger.warning(f'Agent error: {se}')
            return Response({'error': 'Agent error'}, status=status.HTTP_400_BAD_REQUEST)

        except MermaidRenderError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f'Error contacting agent: {e}')
            return Response({'error': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
