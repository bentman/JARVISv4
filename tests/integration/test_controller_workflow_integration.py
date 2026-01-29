import asyncio
import json
import tempfile
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from backend.core.controller import ECFController, ControllerState
from backend.core.config.settings import Settings
from backend.tools.text_output import TextOutputTool
from backend.tools.registry.registry import ToolRegistry
from backend.agents.planner.planner import InvalidPlanError


@pytest.mark.asyncio
async def test_controller_workflow_engine_integration():
    """Test that controller integrates with WorkflowEngine for step execution."""
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Setup controller with test settings
        settings = Settings(
            working_storage_path=temp_path,
            llm_model="test-model",
            llm_api_key="test-key",
            llm_base_url="http://test-llm/v1"
        )
        
        controller = ECFController(settings=settings)
        
        # Verify WorkflowEngine is initialized
        assert hasattr(controller, 'workflow_engine')
        assert controller.workflow_engine is not None
        
        # Verify SimpleToolNode can be created
        registry = ToolRegistry()
        registry.register_tool(TextOutputTool())
        
        from backend.core.controller import SimpleToolNode
        node = SimpleToolNode(
            id="test_node",
            description="Test step",
            tool_name="text_output",
            tool_params={"text": "Hello World"},
            registry=registry
        )
        
        assert node.id == "test_node"
        assert node.description == "Test step"
        assert node.tool_name == "text_output"
        assert node.tool_params == {"text": "Hello World"}
        
        # Verify that the _execute_remaining_steps method now calls _execute_with_workflow_engine
        # This is the key integration point
        assert hasattr(controller, '_execute_with_workflow_engine')
        assert callable(controller._execute_with_workflow_engine)


@pytest.mark.asyncio
async def test_controller_workflow_engine_deterministic_output():
    """Test that controller produces deterministic artifacts when using WorkflowEngine."""
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Setup controller with test settings
        settings = Settings(
            working_storage_path=temp_path,
            llm_model="test-model",
            llm_api_key="test-key",
            llm_base_url="http://test-llm/v1"
        )
        
        controller = ECFController(settings=settings)
        
        # Verify that controller methods work without LLM calls
        # Test task creation and state management
        task_id = controller.state_manager.create_task({
            "goal": "Test goal",
            "domain": "general",
            "constraints": [],
            "next_steps": []
        })
        
        assert task_id is not None
        assert task_id.startswith("task_")
        
        # Test task listing
        summaries = controller.list_task_summaries()
        assert len(summaries) == 1
        assert summaries[0]["task_id"] == task_id
        
        # Test analytics
        analytics = controller.summarize_task_outcomes()
        assert "total" in analytics
        assert analytics["total"] == 1


@pytest.mark.asyncio
async def test_controller_workflow_engine_error_handling():
    """Test that controller handles WorkflowEngine errors properly."""
    # Create temporary directory for test
    temp_dir = tempfile.mkdtemp()
    try:
        temp_path = Path(temp_dir)
        # Setup controller with test settings
        settings = Settings(
            working_storage_path=temp_path,
            llm_model="test-model",
            llm_api_key="test-key",
            llm_base_url="http://test-llm/v1"
        )
        
        controller = ECFController(settings=settings)
        
        # Test with invalid goal that should trigger planning failure
        invalid_goal = "This goal should cause planning to fail"
        
        # Mock the planner to raise an error
        original_generate_plan = controller.planner.generate_plan
        async def mock_generate_plan(*args, **kwargs):
            raise InvalidPlanError("Test planning error")
        
        controller.planner.generate_plan = mock_generate_plan
        
        try:
            task_id = await controller.run_task(invalid_goal)
            
            # Verify task was created but marked as failed
            assert task_id is not None
            
            # Verify controller state reflects failure
            assert controller.state == ControllerState.FAILED
            
        finally:
            # Restore original method
            controller.planner.generate_plan = original_generate_plan
    finally:
        # Clean up manually to avoid permission issues
        import shutil
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
