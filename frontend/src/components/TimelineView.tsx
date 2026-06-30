import { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft, Clock, TrendingUp, TrendingDown, Activity } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"

export function TimelineView() {
  const { id } = useParams()
  const [timeline, setTimeline] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    fetch(`http://localhost:8000/api/persona/${id}/timeline`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to load timeline. The original chat file might have been deleted.")
        return res.json()
      })
      .then(data => {
        const formatted = data.timeline.map((chunk: any) => ({
          name: chunk.period,
          date: `${chunk.start_date.substring(5)} to ${chunk.end_date.substring(5)}`,
          Words: chunk.metrics.avg_words,
          EmojiRate: chunk.metrics.emoji_rate_pct,
          QuestionRate: chunk.metrics.question_rate_pct
        }))
        setTimeline(formatted)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="flex h-screen items-center justify-center text-white/50 bg-[#0d1117] animate-pulse">Analyzing Timeline Drift...</div>
  if (error) return <div className="flex h-screen items-center justify-center text-red-500 bg-[#0d1117] px-8 text-center">{error}</div>

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#161b22] border border-gray-700 p-3 rounded-lg shadow-xl">
          <p className="text-gray-400 text-xs mb-2">{payload[0].payload.date}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2 text-sm font-mono">
              <span style={{ color: entry.color }}>{entry.name}:</span>
              <span className="text-white">{entry.value}</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  }

  return (
    <div className="min-h-screen bg-[#0d1117] text-gray-200 p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="flex items-center gap-4 border-b border-gray-800 pb-6">
          <Link to={`/persona/${id}`} className="p-2 hover:bg-white/10 rounded-full transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <Clock className="w-8 h-8 text-indigo-500" />
              Timeline Drift
            </h1>
            <p className="text-gray-400 mt-1">Visualize how this persona's communication style evolved over time.</p>
          </div>
        </div>

        <div className="bg-[#161b22] border border-gray-800 rounded-2xl p-6">
          <h2 className="text-xl font-bold text-white mb-6">Style Evolution</h2>
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} tickLine={false} />
                <YAxis yAxisId="left" stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" orientation="right" stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                
                <Line 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="Words" 
                  name="Avg Words / Msg"
                  stroke="#3b82f6" 
                  strokeWidth={3}
                  dot={{ r: 4, strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                />
                <Line 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="EmojiRate" 
                  name="Emoji %"
                  stroke="#eab308" 
                  strokeWidth={3}
                  dot={{ r: 4, strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                />
                <Line 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="QuestionRate" 
                  name="Question %"
                  stroke="#ec4899" 
                  strokeWidth={3}
                  dot={{ r: 4, strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                  strokeDasharray="5 5"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {['Words', 'EmojiRate', 'QuestionRate'].map((metric, i) => {
            const first = timeline[0][metric]
            const last = timeline[timeline.length - 1][metric]
            const diff = last - first
            const isUp = diff > 0
            
            return (
              <div key={metric} className="bg-[#161b22] border border-gray-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-gray-400 font-medium">{metric === 'Words' ? 'Verbosity' : metric.replace('Rate', ' Rate')}</h3>
                  {isUp ? <TrendingUp className="w-5 h-5 text-green-500" /> : <TrendingDown className="w-5 h-5 text-red-500" />}
                </div>
                <div className="flex items-end gap-3">
                  <span className="text-3xl font-bold text-white">{last}{metric !== 'Words' && '%'}</span>
                  <span className={`text-sm font-medium mb-1 ${isUp ? 'text-green-500' : 'text-red-500'}`}>
                    {isUp ? '+' : ''}{diff.toFixed(1)}{metric !== 'Words' && '%'} since start
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
