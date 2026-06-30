"""
Prompt Compiler — 100% deterministic. No LLM.
Builds the final persona output into a strict 4-Layer architecture.
"""

def _format_evidence_block(block: dict) -> str:
    if not block:
        return "  (No evidence available)"
    conf = block.get('confidence', '?')
    det = block.get('detected', '?')
    lines = [
        f"  Confidence: {conf}%",
        f"  Detected: {det}"
    ]
    if block.get('examples'):
        lines.append("  Examples:")
        for ex in block.get('examples', []):
            lines.append(f"    - {ex}")
    return "\n".join(lines)


def _format_llm_inference(title: str, content: dict) -> str:
    if not content:
        return ""
    lines = [f"{title}"]
    
    for k, v in content.items():
        if k == "evidence_block":
            continue
        if isinstance(v, list):
            lines.append(f"  {k.replace('_', ' ').capitalize()}: {', '.join(v)}")
        else:
            lines.append(f"  {k.replace('_', ' ').capitalize()}: {v}")
            
    lines.append(_format_evidence_block(content.get("evidence_block", {})))
    lines.append("")
    return "\n".join(lines)


def _format_topic_graph(topic_graph: dict) -> str:
    if not topic_graph:
        return "  (No topics detected)"
    lines = []
    for topic, data in sorted(topic_graph.items(), key=lambda x: -x[1].get("percentage", 0)):
        pct = data.get("percentage", 0)
        conf = data.get("confidence", 0)
        lines.append(f"  {topic}: {pct}% (Confidence: {conf}%)")
        lines.append(f"    Avg length: {data.get('average_reply_length')} words")
        if data.get('most_common_words'):
            lines.append(f"    Common words: {', '.join(data['most_common_words'])}")
        wt = data.get('weighted_transitions')
        if wt:
            wt_str = ", ".join(f"{k} ({v})" for k, v in wt.items())
            lines.append(f"    Transitions to: {wt_str}")
    return "\n".join(lines)


def _format_response_modes(modes: dict) -> str:
    if not modes:
        return "  (no mode data)"
    lines = []
    for mode, data in sorted(modes.items(), key=lambda x: -float(x[1].strip('%')) if isinstance(x[1], str) else 0):
        lines.append(f"  {mode}: {data}")
    return "\n".join(lines)


def _format_scenario_library(library: dict, name: str) -> str:
    if not library:
        return "  (no scenario data)"
    lines = []
    for scenario, examples in library.items():
        label = scenario.title()
        lines.append(f"  [{label}]")
        for ex in examples[:3]:  # cap at 3 per scenario to keep prompt lean
            lines.append(f'    User: {ex["user"][:100]}')
            lines.append(f'    {name}: {ex["assistant"][:100]}')
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
    if quirks.get("preferred_spellings"):
        spellings = ", ".join([f"{v} (over {k})" for k, v in quirks["preferred_spellings"].items()])
        parts.append(f"  Preferred Spellings: {spellings}")
    return "\n".join(parts) if parts else "  (none detected)"


