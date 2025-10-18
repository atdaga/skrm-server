import asyncio

import weaviate
from weaviate.classes.config import Configure, DataType, Property

from ..logging import get_logger

logger = get_logger(__name__)

async_weaviate_client = weaviate.use_async_with_local()


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


# async def test_weaviate():
#     """Test Weaviate connection."""
#     async with WeaviateClient() as client:
#         await client.create_collection("skrm")


if __name__ == "__main__":
    # asyncio.run(test_weaviate())
    asyncio.run(create_collection("skrm_tmp1"))