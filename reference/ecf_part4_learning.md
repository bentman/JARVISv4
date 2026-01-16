# ECF Implementation Plan - Part 4: Learning Pipeline & Fine-Tuning

## Overview

The explicit learning loop transforms execution experience into permanent capability improvements through targeted fine-tuning. This replaces the "prompt gets longer" anti-pattern with weight updates.

---

## I. Complete Learning Pipeline

```
┌──────────────────────────────────────────────────────────┐
│ Stage 1: Episode Capture                                 │
│ → Every task execution becomes training candidate        │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 2: Quality Filtering                               │
│ → Multi-gate admission (success, tests, no violations)   │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 3: Dataset Extraction                              │
│ → Convert to instruction-following format (Alpaca-style) │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 4: Catastrophic Forgetting Prevention              │
│ → Mix curriculum (70%) with basal dataset (30%)          │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 5: Unsloth Fine-Tuning                            │
│ → LoRA/QLoRA training on consumer hardware              │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 6: Gated Deployment                                │
│ → Regression suite → Smoke tests → Security checks       │
└──────────────────────────────────────────────────────────┘
```

---

## II. Stage 1: Episode Capture

### Complete Trace Extraction

```python
class EpisodeCaptureSystem:
    """
    Extracts complete execution traces for training dataset construction.
    """
    
    def __init__(self, memory_system):
        self.memory = memory_system
    
    def capture_episode(self, task_id):
        """
        Extract everything that happened during task execution.
        """
        # Get all decisions
        decisions = self.memory.episodic.get_task_history(task_id)
        
        # Get tool transcripts
        transcripts = self._get_tool_transcripts(task_id)
        
        # Get final artifacts
        artifacts = self._get_artifacts(task_id)
        
        # Get validation events
        validations = self._get_validations(task_id)
        
        # Classify outcome
        outcome = self._classify_outcome(decisions, validations)
        
        # Score quality
        quality_score = self._score_quality(
            decisions, 
            validations, 
            artifacts
        )
        
        return Episode(
            task_id=task_id,
            decisions=decisions,
            transcripts=transcripts,
            artifacts=artifacts,
            validations=validations,
            outcome=outcome,
            quality_score=quality_score,
            captured_at=datetime.now()
        )
    
    def _get_tool_transcripts(self, task_id):
        """Get all tool invocations for this task."""
        cursor = self.memory.episodic.db.execute("""
            SELECT tc.* 
            FROM tool_calls tc
            JOIN decisions d ON tc.decision_id = d.id
            WHERE d.task_id = ?
            ORDER BY tc.timestamp
        """, (task_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_artifacts(self, task_id):
        """Collect all created artifacts."""
        artifacts = {
            "files": [],
            "data": {},
            "metrics": {}
        }
        
        decisions = self.memory.episodic.get_task_history(task_id)
        for decision in decisions:
            created = json.loads(decision.get("artifacts_created", "{}"))
            
            if "files" in created:
                artifacts["files"].extend(created["files"])
            
            if "data" in created:
                artifacts["data"].update(created["data"])
        
        return artifacts
    
    def _get_validations(self, task_id):
        """Get all validation events."""
        cursor = self.memory.episodic.db.execute("""
            SELECT v.* 
            FROM validations v
            JOIN decisions d ON v.decision_id = d.id
            WHERE d.task_id = ?
            ORDER BY v.timestamp
        """, (task_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def _classify_outcome(self, decisions, validations):
        """Determine final task outcome."""
        final_decision = decisions[-1] if decisions else None
        
        if not final_decision:
            return "incomplete"
        
        if final_decision["outcome"] == "success":
            # Check if all validations passed
            all_passed = all(v["passed"] for v in validations)
            return "success" if all_passed else "partial_success"
        
        return "failure"
    
    def _score_quality(self, decisions, validations, artifacts):
        """
        Multi-factor quality assessment.
        Returns float 0.0-1.0
        """
        score = 1.0
        
        # Factor 1: Retry penalty
        retry_count = sum(1 for d in decisions if d["outcome"] == "retry")
        score *= max(0, 1 - 0.1 * retry_count)
        
        # Factor 2: Validation failure penalty
        validation_failures = sum(1 for v in validations if not v["passed"])
        score *= max(0, 1 - 0.15 * validation_failures)
        
        # Factor 3: Error penalty
        error_count = sum(1 for d in decisions if d["error_message"])
        score *= max(0, 1 - 0.2 * error_count)
        
        # Factor 4: Test coverage bonus
        has_tests = any("test" in f for f in artifacts.get("files", []))
        if has_tests:
            score *= 1.2
        
        # Factor 5: Clean execution bonus
        clean = all(d["error_message"] is None for d in decisions)
        if clean:
            score *= 1.1
        
        # Factor 6: Completeness bonus
        if len(decisions) >= 3:  # Multi-step task
            score *= 1.05
        
        return min(score, 1.0)
```

