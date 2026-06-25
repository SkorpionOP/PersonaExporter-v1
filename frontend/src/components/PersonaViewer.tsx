import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Download, ArrowLeft, BarChart2, Brain, Quote, MessageSquare, PenTool, ShieldAlert, Zap, Hash, Activity } from "lucide-react";
import { motion } from "framer-motion";
import axios from "axios";

const Section = ({ icon: Icon, title, color, children, delay = 0, span = 1 }: any) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    style={{ gridColumn: `span ${span} / span ${span}` }}
    className="rounded-3xl bg-white/5 border border-white/10 p-8"
  >
    <div className="flex items-center gap-3 mb-6">
      <Icon className={`w-5 h-5 ${color}`} />
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
    </div>
    {children}
  </motion.div>
);

const Tag = ({ label, variant = "neutral" }: any) => {
  const styles: any = {
    neutral: "bg-white/10 border-white/20 text-white/80",
    green: "bg-green-500/15 border-green-500/30 text-green-300",
    red: "bg-red-500/15 border-red-500/30 text-red-300",
    blue: "bg-blue-500/15 border-blue-500/30 text-blue-300",
  };
  return (
    <span className={`inline-flex px-3 py-1 rounded-full text-sm border ${styles[variant]}`}>
      {label}
    </span>
  );
};

const StatRow = ({ label, value, unit = "" }: any) => (
  <div className="flex items-center justify-between py-2 border-b border-white/5">
    <span className="text-white/50 text-sm">{label}</span>
    <span className="font-mono font-medium text-white">{value}{unit}</span>
  </div>
);

