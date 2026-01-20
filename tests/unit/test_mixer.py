import json
import pytest
from pathlib import Path
from backend.learning.mixer import DatasetMixer

@pytest.fixture
def sample_data(tmp_path):
    basal_path = tmp_path / "basal.json"
    curriculum_path = tmp_path / "curriculum.json"
    
    basal_data = [{"instruction": f"Basal {i}", "metadata": {"task_id": f"golden_{i}"}} for i in range(10)]
    curriculum_data = [{"instruction": f"Curriculum {i}"} for i in range(14)]
    
    with open(basal_path, "w") as f:
        json.dump(basal_data, f)
    with open(curriculum_path, "w") as f:
        json.dump(curriculum_data, f)
        
    return basal_path, curriculum_path

def test_mixer_ratio_calculation(sample_data, tmp_path):
    basal_path, curriculum_path = sample_data
    mixer = DatasetMixer(basal_path=basal_path)
    output_path = tmp_path / "mixed.json"
    
    # 14 curriculum items, 0.7 ratio -> 20 total -> 6 basal items
    mixed = mixer.mix_datasets(
        curriculum_path=curriculum_path,
        output_path=output_path,
        curriculum_ratio=0.7
    )
    
    assert len(mixed) == 20
    basal_count = sum(1 for item in mixed if "golden" in str(item.get("metadata", {}).get("task_id", "")))
    assert basal_count == 6
    assert output_path.exists()

def test_mixer_oversampling(sample_data, tmp_path):
    basal_path, curriculum_path = sample_data
    # Use only 2 basal items
    small_basal = tmp_path / "small_basal.json"
    with open(small_basal, "w") as f:
        json.dump([{"instruction": "B1", "metadata": {"task_id": "golden_1"}}, 
                   {"instruction": "B2", "metadata": {"task_id": "golden_2"}}], f)
                   
    mixer = DatasetMixer(basal_path=small_basal)
    
    # 14 curriculum -> needs 6 basal. 6 > 2, so must oversample.
    mixed = mixer.mix_datasets(curriculum_path=curriculum_path, curriculum_ratio=0.7)
    
    assert len(mixed) == 20
    basal_items = [item for item in mixed if "golden" in str(item.get("metadata", {}).get("task_id", ""))]
    assert len(basal_items) == 6
