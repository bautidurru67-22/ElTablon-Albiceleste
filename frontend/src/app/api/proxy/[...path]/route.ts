import { NextRequest, NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET(
  _req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const target = `${API_BASE}/api/competitions/${params.path.join('/')}`

  try {
    const res = await fetch(target, { cache: 'no-store' })
    const text = await res.text()

    return new NextResponse(text, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('Content-Type') ?? 'application/json' },
    })
  } catch {
    return NextResponse.json(
      { detail: 'Proxy error to backend competitions API' },
      { status: 502 }
    )
  }
}
