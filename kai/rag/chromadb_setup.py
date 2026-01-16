"""
ChromaDB Setup for Nigerian Food Knowledge Base

This module initializes ChromaDB with OpenAI embeddings and loads enriched
Nigerian food data for semantic search and retrieval.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()


class NigerianFoodVectorDB:
    """Vector database for Nigerian food nutrition data using ChromaDB"""

    def __init__(
        self,
        persist_directory: str = "chromadb_data",
        collection_name: str = "nigerian_foods",
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize ChromaDB with OpenAI embeddings.

        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
            openai_api_key: OpenAI API key (reads from env if not provided)
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Get OpenAI API key
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Initialize OpenAI embedding function
        # Using text-embedding-3-large for best performance (3072 dimensions)
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-large"
        )

        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Nigerian food nutrition database"}
        )

    def _create_document_text(self, food: Dict[str, Any]) -> str:
        """
        Create searchable text from food data.

        Combines name, aliases, description, health benefits, and cultural
        significance for comprehensive semantic search.

        Args:
            food: Food data dictionary

        Returns:
            Formatted text for embedding
        """
        nutrients = food.get("nutrients_per_100g", {})

        # Build comprehensive searchable text
        text_parts = [
            f"Food: {food['name']}",
            f"Also known as: {', '.join(food.get('aliases', []))}",
            f"Category: {food['category']}",
            f"Description: {food['description']}",
            f"Typical portion: {food.get('typical_portion', 'N/A')}",
            f"Meal types: {', '.join(food.get('meal_types', []))}",
            f"Cooking methods: {', '.join(food.get('cooking_methods', []))}",
            f"Common pairings: {', '.join(food.get('common_pairings', []))}",
            f"Dietary flags: {', '.join(food.get('dietary_flags', []))}",
            f"Health benefits: {' '.join(food.get('health_benefits', []))}",
            f"Cultural significance: {food.get('cultural_significance', '')}",
            f"Price tier: {food.get('price_tier', 'N/A')}",
            f"Availability: {food.get('availability', 'N/A')}",
            # Add key nutrients for searchability
            f"Calories: {nutrients.get('calories', 'N/A')} per 100g",
            f"Protein: {nutrients.get('protein', 'N/A')}g per 100g",
            f"Iron: {nutrients.get('iron', 'N/A')}mg per 100g",
            f"Calcium: {nutrients.get('calcium', 'N/A')}mg per 100g",
        ]

        return "\n".join(text_parts)

    def _create_metadata(self, food: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create metadata for filtering and retrieval.

        Args:
            food: Food data dictionary

        Returns:
            Metadata dictionary (must be JSON-serializable)
        """
        nutrients = food.get("nutrients_per_100g", {})
        common_servings = food.get("common_servings", {})

        return {
            "food_id": food["id"],
            "name": food["name"],
            "category": food["category"],
            "region": food.get("region", "Nigeria"),
            "price_tier": food.get("price_tier", "mid"),
            "availability": food.get("availability", "widely_available"),
            "confidence": food.get("confidence", 0.0),
            # Store ALL 8 nutrients for filtering and retrieval
            "calories": nutrients.get("calories", 0),
            "protein": nutrients.get("protein", 0),
            "carbohydrates": nutrients.get("carbohydrates", 0),
            "fat": nutrients.get("fat", 0),
            "iron": nutrients.get("iron", 0),
            "calcium": nutrients.get("calcium", 0),
            "potassium": nutrients.get("potassium", 0),
            "zinc": nutrients.get("zinc", 0),
            # Store dietary flags as comma-separated string
            "dietary_flags": ",".join(food.get("dietary_flags", [])),
            "meal_types": ",".join(food.get("meal_types", [])),
            # CRITICAL: Store portion limits from v2 database for realistic estimation
            "typical_portion_g": common_servings.get("typical_portion_g", 150),
            "min_reasonable_g": common_servings.get("min_reasonable_g", 50),
            "max_reasonable_g": common_servings.get("max_reasonable_g", 300),
        }

    def load_foods_from_jsonl(self, jsonl_path: str) -> int:
        """
        Load Nigerian food data from JSONL file into ChromaDB.

        Args:
            jsonl_path: Path to the enriched foods JSONL file

        Returns:
            Number of foods loaded
        """
        foods_loaded = 0
        documents = []
        metadatas = []
        ids = []

        print(f"\n📂 Loading foods from {jsonl_path}...")

        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    food = json.loads(line)

                    # Create document text for embedding
                    doc_text = self._create_document_text(food)
                    documents.append(doc_text)

                    # Create metadata for filtering
                    metadata = self._create_metadata(food)
                    metadatas.append(metadata)

                    # Use food ID as document ID
                    ids.append(food["id"])

                    foods_loaded += 1

                    if foods_loaded % 10 == 0:
                        print(f"   Processed {foods_loaded} foods...")

                except json.JSONDecodeError as e:
                    print(f"   ✗ Error parsing line {line_num}: {e}")
                    continue
                except Exception as e:
                    print(f"   ✗ Error processing line {line_num}: {e}")
                    continue

        # Add all documents to ChromaDB in batch
        if documents:
            print(f"\n🔄 Adding {len(documents)} foods to ChromaDB...")
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"   ✓ Successfully added {foods_loaded} foods to ChromaDB")

        return foods_loaded

    def search(
        self,
        query: str,
        n_results: int = 5,
        category_filter: Optional[str] = None,
        dietary_filter: Optional[str] = None,
        meal_type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for foods using semantic similarity.

        Args:
            query: Natural language search query
            n_results: Number of results to return
            category_filter: Filter by category (e.g., "staple", "protein")
            dietary_filter: Filter by dietary flag (e.g., "vegetarian", "gluten_free")
            meal_type_filter: Filter by meal type (e.g., "breakfast", "lunch")

        Returns:
            List of matching food documents with metadata
        """
        # Build where clause for filtering
        # Note: ChromaDB doesn't support $contains, so we'll filter post-query
        where_clause = {}
        if category_filter:
            where_clause["category"] = category_filter

        # Perform semantic search
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results * 3,  # Get more results for post-filtering
            where=where_clause if where_clause else None,
            include=["documents", "metadatas", "distances"]
        )

        # Post-filter for dietary flags and meal types
        filtered_results = []
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]

            # Check dietary filter
            if dietary_filter:
                dietary_flags = metadata.get('dietary_flags', '')
                if dietary_filter not in dietary_flags:
                    continue

            # Check meal type filter
            if meal_type_filter:
                meal_types = metadata.get('meal_types', '')
                if meal_type_filter not in meal_types:
                    continue

            filtered_results.append(i)

            # Stop when we have enough results
            if len(filtered_results) >= n_results:
                break

        # Return only filtered results
        results['ids'][0] = [results['ids'][0][i] for i in filtered_results]
        results['metadatas'][0] = [results['metadatas'][0][i] for i in filtered_results]
        results['documents'][0] = [results['documents'][0][i] for i in filtered_results]
        results['distances'][0] = [results['distances'][0][i] for i in filtered_results]

        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "name": results['metadatas'][0][i]['name'],
                "category": results['metadatas'][0][i]['category'],
                "distance": results['distances'][0][i],
                "similarity": 1 - results['distances'][0][i],  # Convert distance to similarity
                "metadata": results['metadatas'][0][i],
                "document": results['documents'][0][i]
            })

        return formatted_results

    def get_food_by_id(self, food_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific food by ID.

        Args:
            food_id: Food ID (e.g., "nigerian-jollof-rice")

        Returns:
            Food data or None if not found
        """
        try:
            result = self.collection.get(
                ids=[food_id],
                include=["documents", "metadatas"]
            )

            if result['ids']:
                return {
                    "id": result['ids'][0],
                    "metadata": result['metadatas'][0],
                    "document": result['documents'][0]
                }
            return None

        except Exception as e:
            print(f"Error retrieving food {food_id}: {e}")
            return None

    def get_foods_by_nutrient(
        self,
        nutrient: str,
        min_value: float,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get foods with high amounts of a specific nutrient.

        Args:
            nutrient: Nutrient name ("protein", "iron", "calcium", "potassium")
            min_value: Minimum value of nutrient
            n_results: Number of results to return

        Returns:
            List of foods matching criteria
        """
        # Map nutrient names to metadata keys
        nutrient_key = nutrient.lower()

        try:
            # Query with nutrient filter
            results = self.collection.get(
                where={nutrient_key: {"$gte": min_value}},
                include=["documents", "metadatas"],
                limit=n_results
            )

            formatted_results = []
            for i in range(len(results['ids'])):
                formatted_results.append({
                    "id": results['ids'][i],
                    "name": results['metadatas'][i]['name'],
                    "category": results['metadatas'][i]['category'],
                    f"{nutrient}_per_100g": results['metadatas'][i].get(nutrient_key, 0),
                    "metadata": results['metadatas'][i]
                })

            # Sort by nutrient value (descending)
            formatted_results.sort(
                key=lambda x: x[f"{nutrient}_per_100g"],
                reverse=True
            )

            return formatted_results

        except Exception as e:
            print(f"Error querying by nutrient: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dictionary with collection stats
        """
        count = self.collection.count()

        return {
            "collection_name": self.collection_name,
            "total_foods": count,
            "persist_directory": self.persist_directory,
            "embedding_model": "text-embedding-3-large",
            "embedding_dimensions": 3072
        }

    def reset_collection(self):
        """Reset the collection (delete all data)"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Nigerian food nutrition database"}
        )
        print(f"✓ Collection '{self.collection_name}' reset")


def initialize_chromadb(
    enriched_foods_path: str = "knowledge-base/data/processed/nigerian_foods_v2_improved.jsonl",
    persist_directory: str = "chromadb_data",
    reset: bool = False
) -> NigerianFoodVectorDB:
    """
    Initialize ChromaDB and load Nigerian food data.

    Args:
        enriched_foods_path: Path to enriched foods JSONL
        persist_directory: Directory for ChromaDB persistence
        reset: Whether to reset existing data

    Returns:
        Initialized NigerianFoodVectorDB instance
    """
    print("\n🚀 Initializing ChromaDB for Nigerian Food Knowledge Base\n")

    # Initialize vector database
    vector_db = NigerianFoodVectorDB(
        persist_directory=persist_directory,
        collection_name="nigerian_foods"
    )

    # Reset if requested
    if reset:
        print("⚠️  Resetting existing collection...")
        vector_db.reset_collection()

    # Check if collection is already populated
    stats = vector_db.get_collection_stats()
    if stats['total_foods'] > 0 and not reset:
        print(f"ℹ️  Collection already contains {stats['total_foods']} foods")
        print("   Use reset=True to reload data\n")
        return vector_db

    # Load foods from JSONL
    foods_loaded = vector_db.load_foods_from_jsonl(enriched_foods_path)

    # Print final stats
    print("\n" + "=" * 60)
    print("✅ ChromaDB Initialization Complete!")
    print("=" * 60)
    stats = vector_db.get_collection_stats()
    print(f"📊 Collection: {stats['collection_name']}")
    print(f"📦 Total foods loaded: {stats['total_foods']}")
    print(f"🔢 Embedding dimensions: {stats['embedding_dimensions']}")
    print(f"💾 Persist directory: {stats['persist_directory']}")
    print("=" * 60 + "\n")

    return vector_db


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_chromadb():
        """Test ChromaDB setup with sample queries"""

        print("🧪 Testing ChromaDB Setup\n")

        # Initialize ChromaDB
        vector_db = initialize_chromadb(
            enriched_foods_path="knowledge-base/data/processed/nigerian_foods_v2_improved.jsonl",
            reset=False  # Set to True to reload all data
        )

        # Test 1: Semantic search
        print("\n1️⃣  Testing semantic search...")
        print("   Query: 'foods high in iron for women'")
        results = vector_db.search(
            query="foods high in iron for women",
            n_results=5
        )
        print(f"\n   Top {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['name']} ({result['category']}) - "
                  f"Similarity: {result['similarity']:.3f}")
            print(f"      Iron: {result['metadata']['iron']}mg per 100g")

        # Test 2: Search with filters
        print("\n\n2️⃣  Testing filtered search...")
        print("   Query: 'breakfast foods' + vegetarian filter")
        results = vector_db.search(
            query="breakfast foods",
            n_results=5,
            dietary_filter="vegetarian"
        )
        print(f"\n   Top {len(results)} vegetarian breakfast foods:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['name']} - Similarity: {result['similarity']:.3f}")

        # Test 3: Get by specific nutrient
        print("\n\n3️⃣  Testing nutrient-based search...")
        print("   Looking for foods with >10g protein per 100g")
        results = vector_db.get_foods_by_nutrient(
            nutrient="protein",
            min_value=10.0,
            n_results=5
        )
        print(f"\n   Top {len(results)} high-protein foods:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['name']} - "
                  f"{result['protein_per_100g']}g protein per 100g")

        # Test 4: Get specific food by ID
        print("\n\n4️⃣  Testing direct food retrieval...")
        food = vector_db.get_food_by_id("nigerian-jollof-rice")
        if food:
            print(f"   ✓ Found: {food['metadata']['name']}")
            print(f"   Category: {food['metadata']['category']}")
            print(f"   Calories: {food['metadata']['calories']} per 100g")

        # Test 5: Collection stats
        print("\n\n5️⃣  Collection Statistics:")
        stats = vector_db.get_collection_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        print("\n✅ All tests completed!\n")

    # Run tests
    asyncio.run(test_chromadb())
