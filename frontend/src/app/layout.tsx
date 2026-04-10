import type { Metadata } from 'next'
import './globals.css'
import Header from '@/components/Header'
import HeroBanner from '@/components/HeroBanner'
import SportNav from '@/components/SportNav'
import AuthProvider from '@/components/AuthProvider'

export const metadata: Metadata = {
  title: 'El Tablón Albiceleste · Donde juega Argentina',
  description: 'Plataforma de información deportiva en tiempo real sobre atletas, equipos y competencias argentinas.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>
          <Header />
          <HeroBanner claimIndex={0} />
          <SportNav />
          <main style={{ maxWidth: 1200, margin: '0 auto', padding: '16px 12px' }}>
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  )
}
