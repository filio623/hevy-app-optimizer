/** @type {import('next').NextConfig} */
const nextConfig = {
  // Add any necessary configuration here
  reactStrictMode: true,
  // swcMinify: true, // Removed as it's default in newer Next.js
  transpilePackages: [
    '@radix-ui/react-toast',
    'lucide-react',
    'class-variance-authority'
  ],
  webpack: (config) => {
    // Add handling for vendor packages
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname, './src'),
    };
    return config;
  },
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['@radix-ui/react-toast', 'lucide-react'],
  },
};

module.exports = nextConfig; 