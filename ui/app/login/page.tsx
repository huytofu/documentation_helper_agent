'use client';

import { LoginForm } from '@/components/auth/LoginForm';
import { CopilotKit } from '@copilotkit/react-core';

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <CopilotKit runtimeUrl="/api/copilotkit">
        <LoginForm />
      </CopilotKit>
    </div>
  );
} 