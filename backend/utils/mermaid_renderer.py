import requests
import logging

logger = logging.getLogger(__name__)


class MermaidRenderError(Exception):
    """Custom exception for Mermaid rendering errors"""
    pass


def render_mermaid_to_png(mermaid_code: str) -> bytes:
    if not mermaid_code or not isinstance(mermaid_code, str):
        raise ValueError("Mermaid code must be a non-empty string")

    try:
        response = requests.post(
            "https://kroki.io/mermaid/png",
            json={"diagram_source": mermaid_code},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        return response.content

    except requests.exceptions.RequestException as e:
        logger.error(f"Kroki API request failed: {str(e)}")
        raise MermaidRenderError(f"Kroki API request failed: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error during Mermaid rendering")
        raise MermaidRenderError(f"Error rendering Mermaid diagram: {str(e)}")
