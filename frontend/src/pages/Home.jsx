import { useQuery } from '@tanstack/react-query'
import { api } from '../api.js'

export default function Home() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['health'], queryFn: () => api('/health') })
  const status = isLoading ? '…' : isError ? 'API ni dosegljiv' : data.db ? 'API + baza OK' : 'Baza ni dosegljiva'

  return (
    <main className="min-h-screen bg-rose-50 font-sans flex flex-col items-center justify-center gap-4 p-4 text-center">
      <h1 className="font-display italic text-4xl text-rose-600">Thisissus 💌</h1>
      <p className="text-rose-900">{status}</p>
    </main>
  )
}
