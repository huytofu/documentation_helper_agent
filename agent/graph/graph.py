from dotenv import load_dotenv
load_dotenv()
import logging
import os

# Import the workflows instead of the compiled apps
# Depending on the FLOW environment variable, import the appropriate workflow
if os.environ.get("FLOW") == "test":
    from agent.graph.test_flow import workflow
elif os.environ.get("FLOW") == "simple":
    from agent.graph.simple_flow import workflow
else:
    from agent.graph.real_flow import workflow

# Import the checkpointer factory
from agent.graph.checkpointers import get_checkpointer

# Configure logging for the graph module
logger = logging.getLogger("graph.graph")
logger.debug("Graph module initialized")

# Get the appropriate checkpointer based on environment
checkpointer = get_checkpointer()
logger.info(f"Using checkpointer: {checkpointer.__class__.__name__}")

# Compile the workflow centrally with streaming enabled
# The compiled app is used to manage the workflow execution
app = workflow.compile(checkpointer=checkpointer)
logger.debug("Graph compiled successfully with streaming enabled")

# Uncomment the following line to generate a visual representation of the graph
# app.get_graph().draw_mermaid_png(output_file_path="graph.png")

# Save Mermaid code to a file for local rendering
mermaid_code = app.get_graph().get_mermaid()
mermaid_path = os.path.join(os.path.dirname(__file__), "graph.mmd")
png_path = os.path.join(os.path.dirname(__file__), "graph.png")

with open(mermaid_path, "w") as f:
    f.write(mermaid_code)
    
logger.info(f"Mermaid diagram code saved to {mermaid_path}")
logger.info("To generate the PNG manually, install mermaid-cli:")
logger.info("npm install -g @mermaid-js/mermaid-cli")
logger.info(f"Then run: mmdc -i {mermaid_path} -o {png_path}")

# Try to render using a longer timeout by using a custom approach
import requests
import base64
import json
import time

try:
    logger.info("Attempting to render diagram using mermaid.ink with longer timeout...")
    # Encode diagram for URL
    encoded_diagram = base64.urlsafe_b64encode(mermaid_code.encode()).decode()
    
    # Use a session with a longer timeout
    session = requests.Session()
    session.timeout = 60  # 60 seconds timeout
    
    # Get the SVG first (typically faster than PNG)
    svg_url = f"https://mermaid.ink/svg/{encoded_diagram}"
    start_time = time.time()
    logger.info(f"Requesting SVG from {svg_url}")
    svg_response = session.get(svg_url, timeout=60)
    
    if svg_response.status_code == 200:
        svg_path = os.path.join(os.path.dirname(__file__), "graph.svg")
        with open(svg_path, "wb") as f:
            f.write(svg_response.content)
        logger.info(f"SVG saved to {svg_path} in {time.time() - start_time:.2f} seconds")
        
        # Now try to get the PNG
        png_url = f"https://mermaid.ink/img/{encoded_diagram}"
        logger.info(f"Requesting PNG from {png_url}")
        png_response = session.get(png_url, timeout=60)
        
        if png_response.status_code == 200:
            with open(png_path, "wb") as f:
                f.write(png_response.content)
            logger.info(f"PNG saved to {png_path}")
        else:
            logger.warning(f"Failed to get PNG: {png_response.status_code}")
    else:
        logger.warning(f"Failed to get SVG: {svg_response.status_code}")
        
except Exception as e:
    logger.warning(f"Error rendering diagram online: {str(e)}")
    logger.info("Falling back to local rendering if possible")
    
    # Try a pure Python approach using subprocess to call npm/npx if available
    try:
        import subprocess
        
        # First check if we have npm/npx available
        npm_check = subprocess.run(
            ["npm", "--version"], 
            capture_output=True, 
            text=True,
            check=False
        )
        
        if npm_check.returncode == 0:
            logger.info("NPM found, attempting to use mermaid-cli locally")
            
            # Install mermaid-cli if needed (will be skipped if already installed)
            subprocess.run(
                ["npm", "install", "-g", "@mermaid-js/mermaid-cli"],
                check=False
            )
            
            # Try to render with mmdc
            result = subprocess.run(
                ["npx", "@mermaid-js/mermaid-cli", "-i", mermaid_path, "-o", png_path],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully generated PNG at {png_path}")
            else:
                logger.warning(f"Failed to generate PNG with mermaid-cli: {result.stderr}")
        else:
            logger.warning("NPM not found, cannot use mermaid-cli")
    
    except Exception as e2:
        logger.warning(f"Error with local rendering fallback: {str(e2)}")
        logger.info(f"You can still view the Mermaid code in {mermaid_path}")
        logger.info("Or render online at https://mermaid.live/")
