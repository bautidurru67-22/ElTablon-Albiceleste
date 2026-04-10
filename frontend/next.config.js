/** @type {import('next').NextConfig} */
const nextConfig = {
  // En producción, NEXT_PUBLIC_API_URL apunta directo al backend deployado.
  // El rewrite solo aplica si NEXT_PUBLIC_API_URL no está definido (dev local).
  async rewrites() {
    // Solo activo en desarrollo local sin variable de entorno
    if (process.env.NEXT_PUBLIC_API_URL) return []
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },

  // Headers de seguridad básicos
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ]
  },

  // Output standalone para Docker si es necesario
  // output: 'standalone',
}

module.exports = nextConfig
