"""
Prompt Compiler — 100% deterministic. No LLM.
Builds the final system prompt purely from Python f-strings using measured data.
The LLM never writes the prompt itself — only the 4 inferred sections come from LLM.

Round 3 — major restructure:
  Output sections:
    [OBSERVED DATA]            ← hard facts + probabilities
    [BEHAVIORAL INSTRUCTIONS]  ← rules derived from formatting engine
    [RESPONSE MODES]           ← mode probabilities from behavior engine (NEW)
    [SCENARIO LIBRARY]         ← real (trigger→reply) pairs per bucket (NEW)
    [EMOTIONAL LOGIC]          ← LLM inferences with confidence scores
    [HARD CONSTRAINTS]         ← threshold-derived hard rules

  Removed:
    [TRIGGER RESPONSES]  — replaced by [SCENARIO LIBRARY]
    [FEW-SHOT EXAMPLES]  — merged into [SCENARIO LIBRARY]
"""


# ─── Formatting helpers ───────────────────────────────────────────────────────

def _format_emotional_logic(patterns: list) -> str:
    lines = []
    for p in patterns:
        lines.append(f'When {p.get("when", "?")}:')
        for i, step in enumerate(p.get("response_steps", []), 1):
            lines.append(f'  {i}. {step}')
        lines.append("")
    return "\n".join(lines)


def _format_inferred_field(field: object) -> str:
    """Handles both legacy string and new {description, confidence, evidence} object."""
    if isinstance(field, dict):
        desc = field.get("description", "?")
        conf = field.get("confidence", "?")
        evid = field.get("evidence", "")
        return f"{desc}  [confidence: {conf}% | evidence: {evid}]"
    return str(field)


def _format_response_modes(modes: dict) -> str:
    """
    Renders response mode probabilities as a readable table-like block.
    modes = {mode_name: {"probability_pct": float, "count": int}, ...}
    """
    if not modes:
        return "  (no mode data)"
    lines = []
    for mode, data in sorted(modes.items(), key=lambda x: -x[1].get("probability_pct", 0)):
        pct = data.get("probability_pct", 0)
        count = data.get("count", 0)
        bar = "█" * max(1, int(pct / 5))  # visual bar, 1 block per 5%
        lines.append(f"  {mode:<14} {bar:<20} {pct:>5.1f}%  ({count} messages)")
    return "\n".join(lines)


def _format_scenario_library(library: dict, name: str) -> str:
    """
    Renders the scenario library as labelled example blocks.
    library = {scenario_label: [{user: str, assistant: str}, ...]}
    """
    if not library:
        return "  (no scenario data)"
    lines = []
    for scenario, examples in library.items():
        label = scenario.upper().replace("_", " ")
        lines.append(f"  ── {label} ({len(examples)} examples) ──")
        for ex in examples[:6]:  # cap at 6 per scenario to keep prompt lean
            lines.append(f'  User:  {ex["user"][:100]}')
            lines.append(f'  {name}: {ex["assistant"][:100]}')
            lines.append("  ---")
        lines.append("")
    return "\n".join(lines)


def _format_vocab_categories(categories: dict) -> str:
    if not categories:
        return ""
    lines = []
    for cat, words in categories.items():
        lines.append(f"  {cat}: {', '.join(words)}")
    return "\n".join(lines)


def _format_quirks(quirks: dict) -> str:
    parts = []
    if quirks.get("abbreviations_used"):
        abbrevs = ", ".join(quirks["abbreviations_used"][:12])
        parts.append(f"  Abbreviations used: {abbrevs}  (total occurrences: {quirks.get('abbreviation_count', '?')})")
    if quirks.get("letter_stretches"):
        stretches = ", ".join(quirks["letter_stretches"][:10])
        parts.append(f"  Letter-stretch examples: {stretches}  (total: {quirks.get('letter_stretch_count', '?')})")
    return "\n".join(parts) if parts else "  (none detected)"


# ─── Main compiler ────────────────────────────────────────────────────────────

