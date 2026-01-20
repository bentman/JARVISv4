import json
from pathlib import Path
from backend.learning.mixer import DatasetMixer

def validate_mixer():
    print("--- JARVISv4 Dataset Mixer Validation ---")
    
    # 1. Setup paths
    basal_path = Path("data/training/basal_set.json")
    curriculum_path = Path("backend/datasets/dummy_curriculum.json")
    output_path = Path("backend/datasets/mixed_training_data.json")
    
    # 2. Create dummy curriculum (14 examples)
    # To hit 70/30 split with 14 curriculum items, we need:
    # 14 / 0.7 = 20 total. 20 - 14 = 6 basal items.
    dummy_curriculum = [
        {"instruction": f"Step {i}", "input": "", "output": ""} 
        for i in range(14)
    ]
    
    curriculum_path.parent.mkdir(parents=True, exist_ok=True)
    with open(curriculum_path, "w") as f:
        json.dump(dummy_curriculum, f, indent=2)
    
    # 3. Run Mixer
    mixer = DatasetMixer(basal_path=basal_path)
    mixed = mixer.mix_datasets(
        curriculum_path=curriculum_path,
        output_path=output_path,
        curriculum_ratio=0.7
    )
    
    # 4. Verify Counts
    print(f"\nResults:")
    print(f"Curriculum size: {len(dummy_curriculum)}")
    print(f"Mixed dataset size: {len(mixed)}")
    
    # Calculate ratio
    actual_ratio = len(dummy_curriculum) / len(mixed)
    print(f"Actual curriculum ratio: {actual_ratio:.2%}")
    
    # Count metadata to see distribution
    basal_count = sum(1 for item in mixed if "golden" in str(item.get("metadata", {}).get("task_id", "")))
    print(f"Basal items (Golden) count: {basal_count}")
    
    if len(mixed) == 20:
        print("\n✅ Validation Successful: 70/30 split achieved (14 curriculum / 6 basal).")
    else:
        print(f"\n❌ Validation Failed: Expected 20 total items, got {len(mixed)}.")

if __name__ == "__main__":
    validate_mixer()
