# ECF Implementation Plan - Part 3: Micro-Agent Architecture

## Overview

Role-separated micro-agents replace the monolithic "do everything" agent. Each agent has a narrow scope and communicates via structured messages, not conversations.

---

## I. The Five Core Agent Roles

### 1. Planner Agent

**Responsibility:** Task decomposition  
**Input:** Goal + constraints  
**Output:** YAML task file with DAG structure  
**Scope:** Never executes tools—only plans  
**Fine-Tuning Focus:** Clear, atomic, verifiable task breakdown

#### Implementation

```python
class PlannerAgent:
    """
    Decomposes high-level goals into executable sub-tasks.
    Blind to execution details—focused on strategy only.
    """
    
    def __init__(self, llm_client, validator):
        self.llm = llm_client
        self.validator = validator
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self):
        return """You are a task planning specialist. Your ONLY job is to decompose goals into sub-tasks.

Rules:
- Each task must be independently verifiable
- Tasks must form a valid DAG (no circular dependencies)
- Be specific: "set up environment" is too vague
- Use concrete deliverables: files, endpoints, tests
- Estimate dependencies accurately

Output Format: YAML only, no explanations."""
    
    def generate_plan(self, goal, constraints, domain=None):
        """Create task decomposition."""
        
        prompt = f"""Decompose this goal into 5-10 concrete sub-tasks.

Goal: {goal}

Constraints:
{self._format_constraints(constraints)}

{f'Domain: {domain}' if domain else ''}

Output YAML with this structure:
```yaml
tasks:
  - id: 1
    description: "Clear, actionable task"
    dependencies: []
    estimated_duration: "X minutes"
  - id: 2
    description: "Another task"
    dependencies: [1]
    estimated_duration: "Y minutes"
```"""
        
        response = self.llm.generate(
            user_prompt=prompt,
            context={"domain": domain, "constraints": constraints},
            max_tokens=1000
        )
        
        plan = self._parse_yaml(response)
        
        # Validate structure
        self._validate_plan(plan)
        
        return plan
    
    def _validate_plan(self, plan):
        """Multi-layer validation of plan quality."""
        
        # 1. Schema validation
        if not self._is_valid_schema(plan):
            raise ValidationError("Plan schema invalid")
        
        # 2. DAG validation (no cycles)
        if not self._is_valid_dag(plan):
            raise ValidationError("Plan contains circular dependencies")
        
        # 3. Task quality checks
        for task in plan.get("tasks", []):
            if len(task["description"]) < 10:
                raise ValidationError(f"Task {task['id']} description too vague")
            
            if not task.get("estimated_duration"):
                raise ValidationError(f"Task {task['id']} missing duration estimate")
    
    def _is_valid_dag(self, plan):
        """Ensure dependencies form acyclic graph."""
        import networkx as nx
        
        graph = nx.DiGraph()
        for task in plan.get("tasks", []):
            graph.add_node(task["id"])
            for dep in task.get("dependencies", []):
                graph.add_edge(dep, task["id"])
        
        return nx.is_directed_acyclic_graph(graph)
    
    def _format_constraints(self, constraints):
        return '\n'.join(f'- {c}' for c in constraints)
    
    def _parse_yaml(self, response):
        """Extract YAML from response (handles markdown wrapping)."""
        import yaml
        import re
        
        # Strip markdown fences if present
        yaml_match = re.search(r'```ya?ml\n(.*?)\n```', response, re.DOTALL)
        if yaml_match:
            response = yaml_match.group(1)
        
        return yaml.safe_load(response)
```

---

### 2. Executor Agent

**Responsibility:** Tool invocation  
**Input:** Single task spec + minimal context  
**Output:** Tool call result + artifacts  
**Scope:** Never plans, never validates—only executes  
**Fine-Tuning Focus:** Correct tool selection and parameter formatting

#### Implementation

