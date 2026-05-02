"""Redis-based semantic cache with embedding vector similarity search.

Architecture:
  1. Compute embedding for (repo_path, query) pair
  2. Search Redis vector index for nearest neighbors
  3. If cosine_similarity > threshold → cache hit (skip LLM call)
  4. If cache miss → call LLM, store result with embedding

Target: 35% hit rate, ~25% LLM cost reduction for onboarding queries.
"""

from __future__ import annotations

import hashlib
import math
import struct
import time
from dataclasses import dataclass, field
from typing import Any

# ── In-memory cache for when Redis is unavailable ──────────────────────

_IN_MEMORY: dict[str, dict[str, Any]] = {}

# ── Types ──────────────────────────────────────────────────────────────


@dataclass
class CacheEntry:
    query: str
    repo_path: str
    response: str
    embedding: list[float] = field(repr=False)
    cached_at: float = field(default_factory=time.time)
    hit_count: int = 0
    ttl: int = 7 * 24 * 3600  # 7 days


@dataclass
class CacheHit:
    entry: CacheEntry
    similarity: float

    @property
    def response(self) -> str:
        return self.entry.response


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    total_queries: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return self.hits / self.total_queries

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_queries": self.total_queries,
            "hit_rate": round(self.hit_rate, 4),
        }


# ── Semantic Cache ─────────────────────────────────────────────────────


