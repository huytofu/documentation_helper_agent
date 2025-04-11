export interface AgentState {
  language: string
  comments: string,
  current_node: string;
  rewritten_query: string;
  framework: string;
  retry_count: number;
  test_counter?: number;
  pass_summarize: boolean;
  summarized: boolean;
  documents: any[];
} 


