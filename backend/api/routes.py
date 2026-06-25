from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from models.database import get_db
from models.schemas import Upload as UploadModel, Persona as PersonaModel
from parsers.whatsapp import WhatsAppParser
from services.stats import generate_statistics, compute_target_stats, compute_pacing
from services.vocab import extract_vocabulary, categorize_vocabulary, detect_quirks
from services.emoji_engine import extract_emojis
from services.formatting import extract_formatting, compute_hard_constraints
from services.behavior import sample_real_conversations, extract_trigger_responses, compute_response_modes, build_scenario_library
from services.llm import infer_behavior_patterns
from services.prompt_compiler import compile_system_prompt
from pdf.generator import generate_persona_pdf
from pydantic import BaseModel
import json
import zipfile
import io
import os

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

        # ── 1. PARSE ─────────────────────────────────────────────────────────
        parser = WhatsAppParser()
        with open(file_path, 'rb') as f:
            conversation = parser.parse(f)

        # ── 2. DETERMINISTIC ENGINES (80%) — zero LLM ─────────────────────────
        global_stats      = generate_statistics(conversation)
        target_stats      = compute_target_stats(conversation.messages, target_person)
        vocab             = extract_vocabulary(conversation.messages, target_person)
        vocab_categories  = categorize_vocabulary(conversation.messages, target_person)
        quirks            = detect_quirks(conversation.messages, target_person)
        emojis            = extract_emojis(conversation.messages, target_person)
        formatting        = extract_formatting(conversation.messages, target_person, target_stats)
        constraints       = compute_hard_constraints(target_stats, emojis)
        real_examples     = sample_real_conversations(conversation.messages, target_person, n=30)
        triggers          = extract_trigger_responses(conversation.messages, target_person)
        response_modes    = compute_response_modes(conversation.messages, target_person)
        scenario_library  = build_scenario_library(conversation.messages, target_person)
        pacing            = compute_pacing(conversation.messages, target_person)

        # ── 3. LLM INFERENCE (20%) — only 4 un-computable inferences ─────────
        target_msgs = [m for m in conversation.messages if m.sender == target_person]
        conversation_sample = "\n".join(
            f"{m.sender}: {m.content}" for m in target_msgs[-200:]
        )
        hard_stats_context = {"stats": target_stats, "vocab": vocab, "emojis": emojis}
        llm_inferences = await infer_behavior_patterns(
            conversation_sample, target_person, hard_stats_context
        )

        # ── 4. COMPILE PROMPT — Python f-string, LLM never writes the prompt ─
        system_prompt = compile_system_prompt(
            name=target_person,
            stats=target_stats,
            vocab=vocab,
            emojis=emojis,
            formatting=formatting,
            constraints=constraints,
            llm_inferences=llm_inferences,
            examples=real_examples,
            triggers=triggers,
            response_modes=response_modes,
            scenario_library=scenario_library,
            pacing=pacing,
            vocab_categories=vocab_categories,
            quirks=quirks,
        )

        # ── 5. STORE ──────────────────────────────────────────────────────────
        persona_data = {
            "statistics": global_stats,
            "target_stats": target_stats,
            "vocab": vocab,
            "vocab_categories": vocab_categories,
            "quirks": quirks,
            "emojis": emojis,
            "formatting": formatting,
            "constraints": constraints,
            "llm_inferences": llm_inferences,
            "real_examples": real_examples,
            "triggers": triggers,
            "response_modes": response_modes,
            "scenario_library": scenario_library,
            "pacing": pacing,
            "system_prompt": system_prompt,
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
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Only .txt files are supported (WhatsApp export)")

    content = await file.read()

    upload_entry = UploadModel(filename=file.filename, status="pending")
    db.add(upload_entry)
    db.commit()
    db.refresh(upload_entry)

    file_path = f"uploads/{upload_entry.id}.txt"
    with open(file_path, "wb") as f:
        f.write(content)

    parser = WhatsAppParser()
    file_io = io.BytesIO(content)
    try:
        conversation = parser.parse(file_io)
    except Exception as e:
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

    file_path = f"uploads/{upload_entry.id}.txt"
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
        zf.writestr("system_prompt.txt", persona_data.get("system_prompt", ""))
        zf.writestr("statistics.json", json.dumps(persona_data.get("target_stats", {}), indent=2))

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=PersonaPack_{persona_id}.zip"}
    )
