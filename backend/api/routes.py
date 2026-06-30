from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from models.database import get_db
from models.schemas import Upload as UploadModel, Persona as PersonaModel
from parsers import get_parser_for_filename

# Phase 1 Deterministic Engines
from services.cleaning import clean_messages
from services.stats_engine import generate_statistics, compute_target_stats
from services.linguistic_engine import analyze_linguistics
from services.behavior_engine import compute_message_types, compute_pacing, compute_conversation_graph, compute_communication_signature
from services.vocab_engine import extract_vocabulary, categorize_vocabulary, detect_quirks
from services.topic_engine import analyze_topics
from services.scenario_engine import extract_scenario_library
from services.emoji_engine import extract_emojis
from services.formatting import extract_formatting, compute_hard_constraints

from services.llm import infer_behavior_patterns
from services.prompt_compiler import compile_system_prompt
from services.evaluation import extract_holdout_set, evaluate_persona
from pdf.generator import generate_persona_pdf

from pydantic import BaseModel
import json
import zipfile
import io
import os
import random

api_router = APIRouter()

@api_router.get("/")
def get_api_root():
    return {"message": "Welcome to the PersonaForge API"}

async def process_chat_background(upload_id: int, file_path: str, target_person: str, db: Session):
    try:
        upload = db.query(UploadModel).filter(UploadModel.id == upload_id).first()
        if not upload:
            return
        upload.status = "processing"
        db.commit()

        parser = get_parser_for_filename(upload.filename)
        with open(file_path, 'rb') as f:
            conversation = parser.parse(f)
            
        all_messages = clean_messages(conversation.messages)

        # ── 1.5 EXTRACT HOLDOUT SET ────────────────────────────────────────────
        messages, holdout_pairs = extract_holdout_set(all_messages, target_person, count=20)

        # ── 2. PHASE 1: DETERMINISTIC ENGINES ─────────────────────────────────
        global_stats       = generate_statistics(conversation)
        target_stats       = compute_target_stats(messages, target_person)
        linguistics        = analyze_linguistics(messages, target_person)
        
        vocab              = extract_vocabulary(messages, target_person)
        vocab_categories   = categorize_vocabulary(messages, target_person)
        quirks             = detect_quirks(messages, target_person)
        emojis             = extract_emojis(messages, target_person)
        formatting         = extract_formatting(messages, target_person, target_stats)
        constraints        = compute_hard_constraints(target_stats, emojis)
        
        message_types      = compute_message_types(messages, target_person)
        pacing             = compute_pacing(messages, target_person)
        conversation_graph = compute_conversation_graph(messages)
        communication_signature = compute_communication_signature(messages, target_person)
        
        topic_graph        = analyze_topics(messages, target_person)
        scenario_library   = extract_scenario_library(messages, target_person)

        # Triggers and real examples can just be extracted from the scenario library
        # to simplify the pipeline. We take 30 random examples from scenario_library values.
        all_scenarios = []
        for v in scenario_library.values():
            all_scenarios.extend(v)
        real_examples = random.sample(all_scenarios, min(30, len(all_scenarios)))

        # ── 3. LLM INFERENCE ──────────────────────────────────────────────────
        target_msgs = [m for m in messages if m.sender == target_person]
        
        # Style drift sampling: First 50, Middle 50, Last 50
        num_msgs = len(target_msgs)
        first_msgs = target_msgs[:50]
        middle_idx = num_msgs // 2
        middle_msgs = target_msgs[max(0, middle_idx - 25) : min(num_msgs, middle_idx + 25)]
        last_msgs = target_msgs[-50:]
        
        sample_parts = []
        if first_msgs:
            sample_parts.append("--- FIRST 50 MESSAGES ---\n" + "\n".join(f"{m.sender}: {m.content}" for m in first_msgs))
        if middle_msgs:
            sample_parts.append("--- MIDDLE 50 MESSAGES ---\n" + "\n".join(f"{m.sender}: {m.content}" for m in middle_msgs))
        if last_msgs:
            sample_parts.append("--- LAST 50 MESSAGES ---\n" + "\n".join(f"{m.sender}: {m.content}" for m in last_msgs))
            
        conversation_sample = "\n\n".join(sample_parts)
        hard_stats_context = {"stats": target_stats, "vocab": vocab, "emojis": emojis}
        llm_inferences = await infer_behavior_patterns(
            conversation_sample, target_person, hard_stats_context
        )

        # ── 4. COMPILE PROMPT ─────────────────────────────────────────────────
        system_prompt = compile_system_prompt(
            name=target_person,
            stats=target_stats,
            vocab=vocab,
            emojis=emojis,
            formatting=formatting,
            constraints=constraints,
            llm_inferences=llm_inferences,
            examples=real_examples,
            response_modes=message_types,
            scenario_library=scenario_library,
            pacing=pacing,
            vocab_categories=vocab_categories,
            quirks=quirks,
            topic_graph=topic_graph,
            triggers=[], # Deprecated, covered by scenario library
            communication_signature=communication_signature,
        )

        # ── 4.5 EVALUATION ────────────────────────────────────────────────────
        evaluation_results = await evaluate_persona(system_prompt["base_prompt"], holdout_pairs)

        # ── 5. STORE ──────────────────────────────────────────────────────────
        persona_data = {
            "statistics": global_stats,
            "target_stats": target_stats,
            "linguistics": linguistics,
            "vocab": vocab,
            "vocab_categories": vocab_categories,
            "quirks": quirks,
            "emojis": emojis,
            "formatting": formatting,
            "constraints": constraints,
            "llm_inferences": llm_inferences,
            "real_examples": real_examples,
            "response_modes": message_types,
            "pacing": pacing,
            "conversation_graph": conversation_graph,
            "communication_signature": communication_signature,
            "topic_graph": topic_graph,
            "scenario_library": scenario_library,
            "system_prompt": system_prompt,
            "evaluation": evaluation_results,
        }

        persona = PersonaModel(
            name=target_person,
            upload_id=upload.id,
            data=json.dumps(persona_data)
        )
        db.add(persona)
        upload.status = "completed"
        db.commit()

    except Exception as e:
        import traceback
        traceback.print_exc()
        upload = db.query(UploadModel).filter(UploadModel.id == upload_id).first()
        if upload:
            upload.status = f"failed: {str(e)}"
            db.commit()


