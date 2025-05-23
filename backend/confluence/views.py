from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from markdown import markdown
from atlassian import Confluence
import logging
import requests

from chat.models import AgentResponse
from mermaid.models import MermaidImage

logger = logging.getLogger(__name__)


class ConfluenceApiView(APIView):
    # Constants
    ERROR_MISSING_TOKEN = {'error': 'Missing required field: token'}
    ERROR_CONFLUENCE_CONFIG = {'error': 'Confluence access configuration error'}
    ERROR_NO_PERMISSIONS = {'error': 'User has no permissions to create pages in Confluence'}
    ERROR_PAGE_CREATION = {'error': 'Failed to create/update Confluence page'}
    ERROR_SERVER = {'error': 'Internal Server Error'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.confluence_url = settings.CONFLUENCE_URL
        self.confluence_username = settings.CONFLUENCE_USERNAME
        self.confluence_api_token = settings.CONFLUENCE_API_TOKEN
        self.confluence_space_key = settings.CONFLUENCE_SPACE_KEY

    def _get_confluence_client(self) -> Confluence | None:
        """Initialize and validate Confluence client."""
        try:
            client = Confluence(
                url=self.confluence_url,
                username=self.confluence_username,
                password=self.confluence_api_token,
                cloud=True
            )
            # Validate space access
            if not client.get_space(self.confluence_space_key):
                logger.error(f"Space {self.confluence_space_key} not found")
                return None
            return client
        except Exception as e:
            logger.error(f"Confluence connection error: {e}")
            return None

    def _create_or_update_page(self, confluence: Confluence, title: str, content: str, parent_id: str = None) -> dict:
        """Create or update a Confluence page."""
        existing_page = confluence.get_page_by_title(space=self.confluence_space_key, title=title)
        if existing_page:
            return confluence.update_page(
                page_id=existing_page['id'],
                title=title,
                body=content,
                parent_id=parent_id,
                type='page',
                representation='storage'
            )
        return confluence.create_page(
            space=self.confluence_space_key,
            title=title,
            body=content,
            parent_id=parent_id,
            type='page',
            representation='storage'
        )

    def _generate_confluence_html(self, responses, token: str) -> str:
        """Generate HTML content for Confluence with responses and diagrams."""
        sections = {
            1: "1. Общее описание проекта",
            2: "2. Цели и задачи проекта",
            3: "3. Пользовательские группы",
            4: "4. Требования и функционал"
        }
        html_content = """
            <h1>Техническое задание</h1>
            <p><em>Этот документ был автоматически сгенерирован системой.</em></p>
            """

        # Add response sections
        for resp in responses:
            if resp.agent_id in sections:
                html_content += f"""
                    <h2>{sections[resp.agent_id]}</h2>
                    <div class="rich-text-section">{markdown(resp.response)}</div>
                    """

        # Add diagram section
        try:
            mermaid_image = MermaidImage.objects.get(token=token)
            images_b64 = mermaid_image.images_b64 or {}
            if images_b64:
                html_content += '<h2>Mermaid Диаграммы</h2>'
                for title, b64_image in images_b64.items():
                    html_content += f"""
                        <h3>{title}</h3>
                        <img src="data:image/png;base64,{b64_image}" alt="{title}" style="max-width: 100%;">
                        """
            else:
                logger.info(f"No diagrams found for token {token}")
        except MermaidImage.DoesNotExist:
            logger.info(f"No MermaidImage found for token {token}")

        return html_content

    @extend_schema(
        summary='Создание страницы ТЗ в Confluence',
        description="""
        Этот эндпоинт позволяет создать или обновить страницу в Confluence с техническим заданием (ТЗ), 
        сгенерированным на основе ответов ИИ-агентов. Пользователь должен предоставить параметры подключения 
        к Confluence (URL, email, API-токен, ключ пространства) и токен чата, связанный с ответами агентов. 
        Страница создается с автоматически сгенерированным HTML-контентом, поддерживающим форматирование Markdown.
        """,
        operation_id='create_confluence_page',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'confluence_url': {
                        'type': 'string',
                        'description': 'Базовый URL экземпляра Confluence.',
                        'example': 'https://your-domain.atlassian.net/wiki'
                    },
                    'confluence_username': {
                        'type': 'string',
                        'description': 'Email пользователя для аутентификации в Confluence Cloud.',
                        'example': 'user@example.com'
                    },
                    'confluence_api_token': {
                        'type': 'string',
                        'description': 'API-токен для доступа к Confluence.',
                        'example': 'your-api-token'
                    },
                    'confluence_space_key': {
                        'type': 'string',
                        'description': 'Ключ пространства в Confluence, где будет создана страница.',
                        'example': 'DEMO'
                    },
                    'token': {
                        'type': 'string',
                        'description': 'Уникальный идентификатор чата, связанный с ответами ИИ-агентов.',
                        'example': '550e8400-e29b-41d4-a716-446655440000'
                    }
                },
                'required': ['confluence_url', 'confluence_username', 'confluence_api_token', 'confluence_space_key',
                             'token']
            }
        },
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response={
                    'type': 'object',
                    'properties': {
                        'page_url': {'type': 'string', 'description': 'URL созданной или обновленной страницы.'},
                        'page_id': {'type': 'string', 'description': 'ID страницы в Confluence.'}
                    }
                },
                description='Страница успешно создана или обновлена в Confluence.',
                examples=[
                    OpenApiExample(
                        'Успешное создание страницы',
                        summary='Страница создана',
                        value={
                            'page_url': "https://your-domain.atlassian.net/wiki/spaces/test1/pages/1671171/token+d1b0cc23-2e9f-4d1e-97b0-6e64e97926a3",
                            'page_id': '1671171'
                        }
                    )
                ]
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response={
                    'type': 'object',
                    'properties': {
                        'error': {'type': 'string', 'description': 'Описание ошибки.'}
                    }
                },
                description='Ошибка в запросе из-за отсутствия обязательных полей.',
                examples=[
                    OpenApiExample(
                        'Отсутствуют обязательные поля',
                        value={'error': 'Missing required fields: confluence_url, confluence_api_token'}
                    )
                ]
            ),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                response={
                    'type': 'object',
                    'properties': {
                        'error': {'type': 'string', 'description': 'Описание ошибки.'}
                    }
                },
                description='У пользователя нет прав на создание страниц в указанном пространстве.',
                examples=[
                    OpenApiExample(
                        'Отсутствие прав',
                        value={'error': 'User has no permissions to create pages in Confluence'}
                    )
                ]
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                response={
                    'type': 'object',
                    'properties': {
                        'error': {'type': 'string', 'description': 'Описание ошибки.'}
                    }
                },
                description='Ответы ИИ-агентов для указанного токена не найдены.',
                examples=[
                    OpenApiExample(
                        'ТЗ не найдено',
                        value={'error': 'No technical specification found for this token'}
                    )
                ]
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiResponse(
                response={
                    'type': 'object',
                    'properties': {
                        'error': {'type': 'string', 'description': 'Описание ошибки.'}
                    }
                },
                description='Внутренняя ошибка сервера.',
                examples=[
                    OpenApiExample(
                        'Внутренняя ошибка',
                        value={'error': 'Internal Server Error'}
                    )
                ]
            ),
            status.HTTP_502_BAD_GATEWAY: OpenApiResponse(
                response={
                    'type': 'object',
                    'properties': {
                        'error': {'type': 'string', 'description': 'Описание ошибки.'}
                    }
                },
                description='Ошибка API Confluence при создании или обновлении страницы.',
                examples=[
                    OpenApiExample(
                        'Ошибка API Confluence',
                        value={'error': 'Failed to create/update Confluence page'}
                    )
                ]
            )
        }
    )
    def post(self, request):
        # Validate token
        token = request.data.get('token')
        if not token:
            return Response(self.ERROR_MISSING_TOKEN, status=status.HTTP_400_BAD_REQUEST)

        # Initialize Confluence client
        confluence = self._get_confluence_client()
        if not confluence:
            return Response(self.ERROR_CONFLUENCE_CONFIG, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Fetch agent responses
        responses = AgentResponse.objects.filter(token=token, agent_id__in=[1, 2, 3, 4]).order_by('agent_id', '-created_at').distinct('agent_id')

        # Generate HTML content with diagrams
        try:
            html_content = self._generate_confluence_html(responses, token)
        except Exception as e:
            logger.exception(f"Error generating HTML content: {e}")
            return Response(self.ERROR_SERVER, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create or update Confluence page
        try:
            page_title = f"Техническое задание [token: {token}]"
            result = self._create_or_update_page(confluence, page_title, html_content)
            page_url = f"{self.confluence_url}{result['_links']['webui']}"

            page_id = result['id']
            rendered = confluence.get_page_by_id(page_id, expand="body.view")
            html_view = rendered["body"]["view"]["value"]

            return Response({'page_url': page_url, 'page_id': page_id, 'html': html_view}, status=status.HTTP_200_OK)
        except requests.exceptions.HTTPError as e:
            logger.error(f"Confluence API error: {e}")
            return Response(self.ERROR_PAGE_CREATION, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            logger.exception(f"Error creating Confluence page: {e}")
            return Response(self.ERROR_SERVER, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
