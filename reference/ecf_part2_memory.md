# ECF Implementation Plan - Part 2: Memory System Implementation

## Overview

The three-tier memory system is the foundation of ECF. It replaces the context window as the source of truth for agent state and history.

---

## I. The Three-Tier Architecture

### Tier 1: Working State (Ephemeral)

**Purpose:** Current task execution context  
**Storage:** Filesystem (YAML/JSON)  
**Retention:** Deleted after task completion (or archived if flagged for training)  
**Access Pattern:** Frequent read/write during execution

#### Schema Definition

```yaml
# task_working_state.yaml
task_id: "task_20260112_001"
goal: "Implement user authentication system"
status: "IN_PROGRESS"
domain: "backend_api"

constraints:
  - "Use bcrypt for password hashing"
  - "Support email + password login"
  - "No third-party auth providers"
  - "Include rate limiting on login endpoint"

current_step:
  index: 3
  description: "Generate password hashing utilities"
  agent: "executor"
  started_at: "2026-01-12T10:15:00Z"
  estimated_duration: "5 minutes"

completed_steps:
  - index: 1
    description: "Generate project structure"
    outcome: "success"
    artifact: "file://project_structure.json"
    completed_at: "2026-01-12T10:05:00Z"
    
  - index: 2
    description: "Create database schema"
    outcome: "success"
    artifact: "file://schema.sql"
    completed_at: "2026-01-12T10:10:00Z"

next_steps:
  - index: 4
    description: "Write authentication routes"
    dependencies: [3]
  - index: 5
    description: "Add input validation"
    dependencies: [4]
  - index: 6
    description: "Write integration tests"
    dependencies: [4, 5]

metadata:
  created_at: "2026-01-12T10:00:00Z"
  estimated_completion: "2026-01-12T10:45:00Z"
  priority: "high"
```

#### Implementation

```python
class WorkingStateManager:
    """Manages ephemeral task state on filesystem."""
    
    def __init__(self, base_path="./tasks"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def create_task(self, task_spec):
        """Initialize new task state."""
        task_id = self._generate_task_id()
        task_file = self.base_path / f"{task_id}.yaml"
        
        state = {
            "task_id": task_id,
            "goal": task_spec["goal"],
            "status": "CREATED",
            "domain": task_spec.get("domain", "general"),
            "constraints": task_spec.get("constraints", []),
            "current_step": None,
            "completed_steps": [],
            "next_steps": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "priority": task_spec.get("priority", "normal")
            }
        }
        
        with open(task_file, "w") as f:
            yaml.dump(state, f, default_flow_style=False)
        
        return task_id
    
    def load_task(self, task_id):
        """Load task state from disk."""
        task_file = self.base_path / f"{task_id}.yaml"
        with open(task_file, "r") as f:
            return yaml.safe_load(f)
    
    def update_task(self, task_id, updates):
        """Update task state (atomic operation)."""
        state = self.load_task(task_id)
        state.update(updates)
        
        task_file = self.base_path / f"{task_id}.yaml"
        temp_file = task_file.with_suffix(".tmp")
        
        # Atomic write
        with open(temp_file, "w") as f:
            yaml.dump(state, f, default_flow_style=False)
        temp_file.replace(task_file)
        
        return state
    
    def complete_step(self, task_id, step_index, outcome, artifact=None):
        """Mark step as completed."""
        state = self.load_task(task_id)
        
        completed_step = {
            "index": step_index,
            "description": state["current_step"]["description"],
            "outcome": outcome,
            "completed_at": datetime.now().isoformat()
        }
        
        if artifact:
            completed_step["artifact"] = artifact
        
        state["completed_steps"].append(completed_step)
        state["current_step"] = None
        
        return self.update_task(task_id, state)
    
    def archive_task(self, task_id, reason="completed"):
        """Move completed task to archive."""
        task_file = self.base_path / f"{task_id}.yaml"
        archive_dir = self.base_path / "archive" / datetime.now().strftime("%Y-%m")
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        archive_file = archive_dir / f"{task_id}_{reason}.yaml"
        task_file.rename(archive_file)
        
        return archive_file
```

---

### Tier 2: Episodic Trace (Immutable Log)

**Purpose:** Complete execution history for auditing and training  
**Storage:** SQLite (local) or PostgreSQL (multi-user)  
**Retention:** Permanent  
**Access Pattern:** Write-once, read-many (append-only)

#### Schema Definition

