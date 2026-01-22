"""
Unit tests for Semantic Memory (Tier 3).
"""
import pytest
import os
import json
from pathlib import Path
from backend.memory.stores.semantic import SemanticMemory

@pytest.fixture
def temp_db(tmp_path):
    """Fixture for a temporary database path."""
    db_path = tmp_path / "test_memory.db"
    return str(db_path)

def test_semantic_memory_init(temp_db):
    """Test initialization of SemanticMemory."""
    memory = SemanticMemory(db_path=temp_db)
    assert memory.count == 0
    assert os.path.exists(temp_db)

def test_add_pattern(temp_db):
    """Test adding a pattern to semantic memory."""
    memory = SemanticMemory(db_path=temp_db)
    
    metadata = {
        "domain": "testing",
        "pattern_name": "test_pattern",
        "description": "A test pattern for unit testing",
        "example_code": "print('hello')",
        "example_context": {"key": "value"}
    }
    
    pattern_id = memory.add_pattern(
        text="test_pattern: A test pattern for unit testing",
        metadata=metadata
    )
    
    assert pattern_id > 0
    assert memory.count == 1
    assert memory.id_map[0] == pattern_id

def test_retrieve_similar(temp_db):
    """Test semantic retrieval."""
    memory = SemanticMemory(db_path=temp_db)
    
    # Add two different patterns
    memory.add_pattern(
        text="Authentication: How to handle user login and passwords",
        metadata={"domain": "security", "pattern_name": "Auth"}
    )
    memory.add_pattern(
        text="Data Visualization: Plotting graphs and charts",
        metadata={"domain": "data_science", "pattern_name": "Viz"}
    )
    
    # Search for something related to login
    results = memory.retrieve(query="login help", k=1)
    
    assert len(results) == 1
    assert results[0]["pattern_name"] == "Auth"
    assert results[0]["domain"] == "security"

def test_retrieve_with_domain_filter(temp_db):
    """Test hybrid search with domain filtering."""
    memory = SemanticMemory(db_path=temp_db)
    
    memory.add_pattern(
        text="Pattern A",
        metadata={"domain": "domain_1", "pattern_name": "A"}
    )
    memory.add_pattern(
        text="Pattern B",
        metadata={"domain": "domain_2", "pattern_name": "B"}
    )
    
    # Search without filter
    results = memory.retrieve(query="Pattern", k=2)
    assert len(results) == 2
    
    # Search with domain filter
    results_f = memory.retrieve(query="Pattern", domain="domain_1", k=2)
    assert len(results_f) == 1
    assert results_f[0]["pattern_name"] == "A"

def test_persistence(temp_db):
    """Test that data persists and index is rebuilt on startup."""
    # First instance: add data
    memory = SemanticMemory(db_path=temp_db)
    memory.add_pattern(
        text="Persistent Pattern",
        metadata={"domain": "general", "pattern_name": "P1"}
    )
    del memory
    
    # Second instance: load data
    memory2 = SemanticMemory(db_path=temp_db)
    assert memory2.count == 1
    
    results = memory2.retrieve(query="Persistent", k=1)
    assert len(results) == 1
    assert results[0]["pattern_name"] == "P1"

def test_guardrails(temp_db):
    """Test guardrail storage and retrieval."""
    memory = SemanticMemory(db_path=temp_db)
    
    memory.add_guardrail(
        rule_type="security",
        rule_text="No hardcoded secrets",
        enforcement_level="block",
        valid_examples=["api_key = os.getenv('KEY')"],
        invalid_examples=["api_key = '12345'"]
    )
    
    guardrails = memory.get_active_guardrails(rule_type="security")
    assert len(guardrails) == 1
    assert guardrails[0]["rule_text"] == "No hardcoded secrets"
    assert "api_key = '12345'" in guardrails[0]["invalid_examples"]
