'use client';

import { CopilotKit } from '@copilotkit/react-core';

export default function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      {children}
    </CopilotKit>
  );
} 