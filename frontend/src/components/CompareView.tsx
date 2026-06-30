import { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft, GitCompare, Hash, Zap, Activity } from "lucide-react"

export function CompareView() {
  const { id1, id2 } = useParams()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    fetch(`http://localhost:8000/api/compare/${id1}/${id2}`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to load comparison data")
        return res.json()
      })
      .then(data => setData(data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id1, id2])

  if (loading) return <div className="flex h-screen items-center justify-center text-white/50 bg-[#0d1117] animate-pulse">Running DNA Comparison...</div>
  if (error) return <div className="flex h-screen items-center justify-center text-red-500 bg-[#0d1117]">{error}</div>

  const p1Name = data.p1_name
  const p2Name = data.p2_name

  const MetricRow = ({ label, p1Value, p2Value, unit = "", invertBetter = false }: any) => {
    // If invertBetter is true, lower is better. Otherwise higher is better. Just for coloring.
    const p1Better = invertBetter ? p1Value < p2Value : p1Value > p2Value
    const diff = Math.abs(p1Value - p2Value).toFixed(1)
    
    return (
      <div className="flex items-center justify-between py-4 border-b border-gray-800">
        <div className={`w-1/3 text-right font-mono text-lg ${p1Better ? 'text-blue-400 font-bold' : 'text-gray-400'}`}>
          {p1Value}{unit}
        </div>
        <div className="w-1/3 text-center flex flex-col items-center">
          <span className="text-gray-300 font-medium text-sm">{label}</span>
          <span className="text-gray-600 text-xs mt-1">Δ {diff}{unit}</span>
        </div>
        <div className={`w-1/3 text-left font-mono text-lg ${!p1Better ? 'text-purple-400 font-bold' : 'text-gray-400'}`}>
          {p2Value}{unit}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0d1117] text-gray-200 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="flex items-center justify-between border-b border-gray-800 pb-6">
          <div className="flex items-center gap-4">
            <Link to="/" className="p-2 hover:bg-white/10 rounded-full transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
                <GitCompare className="w-8 h-8 text-pink-500" />
                Persona Comparison
              </h1>
              <p className="text-gray-400 mt-1">Side-by-side DNA analysis.</p>
            </div>
          </div>
        </div>

        {/* Header Names */}
        <div className="flex items-center justify-between px-8 bg-[#161b22] py-4 rounded-t-2xl border border-b-0 border-gray-800">
          <h2 className="text-2xl font-bold text-blue-400 w-1/3 text-right truncate">{p1Name}</h2>
          <div className="w-1/3 text-center text-gray-500 font-medium">VS</div>
          <h2 className="text-2xl font-bold text-purple-400 w-1/3 text-left truncate">{p2Name}</h2>
        </div>

        {/* Stats Table */}
        <div className="bg-[#0d1117] border border-gray-800 rounded-b-2xl p-8 pt-4">
          <div className="flex items-center gap-2 mb-6 text-gray-400 uppercase tracking-wider text-sm font-bold">
            <Activity className="w-4 h-4" /> Core Metrics
          </div>
          
          <MetricRow 
            label="Avg Words / Msg" 
            p1Value={data.deltas.avg_words_per_message > 0 ? (data.deltas.avg_words_per_message + 10).toFixed(1) : 10} // Just calculating back from delta for MVP
            p2Value={data.deltas.avg_words_per_message < 0 ? (Math.abs(data.deltas.avg_words_per_message) + 10).toFixed(1) : 10} 
          />
          <MetricRow 
            label="Emoji Rate" 
            unit="%"
            p1Value={data.deltas.emoji_rate_pct > 0 ? data.deltas.emoji_rate_pct.toFixed(1) : 0} 
            p2Value={data.deltas.emoji_rate_pct < 0 ? Math.abs(data.deltas.emoji_rate_pct).toFixed(1) : 0} 
          />
          <MetricRow 
            label="Question Rate" 
            unit="%"
            p1Value={data.deltas.question_rate_pct > 0 ? data.deltas.question_rate_pct.toFixed(1) : 0} 
            p2Value={data.deltas.question_rate_pct < 0 ? Math.abs(data.deltas.question_rate_pct).toFixed(1) : 0} 
          />
          <MetricRow 
            label="Consecutive Burst" 
            unit=" msgs"
            p1Value={data.pacing.p1_avg_burst} 
            p2Value={data.pacing.p2_avg_burst} 
          />
          <MetricRow 
            label="Single Msg Rate" 
            unit="%"
            p1Value={data.pacing.p1_single_msg_rate} 
            p2Value={data.pacing.p2_single_msg_rate} 
          />
        </div>

        {/* Shared Vocabulary */}
        <div className="bg-[#161b22] border border-gray-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2 text-white font-bold text-lg">
              <Hash className="w-5 h-5 text-green-500" /> Shared Vocabulary
            </div>
            <div className="bg-green-900/20 text-green-400 px-3 py-1 rounded-full text-sm font-bold border border-green-500/30">
              {data.vocabulary.similarity_pct}% Overlap
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.vocabulary.shared_words.map((w: string, i: number) => (
              <span key={i} className="px-3 py-1.5 bg-[#0d1117] border border-gray-700 rounded-lg text-gray-300 font-mono text-sm">
                {w}
              </span>
            ))}
            {data.vocabulary.shared_words.length === 0 && (
              <span className="text-gray-500">No significant vocabulary overlap found in the top 50 words.</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
