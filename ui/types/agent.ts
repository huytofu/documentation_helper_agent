export interface AgentState {
  reload: boolean;
  last_message_content: string;
  language: string
  comments: string,
  current_node: string;
  query: string;
  rewritten_query: string;
  framework: string;
  retry_count: number;
  test_counter?: number;
  // pass_summarize: boolean;
  // summarized: boolean;
  // documents: any[];
} 


