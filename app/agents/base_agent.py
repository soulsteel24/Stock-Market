"""Base agent class for all reasoning agents."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, name: str):
        """Initialize agent with name."""
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    async def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate input data and return results.
        
        Args:
            data: Dictionary containing analysis data
            
        Returns:
            Dictionary with evaluation results
        """
        pass
    
    def log_decision(self, decision: str, reason: str):
        """Log an agent decision."""
        self.logger.info(f"[{self.name}] Decision: {decision} | Reason: {reason}")