```sql
-- Core decision log
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- State machine context
    state TEXT NOT NULL,  -- "PLANNING", "EXECUTING", "VALIDATING"
    agent TEXT NOT NULL,  -- "planner", "executor", "critic"
    
    -- Input context snapshot
    context_snapshot JSON NOT NULL,
    
    -- Model interaction
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    model_version TEXT,
    temperature REAL,
    
    -- Output
    action_taken TEXT NOT NULL,
    artifacts_created JSON,  -- {"files": ["auth.py"], "lines": 87}
    
    -- Validation
    validation_status TEXT,  -- "passed", "failed", "skipped"
    validation_feedback JSON,
    
    -- Outcome
    outcome TEXT NOT NULL,  -- "success", "failure", "retry"
    error_message TEXT,
    
    -- Tracing
    trace_id TEXT NOT NULL,  -- For distributed tracing
    parent_decision_id INTEGER,
    
    FOREIGN KEY (parent_decision_id) REFERENCES decisions(id)
);

CREATE INDEX idx_task_id ON decisions(task_id);
CREATE INDEX idx_timestamp ON decisions(timestamp);
CREATE INDEX idx_trace_id ON decisions(trace_id);
CREATE INDEX idx_outcome ON decisions(outcome);
CREATE INDEX idx_state_agent ON decisions(state, agent);

-- Tool execution transcripts
CREATE TABLE tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    tool_name TEXT NOT NULL,
    params JSON NOT NULL,
    
    -- Execution
    started_at DATETIME,
    completed_at DATETIME,
    duration_ms INTEGER,
    
    -- Result
    status TEXT,  -- "success", "failure", "timeout"
    result JSON,
    stdout TEXT,
    stderr TEXT,
    exit_code INTEGER,
    
    -- Resource usage
    cpu_time_ms INTEGER,
    memory_peak_mb INTEGER,
    
    FOREIGN KEY (decision_id) REFERENCES decisions(id)
);

CREATE INDEX idx_decision_id ON tool_calls(decision_id);
CREATE INDEX idx_tool_name ON tool_calls(tool_name);
CREATE INDEX idx_status ON tool_calls(status);

-- Validation events
CREATE TABLE validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    validator_type TEXT,  -- "schema", "functional", "semantic"
    passed BOOLEAN NOT NULL,
    
    -- Details
    requirements_checked JSON,
    violations JSON,
    feedback TEXT,
    
    FOREIGN KEY (decision_id) REFERENCES decisions(id)
);

CREATE INDEX idx_validation_decision ON validations(decision_id);
CREATE INDEX idx_validation_passed ON validations(passed);
```

#### Implementation

```python
class EpisodicMemory:
    """Immutable decision log with complete execution history."""
    
    def __init__(self, db_path="./data/memory.db"):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """Create tables if they don't exist."""
        with open("schema.sql") as f:
            self.db.executescript(f.read())
        self.db.commit()
    
    def record_decision(self, task_id, state, agent, context, 
                       action, outcome, **kwargs):
        """Append decision to log (immutable)."""
        cursor = self.db.execute("""
            INSERT INTO decisions (
                task_id, state, agent, context_snapshot,
                action_taken, outcome, trace_id,
                prompt_tokens, completion_tokens, model_version,
                validation_status, error_message, artifacts_created
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            state,
            agent,
            json.dumps(context),
            action,
            outcome,
            kwargs.get("trace_id", str(uuid.uuid4())),
            kwargs.get("prompt_tokens"),
            kwargs.get("completion_tokens"),
            kwargs.get("model_version"),
            kwargs.get("validation_status"),
            kwargs.get("error_message"),
            json.dumps(kwargs.get("artifacts_created", {}))
        ))
        
        self.db.commit()
        return cursor.lastrowid
    
    def record_tool_call(self, decision_id, tool_name, params, result):
        """Log tool execution details."""
        self.db.execute("""
            INSERT INTO tool_calls (
                decision_id, tool_name, params,
                started_at, completed_at, duration_ms,
                status, result, stdout, stderr, exit_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_id,
            tool_name,
            json.dumps(params),
            result.get("started_at"),
            result.get("completed_at"),
            result.get("duration_ms"),
            result.get("status"),
            json.dumps(result.get("data", {})),
            result.get("stdout"),
            result.get("stderr"),
            result.get("exit_code")
        ))
        self.db.commit()
    
    def get_task_history(self, task_id, limit=None):
        """Retrieve complete decision history for task."""
        query = """
            SELECT * FROM decisions 
            WHERE task_id = ? 
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.db.execute(query, (task_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_decisions(self, task_id, count=5):
        """Get last N decisions for context assembly."""
        cursor = self.db.execute("""
            SELECT * FROM decisions 
            WHERE task_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (task_id, count))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def query_by_domain(self, domain, outcome="success", days=30):
        """Find successful episodes in domain for training."""
        cursor = self.db.execute("""
            SELECT DISTINCT task_id 
            FROM decisions 
            WHERE json_extract(context_snapshot, '$.task.domain') = ?
            AND outcome = ?
            AND timestamp > datetime('now', '-{} days')
            GROUP BY task_id
        """.format(days), (domain, outcome))
        
        return [row[0] for row in cursor.fetchall()]
```

