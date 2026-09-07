"""Provider interface — the swap-in-one-flag layer.

We lean on Strands' own model abstraction rather than reinventing it: this factory
returns a configured Strands model based on MODEL_PROVIDER. Dev on Ollama for free,
ship on Bedrock, without touching the agent loop.
"""
import os


def get_model():
    provider = os.environ.get("MODEL_PROVIDER", "bedrock").lower()

    if provider == "bedrock":
        from strands.models import BedrockModel
        return BedrockModel(
            model_id=os.environ.get("AGENT_MODEL", "global.anthropic.claude-haiku-4-5"),
            region_name=os.environ.get("AWS_REGION", "ap-southeast-2"),
        )

    if provider == "ollama":
        from strands.models.ollama import OllamaModel
        return OllamaModel(
            host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            model_id=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        )

    if provider == "openai":
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"api_key": os.environ.get("OPENAI_API_KEY")},
            model_id=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        )

    raise ValueError(f"Unknown MODEL_PROVIDER: {provider!r} (use bedrock|ollama|openai)")
