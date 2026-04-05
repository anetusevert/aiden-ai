const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  /**
   * Same-origin API mode uses `NEXT_PUBLIC_API_PREFIX` (default `/api`) so the browser
   * calls `/api/auth/me`, etc. Without a rewrite, Next.js has no route for `/api/*` and
   * auth can fail or hang depending on environment. Proxy to the FastAPI server in dev.
   * When `NEXT_PUBLIC_API_BASE_URL` is set (full URL), the client talks to the API directly — skip proxy.
   */
  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_BASE_URL) {
      return [];
    }
    const target =
      process.env.API_PROXY_TARGET ||
      process.env.API_INTERNAL_BASE_URL ||
      'http://127.0.0.1:8000';
    const base = String(target).replace(/\/$/, '');
    return [
      {
        source: '/api/:path*',
        destination: `${base}/:path*`,
      },
    ];
  },
  webpack(config) {
    config.resolve.alias['next-intl'] = path.resolve(
      __dirname,
      'src/lib/next-intl-shim.tsx'
    );
    return config;
  },
};

module.exports = nextConfig;
