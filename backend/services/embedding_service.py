from openai import OpenAI
from config import settings


class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL

    def embed(self, text: str) -> list:
        response = self.client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list) -> list:
        response = self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [d.embedding for d in response.data]
