'use client';

import { CopilotKit } from '@copilotkit/react-core';
import { useEffect, useState } from 'react';

export function CopilotProvider({ children }: { children: React.ReactNode }) {
  // Use a state to track if component has mounted
  const [mounted, setMounted] = useState(false);

  // Set mounted to true when component mounts
  useEffect(() => {
    setMounted(true);
  }, []);

  // Only render CopilotKit on client-side
  if (!mounted) {
    return <>{children}</>;
  }

  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      {children}
    </CopilotKit>
  );
} 