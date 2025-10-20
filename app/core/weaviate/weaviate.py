# ruff: noqa
# mypy: ignore-errors
import asyncio
import os
from datetime import datetime, timezone

import weaviate
from weaviate.classes.config import Configure, DataType, Property

from ..logging import get_logger

os.environ[
    "OPENAI_APIKEY"
] = "TODO: Add OpenAI API key"

logger = get_logger(__name__)

async_weaviate_client = weaviate.use_async_with_local()

text2vec_openai = Configure.Vectors.text2vec_openai(
    name="text",
    model="text-embedding-3-small",
    source_properties=["text"],
)

text2vec_cohere = Configure.Vectors.text2vec_cohere(
    name="text",
    source_properties=["text"],
    vector_index_config=Configure.VectorIndex.dynamic(
        hnsw=Configure.VectorIndex.hnsw(
            quantizer=Configure.VectorIndex.Quantizer.sq(training_limit=50000)
        ),
        flat=Configure.VectorIndex.flat(quantizer=Configure.VectorIndex.Quantizer.bq()),
        threshold=10000,
    ),
)


async def create_collection(name: str):
    """Create a collection."""
    logger.info(f"Creating collection {name}...")
    async with async_weaviate_client as client:
        await client.collections.create(
            name=name,
            multi_tenancy_config=Configure.multi_tenancy(
                enabled=True,
                auto_tenant_creation=True,
                auto_tenant_activation=True,
            ),
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="date", data_type=DataType.DATE),
                Property(name="tags", data_type=DataType.TEXT_ARRAY),
            ],
            vector_config=[
                Configure.Vectors.text2vec_cohere(
                    name="text",
                    source_properties=["text"],
                    vector_index_config=Configure.VectorIndex.dynamic(
                        hnsw=Configure.VectorIndex.hnsw(
                            quantizer=Configure.VectorIndex.Quantizer.sq(training_limit=50000)
                        ),
                        flat=Configure.VectorIndex.flat(
                            quantizer=Configure.VectorIndex.Quantizer.bq()
                        ),
                        threshold=10000
                    )
                )
            ],
            generative_config=Configure.Generative.cohere(model="command-r-plus")
            # MTConfig
        )
    logger.info(f"Collection {name} created")


async def create_tenant(tenant_name: str, collection_name: str):
    """Create a tenant."""
    logger.info(f"Creating tenant {tenant_name}...")
    async with async_weaviate_client as client:
        collection = client.collections.get(collection_name)
        await collection.tenants.create([tenant_name])

    logger.info(f"Tenant {tenant_name} created")


async def insert_prd(tenant_name: str, collection_name: str):
    from langchain_text_splitters import MarkdownTextSplitter

    with open("prd_examples/project_phoenix.md", encoding="utf-8") as f:
        project_text = f.read()

    # split data
    text_splitter = MarkdownTextSplitter(
        # separators=["\n\n", "\n'", ".", " ", ""], # default separators for markdown
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = text_splitter.split_text(project_text)
    print(f"Original text length: {len(project_text)} characters")
    print(f"Number of chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(
            f"Chunk {i+1} (length {len(chunk)}): {chunk[:600]}..."
        )  # Print first 600 chars

    async with async_weaviate_client as client:
        collection = client.collections.get(collection_name).with_tenant(tenant_name)
        for chunk in chunks:
            await collection.data.insert(
                properties={
                    "text": chunk,
                    "date": datetime.now(timezone.utc),
                    "tags": ["prd", "chunk"],
                },
            )


async def test_openai():
    from openai import OpenAI

    with open("prd_examples/project_phoenix.md", encoding="utf-8") as f:
        project_text = f.read()

    openAI_client = OpenAI(
        api_key="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"
    )

    response = openAI_client.responses.create(
        model="gpt-4o-mini",
        input=f"Using the following PRD, create SCRUM epics and user stories. Include developmentdependencies between epics and user stories for the project:  {project_text}",
        temperature=0.6,
    )

    with open("prd_examples/project_phoenix_response.md", "w", encoding="utf-8") as f:
        f.write(response.output_text)

    print(response.output_text)


async def test_embeddings():
    from langchain_text_splitters import MarkdownTextSplitter

    with open("prd_examples/project_phoenix_response.md", encoding="utf-8") as f:
        project_text = f.read()

    # split data
    text_splitter = MarkdownTextSplitter(
        # separators=["\n\n", "\n'", ".", " ", ""], # default separators for markdown
        chunk_size=00,
        chunk_overlap=50,
    )
    chunks = text_splitter.split_text(project_text)
    print(f"Original text length: {len(project_text)} characters")
    print(f"Number of chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(
            f"Chunk {i+1} (length {len(chunk)}): {chunk[:100]}..."
        )  # Print first 100 chars

    async with async_weaviate_client as client:
        # Ingest chunks
        with client.batch as batch:
            for chunk in chunks:
                pass

        print("Chunks successfully ingested into Weaviate.")

    # # Create embeddings and save it to a file
    # embeddings = OpenAIEmbeddings()
    # vectors = embeddings.embed_documents(chunks)
    # with open("prd_examples/project_phoenix.vectors", "w", encoding="utf-8") as f:
    #     f.write(json.dumps(vectors))
    # # print(vectors)


if __name__ == "__main__":
    # asyncio.run(create_collection("skrm"))
    # asyncio.run(create_tenant("project_a", "skrm"))
    asyncio.run(insert_prd("project_a", "skrm"))
    # asyncio.run(test_openai())
    # asyncio.run(test_embeddings())