---

## III. Stage 2: Quality Filtering

### Multi-Gate Admission

```python
class QualityFilter:
    """
    Multi-layered filtering for training dataset admission.
    Only high-quality episodes become training data.
    """
    
    def __init__(self, guardrails):
        self.guardrails = guardrails
        self.filters = [
            self._gate_outcome,
            self._gate_quality_score,
            self._gate_security,
            self._gate_deterministic_tests,
            self._gate_novelty
        ]
    
    def filter_episodes(self, episodes, min_quality=0.8):
        """
        Apply all gates sequentially.
        Episode must pass ALL gates to be admitted.
        """
        admitted = []
        rejected = []
        
        for episode in episodes:
            passed = True
            rejection_reason = None
            
            for gate in self.filters:
                gate_result = gate(episode, min_quality, admitted)
                if not gate_result.passed:
                    passed = False
                    rejection_reason = gate_result.reason
                    break
            
            if passed:
                admitted.append(episode)
            else:
                rejected.append((episode, rejection_reason))
        
        return admitted, rejected
    
    def _gate_outcome(self, episode, min_quality, admitted):
        """Gate 1: Must be successful."""
        if episode.outcome != "success":
            return FilterResult(False, "outcome_not_success")
        return FilterResult(True)
    
    def _gate_quality_score(self, episode, min_quality, admitted):
        """Gate 2: Quality score threshold."""
        if episode.quality_score < min_quality:
            return FilterResult(
                False, 
                f"quality_too_low: {episode.quality_score:.2f} < {min_quality}"
            )
        return FilterResult(True)
    
    def _gate_security(self, episode, min_quality, admitted):
        """Gate 3: No security violations."""
        violations = self._detect_security_violations(episode)
        
        if violations:
            return FilterResult(
                False, 
                f"security_violations: {', '.join(violations)}"
            )
        return FilterResult(True)
    
    def _gate_deterministic_tests(self, episode, min_quality, admitted):
        """Gate 4: Passes deterministic checks."""
        # Check for common issues
        for decision in episode.decisions:
            # No secrets in output
            if self._contains_secrets(decision["action_taken"]):
                return FilterResult(False, "contains_secrets")
            
            # No PII
            if self._contains_pii(decision["action_taken"]):
                return FilterResult(False, "contains_pii")
            
            # Valid JSON/YAML (if structured output)
            if not self._validate_structure(decision["action_taken"]):
                return FilterResult(False, "malformed_output")
        
        return FilterResult(True)
    
    def _gate_novelty(self, episode, min_quality, admitted):
        """Gate 5: Not duplicate of existing examples."""
        # Check against already-admitted examples
        for existing in admitted:
            similarity = self._calculate_similarity(episode, existing)
            if similarity > 0.95:
                return FilterResult(False, "duplicate_pattern")
        
        return FilterResult(True)
    
    def _detect_security_violations(self, episode):
        """Check for common security issues."""
        violations = []
        
        for decision in episode.decisions:
            action = decision["action_taken"]
            
            # Check against security guardrails
            for guardrail in self.guardrails.get_active_guardrails("security"):
                if self._violates_guardrail(action, guardrail):
                    violations.append(guardrail["rule_text"])
        
        return violations
    
    def _contains_secrets(self, text):
        """Detect API keys, passwords, tokens."""
        secret_patterns = [
            r'[A-Za-z0-9]{32,}',  # Long hex strings
            r'sk-[A-Za-z0-9]{48}',  # OpenAI API keys
            r'ghp_[A-Za-z0-9]{36}',  # GitHub tokens
            r'password\s*[:=]\s*["\']?[\w!@#$%^&*]+',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_pii(self, text):
        """Detect personally identifiable information."""
        # Email addresses
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            return True
        
        # Phone numbers
        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
            return True
        
        # SSN patterns
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):
            return True
        
        return False


@dataclass
class FilterResult:
    passed: bool
    reason: str = None
```

