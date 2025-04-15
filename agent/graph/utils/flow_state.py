"""Flow state management for LangGraph execution."""

import logging
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class FlowState:
    """Thread-safe state container for flow execution."""
    iteration_count: int = 0
    retry_count: int = 0
    _lock: Lock = field(default_factory=Lock)

    def increment_iteration(self) -> bool:
        """Atomically increment iteration count and check limit."""
        with self._lock:
            self.iteration_count += 1
            return self.iteration_count < 2  # MAX_ITERATIONS

    def increment_retry(self) -> bool:
        """Atomically increment retry count and check limit."""
        with self._lock:
            self.retry_count += 1
            return self.retry_count < 2  # MAX_RETRIES

# Global flow state instance
flow_state = FlowState()

def reset_flow_state():
    """Reset the flow state counters to zero."""
    with flow_state._lock:
        logger.info("Resetting flow state counters")
        flow_state.iteration_count = 0
        flow_state.retry_count = 0

def check_iteration_limit() -> bool:
    """Check if the flow has exceeded maximum iterations."""
    if not flow_state.increment_iteration():
        logger.error("Flow exceeded maximum iterations (2)")
        return False
    return True 