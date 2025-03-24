from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging
import uuid

logger = logging.getLogger(__name__)


class ChatAPIView(APIView):
    def post(self, request):
        try:
            token = request.data.get('token')
            text = request.data.get('text')

            if not text:
                return Response({'error': 'The "text" field is required'}, status=status.HTTP_400_BAD_REQUEST)

            if not token:
                token = str(uuid.uuid4())

            # ============================================== Вызов агента ==============================================
            response_agent = f'call_agent({token}, {text})'
            # ============================================== Вызов агента ==============================================

            return Response({'token': token, 'text': response_agent}, status=status.HTTP_200_OK)

        except ValueError as ve:
            logger.warning(f'Agent error: {ve}')
            return Response({'error': 'Agent error'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f'Error contacting agent: {e}')
            return Response({'error': 'Internal Server Error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