```python
class ExecutorAgent:
    """
    Executes single atomic task using available tools.
    Completely blind to overall strategy—focuses on current step only.
    """
    
    def __init__(self, llm_client, tool_executor):
        self.llm = llm_client
        self.tool_executor = tool_executor
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self):
        return """You are a task executor. Your ONLY job is to invoke the correct tool for the given task.

Rules:
- Choose ONE tool that directly accomplishes the task
- Format parameters exactly as tool expects
- Do NOT plan ahead or explain
- Do NOT validate output (that's Critic's job)

Output Format: JSON tool call only, no commentary."""
    
    def execute_step(self, task, context):
        """Perform single atomic operation."""
        
        prompt = f"""Execute this specific task using available tools.

Task: {task['description']}

Available Tools:
{self._format_tool_catalog()}

Context from Previous Steps:
{self._format_context(context)}

Output JSON in this format:
```json
{{
  "tool": "tool_name",
  "params": {{
    "param1": "value1",
    "param2": "value2"
  }},
  "rationale": "One sentence explaining choice"
}}
```

Execute ONLY the specified task. One tool call."""
        
        response = self.llm.generate(
            user_prompt=prompt,
            context=context,
            max_tokens=2000
        )
        
        tool_call = self._parse_json(response)
        
        # Execute tool deterministically
        result = self.tool_executor.execute(
            tool_name=tool_call["tool"],
            params=tool_call["params"],
            timeout=300  # 5 minute timeout
        )
        
        return ExecutionResult(
            task_id=task["id"],
            tool_call=tool_call,
            result=result,
            artifacts=self._extract_artifacts(result)
        )
    
    def _format_tool_catalog(self):
        """Generate tool documentation for prompt."""
        tools = self.tool_executor.list_tools()
        
        catalog = []
        for tool in tools:
            catalog.append(f"""
Tool: {tool.name}
Description: {tool.description}
Parameters: {json.dumps(tool.parameters, indent=2)}
Example: {json.dumps(tool.example, indent=2)}
""")
        
        return '\n---\n'.join(catalog)
    
    def _format_context(self, context):
        """Format context for executor (only completed artifacts)."""
        completed = context.get("history", [])
        
        artifacts = {}
        for decision in completed:
            if decision.get("artifacts_created"):
                artifacts.update(decision["artifacts_created"])
        
        return json.dumps(artifacts, indent=2) if artifacts else "No previous artifacts"
    
    def _extract_artifacts(self, result):
        """Extract created artifacts from tool result."""
        artifacts = {}
        
        if result.get("files_created"):
            artifacts["files"] = result["files_created"]
        
        if result.get("stdout"):
            # Parse output for artifact indicators
            # e.g., "Created: /sandbox/file.py"
            pass
        
        return artifacts
    
    def _parse_json(self, response):
        """Extract JSON from response."""
        import re
        
        json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
        
        return json.loads(response)
```

---

### 3. Critic Agent

**Responsibility:** Output validation  
**Input:** Execution result + requirements  
**Output:** Pass/fail + specific feedback  
**Scope:** Never fixes issues—only validates  
**Fine-Tuning Focus:** Accurate requirement matching

#### Implementation