---

## IV. Stage 3: Dataset Extraction

### Instruction-Following Format

```python
class DatasetExtractor:
    """
    Converts episodes into instruction-following training examples.
    Formats as Alpaca-style tuples.
    """
    
    def extract_training_examples(self, episodes):
        """
        Transform episodes into (instruction, input, output) tuples.
        """
        all_examples = []
        
        for episode in episodes:
            examples = self._extract_from_episode(episode)
            all_examples.extend(examples)
        
        # Sanitize
        sanitized = self._sanitize_examples(all_examples)
        
        return sanitized
    
    def _extract_from_episode(self, episode):
        """Extract training tuple from each decision in episode."""
        examples = []
        
        for i, decision in enumerate(episode.decisions):
            context = json.loads(decision["context_snapshot"])
            
            # Build instruction (what agent was asked to do)
            instruction = self._build_instruction(context, decision)
            
            # Build input (context provided)
            input_data = self._build_input(context, i)
            
            # Output (what agent did)
            output = decision["action_taken"]
            
            # Metadata
            metadata = {
                "task_id": episode.task_id,
                "step_index": i,
                "agent_role": decision["agent"],
                "domain": context.get("task", {}).get("domain"),
                "timestamp": decision["timestamp"],
                "quality_score": episode.quality_score
            }
            
            example = {
                "instruction": instruction,
                "input": input_data,
                "output": output,
                "metadata": metadata
            }
            
            examples.append(example)
        
        return examples
    
    def _build_instruction(self, context, decision):
        """Create clear instruction based on agent role."""
        role = decision["agent"]
        task = context.get("task", {})
        
        if role == "planner":
            return f"Decompose this goal into executable sub-tasks: {task.get('goal')}"
        
        elif role == "executor":
            step = task.get("current_step", {})
            return f"Execute this task: {step.get('description')}"
        
        elif role == "critic":
            return "Validate if the output meets all requirements."
        
        return task.get("goal", "Complete the task")
    
    def _build_input(self, context, step_index):
        """Format context as input field."""
        task = context.get("task", {})
        history = context.get("history", [])
        
        input_dict = {
            "constraints": task.get("constraints", []),
            "domain": task.get("domain"),
        }
        
        # Include relevant history (last 3 steps only)
        if history:
            input_dict["previous_steps"] = [
                {
                    "action": h.get("action_taken"),
                    "outcome": h.get("outcome")
                }
                for h in history[-3:]
            ]
        
        # For executor, include available tools
        if context.get("agent") == "executor":
            input_dict["available_tools"] = context.get("tools", [])
        
        return json.dumps(input_dict, indent=2)
    
    def _sanitize_examples(self, examples):
        """Remove sensitive information."""
        sanitizers = [
            EmailSanitizer(),
            SecretsSanitizer(),
            FilePathSanitizer(),  # Replace absolute paths
            TimestampNormalizer()  # Normalize timestamps
        ]
        
        sanitized = []
        for example in examples:
            clean_example = example.copy()
            
            for sanitizer in sanitizers:
                clean_example = sanitizer.process(clean_example)
            
            sanitized.append(clean_example)
        
        return sanitized


class EmailSanitizer:
    def process(self, example):
        """Replace emails with placeholder."""
        example = example.copy()
        
        for field in ["instruction", "input", "output"]:
            if field in example:
                example[field] = re.sub(
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    'user@example.com',
                    example[field]
                )
        
        return example


class SecretsSanitizer:
    def process(self, example):
        """Replace API keys, tokens with placeholder."""
        example = example.copy()
        
        patterns = {
            r'sk-[A-Za-z0-9]{48}': 'sk-REDACTED',
            r'ghp_[A-Za-z0-9]{36}': 'ghp_REDACTED',
            r'[A-Za-z0-9]{32,}': 'TOKEN_REDACTED'
        }
        
        for field in ["instruction", "input", "output"]:
            if field in example:
                text = example[field]
                for pattern, replacement in patterns.items():
                    text = re.sub(pattern, replacement, text)
                example[field] = text
        
        return example
```

