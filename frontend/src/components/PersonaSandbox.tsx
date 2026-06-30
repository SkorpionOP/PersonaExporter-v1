import { useState, useRef, useEffect } from "react"
import { useParams, Link } from "react-router-dom"

type Message = {
  role: "user" | "assistant"
  content: string
}

type Reasoning = {
  detected_intent?: { scenario: string; emotion: string; topic: string }
  retrieved_memories?: Array<{ message: string; score: number; scenario: string; topic: string; emotion: string }>
  similarity_scores?: number[]
}

export function PersonaSandbox() {
  const { id } = useParams()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [lastReasoning, setLastReasoning] = useState<Reasoning | null>(null)
  
  const endOfMessagesRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userMsg = input
    setInput("")
    setMessages(prev => [...prev, { role: "user", content: userMsg }])
    setLoading(true)

    try {
      const res = await fetch(`http://localhost:8000/api/chat/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_msg: userMsg,
          chat_history: messages.slice(-5) // Send last 5 context
        })
      })

      if (!res.ok) throw new Error("Failed to send message")
      
      const data = await res.json()
      setMessages(prev => [...prev, { role: "assistant", content: data.reply }])
      setLastReasoning(data.reasoning)
    } catch (e) {
      console.error(e)
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, the runtime encountered an error." }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-[#0d1117] text-gray-200">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col border-r border-gray-800 relative">
        {/* Header */}
        <div className="h-16 flex items-center px-6 border-b border-gray-800 bg-[#161b22] shrink-0 justify-between">
          <div>
            <h1 className="text-xl font-bold">Persona Runtime</h1>
            <p className="text-sm text-gray-400">Digital Twin Sandbox</p>
          </div>
          <Link to={`/persona/${id}`} className="text-sm bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-md transition-colors">
            Back to Report
          </Link>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-4">
              <div className="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center text-2xl">🤖</div>
              <p>Start chatting with the dynamic persona.</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[70%] rounded-2xl px-5 py-3 ${
                m.role === "user" 
                  ? "bg-blue-600 text-white rounded-br-none" 
                  : "bg-[#21262d] text-gray-200 rounded-bl-none border border-gray-700"
              }`}>
                <p className="whitespace-pre-wrap">{m.content}</p>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-[#21262d] text-gray-400 rounded-2xl rounded-bl-none px-5 py-3 border border-gray-700">
                <span className="animate-pulse">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={endOfMessagesRef} />
        </div>

        {/* Input */}
        <div className="p-4 bg-[#161b22] border-t border-gray-800 shrink-0">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Type a message..."
              className="flex-1 bg-[#0d1117] border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500 transition-colors"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 rounded-lg font-medium transition-colors"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Reasoning Side Panel */}
      <div className="w-96 bg-[#161b22] flex flex-col shrink-0 overflow-y-auto">
        <div className="h-16 flex items-center px-6 border-b border-gray-800 shrink-0 bg-[#161b22] sticky top-0">
          <h2 className="text-lg font-bold">RAG Diagnostic Panel</h2>
        </div>
        
        <div className="p-6 space-y-8">
          {!lastReasoning ? (
            <p className="text-gray-500 text-sm text-center mt-10">Send a message to see the retrieval pipeline in action.</p>
          ) : (
            <>
              {/* Intent */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">Detected Intent</h3>
                <div className="bg-[#0d1117] border border-gray-800 rounded-lg p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Scenario</span>
                    <span className="font-medium text-blue-400">{lastReasoning.detected_intent?.scenario}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Emotion</span>
                    <span className="font-medium text-purple-400">{lastReasoning.detected_intent?.emotion}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Topic</span>
                    <span className="font-medium text-green-400">{lastReasoning.detected_intent?.topic}</span>
                  </div>
                </div>
              </div>

              {/* Retrieved Memories */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">Retrieved FAISS Memories</h3>
                <div className="space-y-3">
                  {lastReasoning.retrieved_memories?.map((mem, i) => (
                    <div key={i} className="bg-[#0d1117] border border-gray-800 rounded-lg p-4 relative overflow-hidden group">
                      <div className="absolute top-0 left-0 w-1 h-full bg-blue-500/20 group-hover:bg-blue-500 transition-colors" />
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-medium bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded">
                          Sim Score: {(mem.score * 100).toFixed(1)}%
                        </span>
                        <span className="text-xs text-gray-500">{mem.scenario}</span>
                      </div>
                      <p className="text-sm text-gray-300 italic mb-2 line-clamp-3">"{mem.message}"</p>
                    </div>
                  ))}
                  {(!lastReasoning.retrieved_memories || lastReasoning.retrieved_memories.length === 0) && (
                    <p className="text-sm text-gray-500">No memories matched confidence threshold.</p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
