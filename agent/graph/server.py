from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from agent.graph.graph import graph as agent_app
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CopilotKitRequest(BaseModel):
    action: str
    input: Dict[str, Any]

@app.post("/copilotkit")
async def handle_copilotkit_request(request: CopilotKitRequest):
    try:
        logger.info(f"Received request: {request}")
        if request.action != "agent":
            logger.error(f"Invalid action: {request.action}")
            raise HTTPException(status_code=400, detail="Invalid action")

        # Initialize the state for the agent
        state = {
            "language": request.input.get("language", "python"),
            "query": request.input.get("request", ""),
            "framework": "",
            "documents": [],
            "generation": "",
            "comment": "",
            "retry_count": 0
        }
        logger.info(f"Initialized state: {state}")
        
        # Run the agent workflow
        logger.info("Starting agent workflow")
        result = await agent_app.ainvoke(state)
        logger.info(f"Workflow completed with result: {result}")
        
        return {
            "response": result.get("generation", "No response generated"),
            "error": None
        }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 