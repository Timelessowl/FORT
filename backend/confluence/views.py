from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from atlassian import Confluence
import logging
import requests
import re
from django.conf import settings

from chat.models import AgentResponse

logger = logging.getLogger(__name__)


class ConfluenceApiView(APIView):

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
        try:
            token = request.data.get('token')
            if not token:
                return Response({'error': 'Missing required field: token'}, status=status.HTTP_400_BAD_REQUEST)
            self.CONFLUENCE_URL        = settings.CONFLUENCE_URL
            self.CONFLUENCE_USERNAME   = settings.CONFLUENCE_USERNAME
            self.CONFLUENCE_API_TOKEN  = settings.CONFLUENCE_API_TOKEN
            self.CONFLUENCE_SPACE_KEY  = settings.CONFLUENCE_SPACE_KEY
            confluence = self.get_confluence_client()
            if not confluence:
                return Response({'error': 'Confluence access configuration error'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if not self.check_confluence_permissions(confluence):
                return Response({'error': 'User has no permissions to create pages in Confluence'},
                                status=status.HTTP_403_FORBIDDEN)

            all_responses = AgentResponse.objects.filter(token=token, agent_id__in=[1, 2, 3, 4]).order_by('agent_id',
                                                                                                          '-created_at').distinct(
                'agent_id')

            if not all_responses.exists():
                return Response({'error': 'No technical specification found for this token'},
                                status=status.HTTP_404_NOT_FOUND)

            page_title = f"Техническое задание [token: {token}]"
            html_content = self.generate_confluence_html(all_responses)

            try:
                result = self.create_or_update_page(confluence, page_title, html_content)

                page_url = f"{self.CONFLUENCE_URL}{result['_links']['webui']}"

                return Response({'page_url': page_url, 'page_id': result['id']}, status=status.HTTP_200_OK)

            except requests.exceptions.HTTPError as http_err:
                logger.error(f"Confluence API error: {http_err}")
                return Response({'error': 'Failed to create/update Confluence page'},
                                status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            logger.exception(f'Error creating Confluence page: {e}')
            return Response({'error': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_confluence_client(self):
        """Создает и возвращает клиент Confluence с проверкой подключения"""
        try:
            confluence = Confluence(url=self.CONFLUENCE_URL, username=self.CONFLUENCE_USERNAME,
                                    password=self.CONFLUENCE_API_TOKEN, cloud=True)

            confluence.get_space(self.CONFLUENCE_SPACE_KEY)
            return confluence
        except Exception as e:
            logger.error(f"Confluence connection error: {e}")
            return None

    def check_confluence_permissions(self, confluence):
        """Проверяет, есть ли у пользователя права на создание страниц"""
        try:
            space = confluence.get_space(self.CONFLUENCE_SPACE_KEY)
            if not space:
                return False

            return True
        except Exception as e:
            logger.error(f"Permission check error: {e}")
            return False

    def create_or_update_page(self, confluence, title, content, parent_id=None):
        """Создает или обновляет страницу в Confluence"""
        existing_page = confluence.get_page_by_title(space=self.CONFLUENCE_SPACE_KEY, title=title)

        if existing_page:
            return confluence.update_page(page_id=existing_page['id'], title=title, body=content, parent_id=parent_id,
                                          type='page', representation='storage')
        else:
            return confluence.create_page(space=self.CONFLUENCE_SPACE_KEY, title=title, body=content,
                                          parent_id=parent_id, type='page', representation='storage')

    def generate_confluence_html(self, responses):
        """Генерирует HTML контент для Confluence с поддержкой Markdown."""
        html_content = """
        <h1>Техническое задание</h1>
        <p><em>Этот документ был автоматически сгенерирован системой.</em></p>
        """

        sections = {
            1: "1. Общее описание проекта",
            2: "2. Цели и задачи проекта",
            3: "3. Пользовательские группы",
            4: "4. Требования и функционал"
        }

        for resp in responses:
            if resp.agent_id not in sections:
                continue

            response_html = self._process_markdown(resp.response)

            html_content += f"""
            <h2>{sections[resp.agent_id]}</h2>
            <div class="rich-text-section">
                {response_html}
            </div>
            """

        return html_content

    def _process_markdown(self, text):
        """Обрабатывает Markdown в тексте и преобразует в HTML."""
        # Замена **текст** на <strong>текст</strong>
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

        # Замена --- на <hr>
        text = re.sub(r'^---\s*$', '<hr>', text, flags=re.MULTILINE)

        # Обработка заголовков (### Текст → <h1>–<h6>)
        def replace_heading(match):
            level = len(match.group(1))  # Количество решеток (1–6)
            text = match.group(2).strip()
            if 1 <= level <= 6:
                return f'<h{level}>{text}</h{level}>'
            return match.group(0)

        text = re.sub(r'^(#{1,6})\s+(.+)$', replace_heading, text, flags=re.MULTILINE)

        # Замена переносов строк на HTML
        # Двойной перенос (\n\n) → новый параграф
        paragraphs = text.split('\n\n')
        response_html = ''
        for paragraph in paragraphs:
            if paragraph.strip():
                # Если строка уже является <hr> или <h1>–<h6>, не оборачиваем в <p>
                if paragraph.startswith('<hr>') or re.match(r'^<h[1-6]>.+</h[1-6]>$', paragraph):
                    response_html += paragraph
                else:
                    # Одинарный перенос (\n) → <br>
                    paragraph = paragraph.replace('\n', '<br>')
                    response_html += f'<p>{paragraph}</p>'
            else:
                response_html += '<p></p>'

        return response_html