class SemanticCache:
    """Semantic cache with embedding-based similarity search.

    Two backends:
    - Redis Stack (vector search via FT.SEARCH with KNN)
    - In-memory (cosine similarity brute-force)

    Usage::

        cache = SemanticCache()
        async with cache:
            hit = await cache.lookup("how does auth work?", "/path/to/repo")
            if hit:
                return hit.response
            result = await llm.generate(...)
            await cache.store("how does auth work?", "/path/to/repo", result)
    """

    def __init__(
        self,
        redis_url: str = "",
        similarity_threshold: float = 0.85,
        embedding_model: str = "text-embedding-3-small",
        embedding_api_key: str = "",
        index_name: str = "repomate_embeddings",
        vector_dim: int = 1536,
        ttl_seconds: int = 7 * 24 * 3600,  # 7 days
    ) -> None:
        self._redis_url = redis_url
        self._threshold = similarity_threshold
        self._embedding_model = embedding_model
        self._embedding_api_key = embedding_api_key
        self._index_name = index_name
        self._vector_dim = vector_dim
        self._ttl = ttl_seconds
        self._redis: Any = None
        self._stats = CacheStats()
        self._initialized = False

    async def __aenter__(self) -> SemanticCache:
        await self.initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    @property
    def stats(self) -> CacheStats:
        return self._stats

    async def initialize(self) -> None:
        """Connect to Redis and create the vector index if needed."""
        if self._initialized:
            return
        if self._redis_url:
            self._redis = await self._connect_redis()
            await self._ensure_index()
        self._initialized = True

    async def _connect_redis(self) -> Any:
        """Connect to Redis. Uses redis-py with optional vector search support."""
        try:
            import redis.asyncio as redis

            r = redis.from_url(self._redis_url, decode_responses=False)
            await r.ping()
            return r
        except ImportError:
            return None
        except Exception:
            return None

    async def _ensure_index(self) -> None:
        """Create the vector search index if it doesn't exist."""
        if self._redis is None:
            return
        try:
            # FT.INFO returns info if index exists, throws if not
            await self._redis.ft(self._index_name).info()
        except Exception:
            # Create index: HNSW with cosine distance
            try:
                from redis.commands.search.field import NumericField, TagField, VectorField
                from redis.commands.search.index_definition import IndexDefinition, IndexType

                schema = (
                    TagField("$.repo_hash", as_name="repo_hash"),
                    NumericField("$.cached_at", as_name="cached_at"),
                    VectorField(
                        "$.embedding",
                        "HNSW",
                        {
                            "TYPE": "FLOAT32",
                            "DIM": self._vector_dim,
                            "DISTANCE_METRIC": "COSINE",
                        },
                        as_name="embedding",
                    ),
                )
                definition = IndexDefinition(
                    prefix=[f"{self._index_name}:"], index_type=IndexType.JSON
                )
                await self._redis.ft(self._index_name).create_index(
                    schema, definition=definition
                )
            except Exception:
                pass  # Index creation failed — will use in-memory fallback

    # ── Public API ─────────────────────────────────────────────────

    async def lookup(
        self, query: str, repo_path: str, *, similarity_threshold: float | None = None
    ) -> CacheHit | None:
        """Search for a cached response semantically similar to the query.

        Returns CacheHit if found with similarity > threshold, None otherwise.
        """
        threshold = similarity_threshold if similarity_threshold is not None else self._threshold
        self._stats.total_queries += 1

        repo_hash = self._repo_hash(repo_path)

        # Try Redis vector search first
        if self._redis is not None:
            hit = await self._redis_lookup(query, repo_hash, threshold)
            if hit is not None:
                self._stats.hits += 1
                hit.entry.hit_count += 1
                return hit

        # Fall back to in-memory brute-force search
        hit = self._memory_lookup(query, repo_path, repo_hash, threshold)
        if hit is not None:
            self._stats.hits += 1
            hit.entry.hit_count += 1
            return hit

        self._stats.misses += 1
        return None

    async def store(
        self, query: str, repo_path: str, response: str
    ) -> None:
        """Store a query-response pair with its embedding vector."""
        repo_hash = self._repo_hash(repo_path)
        embedding = await self._compute_embedding(
            f"repo: {repo_path}\nquery: {query}"
        )

        entry = CacheEntry(
            query=query,
            repo_path=repo_path,
            response=response,
            embedding=embedding,
            ttl=self._ttl,
        )

        # Store in Redis
        if self._redis is not None:
            await self._redis_store(entry, repo_hash)

        # Always store in memory (fast fallback)
        key = self._cache_key(query, repo_hash)
        _IN_MEMORY[key] = {
            "entry": entry,
            "expires_at": time.time() + self._ttl,
        }

    # ── Embedding ─────────────────────────────────────────────────

    async def _compute_embedding(self, text: str) -> list[float]:
        """Compute embedding vector for the given text.

        Uses OpenAI embeddings API if an API key is available,
        otherwise returns a fast hash-based deterministic vector.
        """
        if self._embedding_api_key:
            return await self._openai_embedding(text)
        return self._hash_embedding(text)

    async def _openai_embedding(self, text: str) -> list[float]:
        """Call OpenAI embeddings API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {self._embedding_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._embedding_model,
                        "input": text[:8192],  # OpenAI's token limit
                    },
                )
                data = resp.json()
                return data["data"][0]["embedding"]
        except Exception:
            return self._hash_embedding(text)

    def _hash_embedding(self, text: str) -> list[float]:
        """Generate a deterministic pseudo-embedding from text hash.

        NOT suitable for production semantic search — this is a fallback
        for environments without embedding API access. Uses character
        n-gram hashes to produce vaguely semantically-useful vectors
        (similar texts produce more similar vectors than random).
        """
        dim = self._vector_dim
        vec = [0.0] * dim

        # Character trigrams — capture surface similarity
        text_lower = text.lower()
        for i in range(len(text_lower) - 2):
            trigram = text_lower[i : i + 3]
            h = hashlib.md5(trigram.encode()).digest()
            idx = struct.unpack("<I", h[:4])[0] % dim
            val = struct.unpack("<h", h[4:6])[0] / 32768.0
            vec[idx] += val

        # Normalize to unit vector
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    # ── Redis Operations ───────────────────────────────────────────

    async def _redis_lookup(
        self, query: str, repo_hash: str, threshold: float
    ) -> CacheHit | None:
        """Search Redis for similar cached entries."""
        try:
            query_embedding = await self._compute_embedding(
                f"repo: {repo_hash}\nquery: {query}"
            )
            embedding_bytes = struct.pack(f"<{len(query_embedding)}f", *query_embedding)

            # KNN search: get top 5 candidates
            from redis.commands.search.query import Query

            q = (
                Query(f"@repo_hash:{{{repo_hash}}} => [KNN 5 @embedding $vec AS score]")
                .sort_by("score")
                .return_fields("score", "$.query", "$.response", "$.embedding", "$.cached_at")
                .dialect(2)
            )

            results = await self._redis.ft(self._index_name).search(
                q, query_params={"vec": embedding_bytes}
            )

            if results and results.docs:
                top = results.docs[0]
                similarity = 1.0 - float(top.score)  # COSINE distance → similarity
                if similarity >= threshold:
                    query_text = getattr(top, "$.query", "")
                    response_text = getattr(top, "$.response", "")
                    cached_at = float(getattr(top, "$.cached_at", 0))

                    # Check TTL expiry
                    if cached_at and (time.time() - cached_at) > self._ttl:
                        return None

                    entry = CacheEntry(
                        query=query_text,
                        repo_path="",  # Not stored separately in Redis
                        response=response_text,
                        embedding=query_embedding,
                        cached_at=cached_at,
                    )
                    return CacheHit(entry=entry, similarity=similarity)
        except Exception:
            pass
        return None

    async def _redis_store(self, entry: CacheEntry, repo_hash: str) -> None:
        """Store a cache entry in Redis."""
        try:
            key = f"{self._index_name}:{self._cache_key(entry.query, repo_hash)}"
            data = {
                "repo_hash": repo_hash,
                "query": entry.query,
                "response": entry.response,
                "embedding": entry.embedding,
                "cached_at": entry.cached_at,
                "hit_count": entry.hit_count,
            }
            await self._redis.json().set(key, "$", data)
            await self._redis.expire(key, self._ttl)
        except Exception:
            pass

    # ── In-Memory Operations ───────────────────────────────────────

    def _memory_lookup(
        self, query: str, repo_path: str, repo_hash: str, threshold: float
    ) -> CacheHit | None:
        """Brute-force cosine similarity search against in-memory cache."""
        query_embedding = self._hash_embedding(
            f"repo: {repo_path}\nquery: {query}"
        )

        now = time.time()
        best_similarity = -1.0
        best_entry: CacheEntry | None = None

        for key, data in list(_IN_MEMORY.items()):
            if data.get("expires_at", 0) < now:
                del _IN_MEMORY[key]
                continue
            # Only match entries for the same repo (key format: repo_hash:query_hash)
            if not key.startswith(f"{repo_hash}:"):
                continue
            entry: CacheEntry = data["entry"]
            sim = _cosine_similarity(query_embedding, entry.embedding)
            if sim > best_similarity:
                best_similarity = sim
                best_entry = entry

        if best_entry is not None and best_similarity >= threshold:
            return CacheHit(entry=best_entry, similarity=best_similarity)
        return None

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _repo_hash(repo_path: str) -> str:
        """Generate a stable hash for a repo path."""
        return hashlib.sha256(repo_path.encode()).hexdigest()[:16]

    @staticmethod
    def _cache_key(query: str, repo_hash: str) -> str:
        """Generate a cache key from query and repo hash."""
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        return f"{repo_hash}:{query_hash}"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
