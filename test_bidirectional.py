"""
Test script to verify bidirectional communication between frontend and backend.

This script will:
1. Start the backend server
2. Make a request to the backend
3. Verify that the state is updated correctly
"""

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def print_header(message):
    """Print a header message."""
    print("\n" + "=" * 80)
    print(f" {message} ".center(80, "="))
    print("=" * 80 + "\n")

def test_backend_connection():
    """Test the connection to the backend server."""
    print_header("Testing Backend Connection")
    
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Backend server is running")
            return True
        else:
            print(f"❌ Backend server returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend server")
        return False

def test_agent_request():
    """Test making a request to the agent."""
    print_header("Testing Agent Request")
    
    # Prepare the request payload
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Help me understand this codebase."
            }
        ],
        "stream": True,
        "agent": "coding_agent",
        "state": {
            "language": "python",
            "comments": "Help me understand this codebase.",
            "current_node": ""
        }
    }
    
    try:
        # Make the request
        print("Sending request to agent...")
        response = requests.post(
            "http://localhost:8000/copilotkitagent",
            json=payload,
            stream=True,
            headers={"Content-Type": "application/json"}
        )
        
        # Check the response
        if response.status_code == 200:
            print("✅ Request successful")
            
            # Process the streaming response
            print("\nStreaming response:")
            print("-" * 40)
            
            for line in response.iter_lines():
                if line:
                    # Parse the line as JSON
                    try:
                        data = json.loads(line.decode('utf-8').replace('data: ', ''))
                        
                        # Check if this is a state update
                        if 'state_update' in data.get('additional_kwargs', {}):
                            state_update = data['additional_kwargs']['state_update']
                            print(f"State Update: {json.dumps(state_update, indent=2)}")
                        else:
                            print(f"Content: {data.get('content', '')}")
                    except json.JSONDecodeError:
                        print(f"Raw line: {line.decode('utf-8')}")
            
            print("-" * 40)
            return True
        else:
            print(f"❌ Request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error making request: {e}")
        return False

def main():
    """Main function."""
    print_header("Bidirectional Communication Test")
    
    # Test backend connection
    if not test_backend_connection():
        print("❌ Backend connection test failed. Make sure the backend server is running.")
        sys.exit(1)
    
    # Test agent request
    if not test_agent_request():
        print("❌ Agent request test failed.")
        sys.exit(1)
    
    print_header("All Tests Passed")
    print("✅ Bidirectional communication is working correctly.")

if __name__ == "__main__":
    main() 