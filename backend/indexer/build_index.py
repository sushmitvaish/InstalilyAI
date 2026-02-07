import json
import os
import sys

# Add parent dir to path so we can import from services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore


def load_parts(filepath: str) -> list:
    """Load parts from JSONL file."""
    parts = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                parts.append(json.loads(line))
    print(f"Loaded {len(parts)} parts from {filepath}")
    return parts


def create_chunks(part: dict) -> list:
    """Create multiple document chunks from a single part for different query types."""
    chunks = []
    ps = part.get("ps_number", "Unknown")
    name = part.get("name", "Unknown Part")
    appliance = part.get("appliance_type", "")

    base_metadata = {
        "ps_number": ps,
        "name": name,
        "appliance_type": appliance,
        "oem_part_number": part.get("oem_part_number", ""),
        "price": part.get("price", ""),
        "image_url": part.get("image_url", ""),
        "source_url": part.get("source_url", ""),
    }

    # Chunk 1: Overview
    overview_parts = [f"Part: {name}", f"PartSelect Number: {ps}"]
    if part.get("oem_part_number"):
        overview_parts.append(f"OEM Part Number: {part['oem_part_number']}")
    if part.get("price"):
        overview_parts.append(f"Price: {part['price']}")
    if part.get("in_stock") is not None:
        overview_parts.append(
            f"Availability: {'In Stock' if part['in_stock'] else 'Out of Stock'}"
        )
    if part.get("description"):
        overview_parts.append(f"Description: {part['description']}")
    if part.get("symptoms_fixed"):
        overview_parts.append(f"Fixes: {part['symptoms_fixed']}")

    overview_text = "\n".join(overview_parts)
    chunks.append({
        "id": f"{ps}_overview",
        "document": overview_text,
        "metadata": {**base_metadata, "chunk_type": "overview"}
    })

    # Chunk 2: Compatibility (if models data exists)
    if part.get("compatible_models"):
        models_list = ", ".join(part["compatible_models"][:50])
        compat_text = (
            f"Part {ps} ({name}) is compatible with the following models: "
            f"{models_list}"
        )
        chunks.append({
            "id": f"{ps}_compatibility",
            "document": compat_text,
            "metadata": {**base_metadata, "chunk_type": "compatibility"}
        })

    # Chunk 3: Installation (if instructions exist)
    if part.get("installation_instructions"):
        install_text = (
            f"Installation instructions for {ps} ({name}):\n"
            f"{part['installation_instructions']}"
        )
        chunks.append({
            "id": f"{ps}_installation",
            "document": install_text,
            "metadata": {**base_metadata, "chunk_type": "installation"}
        })

    return chunks


def build_index(parts_file: str = "data/parts.jsonl", batch_size: int = 50):
    """Build the ChromaDB index from scraped parts data."""
    parts = load_parts(parts_file)

    embedding_service = EmbeddingService()
    vector_store = VectorStore()

    # Create all chunks
    all_chunks = []
    for part in parts:
        chunks = create_chunks(part)
        all_chunks.extend(chunks)

    print(f"Created {len(all_chunks)} chunks from {len(parts)} parts")

    # Process in batches
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        ids = [c["id"] for c in batch]
        documents = [c["document"] for c in batch]
        metadatas = [c["metadata"] for c in batch]

        print(f"Embedding batch {i // batch_size + 1}/"
              f"{(len(all_chunks) + batch_size - 1) // batch_size}...")

        embeddings = embedding_service.embed_batch(documents)

        vector_store.add_documents(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    total = vector_store.count()
    print(f"\nIndexing complete! {total} documents in ChromaDB.")


if __name__ == "__main__":
    parts_file = sys.argv[1] if len(sys.argv) > 1 else "data/parts.jsonl"
    build_index(parts_file)
