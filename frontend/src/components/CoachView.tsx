import { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft, CheckCircle, XCircle, Shield, Brain } from "lucide-react"

export function CoachView() {
  const { id } = useParams()
  const [advice, setAdvice] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    fetch(`http://localhost:8000/api/persona/${id}/coach`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to load coach advice")
        return res.json()
      })
      .then(data => setAdvice(data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="flex h-screen items-center justify-center text-white/50 bg-[#0d1117] animate-pulse">Generating Behavioral Advice...</div>
  if (error) return <div className="flex h-screen items-center justify-center text-red-500 bg-[#0d1117]">{error}</div>

  return (
    <div className="min-h-screen bg-[#0d1117] text-gray-200 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="flex items-center gap-4 border-b border-gray-800 pb-6">
          <Link to={`/persona/${id}`} className="p-2 hover:bg-white/10 rounded-full transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <Brain className="w-8 h-8 text-blue-500" />
              Communication Coach
            </h1>
            <p className="text-gray-400 mt-1">Actionable behavioral advice powered by LLM DNA analysis.</p>
          </div>
        </div>

        {advice.overall_vibe && (
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-2xl p-6 text-center">
            <h2 className="text-sm font-bold text-blue-400 uppercase tracking-wider mb-2">Overall Vibe</h2>
            <p className="text-xl text-blue-100 font-medium">{advice.overall_vibe}</p>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-green-900/10 border border-green-500/20 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <h2 className="text-xl font-bold text-white">Do's</h2>
            </div>
            <ul className="space-y-4">
              {advice.dos?.map((d: string, i: number) => (
                <li key={i} className="flex gap-3 text-gray-300">
                  <span className="text-green-500 mt-1">✦</span>
                  <span>{d}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-red-900/10 border border-red-500/20 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-6">
              <XCircle className="w-6 h-6 text-red-500" />
              <h2 className="text-xl font-bold text-white">Don'ts</h2>
            </div>
            <ul className="space-y-4">
              {advice.donts?.map((d: string, i: number) => (
                <li key={i} className="flex gap-3 text-gray-300">
                  <span className="text-red-500 mt-1">✦</span>
                  <span>{d}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {advice.conflict_resolution && (
          <div className="bg-[#161b22] border border-gray-800 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-6 h-6 text-orange-500" />
              <h2 className="text-xl font-bold text-white">Conflict Resolution</h2>
            </div>
            <p className="text-gray-300 leading-relaxed">{advice.conflict_resolution}</p>
          </div>
        )}
      </div>
    </div>
  )
}
