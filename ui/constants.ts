/**
 * Constants used throughout the application
 */

// Agent name - must match the name used in the backend
export const AGENT_NAME = "coding_agent";

// API endpoints
export const API_ENDPOINT = "/api/copilotkit";
export const BACKEND_ENDPOINT = process.env.REMOTE_ACTION_URL || "http://localhost:8000/copilotkitagent"; 
export const BACKEND_ENDPOINT_2 = process.env.REMOTE_ACTION_URL || "http://104.255.9.187:8000/copilotkitagent"; 