---

### Tier 3: Semantic Memory (Curated Knowledge)

**Purpose:** Long-term validated patterns and guardrails  
**Storage:** SQLite + FAISS vector index  
**Retention:** Permanent with periodic pruning  
**Access Pattern:** Hybrid (SQL + vector search)

#### Schema Definition

```sql
-- Validated patterns (distilled from experience)
CREATE TABLE patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    pattern_name TEXT NOT NULL,
    description TEXT,
    
    -- Evidence
    example_code TEXT,
    example_context JSON,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_validated DATETIME,
    
    -- Embeddings
    embedding_id INTEGER,  -- Index in FAISS
    
    -- Metadata
    version INTEGER DEFAULT 1,
    deprecated BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_domain ON patterns(domain);
CREATE INDEX idx_pattern_name ON patterns(pattern_name);
CREATE INDEX idx_deprecated ON patterns(deprecated);
CREATE INDEX idx_success_rate ON patterns(success_count, failure_count);

-- User guardrails and preferences
CREATE TABLE guardrails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type TEXT NOT NULL,  -- "security", "style", "domain"
    rule_text TEXT NOT NULL,
    enforcement_level TEXT DEFAULT 'warn',  -- "block", "warn", "log"
    
    -- Examples
    valid_examples JSON,
    invalid_examples JSON,
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    enabled BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_rule_type ON guardrails(rule_type);
CREATE INDEX idx_enforcement ON guardrails(enforcement_level);
CREATE INDEX idx_enabled ON guardrails(enabled);
```

#### Implementation

```python
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class SemanticMemory:
    """Hybrid semantic + symbolic long-term memory."""
    
    def __init__(self, db_path="./data/memory.db", 
                 embedding_model="all-MiniLM-L6-v2"):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        
        # Vector search
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        self.encoder = SentenceTransformer(embedding_model)
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        
        self._load_embeddings()
    
    def _load_embeddings(self):
        """Load existing pattern embeddings into FAISS."""
        cursor = self.db.execute("""
            SELECT id, pattern_name, description, example_code 
            FROM patterns 
            WHERE deprecated = FALSE
        """)
        
        patterns = cursor.fetchall()
        if not patterns:
            return
        
        # Build index
        texts = [f"{p['pattern_name']}: {p['description']}" for p in patterns]
        embeddings = self.encoder.encode(texts)
        self.index.add(embeddings.astype('float32'))
        
        # Store mapping
        self.id_map = {i: p['id'] for i, p in enumerate(patterns)}
    
    def add_pattern(self, domain, pattern_name, description, 
                   example_code, example_context):
        """Add new validated pattern."""
        # Generate embedding
        text = f"{pattern_name}: {description}"
        embedding = self.encoder.encode([text])[0]
        
        # Add to FAISS
        embedding_id = self.index.ntotal
        self.index.add(embedding.reshape(1, -1).astype('float32'))
        
        # Store in DB
        cursor = self.db.execute("""
            INSERT INTO patterns (
                domain, pattern_name, description,
                example_code, example_context, embedding_id
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            domain, pattern_name, description,
            example_code, json.dumps(example_context), embedding_id
        ))
        
        self.db.commit()
        return cursor.lastrowid
    
    def retrieve_similar_patterns(self, query, domain=None, k=5):
        """Hybrid retrieval: semantic search + domain filtering."""
        # 1. Semantic search with FAISS
        query_embedding = self.encoder.encode([query])[0]
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1).astype('float32'), 
            k=k*2  # Over-retrieve for filtering
        )
        
        # 2. Get pattern IDs
        pattern_ids = [self.id_map[i] for i in indices[0] if i in self.id_map]
        
        # 3. SQL filtering
        placeholders = ','.join('?' * len(pattern_ids))
        query = f"""
            SELECT * FROM patterns 
            WHERE id IN ({placeholders})
            AND deprecated = FALSE
        """
        params = pattern_ids
        
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        
        query += " ORDER BY success_count DESC LIMIT ?"
        params.append(k)
        
        cursor = self.db.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def increment_pattern_success(self, pattern_id):
        """Track pattern usage (for ranking)."""
        self.db.execute("""
            UPDATE patterns 
            SET success_count = success_count + 1,
                last_validated = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (pattern_id,))
        self.db.commit()
    
    def add_guardrail(self, rule_type, rule_text, enforcement_level,
                     valid_examples=None, invalid_examples=None):
        """Store user guardrail."""
        self.db.execute("""
            INSERT INTO guardrails (
                rule_type, rule_text, enforcement_level,
                valid_examples, invalid_examples
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            rule_type, rule_text, enforcement_level,
            json.dumps(valid_examples or []),
            json.dumps(invalid_examples or [])
        ))
        self.db.commit()
    
    def get_active_guardrails(self, rule_type=None):
        """Retrieve enabled guardrails."""
        query = "SELECT * FROM guardrails WHERE enabled = TRUE"
        params = []
        
        if rule_type:
            query += " AND rule_type = ?"
            params.append(rule_type)
        
        cursor = self.db.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
```

