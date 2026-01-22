"""
Regression Suite for JARVISv4.
Evaluates candidate models against historically successful task traces.
Enforces a minimum pass rate for deployment promotion.
"""
import logging
import sqlite3
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from backend.core.llm.provider import OpenAIProvider
from backend.core.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class RegressionSuite:
    """
    Validates that a new adapter or model version preserves existing 
    capabilities and doesn't regress on critical 'Golden Path' workflows.
    """
    
    def __init__(self, min_pass_rate: float = 0.95):
        self.min_pass_rate = min_pass_rate

    async def _mine_successful_episodes(self, db_path: Path) -> List[Dict[str, Any]]:
        """
        Extracts successful tasks from the SQLite store to build a test set.
        """
        if not db_path.exists():
            logger.warning(f"Database not found at {db_path}")
            return []

        episodes = []
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT metadata FROM memory_items")
                rows = cursor.fetchall()
                
                for row in rows:
                    try:
                        metadata = json.loads(row[0])
                        # A successful task has status 'COMPLETED'
                        if metadata.get("status") == "COMPLETED":
                            goal = metadata.get("goal")
                            completed_steps = metadata.get("completed_steps", [])
                            
                            if goal and completed_steps:
                                # Use the last step's artifact as the expected output
                                expected_output = completed_steps[-1].get("artifact")
                                episodes.append({
                                    "input": goal,
                                    "expected": expected_output
                                })
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        logger.debug(f"Skipping malformed memory item: {e}")
                        continue
        except sqlite3.Error as e:
            logger.error(f"Error mining episodes from SQLite: {e}")
            
        logger.info(f"Mined {len(episodes)} successful episodes from {db_path}")
        for i, ep in enumerate(episodes):
            logger.info(f"Mined Episode {i+1}: Input='{ep['input']}', Expected='{ep['expected']}'")
        return episodes

    async def _matches_expected(
        self, 
        input_text: str, 
        expected: str, 
        actual: str, 
        judge_provider: BaseLLMProvider
    ) -> bool:
        """
        Uses an LLM judge to determine if the actual output matches the expected one semantically.
        """
        prompt = f"""
Goal: {input_text}
Expected Output: {expected}
Actual Output: {actual}

Evaluate if the Actual Output satisfies the Goal and is semantically equivalent to or better than the Expected Output.
Consider technical correctness and whether the core objective was achieved.

        Respond with exactly one word: YES if it matches/exceeds, NO otherwise.
"""
        logger.info(f"JUDGE PROMPT:\n{prompt}")
        try:
            response = await judge_provider.generate(prompt)
            logger.info(f"JUDGE RESPONSE: {response}")
            decision = response.strip().upper()
            return "YES" in decision
        except Exception as e:
            logger.error(f"Error during LLM judging: {e}")
            return False

    async def run_evaluation(
        self, 
        model_provider: BaseLLMProvider, 
        db_path: Path,
        judge_provider: Optional[BaseLLMProvider] = None
    ) -> Dict[str, Any]:
        """
        Executes evaluation of a candidate model against mined successful episodes.
        
        Args:
            model_provider: The LLM provider for the model being tested.
            db_path: Path to the SQLite database containing historical data.
            judge_provider: Optional provider for the judge. If None, uses model_provider.
            
        Returns:
            Dict containing pass/fail status, scores, and detailed metrics.
        """
        logger.info(f"Starting regression evaluation using DB: {db_path}")
        
        episodes = await self._mine_successful_episodes(db_path)
        
        if not episodes:
            return {
                "status": "SKIPPED",
                "pass_rate": 0.0,
                "promoted": False,
                "metrics": {"total_tests": 0, "passed": 0, "failed": 0},
                "notes": "No successful episodes found in history."
            }

        passed = 0
        total = len(episodes)
        judge = judge_provider or model_provider
        
        results = []
        for i, episode in enumerate(episodes):
            logger.info(f"Running test case {i+1}/{total}: {episode['input'][:50]}...")
            
            actual_output = await model_provider.generate(episode['input'])
            is_match = await self._matches_expected(
                episode['input'], 
                episode['expected'], 
                actual_output, 
                judge
            )
            
            if is_match:
                passed += 1
                logger.info(f"  ✅ Test case {i+1} passed")
            else:
                logger.warning(f"  ✗ Test case {i+1} failed")
                
            results.append({
                "input": episode['input'],
                "expected": episode['expected'],
                "actual": actual_output,
                "passed": is_match
            })

        pass_rate = passed / total
        is_promoted = pass_rate >= self.min_pass_rate
        
        result = {
            "status": "PASSED" if is_promoted else "FAILED",
            "pass_rate": pass_rate,
            "threshold": self.min_pass_rate,
            "promoted": is_promoted,
            "metrics": {
                "total_tests": total,
                "passed": passed,
                "failed": total - passed
            },
            "results": results
        }
        
        if is_promoted:
            logger.info(f"✅ Regression PASSED (Score: {pass_rate:.2%})")
        else:
            logger.error(f"❌ Regression FAILED (Score: {pass_rate:.2%})")
            
        return result