---

## V. Stage 4: Catastrophic Forgetting Prevention

### Basal Dataset Mixing

```python
class BasalDatasetManager:
    """
    Maintains general instruction-following capability during fine-tuning.
    Mixes task-specific curriculum with general examples.
    """
    
    def __init__(self, basal_dataset_path):
        self.basal_examples = self._load_basal_dataset(basal_dataset_path)
        
    def _load_basal_dataset(self, path):
        """
        Load curated general instruction-following examples.
        Sources: Alpaca, Dolly, FLAN, custom curated examples.
        """
        with open(path, 'r') as f:
            if path.endswith('.jsonl'):
                examples = [json.loads(line) for line in f]
            else:
                examples = json.load(f)
        
        return examples
    
    def mix_datasets(self, curriculum, ratio=0.7):
        """
        Blend curriculum (task-specific) with basal (general).
        
        Args:
            curriculum: Task-specific training examples
            ratio: Proportion of curriculum (0.7 = 70% curriculum, 30% basal)
        
        Returns:
            Mixed dataset
        """
        # Calculate sizes
        curriculum_size = len(curriculum)
        basal_size = int(curriculum_size * (1 - ratio) / ratio)
        
        # Sample from basal dataset
        if basal_size > len(self.basal_examples):
            # Oversample if needed
            basal_sample = random.choices(self.basal_examples, k=basal_size)
        else:
            basal_sample = random.sample(self.basal_examples, k=basal_size)
        
        # Combine and shuffle
        mixed = curriculum + basal_sample
        random.shuffle(mixed)
        
        return mixed
    
    def create_domain_specific_basal(self, domain, size=1000):
        """
        Create domain-specific basal subset.
        Helps preserve domain knowledge while learning new tasks.
        """
        # Filter basal examples by domain
        domain_examples = [
            ex for ex in self.basal_examples
            if domain.lower() in ex.get("instruction", "").lower()
            or domain.lower() in ex.get("input", "").lower()
        ]
        
        if len(domain_examples) < size:
            # Add random general examples
            additional = random.sample(
                self.basal_examples, 
                size - len(domain_examples)
            )
            domain_examples.extend(additional)
        
        return domain_examples[:size]
```

### Regression Suite

