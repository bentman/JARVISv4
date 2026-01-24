import sys
import asyncio
import argparse
import logging
from typing import Optional

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_goal(goal: str):
    """Initialize controller and run the requested goal."""
    from backend.core.controller import ECFController
    controller = ECFController()
    print(f"\n--- Starting ECF Task ---")
    print(f"Goal: {goal}")
    print(f"-------------------------\n")
    task_id = await controller.run_task(goal)
    
    print(f"\n-------------------------")
    print(f"Task Processed: {task_id}")
    print(f"Final State: {controller.state.value}")
    print(f"-------------------------\n")


async def run_resume(task_id: str):
    """Initialize controller and resume an existing task."""
    from backend.core.controller import ECFController
    controller = ECFController()
    print(f"\n--- Resuming ECF Task ---")
    print(f"Task ID: {task_id}")
    print(f"-------------------------\n")

    resumed_task_id = await controller.resume_task(task_id)

    print(f"\n-------------------------")
    print(f"Task Processed: {resumed_task_id}")
    print(f"Final State: {controller.state.value}")
    print(f"-------------------------\n")


async def run_list_tasks(settings) -> int:
    """Print deterministic task summaries (read-only)."""
    from backend.core.controller import ECFController

    controller = ECFController(settings=settings)
    summaries = controller.list_task_summaries()
    for summary in summaries:
        print(
            "TASK "
            f"task_id={summary.get('task_id')} "
            f"lifecycle={summary.get('lifecycle')} "
            f"status={summary.get('status')} "
            f"completed_steps={summary.get('completed_steps')} "
            f"next_steps={summary.get('next_steps')} "
            f"has_current_step={summary.get('has_current_step')}"
        )
    await controller.llm.close()
    return len(summaries)

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JARVISv4 ECF CLI")
    parser.add_argument("--goal", type=str, help="The high-level goal to execute")
    parser.add_argument("--resume-task-id", type=str, help="Resume an existing task by ID")
    parser.add_argument("--list-tasks", action="store_true", help="List tasks from disk (read-only)")
    parser.add_argument("--env-file", type=str, help="Path to .env file to load")
    parser.add_argument("--llm-base-url", type=str, help="Override LLM base URL")
    parser.add_argument("--llm-model", type=str, help="Override LLM model")
    parser.add_argument("--llm-api-key", type=str, help="Override LLM API key")
    parser.add_argument("--check-llm", action="store_true", help="Run LLM connectivity check and exit")
    parser.add_argument("--llm-timeout-seconds", type=float, default=5.0, help="LLM timeout for preflight check")
    parser.add_argument("--llm-max-retries", type=int, default=0, help="LLM retries for preflight check")

    return parser.parse_args()


def _resolve_settings(args: argparse.Namespace):
    from pathlib import Path
    from backend.core.config.settings import load_settings

    env_file = Path(args.env_file) if args.env_file else None
    settings = load_settings(env_file=env_file, override_environ=True)

    if args.llm_base_url:
        settings = settings.__class__(**{**settings.__dict__, "llm_base_url": args.llm_base_url})
    if args.llm_model:
        settings = settings.__class__(**{**settings.__dict__, "llm_model": args.llm_model})
    if args.llm_api_key is not None:
        settings = settings.__class__(**{**settings.__dict__, "llm_api_key": args.llm_api_key})

    return settings


def _validate_llm_config(settings) -> Optional[str]:
    if settings.llm_provider and settings.llm_provider.lower() != "openai":
        return f"CONFIG_ERROR: Unsupported LLM_PROVIDER={settings.llm_provider}. Supported: openai"

    if not settings.llm_model:
        return "CONFIG_ERROR: LLM_MODEL is required (example: llama3.1:8b)"

    if not settings.llm_base_url:
        return "CONFIG_ERROR: LLM_BASE_URL is required (example: http://localhost:11434/v1)"

    return None


async def _check_llm(settings, timeout: float, max_retries: int) -> bool:
    from openai import (
        AsyncOpenAI,
        APIConnectionError,
        APITimeoutError,
        APIStatusError,
        BadRequestError,
        AuthenticationError,
        PermissionDeniedError
    )

    api_key = settings.llm_api_key or "sk-no-key-required"
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=settings.llm_base_url,
        timeout=timeout,
        max_retries=0
    )
    try:
        await client.models.list()
        print(f"LLM_OK base_url={settings.llm_base_url} model={settings.llm_model}")
        return True
    except APITimeoutError as err:
        category = "unreachable"
        error = err
    except APIConnectionError as err:
        category = "unreachable"
        error = err
    except BadRequestError as err:
        category = "bad_request"
        error = err
    except AuthenticationError as err:
        category = "auth"
        error = err
    except PermissionDeniedError as err:
        category = "auth"
        error = err
    except APIStatusError as err:
        category = "http_error"
        error = err
    except Exception as err:
        category = "unknown"
        error = err
    print(f"LLM_CHECK_FAILED category={category}")
    print(f"Resolved base_url={settings.llm_base_url} model={settings.llm_model}")
    print(f"Error: {type(error).__name__}: {error}")
    print("Hints: verify Ollama is running, base_url is http://localhost:11434/v1, and model exists (ollama list).")
    await client.close()
    return False


def main():
    args = _parse_args()
    
    try:
        settings = _resolve_settings(args)
    except Exception as exc:
        print(f"CONFIG_ERROR: Failed to load settings: {exc}")
        print("Hint: ensure required dependencies are installed (use backend/.venv).")
        sys.exit(2)

    try:
        if args.check_llm:
            ok = asyncio.run(_check_llm(settings, args.llm_timeout_seconds, args.llm_max_retries))
            sys.exit(0 if ok else 2)

        if args.list_tasks:
            count = asyncio.run(run_list_tasks(settings))
            print(f"TASK_SUMMARY_COUNT={count}")
            sys.exit(0)

        config_error = _validate_llm_config(settings)
        if config_error:
            print(config_error)
            sys.exit(2)

        if args.resume_task_id:
            ok = asyncio.run(_check_llm(settings, args.llm_timeout_seconds, args.llm_max_retries))
            if not ok:
                sys.exit(2)
            asyncio.run(run_resume(args.resume_task_id))
        elif args.goal:
            ok = asyncio.run(_check_llm(settings, args.llm_timeout_seconds, args.llm_max_retries))
            if not ok:
                sys.exit(2)
            asyncio.run(run_goal(args.goal))
        else:
            print("JARVISv4 Backend initialized. Use --goal to execute a task.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except ModuleNotFoundError as exc:
        print(f"DEPENDENCY_ERROR: {exc}")
        print("Hint: activate backend/.venv and install requirements.txt.")
        sys.exit(2)

if __name__ == "__main__":
    main()