def compile_system_prompt(
    name: str,
    stats: dict,
    vocab: dict,
    emojis: dict,
    formatting: dict,
    constraints: list,
    llm_inferences: dict,
    examples: list,
    response_modes: dict = None,
    scenario_library: dict = None,
    pacing: dict = None,
    vocab_categories: dict = None,
    quirks: dict = None,
    topic_graph: dict = None,
    triggers: list = None,
    linguistics: dict = None,
    conversation_graph: dict = None,
    communication_signature: list = None,
) -> dict:
    response_modes = response_modes or {}
    scenario_library = scenario_library or {}
    pacing = pacing or {}
    vocab_categories = vocab_categories or {}
    quirks = quirks or {}
    topic_graph = topic_graph or {}
    linguistics = linguistics or {}
    conversation_graph = conversation_graph or {}
    communication_signature = communication_signature or []
    
    words_stats = stats.get("words", {})
    timing_stats = stats.get("timing", {})
    lexical = linguistics.get("lexical_richness", {})

    layer1 = f"""━━━━━━━━━━━━━━
LAYER 1: Statistics
━━━━━━━━━━━━━━
Messages Analyzed: {stats.get("total_messages", "?")}
Words:
  Average: {words_stats.get("average", "?")}
  Median: {words_stats.get("median", "?")}
  P90: {words_stats.get("p90", "?")}
  Longest: {words_stats.get("longest", "?")}

Activity Timing:
  Morning: {timing_stats.get("morning_pct", "?")}%
  Night: {timing_stats.get("night_pct", "?")}%

Burst stats:
  Avg burst length: {pacing.get("avg_consecutive_messages", "?")}
  Solo message rate: {pacing.get("single_message_rate_pct", "?")}%

Linguistics:
  Avg Sentence Length: {linguistics.get("sentence_metrics", {}).get("average_length", "?")} words
  Avg Clauses: {linguistics.get("sentence_metrics", {}).get("average_clauses", "?")}
  One-word replies: {linguistics.get("sentence_metrics", {}).get("one_word_replies_pct", "?")}%
  Emojis per msg: {linguistics.get("structure_metrics", {}).get("emojis_per_message", "?")}
  Questions per msg: {linguistics.get("structure_metrics", {}).get("questions_per_message", "?")}

Lexical Richness:
  Unique Words: {lexical.get("unique_words", "?")}
  Type-Token Ratio: {lexical.get("type_token_ratio", "?")}
  Repetition Score: {lexical.get("repetition_score", "?")}%
"""

    layer2 = f"""━━━━━━━━━━━━━━
LAYER 2: Observed Patterns
━━━━━━━━━━━━━━
Vocabulary Categories:
{_format_vocab_categories(vocab_categories)}

Topic Graph:
{_format_topic_graph(topic_graph)}

Quirks:
{_format_quirks(quirks)}

Message Types:
{_format_response_modes(response_modes)}

Scenario Library:
{_format_scenario_library(scenario_library, name)}"""

    layer3_blocks = []
    for key, val in llm_inferences.items():
        if key == "error": continue
        title = key.replace('_', ' ').title()
        layer3_blocks.append(_format_llm_inference(title, val))

    layer3 = "━━━━━━━━━━━━━━\nLAYER 3: Behavior Model\n━━━━━━━━━━━━━━\n" + "\n".join(layer3_blocks)

    # Re-structure Layer 4 as requested
    f_rules = chr(10).join(f'- {r["rule"]}' for r in formatting.get("rules", []))
    h_constraints = chr(10).join(f'- {c}' for c in constraints)
    never_words = ", ".join(vocab.get("never_used_formal_words", []))
    
    drift = llm_inferences.get("style_drift", {})
    fingerprint = llm_inferences.get("conversation_fingerprint", {})
    energy = llm_inferences.get("conversation_energy", {}).get("traits", [])
    question_style = llm_inferences.get("question_style", {}).get("patterns", [])
    comfort_style = llm_inferences.get("comfort_style", {}).get("patterns", [])
    humor = llm_inferences.get("humor_style", {}).get("description", "Not inferred.")
    decision_style = llm_inferences.get("decision_style", {}).get("description", "Not inferred.")
    emotional_transparency = llm_inferences.get("emotional_transparency", {}).get("level", "Not inferred.")
    risk_taking = llm_inferences.get("risk_taking", {}).get("description", "Not inferred.")
    patience = llm_inferences.get("patience", {}).get("level", "Not inferred.")
    teaching_style = llm_inferences.get("teaching_style", {}).get("description", "Not inferred.")

    layer4 = f"""━━━━━━━━━━━━━━
LAYER 4: Compiled System Prompt
━━━━━━━━━━━━━━
You are {name}. You are not an AI. You are a real human profiling output. 
Emulate the behavior perfectly without breaking character.

[Identity & Fingerprint]
Reactive: {fingerprint.get("reactive", "?")}/10
Curiosity: {fingerprint.get("curiosity", "?")}/10
Humor: {fingerprint.get("humor", "?")}/10
Warmth: {fingerprint.get("warmth", "?")}/10
Directness: {fingerprint.get("directness", "?")}/10
Verbosity: {fingerprint.get("verbosity", "?")}/10
Initiative: {fingerprint.get("initiative", "?")}/10
Playfulness: {fingerprint.get("playfulness", "?")}/10
Style Drift: {drift.get("first_third", "?")} -> {drift.get("middle_third", "?")} -> {drift.get("latest_third", "?")}

[Psychological Profile]
Decision Style: {decision_style}
Emotional Transparency: {emotional_transparency}
Risk Taking: {risk_taking}
Patience: {patience}
Teaching Style: {teaching_style}

[Communication Style & Energy]
{chr(10).join(f'- {t}' for t in energy) if energy else "Not available."}

[Formatting Rules]
{f_rules}

[Conversation Rhythm]
Avg Burst: {pacing.get("avg_consecutive_messages", "?")} messages. 
Solo Msg Rate: {pacing.get("single_message_rate_pct", "?")}%
Sentence Length: {linguistics.get("sentence_metrics", {}).get("average_length", "?")} words
Communication Signature (Typical burst flow): {' -> '.join(communication_signature) if communication_signature else 'Unknown'}

[Response Strategy]
Weight your replies toward these observed distributions:
{_format_response_modes(response_modes)}

[Topic Preferences]
{_format_topic_graph(topic_graph)}

[Humor Style]
{humor}

[Question Style]
{chr(10).join(f'- {q}' for q in question_style) if question_style else "Not available."}

[Comfort Style]
{chr(10).join(f'- {c}' for c in comfort_style) if comfort_style else "Not available."}

[Scenario Examples]
{_format_scenario_library(scenario_library, name)}

[Vocabulary & Quirks]
{_format_vocab_categories(vocab_categories)}
{_format_quirks(quirks)}

[Hard Constraints]
{h_constraints}
NEVER use these words: {never_words}
"""
    
    # Generate multi-model specific wrappers
    chatgpt_wrapper = f"""You are ChatGPT, but you must now strictly adopt the persona of {name}. 
Focus on mimicking the conversational rhythm, formatting rules, and vocabulary precisely. 
Never break character, never offer assistance, and never use typical AI caveats.
---
{layer4}"""

    claude_wrapper = f"""<persona>
You are {name}.
Follow the psychological and behavioral guidelines outlined below strictly.
Pay special attention to the Identity & Fingerprint metrics to inform your tone.
</persona>

<guidelines>
{layer4}
</guidelines>"""

    gemini_wrapper = f"""Adopt the persona of {name}. 
Crucially, you must adhere to the hard constraints and formatting rules to sound human.
Use the scenario examples as a direct reference for how you construct your sentences.
---
{layer4}"""

    return {
        "full_report": "\n\n".join([layer1, layer2, layer3, layer4]),
        "base_prompt": layer4,
        "chatgpt": chatgpt_wrapper,
        "claude": claude_wrapper,
        "gemini": gemini_wrapper
    }
