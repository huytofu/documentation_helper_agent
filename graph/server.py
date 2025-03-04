from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from graph.graph import app as agent_app

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
        if request.action != "agent":
            raise HTTPException(status_code=400, detail="Invalid action")

        # Initialize the state for the agent
        state = {
            "language": request.input.get("language", "python"),
            "query": request.input.get("request", ""),
            "documents": [],
            "generation": "",
            "comment": "",
        }
        
        # Run the agent workflow
        result = await agent_app.ainvoke(state)
        
        return {
            "response": result.get("generation", "No response generated"),
            "error": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 