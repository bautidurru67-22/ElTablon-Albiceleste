import { NextRequest, NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const rawPath = params.path.join('/')
  const query = req.nextUrl.search || ''

  const base = API_BASE.replace(/\/+$/, '')
  let path = rawPath.replace(/^\/+/, '')

  // Soporta ambas configuraciones:
  // - NEXT_PUBLIC_API_URL = https://host
  // - NEXT_PUBLIC_API_URL = https://host/api
  if (base.endsWith('/api') && path.startsWith('api/')) {
    path = path.slice(4)
  }

  const target = `${base}/${path}${query}`

  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 10000)
    const res = await fetch(target, { cache: 'no-store', signal: controller.signal })
    clearTimeout(timer)
    const text = await res.text()

    return new NextResponse(text, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('Content-Type') ?? 'application/json' },
    })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { detail: 'Proxy timeout to backend API' },
        { status: 504 }
      )
    }
    return NextResponse.json(
      { detail: 'Proxy error to backend API' },
      { status: 502 }
    )
  }
}