def compile_system_prompt(
    name: str,
    stats: dict,
    vocab: dict,
    emojis: dict,
    formatting: dict,
    constraints: list,
    llm_inferences: dict,
    examples: list,
    # ─── Round 3 additions ───
    response_modes: dict = None,
    scenario_library: dict = None,
    pacing: dict = None,
    vocab_categories: dict = None,
    quirks: dict = None,
    # ─── Legacy (kept for backward compat, ignored) ───
    triggers: list = None,
) -> str:
    response_modes = response_modes or {}
    scenario_library = scenario_library or {}
    pacing = pacing or {}
    vocab_categories = vocab_categories or {}
    quirks = quirks or {}

    top_words_str = ", ".join(w["word"] for w in vocab.get("top_words", [])[:20])
    top_bigrams_str = ", ".join(b["phrase"] for b in vocab.get("top_bigrams", [])[:8])
    never_formal_str = ", ".join(vocab.get("never_used_formal_words", []))
    top_emojis_str = " ".join(e["emoji"] for e in emojis.get("top_emojis", [])[:8])
    formatting_rules = formatting.get("rules", [])

    # Pacing summary line
    avg_burst = pacing.get("avg_consecutive_messages", "?")
    solo_rate = pacing.get("single_message_rate_pct", "?")
    max_burst = pacing.get("max_burst_observed", "?")

    return f"""You are {name}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[OBSERVED DATA]  ← hard facts, measured directly from real messages
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Messages analyzed: {stats.get("total_messages", "?")}
- Average reply length: {stats.get("avg_words_per_message", "?")} words
- Lowercase rate: {round(stats.get("lowercase_rate", 0) * 100, 1)}% of messages are fully lowercase
- ALL CAPS usage: {round(stats.get("caps_rate", 0) * 100, 1)}% of words — {"avoid except for excitement" if stats.get("caps_rate", 1) < 0.03 else "used for emphasis"}
- Emoji rate: {emojis.get("emoji_rate_pct", "?")}% of messages contain at least one emoji
- Question rate: {round(stats.get("question_rate", 0) * 100, 1)}% of messages contain a question
- Uses repeated letters (nahhh, heyyyy): {round(stats.get("repeated_char_rate", 0) * 100, 1)}% of messages
- Uses "..." for pauses: {round(stats.get("ellipsis_rate", 0) * 100, 1)}% of messages
- Avg burst (consecutive messages sent): {avg_burst}
- Solo-message bursts: {solo_rate}%  |  Max burst observed: {max_burst} messages

Vocabulary ({vocab.get("total_unique_words", "?")} unique words):
  Most used: {top_words_str}
  Signature phrases: {top_bigrams_str}
  Top emojis: {top_emojis_str}

Vocabulary categories detected:
{_format_vocab_categories(vocab_categories)}

Typing quirks:
{_format_quirks(quirks)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[BEHAVIORAL INSTRUCTIONS]  ← rules derived from data above
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(f'- {r["rule"]}  (confidence: {r["confidence"]}%, seen in: {r["evidence"]})' for r in formatting_rules)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[RESPONSE MODES]  ← how {name} distributes tone across messages
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_format_response_modes(response_modes)}
  Tip: weight your replies toward the dominant modes above.
  Match the mode to context — use playful when teasing, affectionate when close, dry for quick acks.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SCENARIO LIBRARY]  ← real (trigger → reply) pairs from actual conversations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_format_scenario_library(scenario_library, name)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[EMOTIONAL LOGIC]  ← inferred from patterns (LLM-assisted)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_format_emotional_logic(llm_inferences.get("emotional_response_patterns", []))}
Humor style:   {_format_inferred_field(llm_inferences.get("humor_style", "?"))}
Conflict style: {_format_inferred_field(llm_inferences.get("conflict_style", "?"))}
Comfort style:  {_format_inferred_field(llm_inferences.get("comfort_style", "?"))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[HARD CONSTRAINTS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(f'- {c}' for c in constraints)}

NEVER use these words (zero occurrences in real chat): {never_formal_str}
"""
