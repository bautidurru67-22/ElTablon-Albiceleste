import { NextRequest, NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL

function getTargetUrl(path: string[], req: NextRequest) {
  if (!API_BASE) {
    throw new Error('NEXT_PUBLIC_API_URL no configurada')
  }
  const clean = API_BASE.endsWith('/') ? API_BASE.slice(0, -1) : API_BASE
  const target = new URL(`${clean}/${path.join('/')}`)
  req.nextUrl.searchParams.forEach((value, key) => {
    target.searchParams.set(key, value)
  })
  return target
}

async function proxy(req: NextRequest, ctx: { params: { path: string[] } }) {
  try {
    const target = getTargetUrl(ctx.params.path, req)
    const body = req.method === 'GET' || req.method === 'HEAD' ? undefined : await req.text()

    const upstream = await fetch(target.toString(), {
      method: req.method,
      headers: {
        'Content-Type': req.headers.get('content-type') ?? 'application/json',
        Authorization: req.headers.get('authorization') ?? '',
      },
      body,
      cache: 'no-store',
    })

    const text = await upstream.text()
    return new NextResponse(text, {
      status: upstream.status,
      headers: { 'Content-Type': upstream.headers.get('content-type') ?? 'application/json' },
    })
  } catch (error) {
    return NextResponse.json(
      { detail: 'Proxy error', error: error instanceof Error ? error.message : 'unknown' },
      { status: 502 }
    )
  }
}

export async function GET(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx)
}

export async function POST(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx)
}

export async function DELETE(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx)
}
