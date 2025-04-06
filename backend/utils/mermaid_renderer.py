from PIL import Image as PILImage
import io, requests
import logging
import base64

logger = logging.getLogger(__name__)


class MermaidRenderError(Exception):
    """Custom exception for Mermaid rendering errors"""
    pass


def render_mermaid_to_png(mermaid_code: str) -> bytes:
    """Преобразует mermaid-код в изображение PNG и возвращает байты"""

    if not mermaid_code or not isinstance(mermaid_code, str):
        raise ValueError("Mermaid code must be a non-empty string")

    try:
        graph_bytes = mermaid_code.encode("utf8")
        base64_bytes = base64.urlsafe_b64encode(graph_bytes)
        base64_string = base64_bytes.decode("ascii")

        response = requests.get('https://mermaid.ink/img/' + base64_string)
        response.raise_for_status()

        img = PILImage.open(io.BytesIO(response.content))
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='PNG')

        return byte_arr.getvalue()

    except Exception as e:
        logger.exception("Failed to render Mermaid diagram")
        raise MermaidRenderError(f"Error rendering Mermaid diagram: {str(e)}")