export function PersonaViewer() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [persona, setPersona] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`http://localhost:8000/api/persona/${id}`)
      .then(res => setPersona(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="flex min-h-screen items-center justify-center text-white/50 text-lg">Decoding persona...</div>;
  if (!persona) return <div className="flex min-h-screen items-center justify-center text-white/50">Persona not found.</div>;

  const d = persona.data;
  const ts = d.target_stats || {};
  const vocab = d.vocab || {};
  const emojis = d.emojis || {};
  const formatting = d.formatting || {};
  const constraints = d.constraints || [];
  const llm = d.llm_inferences || {};
  const triggers = d.triggers || [];
  const examples = d.real_examples || [];
  const responseModes = d.response_modes || {};
  const scenarioLibrary = d.scenario_library || {};
  const pacing = d.pacing || {};
  const vocabCategories = d.vocab_categories || {};
  const quirks = d.quirks || {};

  // Helper: render a field that may be a plain string or {description, confidence, evidence}
  const renderInferredField = (field: any) => {
    if (!field) return null;
    if (typeof field === 'string') return { desc: field, confidence: null, evidence: null };
    return { desc: field.description, confidence: field.confidence, evidence: field.evidence };
  };

  return (
    <div className="min-h-screen p-6 md:p-10 max-w-[1400px] mx-auto text-white">
      {/* Header */}
      <motion.header initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-10">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate("/")} className="p-2 hover:bg-white/10 rounded-full transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{persona.name}</h1>
            <p className="text-white/40 text-sm mt-0.5">{ts.total_messages?.toLocaleString()} messages analyzed</p>
          </div>
        </div>
        <button
          onClick={() => window.location.href = `http://localhost:8000/api/persona/${id}/download`}
          className="flex items-center gap-2 px-5 py-2.5 bg-white text-black font-semibold rounded-full hover:bg-white/90 transition-colors text-sm"
        >
          <Download className="w-4 h-4" />
          Export PersonaPack
        </button>
      </motion.header>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">

        {/* ── Measured Statistics ─────────────────────────────────────────── */}
        <Section icon={Activity} title="Measured Statistics" color="text-blue-400" delay={0.05} span={4}>
          <StatRow label="Total Messages" value={ts.total_messages?.toLocaleString()} />
          <StatRow label="Avg Words / Message" value={ts.avg_words_per_message} />
          <StatRow label="Avg Word Length" value={ts.avg_word_length} unit=" chars" />
          <StatRow label="Lowercase Rate" value={Math.round((ts.lowercase_rate||0)*100)} unit="%" />
          <StatRow label="Emoji Rate" value={emojis.emoji_rate_pct} unit="%" />
          <StatRow label="Question Rate" value={Math.round((ts.question_rate||0)*100)} unit="%" />
          <StatRow label="Ellipsis Rate" value={Math.round((ts.ellipsis_rate||0)*100)} unit="%" />
          <StatRow label="Stretched Letters" value={Math.round((ts.repeated_char_rate||0)*100)} unit="%" />
          <StatRow label="Greeting Rate" value={Math.round((ts.greeting_rate||0)*100)} unit="%" />
          <StatRow label="Media Sent" value={ts.media_messages?.toLocaleString()} />
        </Section>

        {/* ── Vocabulary ──────────────────────────────────────────────────── */}
        <Section icon={Hash} title="Vocabulary (real word frequency)" color="text-purple-400" delay={0.1} span={8}>
          <p className="text-white/40 text-xs mb-4 uppercase tracking-wider">Top 20 words — {vocab.total_unique_words?.toLocaleString()} unique total</p>
          <div className="flex flex-wrap gap-2 mb-6">
            {vocab.top_words?.slice(0, 20).map((w: any, i: number) => (
              <span key={i} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/10 border border-white/10 text-sm font-mono">
                <span>{w.word}</span>
                <span className="text-white/30 text-xs">{w.count}</span>
              </span>
            ))}
          </div>
          <p className="text-white/40 text-xs mb-3 uppercase tracking-wider">Signature bigrams (phrases)</p>
          <div className="flex flex-wrap gap-2 mb-6">
            {vocab.top_bigrams?.slice(0, 8).map((b: any, i: number) => (
              <Tag key={i} label={`"${b.phrase}" ×${b.count}`} variant="blue" />
            ))}
          </div>
          <p className="text-white/40 text-xs mb-3 uppercase tracking-wider">Never uses (formal words with 0 occurrences)</p>
          <div className="flex flex-wrap gap-2">
            {vocab.never_used_formal_words?.map((w: string, i: number) => (
              <Tag key={i} label={w} variant="red" />
            ))}
          </div>
        </Section>

        {/* ── Emoji Profile ───────────────────────────────────────────────── */}
        <Section icon={MessageSquare} title="Emoji Profile" color="text-yellow-400" delay={0.15} span={4}>
          <StatRow label="Total Emojis Sent" value={emojis.total_emojis_sent?.toLocaleString()} />
          <StatRow label="Unique Emojis" value={emojis.unique_emojis} />
          <div className="mt-5 space-y-3">
            {emojis.top_emojis?.map((e: any, i: number) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-2xl w-8">{e.emoji}</span>
                <div className="flex-1">
                  <div className="flex justify-between text-xs text-white/40 mb-1">
                    <span>{e.count} times</span>
                    <span>{e.frequency_pct}%</span>
                  </div>
                  <div className="h-1 rounded-full bg-white/10">
                    <div className="h-1 rounded-full bg-yellow-400" style={{ width: `${Math.min(e.frequency_pct * 2, 100)}%` }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* ── Formatting Rules ─────────────────────────────────────────────── */}
        <Section icon={PenTool} title="Formatting Rules (data-derived)" color="text-pink-400" delay={0.2} span={8}>
          <div className="space-y-4">
            {formatting.rules?.map((rule: any, i: number) => (
              <div key={i} className="bg-black/30 rounded-2xl p-5 border border-white/5">
                <div className="flex items-center justify-between mb-2">
                  <p className="font-medium text-white">{rule.rule}</p>
                  <span className="text-xs font-mono text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">
                    {rule.confidence}% confidence
                  </span>
                </div>
                <p className="text-white/40 text-sm">{rule.evidence}</p>
                {rule.examples && rule.examples.length > 0 && (
                  <div className="mt-3 flex flex-col gap-1">
                    {rule.examples.slice(0, 2).map((ex: string, j: number) => (
                      <span key={j} className="text-xs text-white/60 font-mono italic">"{ex}"</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>

        {/* ── Emotional Logic (LLM) ────────────────────────────────────────── */}
        <Section icon={Brain} title="Emotional Logic (LLM inferred)" color="text-violet-400" delay={0.25} span={6}>
          <div className="space-y-5">
            {llm.emotional_response_patterns?.map((p: any, i: number) => (
              <div key={i} className="bg-gradient-to-r from-violet-900/30 to-transparent rounded-2xl p-5 border border-violet-500/20">
                <p className="text-white/50 text-xs mb-3 uppercase tracking-wider">When {p.when}</p>
                <div className="flex flex-col gap-1.5">
                  {p.response_steps?.map((step: string, j: number) => (
                    <div key={j} className="flex items-start gap-2">
                      <span className="text-violet-400 font-mono text-xs mt-0.5">{j + 1}.</span>
                      <span className="text-white/80 text-sm">{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {llm.humor_style && (
              <div className="pt-4 border-t border-white/10 space-y-3">
                {([['Humor', llm.humor_style], ['Conflict', llm.conflict_style], ['Comfort', llm.comfort_style]] as [string, any][]).map(([label, field]) => {
                  const f = renderInferredField(field);
                  if (!f) return null;
                  return (
                    <div key={label}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-white/40 text-xs uppercase">{label}</span>
                        {f.confidence != null && (
                          <span className="text-xs font-mono text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded-full">{f.confidence}% confidence</span>
                        )}
                      </div>
                      <p className="text-white/80 text-sm">{f.desc}</p>
                      {f.evidence && <p className="text-white/30 text-xs mt-0.5 italic">{f.evidence}</p>}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Section>

        {/* ── Response Modes ───────────────────────────────────────────────── */}
        {Object.keys(responseModes).length > 0 && (
          <Section icon={BarChart2} title="Response Modes (tone distribution)" color="text-cyan-400" delay={0.28} span={6}>
            <div className="space-y-3">
              {Object.entries(responseModes)
                .sort(([, a]: any, [, b]: any) => b.probability_pct - a.probability_pct)
                .map(([mode, data]: any) => (
                  <div key={mode}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white/70 text-sm capitalize">{mode}</span>
                      <span className="font-mono text-xs text-cyan-300">{data.probability_pct}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-white/10">
                      <div className="h-1.5 rounded-full bg-cyan-400/70" style={{ width: `${Math.min(data.probability_pct, 100)}%` }} />
                    </div>
                    <p className="text-white/30 text-xs mt-0.5">{data.count} messages</p>
                  </div>
                ))}
            </div>
          </Section>
        )}

        {/* ── Pacing Stats ─────────────────────────────────────────────────── */}
        {pacing.avg_consecutive_messages && (
          <Section icon={Activity} title="Conversation Pacing (burst analysis)" color="text-amber-400" delay={0.29} span={6}>
            <StatRow label="Avg Consecutive Messages" value={pacing.avg_consecutive_messages} />
            <StatRow label="Single-Message Bursts" value={pacing.single_message_rate_pct} unit="%" />
            <StatRow label="Multi-Message Bursts" value={pacing.multi_message_burst_rate_pct} unit="%" />
            <StatRow label="Max Burst Observed" value={pacing.max_burst_observed} unit=" msgs" />
            {pacing.burst_distribution && (
              <div className="mt-4">
                <p className="text-white/40 text-xs uppercase mb-2">Burst distribution</p>
                <div className="space-y-1.5">
                  {Object.entries(pacing.burst_distribution).map(([k, v]: any) => (
                    <div key={k} className="flex items-center gap-2 text-xs">
                      <span className="text-white/40 w-20">{k.replace('_messages','')}</span>
                      <div className="flex-1 h-1 bg-white/10 rounded-full">
                        <div className="h-1 rounded-full bg-amber-400/60" style={{ width: `${Math.min(v, 100)}%` }} />
                      </div>
                      <span className="font-mono text-amber-300">{v}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

        {/* ── Hard Constraints ─────────────────────────────────────────────── */}
        <Section icon={ShieldAlert} title="Hard Constraints (rule-derived)" color="text-red-400" delay={0.3} span={6}>
          <div className="flex flex-col gap-2">
            {constraints.map((c: string, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-black/30 rounded-xl border border-white/5">
                <span className="text-red-400 mt-0.5">⊗</span>
                <span className="text-white/80 text-sm">{c}</span>
              </div>
            ))}
          </div>
        </Section>

        {/* ── Scenario Library ─────────────────────────────────────────────── */}
        {Object.keys(scenarioLibrary).length > 0 && (
          <Section icon={Zap} title="Scenario Library (real trigger → reply pairs)" color="text-orange-400" delay={0.35} span={12}>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {Object.entries(scenarioLibrary).map(([scenario, exs]: any) => (
                <div key={scenario} className="bg-black/40 rounded-2xl p-5 border border-white/5">
                  <p className="text-white/40 text-xs mb-3 uppercase tracking-wider font-semibold">{scenario.replace(/_/g, ' ')} — {exs.length} pairs</p>
                  <div className="flex flex-col gap-3">
                    {exs.slice(0, 4).map((ex: any, j: number) => (
                      <div key={j} className="text-sm border-b border-white/5 pb-3 last:border-0 last:pb-0">
                        <p className="text-white/40 text-xs mb-0.5">→ trigger</p>
                        <p className="text-white/60 italic mb-1.5">"{ex.trigger || ex.user}"</p>
                        <p className="text-white/40 text-xs mb-0.5">{persona.name} replied</p>
                        <p className="text-orange-300 font-mono text-xs">"{ex.response || ex.assistant}"</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* ── Vocabulary Categories + Quirks ───────────────────────────────── */}
        {(Object.keys(vocabCategories).length > 0 || quirks.abbreviations_used?.length > 0) && (
          <Section icon={Hash} title="Vocabulary Categories & Quirks" color="text-lime-400" delay={0.38} span={6}>
            {Object.keys(vocabCategories).length > 0 && (
              <div className="mb-5">
                <p className="text-white/40 text-xs uppercase mb-3">Word categories detected</p>
                <div className="space-y-2">
                  {Object.entries(vocabCategories).map(([cat, words]: any) => (
                    <div key={cat} className="flex flex-wrap items-center gap-2">
                      <span className="text-white/30 text-xs w-24 capitalize">{cat.replace(/_/g, ' ')}</span>
                      <div className="flex flex-wrap gap-1">
                        {words.map((w: string) => (
                          <span key={w} className="text-xs px-2 py-0.5 rounded-md bg-lime-500/10 border border-lime-500/20 text-lime-300 font-mono">{w}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {quirks.abbreviations_used?.length > 0 && (
              <div className="mb-4">
                <p className="text-white/40 text-xs uppercase mb-2">Abbreviations used <span className="text-lime-400 normal-case">({quirks.abbreviation_count} total)</span></p>
                <div className="flex flex-wrap gap-1">
                  {quirks.abbreviations_used.map((a: string) => (
                    <span key={a} className="text-xs px-2 py-0.5 rounded-md bg-white/10 border border-white/10 text-white/70 font-mono">{a}</span>
                  ))}
                </div>
              </div>
            )}
            {quirks.letter_stretches?.length > 0 && (
              <div>
                <p className="text-white/40 text-xs uppercase mb-2">Letter-stretch patterns <span className="text-lime-400 normal-case">({quirks.letter_stretch_count} total)</span></p>
                <div className="flex flex-wrap gap-1">
                  {quirks.letter_stretches.map((s: string) => (
                    <span key={s} className="text-xs px-2 py-0.5 rounded-md bg-white/10 border border-white/10 text-white/70 font-mono italic">{s}</span>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

        {/* ── Few-Shot Examples ────────────────────────────────────────────── */}
        <Section icon={MessageSquare} title={`Few-Shot Examples (${examples.length} real conversations)`} color="text-teal-400" delay={0.4} span={12}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {examples.slice(0, 30).map((ex: any, i: number) => (
              <div key={i} className="bg-black/40 p-5 rounded-2xl flex flex-col gap-3 border border-white/5">
                <div>
                  <span className="text-xs text-white/30 uppercase">User</span>
                  <div className="mt-1 bg-white/10 px-4 py-2 rounded-2xl rounded-tl-sm text-sm text-white/80">{ex.user}</div>
                </div>
                <div className="items-end flex flex-col">
                  <span className="text-xs text-white/30 uppercase">{persona.name}</span>
                  <div className="mt-1 bg-teal-600/40 px-4 py-2 rounded-2xl rounded-tr-sm text-sm text-white/90">{ex.assistant}</div>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* ── System Prompt ────────────────────────────────────────────────── */}
        <Section icon={Quote} title="Compiled System Prompt" color="text-green-400" delay={0.45} span={12}>
          <pre className="bg-black/60 p-8 rounded-2xl overflow-x-auto text-sm text-green-300 font-mono whitespace-pre-wrap leading-relaxed border border-green-500/10">
            {d.system_prompt || "No prompt compiled."}
          </pre>
        </Section>

      </div>
    </div>
  );
}
