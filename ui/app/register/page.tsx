'use client';

import { RegisterForm } from '@/components/auth/RegisterForm';
import { CopilotKit } from '@copilotkit/react-core';

export default function RegisterPage() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <CopilotKit runtimeUrl="/api/copilotkit">
        <RegisterForm />
      </CopilotKit>
    </div>
  );
} 