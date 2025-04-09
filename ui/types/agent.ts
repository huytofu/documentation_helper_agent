export interface AgentState {
  language: string
  comments: string,
  query: string;
  messages: [];
  test_counter?: number;
  current_node: string;
} 