```python
class CriticAgent:
    """
    Validates outputs against requirements and guardrails.
    Never attempts to fix issues—only identifies them.
    """
    
    def __init__(self, llm_client, guardrails):
        self.llm = llm_client
        self.guardrails = guardrails
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self):
        return """You are a requirements validator. Your ONLY job is to check if output meets ALL requirements.

Rules:
- Be strict: any missing requirement = FAIL
- Check against explicit requirements only
- Provide specific violations, not vague feedback
- Do NOT suggest fixes (that's not your job)

Output Format: JSON validation result only."""
    
    def validate(self, output, requirements, task_spec):
        """Multi-layer validation pipeline."""
        
        # Layer 1: Deterministic checks (fast)
        deterministic_result = self._deterministic_validation(output, requirements)
        if not deterministic_result.passed:
            return deterministic_result
        
        # Layer 2: Functional tests (if applicable)
        if self._requires_functional_tests(task_spec):
            test_result = self._run_functional_tests(output, task_spec)
            if not test_result.passed:
                return ValidationResult(
                    valid=False,
                    reason="Functional tests failed",
                    feedback=test_result.failures,
                    layer="functional"
                )
        
        # Layer 3: LLM semantic validation (slow, used last)
        semantic_result = self._semantic_validation(output, requirements, task_spec)
        
        return semantic_result
    
    def _deterministic_validation(self, output, requirements):
        """Fast schema and type checks."""
        
        # Schema validation
        if not self._validate_schema(output):
            return ValidationResult(
                valid=False,
                reason="Schema validation failed",
                feedback=self._get_schema_errors(output),
                layer="schema"
            )
        
        # Guardrail checks
        violations = []
        for guardrail in self.guardrails.get_active_guardrails():
            if not self._check_guardrail(output, guardrail):
                violations.append(guardrail["rule_text"])
        
        if violations:
            return ValidationResult(
                valid=False,
                reason="Guardrail violations detected",
                feedback={"violations": violations},
                layer="guardrails"
            )
        
        return ValidationResult(valid=True, layer="schema")
    
    def _semantic_validation(self, output, requirements, task_spec):
        """LLM-based validation for semantic requirements."""
        
        prompt = f"""Validate if this output satisfies ALL requirements.

Output:
{json.dumps(output.to_dict(), indent=2)}

Requirements:
{self._format_requirements(requirements)}

Task Context:
{json.dumps(task_spec, indent=2)}

Respond with JSON:
```json
{{
  "valid": true/false,
  "reason": "Specific explanation",
  "violations": ["List of unmet requirements"],
  "confidence": 0.0-1.0
}}
```

Be strict. If ANY requirement is not clearly met, respond with valid: false."""
        
        response = self.llm.generate(
            user_prompt=prompt,
            context={"requirements": requirements, "task": task_spec},
            max_tokens=500
        )
        
        validation = self._parse_json(response)
        
        return ValidationResult(
            valid=validation["valid"],
            reason=validation["reason"],
            feedback=validation.get("violations", []),
            confidence=validation.get("confidence", 0.0),
            layer="semantic"
        )
    
    def _format_requirements(self, requirements):
        """Format requirements for prompt."""
        if isinstance(requirements, list):
            return '\n'.join(f'{i+1}. {req}' for i, req in enumerate(requirements))
        return str(requirements)
    
    def _requires_functional_tests(self, task_spec):
        """Determine if task needs functional testing."""
        # Code-related tasks should run tests
        code_indicators = ["write", "implement", "create", "build"]
        description = task_spec.get("description", "").lower()
        
        return any(indicator in description for indicator in code_indicators)
    
    def _run_functional_tests(self, output, task_spec):
        """Execute functional tests if output includes code."""
        # Run pytest, unittest, or custom tests
        # Return test results
        pass
```

---

### 4. Curator Agent

**Responsibility:** Training data mining  
**Input:** Execution logs from time window  
**Output:** Curated training dataset  
**Scope:** Never executes tasks—only analyzes logs  
**Fine-Tuning Focus:** Example quality assessment

#### Implementation

