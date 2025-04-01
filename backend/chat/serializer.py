from rest_framework import serializers


class ChatResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    text = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()
