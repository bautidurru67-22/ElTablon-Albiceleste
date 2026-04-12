"use client"

import { useEffect, useState } from "react"

export default function Home() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/hoy`
        )
        const json = await res.json()
        setData(json)
      } catch (error) {
        console.error("Error:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  return (
    <main style={{ padding: 20 }}>
      <h1>HOY - Agenda deportiva</h1>

      {loading && <p>Cargando...</p>}

      {!loading && (
        <pre style={{ background: "#111", color: "#0f0", padding: 10 }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </main>
  )
}
