from django.db import models
import uuid


class AgentResponse(models.Model):
    token = models.UUIDField(verbose_name="Идентификатор чата")
    agent_id = models.IntegerField(verbose_name="ID агента")
    response = models.TextField(verbose_name="Ответ агента")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['token', 'agent_id']),
        ]

    def __str__(self):
        return f"Response for token {self.token} from agent {self.agent_id}"