@api_router.post("/upload")
async def upload_chat(file: UploadFile = File(...), db: Session = Depends(get_db)):
    fn_lower = file.filename.lower()
    if not (fn_lower.endswith('.txt') or fn_lower.endswith('.json')):
        raise HTTPException(status_code=400, detail="Unsupported file format. Must be .txt (WhatsApp) or .json (Telegram).")

    content = await file.read()

    upload_entry = UploadModel(filename=file.filename, status="pending")
    db.add(upload_entry)
    db.commit()
    db.refresh(upload_entry)

    ext = os.path.splitext(file.filename)[1]
    file_path = f"uploads/{upload_entry.id}{ext}"
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        parser = get_parser_for_filename(file.filename)
        file_io = io.BytesIO(content)
        conversation = parser.parse(file_io)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse chat: {str(e)}")

    return {
        "upload_id": upload_entry.id,
        "participants": conversation.participants,
        "message": "File uploaded successfully.",
    }


class ProcessRequest(BaseModel):
    target_person: str

@api_router.post("/process/{upload_id}")
async def process_chat(upload_id: int, request: ProcessRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    upload_entry = db.query(UploadModel).filter(UploadModel.id == upload_id).first()
    if not upload_entry:
        raise HTTPException(status_code=404, detail="Upload not found")

    ext = os.path.splitext(upload_entry.filename)[1]
    file_path = f"uploads/{upload_entry.id}{ext}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on server")

    background_tasks.add_task(process_chat_background, upload_entry.id, file_path, request.target_person, db)
    return {"message": "Processing started."}


@api_router.get("/status/{upload_id}")
def get_status(upload_id: int, db: Session = Depends(get_db)):
    upload = db.query(UploadModel).filter(UploadModel.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    response = {"status": upload.status}
    if upload.status == "completed":
        persona = db.query(PersonaModel).filter(PersonaModel.upload_id == upload_id).first()
        if persona:
            response["persona_id"] = persona.id
    return response


@api_router.get("/persona/{persona_id}")
def get_persona(persona_id: int, db: Session = Depends(get_db)):
    persona = db.query(PersonaModel).filter(PersonaModel.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return {
        "id": persona.id,
        "name": persona.name,
        "data": json.loads(persona.data)
    }


@api_router.get("/persona/{persona_id}/download")
def download_persona_pack(persona_id: int, db: Session = Depends(get_db)):
    persona = db.query(PersonaModel).filter(PersonaModel.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    persona_data = json.loads(persona.data)
    pdf_bytes = generate_persona_pdf(persona_data, chart_base64=None)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("persona.pdf", pdf_bytes)
        zf.writestr("persona.json", json.dumps(persona_data, indent=2))
        
        sys_prompt_data = persona_data.get("system_prompt", {})
        if isinstance(sys_prompt_data, dict):
            zf.writestr("system_prompt_base.txt", sys_prompt_data.get("base_prompt", ""))
            zf.writestr("system_prompt_chatgpt.txt", sys_prompt_data.get("chatgpt", ""))
            zf.writestr("system_prompt_claude.txt", sys_prompt_data.get("claude", ""))
            zf.writestr("system_prompt_gemini.txt", sys_prompt_data.get("gemini", ""))
            zf.writestr("full_report.txt", sys_prompt_data.get("full_report", ""))
        else:
            zf.writestr("system_prompt.txt", sys_prompt_data)
            
        zf.writestr("statistics.json", json.dumps(persona_data.get("target_stats", {}), indent=2))
        if "evaluation" in persona_data:
            zf.writestr("evaluation_report.json", json.dumps(persona_data.get("evaluation", {}), indent=2))

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=PersonaPack_{persona_id}.zip"}
    )