```python
class RegressionSuite:
    """
    Test suite derived from previously-solved tasks.
    New adapters must maintain performance on past tasks.
    """
    
    def __init__(self, memory_system):
        self.memory = memory_system
        self.test_cases = self._build_test_suite()
    
    def _build_test_suite(self, size=50):
        """
        Mine decision log for diverse, successful tasks.
        Ensures coverage across domains and task types.
        """
        # Get successful tasks across domains
        cursor = self.memory.episodic.db.execute("""
            SELECT DISTINCT 
                d.task_id,
                json_extract(d.context_snapshot, '$.task.goal') as goal,
                json_extract(d.context_snapshot, '$.task.domain') as domain,
                COUNT(*) as step_count
            FROM decisions d
            WHERE d.outcome = 'success'
            AND d.validation_status = 'passed'
            GROUP BY d.task_id, domain
            HAVING step_count >= 3
            ORDER BY RANDOM()
        """)
        
        candidates = cursor.fetchall()
        
        # Stratified sampling by domain
        test_cases_by_domain = {}
        for task_id, goal, domain, step_count in candidates:
            if domain not in test_cases_by_domain:
                test_cases_by_domain[domain] = []
            
            test_case = self._create_test_case(task_id, goal, domain)
            test_cases_by_domain[domain].append(test_case)
        
        # Balance across domains
        test_cases = []
        domains = list(test_cases_by_domain.keys())
        per_domain = size // len(domains) if domains else 0
        
        for domain in domains:
            test_cases.extend(test_cases_by_domain[domain][:per_domain])
        
        return test_cases[:size]
    
    def _create_test_case(self, task_id, goal, domain):
        """Build test case from historical task."""
        # Get first decision (input)
        decisions = self.memory.episodic.get_task_history(task_id, limit=1)
        first_decision = decisions[0]
        
        # Get final decision (expected output pattern)
        final_decisions = self.memory.episodic.get_task_history(task_id)
        final_decision = final_decisions[-1]
        
        return TestCase(
            task_id=task_id,
            goal=goal,
            domain=domain,
            prompt=self._build_test_prompt(first_decision),
            expected_pattern=self._extract_pattern(final_decision),
            validation_criteria=self._extract_validation(task_id)
        )
    
    def test_adapter(self, adapter_path):
        """
        Run all test cases against new adapter.
        Returns pass rate (0.0-1.0).
        """
        model = self._load_model_with_adapter(adapter_path)
        
        passed = 0
        failed_cases = []
        
        for test_case in self.test_cases:
            result = model.generate(test_case.prompt, max_tokens=1000)
            
            if self._matches_expected(result, test_case):
                passed += 1
            else:
                failed_cases.append((test_case, result))
        
        pass_rate = passed / len(self.test_cases)
        
        return RegressionResult(
            pass_rate=pass_rate,
            passed=passed,
            failed=len(failed_cases),
            failed_cases=failed_cases
        )
    
    def _matches_expected(self, result, test_case):
        """Check if result matches expected pattern."""
        # Flexible matching (not exact string match)
        # Check for key elements in expected pattern
        pattern = test_case.expected_pattern
        
        # Extract key actions
        expected_actions = pattern.get("actions", [])
        result_lower = result.lower()
        
        matched_actions = sum(
            1 for action in expected_actions
            if action.lower() in result_lower
        )
        
        # Require 80% of key actions present
        match_threshold = 0.8
        return (matched_actions / len(expected_actions)) >= match_threshold
```

---

## VI. Stage 5: Unsloth Fine-Tuning

