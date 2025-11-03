"""
Agent Memory System

Stores and retrieves agent experiences and knowledge.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memories."""
    EXPERIENCE = "experience"  # Short-term experiences
    EPISODE = "episode"  # Task episodes
    KNOWLEDGE = "knowledge"  # Long-term knowledge
    OBSERVATION = "observation"  # Environmental observations


@dataclass
class Memory:
    """A single memory."""
    id: str
    content: str
    memory_type: MemoryType
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    importance: float = 0.5


class AgentMemory:
    """
    Agent memory system with vector storage support.

    Example:
        memory = AgentMemory()

        # Store a memory
        memory.store("Executed query successfully", memory_type="experience")

        # Retrieve relevant memories
        memories = memory.retrieve("query execution", limit=5)
    """

    def __init__(
        self,
        vector_store: Optional[Any] = None,
        embedding_provider: Optional[Any] = None,
        max_memories: int = 1000
    ):
        """
        Initialize agent memory.

        Args:
            vector_store: Optional vector store (e.g., Qdrant)
            embedding_provider: Optional embedding model
            max_memories: Maximum memories to keep in RAM
        """
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.max_memories = max_memories

        # In-memory storage
        self.memories: List[Memory] = []
        self.memory_index: Dict[str, Memory] = {}

    def store(
        self,
        content: str,
        memory_type: str = "experience",
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> str:
        """
        Store a memory.

        Args:
            content: Memory content
            memory_type: Type of memory
            metadata: Optional metadata
            importance: Importance score (0-1)

        Returns:
            Memory ID
        """
        # Generate memory ID
        memory_id = self._generate_id(content)

        # Get embedding if available
        embedding = None
        if self.embedding_provider:
            embedding = self.embedding_provider.embed(content)

        # Create memory
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=MemoryType(memory_type),
            timestamp=datetime.now(),
            metadata=metadata or {},
            embedding=embedding,
            importance=importance
        )

        # Store in RAM
        self.memories.append(memory)
        self.memory_index[memory_id] = memory

        # Store in vector store if available
        if self.vector_store and embedding:
            self._store_in_vector_db(memory)

        # Prune if needed
        if len(self.memories) > self.max_memories:
            self._prune_memories()

        logger.debug(f"Stored memory: {memory_id}")
        return memory_id

    def retrieve(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Memory]:
        """
        Retrieve relevant memories.

        Args:
            query: Search query
            memory_type: Filter by memory type
            limit: Maximum memories to return

        Returns:
            List of relevant memories
        """
        # Use vector search if available
        if self.vector_store and self.embedding_provider:
            return self._retrieve_from_vector_db(query, memory_type, limit)

        # Fall back to keyword search
        return self._retrieve_keyword(query, memory_type, limit)

    def get(self, memory_id: str) -> Optional[Memory]:
        """
        Get a specific memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory or None
        """
        return self.memory_index.get(memory_id)

    def delete(self, memory_id: str):
        """
        Delete a memory.

        Args:
            memory_id: Memory ID
        """
        if memory_id in self.memory_index:
            memory = self.memory_index[memory_id]
            self.memories.remove(memory)
            del self.memory_index[memory_id]

            # Delete from vector store
            if self.vector_store:
                self._delete_from_vector_db(memory_id)

            logger.debug(f"Deleted memory: {memory_id}")

    def clear(self, memory_type: Optional[str] = None):
        """
        Clear memories.

        Args:
            memory_type: Optional type to clear, or all if None
        """
        if memory_type:
            # Clear specific type
            type_enum = MemoryType(memory_type)
            self.memories = [m for m in self.memories if m.memory_type != type_enum]
            self.memory_index = {
                k: v for k, v in self.memory_index.items()
                if v.memory_type != type_enum
            }
        else:
            # Clear all
            self.memories.clear()
            self.memory_index.clear()

        logger.info(f"Cleared memories: {memory_type or 'all'}")

    def get_recent(self, limit: int = 10, memory_type: Optional[str] = None) -> List[Memory]:
        """
        Get most recent memories.

        Args:
            limit: Maximum memories
            memory_type: Optional type filter

        Returns:
            List of recent memories
        """
        filtered = self.memories
        if memory_type:
            type_enum = MemoryType(memory_type)
            filtered = [m for m in filtered if m.memory_type == type_enum]

        # Sort by timestamp
        sorted_memories = sorted(filtered, key=lambda m: m.timestamp, reverse=True)
        return sorted_memories[:limit]

    def get_important(self, limit: int = 10, threshold: float = 0.7) -> List[Memory]:
        """
        Get important memories.

        Args:
            limit: Maximum memories
            threshold: Minimum importance

        Returns:
            List of important memories
        """
        important = [m for m in self.memories if m.importance >= threshold]
        sorted_memories = sorted(important, key=lambda m: m.importance, reverse=True)
        return sorted_memories[:limit]

    def summarize(self) -> Dict[str, Any]:
        """
        Summarize memory statistics.

        Returns:
            Memory summary
        """
        type_counts = {}
        for memory_type in MemoryType:
            count = sum(1 for m in self.memories if m.memory_type == memory_type)
            type_counts[memory_type.value] = count

        return {
            "total_memories": len(self.memories),
            "by_type": type_counts,
            "oldest": self.memories[0].timestamp.isoformat() if self.memories else None,
            "newest": self.memories[-1].timestamp.isoformat() if self.memories else None
        }

    def _generate_id(self, content: str) -> str:
        """Generate a unique ID for content."""
        timestamp = datetime.now().isoformat()
        data = f"{content}{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _store_in_vector_db(self, memory: Memory):
        """Store memory in vector database."""
        try:
            if hasattr(self.vector_store, 'upsert'):
                self.vector_store.upsert(
                    collection_name="agent_memory",
                    points=[{
                        "id": memory.id,
                        "vector": memory.embedding,
                        "payload": {
                            "content": memory.content,
                            "type": memory.memory_type.value,
                            "timestamp": memory.timestamp.isoformat(),
                            "metadata": memory.metadata,
                            "importance": memory.importance
                        }
                    }]
                )
        except Exception as e:
            logger.error(f"Error storing in vector DB: {e}")

    def _retrieve_from_vector_db(
        self,
        query: str,
        memory_type: Optional[str],
        limit: int
    ) -> List[Memory]:
        """Retrieve memories from vector database."""
        try:
            # Get query embedding
            query_embedding = self.embedding_provider.embed(query)

            # Search vector store
            filters = {}
            if memory_type:
                filters["type"] = memory_type

            results = self.vector_store.search(
                collection_name="agent_memory",
                query_vector=query_embedding,
                limit=limit,
                query_filter=filters if filters else None
            )

            # Convert to Memory objects
            memories = []
            for result in results:
                payload = result.payload
                memory = Memory(
                    id=result.id,
                    content=payload["content"],
                    memory_type=MemoryType(payload["type"]),
                    timestamp=datetime.fromisoformat(payload["timestamp"]),
                    metadata=payload.get("metadata", {}),
                    embedding=result.vector,
                    importance=payload.get("importance", 0.5)
                )
                memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"Error retrieving from vector DB: {e}")
            return self._retrieve_keyword(query, memory_type, limit)

    def _retrieve_keyword(
        self,
        query: str,
        memory_type: Optional[str],
        limit: int
    ) -> List[Memory]:
        """Retrieve memories using keyword search."""
        query_lower = query.lower()
        filtered = self.memories

        # Filter by type
        if memory_type:
            type_enum = MemoryType(memory_type)
            filtered = [m for m in filtered if m.memory_type == type_enum]

        # Score by keyword match
        scored = []
        for memory in filtered:
            content_lower = memory.content.lower()
            score = sum(1 for word in query_lower.split() if word in content_lower)
            if score > 0:
                scored.append((memory, score))

        # Sort by score and recency
        scored.sort(key=lambda x: (x[1], x[0].timestamp), reverse=True)

        return [m for m, _ in scored[:limit]]

    def _delete_from_vector_db(self, memory_id: str):
        """Delete memory from vector database."""
        try:
            if hasattr(self.vector_store, 'delete'):
                self.vector_store.delete(
                    collection_name="agent_memory",
                    points_selector=[memory_id]
                )
        except Exception as e:
            logger.error(f"Error deleting from vector DB: {e}")

    def _prune_memories(self):
        """Prune least important memories."""
        # Keep important memories and recent memories
        to_keep = []

        # Keep all important memories (importance > 0.7)
        important = [m for m in self.memories if m.importance > 0.7]
        to_keep.extend(important)

        # Keep most recent memories
        recent = sorted(self.memories, key=lambda m: m.timestamp, reverse=True)
        to_keep.extend(recent[:int(self.max_memories * 0.3)])

        # Remove duplicates
        to_keep = list({m.id: m for m in to_keep}.values())

        # If still too many, remove oldest with low importance
        if len(to_keep) > self.max_memories:
            to_keep.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
            to_keep = to_keep[:self.max_memories]

        # Update memory lists
        self.memories = to_keep
        self.memory_index = {m.id: m for m in to_keep}

        logger.info(f"Pruned memories to {len(self.memories)}")


__all__ = ["AgentMemory", "Memory", "MemoryType"]
