import sqlite3
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, Optional
from .config.settings import Settings

logger = logging.getLogger(__name__)

class BudgetService:
    """
    BudgetService ports the high-maturity Budget Service from v2 to JARVISv4.
    It provides safety limits and cost enforcement using SQLite for persistence.
    """
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db_path = settings.budget_db_path
        self.enforcement_level = settings.budget_enforcement_level
        self.limits = settings.budget_limits or {}
        self._init_db()

    def _init_db(self):
        """Initialize the budget database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS budget_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    cost REAL NOT NULL,
                    item_id TEXT
                )
            """)
            conn.commit()

    def check_availability(self, category: str, cost: float) -> bool:
        """
        Pre-check if an action is allowed based on current budget and enforcement level.
        
        Args:
            category: The budget category to check.
            cost: The estimated cost of the action.
            
        Returns:
            bool: True if the action is allowed, False if blocked.
        """
        if self.enforcement_level == "none":
            return True

        limit = self.limits.get(category, 0.0)
        if limit <= 0:
            # If no limit defined for category, it's allowed.
            return True

        current_spend = self._get_current_spend(category)
        is_within = (current_spend + cost) <= limit

        if not is_within:
            if self.enforcement_level == "block":
                logger.warning(f"Budget blocked for category '{category}': current {current_spend:.4f} + cost {cost:.4f} exceeds limit {limit:.4f}")
                return False
            elif self.enforcement_level == "log":
                logger.warning(f"Budget limit exceeded for category '{category}': current {current_spend:.4f} + cost {cost:.4f} exceeds limit {limit:.4f}")
                return True
        
        return True

    def record_spend(self, category: str, cost: float, item_id: Optional[str] = None):
        """
        Log consumption of budget.
        
        Args:
            category: The budget category.
            cost: The actual cost incurred.
            item_id: Optional identifier for the item/action that caused the cost.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO budget_events (timestamp, category, cost, item_id) VALUES (?, ?, ?, ?)",
                (datetime.now(UTC).isoformat(), category, cost, item_id)
            )
            conn.commit()

    def get_status(self) -> Dict[str, Any]:
        """
        Return current usage vs limits for all categories.
        
        Returns:
            dict: Current usage status.
        """
        status = {}
        # Get all categories from events or limits
        all_categories = set(self.limits.keys())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT category, SUM(cost) FROM budget_events GROUP BY category")
            rows = cursor.fetchall()
            for row in rows:
                all_categories.add(row[0])

        for cat in all_categories:
            spend = self._get_current_spend(cat)
            limit = self.limits.get(cat, 0.0)
            status[cat] = {
                "spend": spend,
                "limit": limit,
                "remaining": max(0.0, limit - spend) if limit > 0 else float('inf')
            }
        return status

    def _get_current_spend(self, category: str) -> float:
        """Calculate total spend for the category in the current daily period."""
        # Simple daily reset: sum costs for today (UTC)
        today = datetime.now(UTC).date().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT SUM(cost) FROM budget_events WHERE category = ? AND timestamp >= ?",
                (category, today)
            )
            row = cursor.fetchone()
            return row[0] if row and row[0] else 0.0
