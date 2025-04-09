export interface AgentState {
  language: string
  comments: string,
  query: string;
  rewritten_query: string;
  framework: string;
  retry_count: number;
  messages: [];
  test_counter?: number;
  current_node: string;
  last_message_content: string;
} 


