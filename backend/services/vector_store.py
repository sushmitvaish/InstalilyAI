import chromadb
from config import settings


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def search(self, query_embedding: list, n_results: int = 5,
               where: dict = None) -> dict:
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"]
        }
        if where:
            kwargs["where"] = where

        return self.collection.query(**kwargs)

    def add_documents(self, ids: list, documents: list,
                      embeddings: list, metadatas: list):
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def count(self) -> int:
        return self.collection.count()
