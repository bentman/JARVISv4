import sys
import asyncio
import argparse
import logging
from backend.core.controller import ECFController

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_goal(goal: str):
    """Initialize controller and run the requested goal."""
    controller = ECFController()
    print(f"\n--- Starting ECF Task ---")
    print(f"Goal: {goal}")
    print(f"-------------------------\n")
    
    task_id = await controller.run_task(goal)
    
    print(f"\n-------------------------")
    print(f"Task Processed: {task_id}")
    print(f"Final State: {controller.state.value}")
    print(f"-------------------------\n")

def main():
    parser = argparse.ArgumentParser(description="JARVISv4 ECF CLI")
    parser.add_argument("--goal", type=str, help="The high-level goal to execute")
    
    args = parser.parse_args()
    
    if args.goal:
        try:
            asyncio.run(run_goal(args.goal))
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(1)
    else:
        print("JARVISv4 Backend initialized. Use --goal to execute a task.")
        sys.exit(0)

if __name__ == "__main__":
    main()