```python
from unsloth import FastLanguageModel, TrainingArguments, SFTTrainer
from datasets import Dataset

class UnslothTrainer:
    """
    Wrapper for Unsloth fine-tuning with ECF-specific configuration.
    Optimized for consumer hardware and local-first deployment.
    """
    
    def __init__(self, config):
        self.config = config
        self.base_model = config.base_model
        
    def train(self, dataset, output_dir):
        """
        Execute fine-tuning cycle with guard-railed settings.
        """
        logger.info(f"Starting fine-tuning on {len(dataset)} examples")
        
        # Load model with 4-bit quantization
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.base_model,
            max_seq_length=2048,
            dtype=None,  # Auto-detect (bfloat16 on modern GPUs)
            load_in_4bit=True
        )
        
        logger.info("Model loaded with 4-bit quantization")
        
        # Configure LoRA
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,  # LoRA rank (balance capacity vs forgetting)
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"
            ],
            lora_alpha=16,
            lora_dropout=0.05,
            bias="none",
            use_gradient_checkpointing="unsloth",  # Unsloth optimization
            random_state=42
        )
        
        logger.info("LoRA adapters configured")
        
        # Prepare dataset
        formatted_dataset = self._format_dataset(dataset, tokenizer)
        
        # Training arguments
        args = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,  # Effective batch size: 16
            warmup_steps=10,
            max_steps=500,  # Adjust based on dataset size
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10,
            optim="adamw_8bit",  # Memory-efficient optimizer
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=42,
            save_strategy="steps",
            save_steps=100,
            save_total_limit=3  # Keep only 3 checkpoints
        )
        
        logger.info(f"Training for {args.max_steps} steps")
        
        # Create trainer
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=formatted_dataset,
            args=args,
            dataset_text_field="text",
            max_seq_length=2048,
            packing=False  # Don't pack examples (maintain clarity)
        )
        
        # Train
        trainer.train()
        
        logger.info("Training completed")
        
        # Save adapter
        adapter_path = f"{output_dir}/final_adapter"
        model.save_pretrained(adapter_path)
        tokenizer.save_pretrained(adapter_path)
        
        logger.info(f"Adapter saved to {adapter_path}")
        
        return adapter_path
    
    def _format_dataset(self, examples, tokenizer):
        """
        Convert examples to Unsloth-compatible format.
        Uses Llama chat template.
        """
        formatted = []
        
        for ex in examples:
            # Combine instruction and input
            prompt = ex["instruction"]
            if ex.get("input"):
                prompt += f"\n\nInput:\n{ex['input']}"
            
            # Format as chat
            text = tokenizer.apply_chat_template(
                [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": ex["output"]}
                ],
                tokenize=False,
                add_generation_prompt=False
            )
            
            formatted.append({"text": text})
        
        return Dataset.from_list(formatted)
```

---

## VII. Stage 6: Gated Deployment

```python
class AdapterDeploymentPipeline:
    """
    Safe promotion from training to production.
    Multi-gate validation with automatic rollback.
    """
    
    def __init__(self, regression_suite, config):
        self.regression_suite = regression_suite
        self.config = config
        self.adapters_dir = Path("./adapters")
        self.adapters_dir.mkdir(exist_ok=True)
        
    def deploy_adapter(self, adapter_path, version):
        """
        Multi-gate deployment with safety checks.
        """
        logger.info(f"Deploying adapter {version}")
        
        # Gate 1: Regression suite
        logger.info("Running regression suite...")
        regression_result = self.regression_suite.test(adapter_path)
        
        if regression_result.pass_rate < 0.95:
            logger.error(f"Regression detected: {regression_result.pass_rate:.2%}")
            return DeploymentResult(
                status="rejected",
                reason="regression_failure",
                details=f"Pass rate: {regression_result.pass_rate:.2%}",
                failed_cases=regression_result.failed_cases
            )
        
        logger.info(f"Regression suite passed: {regression_result.pass_rate:.2%}")
        
        # Gate 2: Smoke tests
        logger.info("Running smoke tests...")
        if not self._run_smoke_tests(adapter_path):
            return DeploymentResult(
                status="rejected",
                reason="smoke_test_failure"
            )
        
        logger.info("Smoke tests passed")
        
        # Gate 3: Security validation
        logger.info("Running security checks...")
        if not self._validate_security(adapter_path):
            return DeploymentResult(
                status="rejected",
                reason="security_check_failure"
            )
        
        logger.info("Security checks passed")
        
        # All gates passed—deploy
        self._version_adapter(adapter_path, version)
        self._update_current_symlink(version)
        self._log_deployment(version, regression_result)
        
        logger.info(f"Adapter {version} deployed successfully")
        
        return DeploymentResult(
            status="deployed",
            version=version,
            regression_score=regression_result.pass_rate
        )
    
    def _version_adapter(self, adapter_path, version):
        """
        Copy adapter to versioned directory.
        Enables rollback to any previous version.
        """
        versioned_path = self.adapters_dir / version
        shutil.copytree(adapter_path, versioned_path)
        
        # Store metadata
        metadata = {
            "version": version,
            "base_model": self.config.base_model,
            "deployed_at": datetime.now().isoformat(),
            "adapter_path": str(versioned_path)
        }
        
        with open(versioned_path / "metadata.