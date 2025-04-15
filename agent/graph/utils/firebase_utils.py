"""Firebase database utilities for conversation history."""

import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, Any, Optional
import datetime
from urllib.parse import quote
import requests
import time
import re

logger = logging.getLogger(__name__)

# Initialize Firebase if not already initialized
def get_firestore_db():
    """Get Firestore database instance."""
    try:
        # Check if app exists
        app = firebase_admin.get_app()
        return firestore.client(app)
    except ValueError:
        # Initialize Firebase Admin with service account from environment
        service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
        if service_account_json:
            try:
                # Remove any surrounding quotes and handle escaped characters
                service_account_json = service_account_json.strip("'\"")
                # Parse the JSON string from environment variable
                service_account_info = json.loads(service_account_json)
                cred = credentials.Certificate(service_account_info)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse FIREBASE_SERVICE_ACCOUNT as JSON: {str(e)}")
                logger.error(f"Raw value: {service_account_json[:100]}...")  # Log first 100 chars
                raise
        else:
            # Fallback to service account file if environment variable not set
            service_account_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or 'serviceAccountKey.json'
            try:
                cred = credentials.Certificate(service_account_path)
            except FileNotFoundError:
                logger.error(f"Service account file not found at {service_account_path}")
                raise
            
        # Initialize the app
        app = firebase_admin.initialize_app(cred)
        
        # Return Firestore client
        return firestore.client(app)

def extract_user_id_from_system_message(content: str) -> Optional[str]:
    """
    Extract user ID from a system message if it contains one.
    
    Args:
        content: The content of the message
        
    Returns:
        The user ID if found, None otherwise
    """
    if not content:
        return None
        
    # Try to find a user ID pattern (assuming it's in the format "User ID: xxx")
    user_id_match = re.search(r'User ID: ([a-zA-Z0-9]{20,36})', content)
    if user_id_match:
        return user_id_match.group(1)
    
    return None

def validate_user_id(user_id: Optional[str]) -> bool:
    """
    Validate a user ID to ensure it's in the correct format.
    
    Args:
        user_id: The user ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not user_id:
        return False
        
    # Check for Firebase Auth UID format (28 chars)
    # or typical UUID format (36 chars with hyphens)
    return (isinstance(user_id, str) and 
            (len(user_id) >= 20 and len(user_id) <= 36) and
            re.match(r'^[a-zA-Z0-9\-]+$', user_id) is not None)

def save_conversation_message(user_id: str, message_type: str, content: str) -> Dict[str, Any]:
    """
    Save a conversation message to Firestore.
    
    Args:
        user_id: The ID of the user
        message_type: The type of message ('question' or 'answer')
        content: The message content
        
    Returns:
        Dict with status and message ID
    """
    # Try to extract user_id from system message if not provided directly
    if not validate_user_id(user_id):
        extracted_id = extract_user_id_from_system_message(content)
        if extracted_id:
            user_id = extracted_id
    
    if not validate_user_id(user_id):
        logger.error("Cannot save conversation message: Invalid user_id")
        return {"success": False, "error": "Invalid user_id"}
        
    try:
        # Get Firestore client
        db = get_firestore_db()
        
        # Create new document in conversation_history collection
        conversation_ref = db.collection('conversation_history').document()
        
        # Create timestamp
        timestamp = datetime.datetime.now()
        
        # Create document data
        doc_data = {
            "user_id": user_id,
            "type": message_type,
            "content": content,
            "timestamp": timestamp
        }
        
        # Save document
        conversation_ref.set(doc_data)
        
        logger.info(f"Saved {message_type} message for user {user_id}")
        return {
            "success": True,
            "message_id": conversation_ref.id,
            "timestamp": timestamp
        }
        
    except Exception as e:
        logger.error(f"Error saving conversation message: {str(e)}")
        return {"success": False, "error": str(e)}

async def save_conversation_message_api(user_id: str, message_type: str, content: str) -> Dict[str, Any]:
    """
    Save a conversation message via API for use from LangGraph nodes.
    
    This version is designed to be called from within LangGraph nodes which
    may not have direct Firebase access. It calls an API endpoint instead.
    
    Args:
        user_id: The ID of the user
        message_type: The type of message ('question' or 'answer')
        content: The message content
        
    Returns:
        Dict with status and message ID
    """
    # Try to extract user_id from system message if not provided directly
    if not validate_user_id(user_id):
        extracted_id = extract_user_id_from_system_message(content)
        if extracted_id:
            user_id = extracted_id
    
    if not validate_user_id(user_id):
        logger.error("Cannot save conversation message: Invalid user_id")
        return {"success": False, "error": "Invalid user_id"}
        
    # This is a placeholder for the actual API implementation
    # In a real scenario, you would use the API endpoint URL from configuration
    try:
        # Call the Firebase REST API directly
        api_url = os.environ.get("FIREBASE_API_URL")
        api_key = os.environ.get("FIREBASE_API_KEY")
        
        if not api_url or not api_key:
            logger.error("Firebase API URL or key not configured")
            return {"success": False, "error": "Firebase API not configured"}
            
        # Format the request payload
        payload = {
            "user_id": user_id,
            "type": message_type,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Make the API request
        response = requests.post(
            f"{api_url}/conversation_history?key={api_key}", 
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return {"success": True, "message_id": response.json().get("name")}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error using API to save conversation: {str(e)}")
        return {"success": False, "error": str(e)}

# Frontend API route handler logic (to be implemented in api/conversation/route.ts)
def handle_conversation_history_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a request to save conversation history from the frontend.
    
    This function is designed to be called from a Next.js API route.
    
    Args:
        request_data: The data from the API request
        
    Returns:
        Dict with status and message ID
    """
    # Extract fields
    user_id = request_data.get("user_id")
    message_type = request_data.get("type")
    content = request_data.get("content")
    
    # Validate required fields
    if not message_type or not content:
        return {"success": False, "error": "Missing required fields"}
        
    # Validate message type
    if message_type not in ["question", "answer"]:
        return {"success": False, "error": "Invalid message type"}
        
    # Try to extract user_id from content if not provided
    if not validate_user_id(user_id):
        extracted_id = extract_user_id_from_system_message(content)
        if extracted_id:
            user_id = extracted_id
    
    # Final validation of user_id
    if not validate_user_id(user_id):
        return {"success": False, "error": "Invalid or missing user_id"}
        
    # Save the message
    return save_conversation_message(user_id, message_type, content) 