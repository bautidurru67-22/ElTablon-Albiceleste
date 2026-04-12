"use client"

import { useEffect, useState } from "react"

export default function Home() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/matches/today`
        )
        const json = await res.json()
        setData(Array.isArray(json) ? json : [])
      } catch (error) {
        console.error("Error:", error)
        setData([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  return (
    <main>
      <h1>HOY - Agenda deportiva</h1>
      {loading ? <p>Cargando...</p> : <pre>{JSON.stringify(data, null, 2)}</pre>}
    </main>
  )
}
