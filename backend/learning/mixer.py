"""
Dataset Mixer for JARVISv4.
Handles the 70/30 split between curated episodes (curriculum) and anchor data (basal).
Ensures uniform batch distribution via shuffling and handles oversampling if necessary.
"""
import json
import random
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class DatasetMixer:
    """
    Manages the blending of task-specific training data with general purpose
    'basal' data to prevent catastrophic forgetting.
    """
    
    def __init__(self, basal_path: Path):
        self.basal_path = Path(basal_path)
        self.basal_data = self._load_json(self.basal_path)
        
    def _load_json(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            logger.warning(f"JSON file not found at {path}. Returning empty list.")
            return []
        with open(path, "r") as f:
            return json.load(f)

    def mix_datasets(
        self, 
        curriculum_path: Path, 
        output_path: Optional[Path] = None, 
        curriculum_ratio: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Mixes curriculum data with basal data according to the specified ratio.
        
        Args:
            curriculum_path: Path to the curated episodes JSON.
            output_path: Optional path to save the mixed dataset.
            curriculum_ratio: Target proportion for curriculum data (default 0.7).
            
        Returns:
            List of mixed training examples.
        """
        curriculum_data = self._load_json(Path(curriculum_path))
        curriculum_count = len(curriculum_data)
        
        if curriculum_count == 0:
            logger.warning("Curriculum dataset is empty. Nothing to mix.")
            return []

        # Calculate required basal count to maintain the ratio
        # ratio = curriculum / (curriculum + basal)
        # basal = (curriculum / ratio) - curriculum
        # basal = curriculum * (1 - ratio) / ratio
        basal_needed = int(curriculum_count * (1 - curriculum_ratio) / curriculum_ratio)
        
        logger.info(f"Curriculum count: {curriculum_count}")
        logger.info(f"Basal needed (for {curriculum_ratio:.0%} split): {basal_needed}")
        
        if not self.basal_data:
            logger.error("No basal data available for mixing!")
            return curriculum_data

        # Sample basal data (with replacement if basal set is smaller than needed)
        if basal_needed > len(self.basal_data):
            logger.info("Oversampling basal dataset...")
            basal_sample = random.choices(self.basal_data, k=basal_needed)
        else:
            basal_sample = random.sample(self.basal_data, k=basal_needed)
            
        # Combine
        mixed_dataset = curriculum_data + basal_sample
        
        # Shuffle to ensure uniform distribution in batches
        random.shuffle(mixed_dataset)
        
        logger.info(f"Final mixed dataset size: {len(mixed_dataset)}")
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(mixed_dataset, f, indent=2)
            logger.info(f"Mixed dataset saved to {output_path}")
            
        return mixed_dataset
