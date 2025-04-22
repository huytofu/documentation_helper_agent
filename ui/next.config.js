/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@copilotkit/react-core", "@copilotkit/react-ui", "@copilotkit/react-textarea"],
}

module.exports = nextConfig 