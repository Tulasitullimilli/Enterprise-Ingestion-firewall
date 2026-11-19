from uuid import uuid4

from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.schemas.ingestion import IngestionRequest, TokenMetadata
from app.services.llm_services import analyze_message
from app.utils.token_counter import estimate_tokens

from app.schemas.assistant import AssistantResult
from app.services.response_servise import generate_response
from app.services.conversation_service import add_message, get_history

from app.services.database_service import initialize_database, database_enabled, list_conversations

app=FastAPI(
    title="Enterprise Structured Ingestion firewall",
    description="Classifies user messages and validates structures AI output.",
    version="1.0.0",
)

#simple local-development CORS configuration.Restrict this in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    if database_enabled():
        initialize_database()

@app.get("/health")
def health_check():
    return {"status":"ok","message":"Ingestion Firewall API is running"}

@app.get("/api/conversation")
def conversations():
    return {"items":list_conversations()}

@app.get("/api/conversations/{session_id}/messages")
def conversation_messages(session_id:str):
    try:UUID(session_id)
    except ValueError:raise HTTPException(status_code=400,detail="Invalid conversation ID.")
    if not database_enabled():
        raise HTTPException(status_code=503,detail="Persistant chat history requires DATABASE_URL")
    return {"session_id":session_id,"items":get_conversation_messages(session_id)}

@app.post("/api/analyze", response_model=AssistantResult)
def analyze(request:IngestionRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422,detail="Message cannot be empty")

    session_id = request.session_id or str(uuid4())

    try:
        result = analyze_message(message)
        result = result.model_copy(update={
            "token_metadata": TokenMetadata(
                estimated_input_tokens=estimate_tokens(message)
            )
        })
        history = get_history(session_id)
        response_markdown = generate_response(
            result,
            history=history,
            current_message=message,
        )
        add_message(session_id, "user", message)
        add_message(session_id, "assistant", response_markdown)
        return AssistantResult(
            **result.model_dump(),
            session_id=session_id,
            response_markdown=response_markdown,
        )

    
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error":"The model response did not pass schema validation.",
                "validation_errors":exc.errors(),
            },
        ) from exc

    
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM request failed.Check the API key,model name,network,and provider limits."
        ) from exc