---

## II. Context Assembly Strategy

```python
class MemorySystem:
    """Unified interface to three-tier memory."""
    
    def __init__(self, config):
        self.working_state = WorkingStateManager(config.tasks_path)
        self.episodic = EpisodicMemory(config.db_path)
        self.semantic = SemanticMemory(config.db_path)
    
    def get_relevant_context(self, task_id, state, max_tokens=2000):
        """
        Assemble context from three tiers—prioritize by relevance.
        Token budget ensures we never exceed model limits.
        """
        context = {}
        token_budget = max_tokens
        
        # 1. Working state (always included - highest priority)
        task_state = self.working_state.load_task(task_id)
        context["task"] = task_state
        token_budget -= self._count_tokens(task_state)
        
        if token_budget <= 0:
            return context  # Fail-safe
        
        # 2. Recent decisions (episodic memory)
        recent_decisions = self.episodic.get_recent_decisions(
            task_id, count=5
        )
        context["history"] = recent_decisions
        token_budget -= self._count_tokens(recent_decisions)
        
        if token_budget <= 500:
            return context  # Not enough budget for semantic search
        
        # 3. Semantic patterns (if budget remains)
        query = f"{task_state['goal']} {state} {task_state.get('domain', '')}"
        patterns = self.semantic.retrieve_similar_patterns(
            query, 
            domain=task_state.get('domain'),
            k=3
        )
        
        # Truncate patterns if needed
        patterns_tokens = self._count_tokens(patterns)
        if patterns_tokens > token_budget:
            patterns = patterns[:1]  # Keep only top pattern
        
        context["patterns"] = patterns
        
        return context
    
    def _count_tokens(self, obj):
        """Estimate token count (rough approximation)."""
        text = json.dumps(obj)
        return len(text) // 4  # ~4 chars per token average
```

---

## III. Memory Maintenance

### Periodic Cleanup

```python
class MemoryMaintenance:
    """Background tasks for memory health."""
    
    def __init__(self, memory_system):
        self.memory = memory_system
    
    def archive_old_tasks(self, days_threshold=90):
        """Archive completed tasks older than threshold."""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        # Find old completed tasks
        cursor = self.memory.episodic.db.execute("""
            SELECT DISTINCT task_id 
            FROM decisions 
            WHERE timestamp < ?
            AND outcome IN ('success', 'failure')
            GROUP BY task_id
        """, (cutoff_date.isoformat(),))
        
        old_tasks = [row[0] for row in cursor.fetchall()]
        
        for task_id in old_tasks:
            self.memory.working_state.archive_task(task_id, "auto_archive")
    
    def prune_low_quality_patterns(self, min_success_rate=0.7):
        """Remove patterns with poor success rates."""
        self.memory.semantic.db.execute("""
            UPDATE patterns 
            SET deprecated = TRUE
            WHERE (success_count * 1.0 / (success_count + failure_count)) < ?
            AND (success_count + failure_count) >= 10
        """, (min_success_rate,))
        
        self.memory.semantic.db.commit()
    
    def rebuild_vector_index(self):
        """Rebuild FAISS index (after schema changes)."""
        self.memory.semantic._load_embeddings()
```

---

## Next Steps

Continue to:
- **Part 3:** Micro-Agent Architecture
- **Part 4:** Learning Pipeline
- **Part 5:** Deployment & Operations
