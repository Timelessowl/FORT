from rest_framework import serializers


class MermaidRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    text = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()
