import argparse
import sys
from pathlib import Path

# Add backend to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from backend.learning.train import LearnerOrchestrator

def main():
    parser = argparse.ArgumentParser(description="JARVISv4 Learning Cycle Trigger")
    parser.add_argument("--dry-run", action="store_true", help="Execute in dry-run mode (no actual training)")
    parser.add_argument("--config", type=str, default="backend/learning/config.yaml", help="Path to training config")
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
        
    try:
        orchestrator = LearnerOrchestrator(config_path)
        success = orchestrator.run_training_cycle(dry_run=args.dry_run)
        
        if success:
            print("\n✅ Learning Cycle trigger COMPLETED.")
        else:
            print("\n❌ Learning Cycle trigger FAILED or was incomplete.")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