```python
class CuratorAgent:
    """
    Mines execution logs for high-quality training examples.
    Acts as gatekeeper for dataset admission.
    """
    
    def __init__(self, llm_client, memory_system):
        self.llm = llm_client
        self.memory = memory_system
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self):
        return """You are a training data quality assessor. Rate examples on:
- Clarity of instructions
- Appropriateness of output
- Generalizability
- No security violations

Score: 0-10 where 8+ is high quality."""
    
    def mine_training_examples(self, time_window, min_quality=0.8):
        """
        Extract training examples from recent successful episodes.
        """
        # Query recent successful tasks
        episodes = self.memory.episodic.db.execute(f"""
            SELECT DISTINCT task_id 
            FROM decisions 
            WHERE outcome = 'success' 
            AND timestamp > datetime('now', '-{time_window.days} days')
            AND validation_status = 'passed'
            GROUP BY task_id
        """).fetchall()
        
        candidates = []
        
        for (task_id,) in episodes:
            # Capture complete episode
            episode = self._capture_episode(task_id)
            
            # Apply quality filters
            if episode.quality_score < min_quality:
                continue
            
            # Extract training tuples
            examples = self._extract_training_tuples(episode)
            
            # LLM-based quality check for each example
            for example in examples:
                if self._is_high_quality_example(example):
                    candidates.append(example)
        
        # Deduplicate
        unique_examples = self._deduplicate(candidates)
        
        # Human review queue (if high-stakes)
        if self._requires_human_review(unique_examples):
            self._send_to_review_queue(unique_examples)
        else:
            self._auto_approve(unique_examples)
        
        return unique_examples
    
    def _capture_episode(self, task_id):
        """Extract complete execution trace for task."""
        decisions = self.memory.episodic.get_task_history(task_id)
        
        # Calculate quality score
        quality_score = self._score_episode_quality(decisions)
        
        return Episode(
            task_id=task_id,
            decisions=decisions,
            quality_score=quality_score
        )
    
    def _score_episode_quality(self, decisions):
        """Multi-factor quality scoring."""
        score = 1.0
        
        # Penalty for retries (indicates instability)
        retry_count = sum(1 for d in decisions if d.get("outcome") == "retry")
        score *= max(0, 1 - 0.1 * retry_count)
        
        # Penalty for validation failures
        validation_failures = sum(
            1 for d in decisions 
            if d.get("validation_status") == "failed"
        )
        score *= max(0, 1 - 0.2 * validation_failures)
        
        # Bonus for test coverage (code tasks)
        has_tests = any(
            "test" in d.get("artifacts_created", {}).get("files", [])
            for d in decisions
        )
        if has_tests:
            score *= 1.2
        
        # Bonus for clean execution
        if all(d.get("error_message") is None for d in decisions):
            score *= 1.1
        
        return min(score, 1.0)
    
    def _extract_training_tuples(self, episode):
        """Convert episode into instruction-following format."""
        examples = []
        
        for decision in episode.decisions:
            context = json.loads(decision["context_snapshot"])
            
            example = {
                "instruction": context["task"]["goal"],
                "input": json.dumps({
                    "current_step": context["task"].get("current_step"),
                    "constraints": context["task"].get("constraints", []),
                    "history": context.get("history", [])[:3]  # Last 3 only
                }),
                "output": decision["action_taken"],
                "metadata": {
                    "task_id": episode.task_id,
                    "agent_role": decision["agent"],
                    "domain": context["task"].get("domain"),
                    "timestamp": decision["timestamp"],
                    "quality_score": episode.quality_score
                }
            }
            
            examples.append(example)
        
        return examples
    
    def _is_high_quality_example(self, example):
        """Use LLM to assess example quality."""
        
        prompt = f"""Rate this training example on quality (0-10).

Instruction: {example['instruction']}
Input: {example['input'][:500]}  # Truncate for efficiency
Output: {example['output'][:500]}

Criteria:
- Clear, unambiguous instructions
- Appropriate output for instruction
- No security violations (secrets, PII)
- Generalizable pattern

Respond with just a number 0-10."""
        
        response = self.llm.generate(
            user_prompt=prompt,
            context={},
            max_tokens=10
        )
        
        try:
            score = int(response.strip())
            return score >= 8
        except ValueError:
            return False  # Conservative: reject if can't parse
    
    def _deduplicate(self, examples):
        """Remove near-duplicate examples."""
        from sklearn.metrics.pairwise import cosine_similarity
        from sentence_transformers import SentenceTransformer
        
        if len(examples) < 2:
            return examples
        
        encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Embed examples
        texts = [f"{ex['instruction']} {ex['output']}" for ex in examples]
        embeddings = encoder.encode(texts)
        
        # Find duplicates (>0.95 similarity)
        unique_indices = [0]  # Keep first
        
        for i in range(1, len(embeddings)):
            similarities = cosine_similarity(
                [embeddings[i]], 
                embeddings[:i]
            )[0]
            
            if max(similarities) < 0.95:
                unique_indices.append(i)
        
        return [examples[i] for i in unique_indices]
```

