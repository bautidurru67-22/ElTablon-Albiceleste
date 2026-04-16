import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL?.replace(/\/$/, "") ||
  "https://tablon-albiceleste-api-production-7173.up.railway.app";

const TARGET_URL = `${BACKEND_URL}/api/hoy`;

export async function GET() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const res = await fetch(TARGET_URL, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
      },
    });

    const text = await res.text();

    return new NextResponse(text, {
      status: res.status,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store, max-age=0",
      },
    });
  } catch (error: any) {
    const message =
      error?.name === "AbortError"
        ? "Proxy timeout al consultar /api/hoy"
        : error?.message || "Proxy error";

    return NextResponse.json(
      {
        ok: false,
        error: message,
        target: TARGET_URL,
      },
      { status: 500 },
    );
  } finally {
    clearTimeout(timeout);
  }
}
