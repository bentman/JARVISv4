import pytest
import sqlite3
import json
import asyncio
from pathlib import Path
from datetime import datetime, UTC

from backend.learning.regression import RegressionSuite
from backend.core.llm.provider import OpenAIProvider

@pytest.fixture
def temp_db(tmp_path):
    """Creates a temporary SQLite database with a successful task."""
    db_path = tmp_path / "test_memory.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE memory_items (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
        """)
        
        # Insert a 'Golden' task
        task_data = {
            "task_id": "golden_001",
            "goal": "Explain what 2+2 is",
            "status": "COMPLETED",
            "completed_steps": [
                {
                    "index": 0,
                    "description": "Calculate",
                    "outcome": "SUCCESS",
                    "artifact": "2+2 is 4"
                }
            ]
        }
        
        conn.execute(
            "INSERT INTO memory_items (id, content, timestamp, metadata) VALUES (?, ?, ?, ?)",
            (
                "item_001",
                "Explain what 2+2 is",
                datetime.now(UTC).isoformat(),
                json.dumps(task_data)
            )
        )
        conn.commit()
    return db_path

@pytest.mark.asyncio
async def test_regression_suite_end_to_end(temp_db):
    """
    Verifies the RegressionSuite can mine from the temp DB and evaluate using the local model.
    """
    # Initialize provider for local Ollama
    provider = OpenAIProvider(
        model="qwen2.5-coder:7b",
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    )
    
    suite = RegressionSuite(min_pass_rate=1.0)
    
    try:
        # Run evaluation
        result = await suite.run_evaluation(
            model_provider=provider,
            db_path=temp_db
        )
        
        # Assertions
        assert result["status"] == "PASSED"
        assert result["metrics"]["total_tests"] == 1
        assert result["metrics"]["passed"] == 1
        assert result["pass_rate"] == 1.0
        assert result["promoted"] is True
        
    finally:
        await provider.close()

@pytest.mark.asyncio
async def test_regression_mining_only(temp_db):
    """
    Verifies only the mining logic without calling the LLM.
    """
    suite = RegressionSuite()
    episodes = await suite._mine_successful_episodes(temp_db)
    
    assert len(episodes) == 1
    assert episodes[0]["input"] == "Explain what 2+2 is"
    assert episodes[0]["expected"] == "2+2 is 4"