---

### 5. Learner Agent

**Responsibility:** Training orchestration  
**Input:** Trigger (scheduled or manual)  
**Output:** New model adapter (if gates pass)  
**Scope:** Coordinates training pipeline—doesn't execute tasks  
**Fine-Tuning Focus:** N/A (doesn't get fine-tuned—orchestrates training for others)

#### Implementation

```python
class LearnerAgent:
    """
    Orchestrates fine-tuning cycles with guard-railed automation.
    Owns the complete learning pipeline.
    """
    
    def __init__(self, curator, trainer, regression_suite, 
                 basal_manager, deployment_pipeline):
        self.curator = curator
        self.trainer = trainer
        self.regression_suite = regression_suite
        self.basal_manager = basal_manager
        self.deployment_pipeline = deployment_pipeline
    
    def run_training_cycle(self, trigger="scheduled", min_examples=100):
        """
        Complete learning loop with safety gates.
        """
        cycle_id = str(uuid.uuid4())
        logger.info(f"Starting training cycle {cycle_id} (trigger: {trigger})")
        
        # Stage 1: Gather training data
        examples = self.curator.mine_training_examples(
            time_window=timedelta(days=7),
            min_quality=0.8
        )
        
        if len(examples) < min_examples:
            logger.warn(f"Insufficient examples: {len(examples)} < {min_examples}")
            return TrainingResult(
                status="skipped",
                reason=f"Only {len(examples)} examples collected"
            )
        
        logger.info(f"Collected {len(examples)} training examples")
        
        # Stage 2: Mix with basal dataset
        mixed_dataset = self.basal_manager.mix_datasets(
            curriculum=examples,
            ratio=0.7  # 70% curriculum, 30% basal
        )
        
        logger.info(f"Mixed dataset: {len(mixed_dataset)} total examples")
        
        # Stage 3: Fine-tune with Unsloth
        try:
            adapter_path = self.trainer.train(
                base_model=self.trainer.config.base_model,
                dataset=mixed_dataset,
                output_dir=f"training_runs/{cycle_id}"
            )
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return TrainingResult(status="failed", reason=str(e))
        
        logger.info(f"Training completed: {adapter_path}")
        
        # Stage 4: Gate with regression suite
        regression_score = self.regression_suite.test(adapter_path)
        
        logger.info(f"Regression score: {regression_score:.2%}")
        
        if regression_score < 0.95:
            logger.warn("Regression detected, rejecting adapter")
            return TrainingResult(
                status="rejected",
                reason="regression",
                score=regression_score
            )
        
        # Stage 5: Deploy
        version = self._generate_version_tag()
        deployment_result = self.deployment_pipeline.deploy_adapter(
            adapter_path=adapter_path,
            version=version
        )
        
        if deployment_result.status != "deployed":
            return TrainingResult(
                status="deployment_failed",
                reason=deployment_result.reason
            )
        
        logger.info(f"Adapter {version} deployed successfully")
        
        return TrainingResult(
            status="deployed",
            version=version,
            regression_score=regression_score,
            examples_count=len(examples),
            cycle_id=cycle_id
        )
    
    def _generate_version_tag(self):
        """Generate semantic version for adapter."""
        # Format: YYYY.MM.DD.N (where N is cycle number for that day)
        date_prefix = datetime.now().strftime("%Y.%m.%d")
        
        # Count existing versions for today
        existing = len(glob.glob(f"adapters/{date_prefix}.*"))
        
        return f"{date_prefix}.{existing + 1}"
```

---

## II. Inter-Agent Communication

### Message Protocol

```python
@dataclass
class AgentMessage:
    """
    Typed messages for agent coordination.
    NOT conversational—structured data only.
    """
    id: str
    sender: str  # "planner", "executor", "critic", etc.
    recipient: str  # "controller" or specific agent
    message_type: str  # "PLAN_READY", "EXECUTION_COMPLETE", etc.
    payload: Dict[str, Any]
    timestamp: datetime
    trace_id: str  # For distributed tracing
    
    def validate_schema(self) -> bool:
        """Enforce message contracts."""
        schema = MESSAGE_SCHEMAS.get(self.message_type)
        if not schema:
            raise ValueError(f"Unknown message type: {self.message_type}")
        
        return jsonschema.validate(self.payload, schema)

# Message type schemas
MESSAGE_SCHEMAS = {
    "PLAN_READY": {
        "type": "object",
        "required": ["task_id", "plan_artifact", "estimated_steps"],
        "properties": {
            "task_id": {"type": "string"},
            "plan_artifact": {"type": "string"},
            "estimated_steps": {"type": "integer"}
        }
    },
    "EXECUTION_COMPLETE": {
        "type": "object",
        "required": ["task_id", "step_index", "result", "artifacts"],
        "properties": {
            "task_id": {"type": "string"},
            "step_index": {"type": "integer"},
            "result": {"type": "object"},
            "artifacts": {"type": "object"}
        }
    },
    "VALIDATION_FAILED": {
        "type": "object",
        "required": ["task_id", "step_index", "violations", "feedback"],
        "properties": {
            "task_id": {"type": "string"},
            "step_index": {"type": "integer"},
            "violations": {"type": "array"},
            "feedback": {"type": "string"}
        }
    }
}

# Example usage
plan_ready_msg = AgentMessage(
    id=str(uuid.uuid4()),
    sender="planner",
    recipient="controller",
    message_type="PLAN_READY",
    payload={
        "task_id": "task_001",
        "plan_artifact": "file://plans/task_001.yaml",
        "estimated_steps": 7
    },
    timestamp=datetime.now(),
    trace_id="trace_123"
)

# Validate before sending
plan_ready_msg.validate_schema()
```

### Shared Ledger (No Conversational Loops)

```python
class AgentLedger:
    """
    Message bus using SQLite for agent coordination.
    Prevents conversational context accumulation.
    """
    
    def __init__(self, db_path="./data/agent_ledger.db"):
        self.db = sqlite3.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message_type TEXT NOT NULL,
                payload JSON NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                trace_id TEXT,
                processed BOOLEAN DEFAULT FALSE
            )
        """)
        self.db.commit()
    
    def send_message(self, message: AgentMessage):
        """Post message to ledger."""
        self.db.execute("""
            INSERT INTO messages 
            VALUES (?, ?, ?, ?, ?, ?, ?, FALSE)
        """, (
            message.id,
            message.sender,
            message.recipient,
            message.message_type,
            json.dumps(message.payload),
            message.timestamp.isoformat(),
            message.trace_id
        ))
        self.db.commit()
    
    def get_unprocessed_messages(self, recipient):
        """Poll for new messages (event-driven alternative: use triggers)."""
        cursor = self.db.execute("""
            SELECT * FROM messages 
            WHERE recipient = ? 
            AND processed = FALSE 
            ORDER BY timestamp ASC
        """, (recipient,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append(AgentMessage(
                id=row[0],
                sender=row[1],
                recipient=row[2],
                message_type=row[3],
                payload=json.loads(row[4]),
                timestamp=datetime.fromisoformat(row[5]),
                trace_id=row[6]
            ))
        
        return messages
    
    def mark_processed(self, message_id):
        """Acknowledge message processing."""
        self.db.execute("""
            UPDATE messages 
            SET processed = TRUE 
            WHERE id = ?
        """, (message_id,))
        self.db.commit()
```

---

## Next Steps

Continue to:
- **Part 4:** Learning Pipeline Details
- **Part 5:** Deployment & Operations
