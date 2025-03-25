from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging

from utils.mermaid_renderer import render_mermaid_to_png, MermaidRenderError

logger = logging.getLogger(__name__)


class MermaidAPIView(APIView):
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
