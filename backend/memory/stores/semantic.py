"""
Semantic Memory (Tier 3) implementation using Scikit-Learn and SQLite.
"""
import sqlite3
import json
import numpy as np
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors

class SemanticMemory:
    """
    Hybrid semantic + symbolic long-term memory.
    Uses Scikit-Learn NearestNeighbors for vector similarity and SQLite for metadata/persistence.
    """

    def __init__(
        self, 
        db_path: str, 
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_dim: int = 384
    ):
        """
        Initialize Semantic Memory.
        
        Args:
            db_path: Path to the SQLite database.
            embedding_model: Name of the SentenceTransformer model.
            embedding_dim: Dimension of the embeddings (384 for all-MiniLM-L6-v2).
        """
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        self.model_name = embedding_model
        
        # Initialize model
        self.encoder = SentenceTransformer(self.model_name)
        
        # We will initialize NearestNeighbors when we have data
        self.nn: Optional[NearestNeighbors] = None
        self.embeddings_cache: List[np.ndarray] = []
        
        # ID mapping: index in self.embeddings_cache -> SQLite ID
        self.id_map: Dict[int, int] = {}
        
        self._init_db()
        self._load_embeddings()

    def _init_db(self):
        """Initialize SQLite tables for patterns and guardrails."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    pattern_name TEXT NOT NULL,
                    description TEXT,
                    example_code TEXT,
                    example_context TEXT, -- JSON string
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_validated TEXT,
                    embedding_id INTEGER,
                    version INTEGER DEFAULT 1,
                    deprecated BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS guardrails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_type TEXT NOT NULL,
                    rule_text TEXT NOT NULL,
                    enforcement_level TEXT DEFAULT 'warn',
                    valid_examples TEXT, -- JSON string
                    invalid_examples TEXT, -- JSON string
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    enabled BOOLEAN DEFAULT 1
                )
            """)
            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_domain ON patterns(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_deprecated ON patterns(deprecated)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_guardrails_type ON guardrails(rule_type)")
            conn.commit()

    def _load_embeddings(self):
        """Load existing pattern embeddings into memory."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, pattern_name, description 
                FROM patterns 
                WHERE deprecated = 0
                ORDER BY id ASC
            """)
            patterns = cursor.fetchall()
            
            if not patterns:
                return

            texts = [f"{p['pattern_name']}: {p['description']}" for p in patterns]
            embeddings = self.encoder.encode(texts)
            
            self.embeddings_cache = [e for e in embeddings]
            self.id_map = {i: p['id'] for i, p in enumerate(patterns)}
            self._rebuild_nn()

    @property
    def count(self) -> int:
        """Return the number of patterns in memory."""
        return len(self.embeddings_cache)

    def _rebuild_nn(self):
        """Rebuild the NearestNeighbors model."""
        if not self.embeddings_cache:
            self.nn = None
            return
            
        X = np.array(self.embeddings_cache)
        self.nn = NearestNeighbors(n_neighbors=min(len(X), 10), metric="cosine")
        self.nn.fit(X)

    def add_pattern(self, text: str, metadata: Dict[str, Any]) -> int:
        """
        Embed and store a new pattern.
        
        Args:
            text: The primary text to embed (e.g. "name: description").
            metadata: Dictionary containing domain, pattern_name, description, 
                      example_code, example_context, etc.
        """
        embedding = self.encoder.encode([text])[0]
        
        # Add to SQLite
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO patterns (
                    domain, pattern_name, description,
                    example_code, example_context, embedding_id,
                    last_validated, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.get("domain", "general"),
                metadata.get("pattern_name", "unnamed"),
                metadata.get("description", ""),
                metadata.get("example_code", ""),
                json.dumps(metadata.get("example_context", {})),
                len(self.embeddings_cache),
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat()
            ))
            pattern_id = cursor.lastrowid
            conn.commit()
            
            if pattern_id is None:
                raise RuntimeError("Failed to insert pattern into database.")
            
            # Update local cache and ID map
            self.id_map[len(self.embeddings_cache)] = pattern_id
            self.embeddings_cache.append(embedding)
            self._rebuild_nn()
            
            return pattern_id

    def retrieve(self, query: str, domain: Optional[str] = None, k: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid search for similar patterns.
        
        Args:
            query: The search query.
            domain: Optional domain filter.
            k: Number of patterns to retrieve.
        """
        if self.nn is None:
            return []

        # 1. Vector similarity search
        query_embedding = self.encoder.encode([query])[0]
        search_k = min(k * 2, len(self.embeddings_cache))
        
        distances, indices = self.nn.kneighbors(
            query_embedding.reshape(1, -1),
            n_neighbors=search_k
        )
        
        # 2. Map indices to SQLite IDs
        pattern_ids = [self.id_map[idx] for idx in indices[0] if idx in self.id_map]
        
        if not pattern_ids:
            return []

        # 3. SQL metadata filtering
        placeholders = ",".join("?" for _ in pattern_ids)
        sql_query = f"""
            SELECT * FROM patterns 
            WHERE id IN ({placeholders}) 
            AND deprecated = 0
        """
        params = list(pattern_ids)
        
        if domain:
            sql_query += " AND domain = ?"
            params.append(str(domain))
            
        sql_query += " ORDER BY success_count DESC LIMIT ?"
        params.append(int(k))
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql_query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            # De-serialize JSON fields
            for res in results:
                if res.get("example_context"):
                    res["example_context"] = json.loads(res["example_context"])
            
            return results

    def add_guardrail(self, rule_type: str, rule_text: str, enforcement_level: str = "warn",
                     valid_examples: Optional[List[str]] = None, invalid_examples: Optional[List[str]] = None):
        """Store a new guardrail."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO guardrails (
                    rule_type, rule_text, enforcement_level,
                    valid_examples, invalid_examples
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                rule_type,
                rule_text,
                enforcement_level,
                json.dumps(valid_examples or []),
                json.dumps(invalid_examples or [])
            ))
            conn.commit()

    def get_active_guardrails(self, rule_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve enabled guardrails."""
        sql_query = "SELECT * FROM guardrails WHERE enabled = 1"
        params = []
        
        if rule_type:
            sql_query += " AND rule_type = ?"
            params.append(rule_type)
            
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql_query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            for res in results:
                if res.get("valid_examples"):
                    res["valid_examples"] = json.loads(res["valid_examples"])
                if res.get("invalid_examples"):
                    res["invalid_examples"] = json.loads(res["invalid_examples"])
            
            return results
