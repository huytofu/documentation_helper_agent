"""PostgreSQL Checkpointer for LangGraph

This module implements a LangGraph checkpointer using PostgreSQL for state persistence.
It can be used with any cloud provider's PostgreSQL service:
- AWS RDS
- Google Cloud SQL
- Azure Database for PostgreSQL
- Digital Ocean Managed PostgreSQL
"""

import os
import json
import logging
import asyncio
from typing import Any, Dict, Optional, List
from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointer

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class PostgresCheckpointer(BaseCheckpointer):
    """LangGraph checkpointer implementation using PostgreSQL.
    
    This checkpointer stores LangGraph state in a PostgreSQL database, allowing for
    persistence across serverless function invocations on any cloud provider.
    """
    
    def __init__(self, 
                 connection_string: Optional[str] = None,
                 table_name: str = "langgraph_states",
                 ttl: Optional[int] = None):
        """Initialize the PostgreSQL checkpointer.
        
        Args:
            connection_string: PostgreSQL connection string (DATABASE_URL env var)
            table_name: Name of the table to store states in
            ttl: Time-to-live for stored states in seconds (optional)
        """
        # Import here to avoid dependency issues if not using PostgreSQL
        try:
            import asyncpg
        except ImportError:
            raise ImportError(
                "The 'asyncpg' package is required to use PostgresCheckpointer. "
                "Install it with 'pip install asyncpg'."
            )
        
        self.asyncpg = asyncpg
        
        # Get connection string from parameter or environment variable
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        
        # Validate connection string
        if not self.connection_string:
            raise ValueError(
                "PostgreSQL connection string is required. "
                "Set DATABASE_URL environment variable or provide it as a parameter."
            )
        
        self.table_name = table_name
        self.ttl = ttl
        self._pool = None
        self._initialized = False
        
        logger.info(f"Initialized PostgreSQL checkpointer with table {table_name}")
    
    async def _get_pool(self):
        """Get or create the connection pool."""
        if self._pool is None:
            self._pool = await self.asyncpg.create_pool(self.connection_string)
        return self._pool
    
    async def _ensure_table_exists(self):
        """Ensure the states table exists."""
        if self._initialized:
            return
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Create the table if it doesn't exist
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    key TEXT PRIMARY KEY,
                    state JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on created_at for TTL cleanup
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_created_at_idx 
                ON {self.table_name} (created_at)
            """)
            
            # Create a function to update the updated_at timestamp
            await conn.execute(f"""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)
            
            # Create a trigger to update the updated_at timestamp
            await conn.execute(f"""
                DROP TRIGGER IF EXISTS update_{self.table_name}_updated_at ON {self.table_name};
                CREATE TRIGGER update_{self.table_name}_updated_at
                BEFORE UPDATE ON {self.table_name}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            """)
        
        self._initialized = True
        logger.info(f"Ensured table {self.table_name} exists")
    
    async def _cleanup_expired_states(self):
        """Clean up expired states based on TTL."""
        if not self.ttl:
            return
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Delete states older than TTL
            await conn.execute(f"""
                DELETE FROM {self.table_name}
                WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '{self.ttl} seconds'
            """)
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a state from PostgreSQL.
        
        Args:
            key: The state key to retrieve
            
        Returns:
            The state dictionary if found, None otherwise
        """
        await self._ensure_table_exists()
        
        try:
            logger.debug(f"Getting state for key: {key}")
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT state FROM {self.table_name} WHERE key = $1",
                    key
                )
                
                if row is None:
                    logger.debug(f"No state found for key: {key}")
                    return None
                
                logger.debug(f"Retrieved state for key: {key}")
                return row['state']
        except Exception as e:
            logger.error(f"Error getting state for key {key}: {str(e)}")
            return None
    
    async def put(self, key: str, state: Dict[str, Any]) -> None:
        """Store a state in PostgreSQL.
        
        Args:
            key: The state key
            state: The state dictionary to store
        """
        await self._ensure_table_exists()
        
        try:
            logger.debug(f"Storing state for key: {key}")
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                # Use upsert (INSERT ... ON CONFLICT DO UPDATE)
                await conn.execute(
                    f"""
                    INSERT INTO {self.table_name} (key, state)
                    VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE
                    SET state = $2, updated_at = CURRENT_TIMESTAMP
                    """,
                    key, state
                )
                
            logger.debug(f"Stored state for key: {key}")
            
            # Cleanup expired states in the background
            asyncio.create_task(self._cleanup_expired_states())
        except Exception as e:
            logger.error(f"Error storing state for key {key}: {str(e)}")
            raise
    
    async def list(self) -> List[str]:
        """List all state keys in PostgreSQL.
        
        Returns:
            List of state keys
        """
        await self._ensure_table_exists()
        
        try:
            logger.debug("Listing all state keys")
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                rows = await conn.fetch(f"SELECT key FROM {self.table_name}")
                keys = [row['key'] for row in rows]
                
            logger.debug(f"Found {len(keys)} state keys")
            return keys
        except Exception as e:
            logger.error(f"Error listing state keys: {str(e)}")
            return []
    
    async def delete(self, key: str) -> None:
        """Delete a state from PostgreSQL.
        
        Args:
            key: The state key to delete
        """
        await self._ensure_table_exists()
        
        try:
            logger.debug(f"Deleting state for key: {key}")
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE key = $1",
                    key
                )
                
            logger.debug(f"Deleted state for key: {key}")
        except Exception as e:
            logger.error(f"Error deleting state for key {key}: {str(e)}")
            raise 