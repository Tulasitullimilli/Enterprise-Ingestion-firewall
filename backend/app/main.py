from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.schemas.ingestion import IngestionRequest, IngestionResult
from app.services.llm_services import analyze_message
from app.utils.token_counter import estimate_tokens

from app.schemas.assistant import AssistantResult
from app.services.response_servise import generate_response

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

@app.get("/health")
def health_check():
    return {"status":"ok","message":"Ingestion Firewall API is running"}

@app.post("/api/analyze", response_model=AssistantResult)
def analyze(request:IngestionRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422,detail="Message cannot be empty")
    
    try:
        #week-1:Detect user intent
        result=analyze_message(message)
        result.token_metadata.estimated_input_tokens = estimate_tokens(message)
        #week-2
        response_markdown = generate_response(result)

        return AssistantResult(
            **result.model_dump(),
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