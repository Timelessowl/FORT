from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_gigachat.chat_models import GigaChat
import logging
import environ
import base64
import os

from mermaid.models import MermaidImage
from chat.models import AgentResponse
from utils.dfd_generator import get_access_token, generate_mermaid_dfd_from_description
from utils.mermaid_renderer import render_mermaid_to_png, MermaidRenderError
from mermaid.serializer import MermaidRequestSerializer, ErrorResponseSerializer
from utils.sanitize_mermaid_code_2 import sanitize_mermaid_code_2
from utils.sanitize_mermaid_code import sanitize_mermaid_code
from utils.tz_critic_agent2 import TzPipeline, call_gigachat

logger = logging.getLogger(__name__)


class MermaidAPIView(APIView):
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
        model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        model_kwargs = {"device": "cpu"}
        encode_kwargs = {"normalize_embeddings": False}
        self.local_embedding = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )

    def _render_diagram(self, title: str, code: str) -> tuple[str | None, bool]:
        """Attempt to render a diagram with retries on sanitized code."""
        for render_func in [lambda c: c, sanitize_mermaid_code_2, sanitize_mermaid_code]:
            try:
                clear_code = render_func(code)
                if clear_code:
                    png_bytes = render_mermaid_to_png(clear_code)
                    return base64.b64encode(png_bytes).decode(), True
            except Exception as e:
                logger.debug(f"Render attempt failed for {title}: {e}")
        logger.exception(f'Error rendering diagram {title}')
        return None, False

    @extend_schema(
        summary='Генерация или изменение набора Mermaid-диаграмм через ИИ-агента',
        description="""
            Этот эндпоинт позволяет пользователю получить массив изображений Mermaid-диаграмм в формате PNG, 
            сгенерированных или измененных ИИ-агентом. Пользователь отправляет обязательный токен 
            (уникальный идентификатор чата) и массив названий диаграмм. На основе токена и названий 
            ИИ-агент генерирует или обновляет Mermaid-код для каждой диаграммы. Сервер рендерит 
            полученные коды в изображения PNG и возвращает их массив в теле ответа в формате JSON.
            """,
        operation_id='generate_or_update_mermaid_diagrams',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'token': {
                        'type': 'string',
                        'description': 'Уникальный идентификатор чата',
                        'example': '550e8400-e29b-41d4-a716-446655440000'
                    },
                    'texts': {
                        'type': 'array',
                        'items': {
                            'type': 'string'
                        },
                        'description': 'Массив названий диаграмм для генерации',
                        'example': ['Main Flow', 'User Authentication', 'Data Processing']
                    }
                },
                'required': ['token', 'texts']
            }
        },
        responses={
            (status.HTTP_200_OK, 'application/json'): OpenApiResponse(
                description='Успешный ответ с массивом изображений Mermaid-диаграмм в формате PNG',
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
                        summary='Генерация нескольких диаграмм',
                        description='ИИ-агент создал набор диаграмм по токену, тексту и названиям',
                        value=['[Binary PNG data]', '[Binary PNG data]']
                    ),
                    OpenApiExample(
                        'Пример обновленных диаграмм',
                        summary='Обновление набора диаграмм',
                        description='ИИ-агент обновил набор диаграмм на основе текста и названий',
                        value=['[Binary PNG data]', '[Binary PNG data]']
                    )
                ]
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=ErrorResponseSerializer,
                description='Ошибка в запросе или обработке',
                examples=[
                    OpenApiExample(
                        name='Отсутствует токен или названия',
                        value={'error': 'The "token" and "diagram_names" fields are required'}
                    ),
                    OpenApiExample(
                        name='Ошибка рендеринга',
                        value={'error': 'Invalid Mermaid syntax in one or more diagrams'}
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
            payload = request.data
            texts = payload.get("texts") or ([payload.get("text")] if payload.get("text") else [])

            if not isinstance(texts, list):
                return JsonResponse({"error": "`texts` must be an array of strings"},
                                    status=status.HTTP_400_BAD_REQUEST)

            if not token:
                return Response({'error': 'The "token" fields are required'}, status=status.HTTP_400_BAD_REQUEST)

            # Initialize pipeline
            pipeline = TzPipeline(llm_callable=call_gigachat, embedding_model=self.local_embedding, llm=self.llm)

            # Gather responses for structured input
            all_responses = AgentResponse.objects.filter(token=token, agent_id__in=[1, 2, 3, 4]).order_by('agent_id',
                                                                                                          '-created_at').distinct(
                'agent_id')

            structured_response = "Собранное техническое задание:\n\n"
            for resp in all_responses:
                section = {
                    1: "1. Общее описание проекта:\n\n",
                    2: "2. Цели и задачи проекта:\n\n",
                    3: "3. Пользовательские группы:\n\n",
                    4: "4. Требования и функционал:\n\n"
                }[resp.agent_id]
                structured_response += f"{section}{resp.response}\n\n"

            # Initial diagram generation
            all_diags = pipeline.generate_all_diagrams(structured_response, self.access_token, texts)
            diagrams_dict = {}
            failed_diagrams = []

            # First pass: Try rendering all diagrams
            for title, code in all_diags.items():
                b64_image, success = self._render_diagram(title, code)
                if success:
                    diagrams_dict[title] = b64_image
                else:
                    failed_diagrams.append(title)

            # Retry failed diagrams up to 3 times
            retry_count = 3
            while failed_diagrams and retry_count > 0:
                logger.info(f'Retry attempt {4 - retry_count} for failed diagrams: {failed_diagrams}')
                retry_count -= 1
                try:
                    all_diags = pipeline.generate_all_diagrams(structured_response, self.access_token, failed_diagrams)
                except Exception as e:
                    logger.exception(f'Error regenerating diagrams: {e}')
                    break

                new_failed_diagrams = []
                for title in failed_diagrams:
                    code = all_diags.get(title)
                    if not code:
                        logger.warning(f'Diagram {title} not found in regenerated diagrams')
                        new_failed_diagrams.append(title)
                        continue

                    b64_image, success = self._render_diagram(title, code)
                    if success:
                        diagrams_dict[title] = b64_image
                    else:
                        new_failed_diagrams.append(title)

                failed_diagrams = new_failed_diagrams

            # Convert diagrams_dict to images_b64 list for response
            images_b64 = list(diagrams_dict.values())

            # Save or update MermaidImage object
            MermaidImage.objects.update_or_create(token=token, defaults={'images_b64': diagrams_dict})

            return JsonResponse({"images": images_b64}, status=status.HTTP_200_OK)

        except SystemExit as se:
            logger.warning(f'Agent error: {se}')
            return Response({'error': 'Agent error'}, status=status.HTTP_400_BAD_REQUEST)

        except MermaidRenderError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f'Error processing request: {e}')
            return Response({'error': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
