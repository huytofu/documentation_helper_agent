/// <reference types="react" />

declare module '@copilotkit/react-textarea' {
  export interface CopilotTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
    value?: string;
    onChange?: (event: React.ChangeEvent<HTMLTextAreaElement>) => void;
  }
  
  export const CopilotTextarea: React.FC<CopilotTextareaProps>;
}

declare module '@copilotkit/react-core' {
  export interface CopilotKitProps {
    url: string;
    children: React.ReactNode;
  }
  
  export const CopilotKit: React.FC<CopilotKitProps>;
} 