from django.db import models


class MermaidImage(models.Model):
    token = models.UUIDField(verbose_name="Идентификатор чата", db_index=True)
    images_b64 = models.JSONField(verbose_name="Схемы")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата Обновления")

    class Meta:
        app_label = 'mermaid'

    def __str__(self):
        return f"MermaidImage for token {self.token}"
