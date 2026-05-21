/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Proxy /api/* pro FastAPI (em dev e prod, mesma máquina)
  async rewrites() {
    const apiBase = process.env.INTERNAL_API_URL || "http://127.0.0.1:8012";
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
