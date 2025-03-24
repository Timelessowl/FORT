from langchain_core.runnables.graph import MermaidDrawMethod
from langchain_core.runnables.graph_mermaid import draw_mermaid_png
import logging

logger = logging.getLogger(__name__)


class MermaidRenderError(Exception):
    """Custom exception for Mermaid rendering errors"""
    pass


def render_mermaid_to_png(mermaid_code: str, background_color: str = 'white') -> bytes:
    """Преобразует mermaid-код в изображение PNG и возвращает байты"""

    if not mermaid_code or not isinstance(mermaid_code, str):
        raise ValueError("Mermaid code must be a non-empty string")

    try:
        png_bytes: bytes = draw_mermaid_png(mermaid_code, draw_method=MermaidDrawMethod.API,
                                            background_color=background_color)
        return png_bytes
    except Exception as e:
        logger.exception("Failed to render Mermaid diagram")
        raise MermaidRenderError(f"Error rendering Mermaid diagram: {str(e)}")
