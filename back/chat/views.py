from django.forms.models import model_to_dict
from rest_framework.response import Response
from rest_framework.views import APIView

from back.chat.models import Chat


# Create your views here.
class ChatAPIView(APIView):
    def get(self, request):
        return Response(Chat.objects.all().values())

    def post(self, request):
        new_chat = Chat.objects.create(title=request.POST['title'])
        return Response({'chat': model_to_dict(new_chat)})
