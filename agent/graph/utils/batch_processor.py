"""Batch processing utilities for efficient handling of multiple requests."""

import asyncio
from typing import List, TypeVar, Callable, Any, Dict
from concurrent.futures import ThreadPoolExecutor
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class BatchResult:
    """Container for batch processing results."""
    success: bool
    result: Any
    error: Exception = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class BatchProcessor:
    """Handles batch processing of requests with parallel execution."""
    
    def __init__(
        self,
        max_batch_size: int = 10,
        max_workers: int = 5,
        timeout: float = 30.0
    ):
        """Initialize the batch processor.
        
        Args:
            max_batch_size: Maximum number of items to process in a batch
            max_workers: Maximum number of concurrent workers
            timeout: Maximum time to wait for batch processing
        """
        self.max_batch_size = max_batch_size
        self.max_workers = max_workers
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    async def process_batch(
        self,
        items: List[T],
        process_fn: Callable[[T], Any],
        batch_size: int = None
    ) -> List[BatchResult]:
        """Process a batch of items in parallel.
        
        Args:
            items: List of items to process
            process_fn: Function to process each item
            batch_size: Optional override for max_batch_size
            
        Returns:
            List of BatchResult objects containing results or errors
        """
        batch_size = batch_size or self.max_batch_size
        results = []
        
        # Split items into batches
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Create tasks for each item in the batch
            tasks = []
            for item in batch:
                task = asyncio.create_task(
                    self._process_item(item, process_fn)
                )
                tasks.append(task)
            
            # Wait for all tasks in the batch to complete
            try:
                batch_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.timeout
                )
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        results.append(BatchResult(
                            success=False,
                            result=None,
                            error=result
                        ))
                    else:
                        results.append(BatchResult(
                            success=True,
                            result=result
                        ))
                        
            except asyncio.TimeoutError:
                logger.error(f"Batch processing timed out after {self.timeout} seconds")
                for task in tasks:
                    if not task.done():
                        task.cancel()
                results.extend([
                    BatchResult(
                        success=False,
                        result=None,
                        error=asyncio.TimeoutError("Batch processing timed out")
                    ) for _ in range(len(tasks))
                ])
        
        return results
    
    async def _process_item(
        self,
        item: T,
        process_fn: Callable[[T], Any]
    ) -> Any:
        """Process a single item using the provided function.
        
        Args:
            item: Item to process
            process_fn: Function to process the item
            
        Returns:
            Processed result
        """
        try:
            # Run the processing function in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                process_fn,
                item
            )
            return result
        except Exception as e:
            logger.error(f"Error processing item: {str(e)}")
            raise
    
    def __del__(self):
        """Cleanup resources when the processor is destroyed."""
        self.executor.shutdown(wait=True)

# Example usage:
"""
# Initialize the batch processor
batch_processor = BatchProcessor(
    max_batch_size=10,
    max_workers=5,
    timeout=30.0
)

# Process a batch of requests
async def process_requests(requests: List[Dict[str, Any]]) -> List[BatchResult]:
    return await batch_processor.process_batch(
        items=requests,
        process_fn=lambda req: process_single_request(req)
    )
""" 