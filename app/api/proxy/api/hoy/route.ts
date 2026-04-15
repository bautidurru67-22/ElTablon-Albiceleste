import { NextResponse } from 'next/server'

const BACKEND_URL =
  'https://tablon-albiceleste-api-production-7173.up.railway.app/api/hoy'

export async function GET() {
  try {
    const res = await fetch(BACKEND_URL, {
      cache: 'no-store',
    })

    const text = await res.text()

    return new NextResponse(text, {
      status: res.status,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store, max-age=0',
      },
    })
  } catch (error: any) {
    return NextResponse.json(
      {
        ok: false,
        error: error?.message || 'Proxy error',
      },
      { status: 500 }
    )
  }
}
