
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from workflow.graph import run_prospect_workflow

app = FastAPI(
    title="ProspectIQ API",
    description="AI-powered personalized B2B outreach",
    version="1.0.0"
)

# Allow requests from React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://prospect-iq-ruby.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OutreachRequest(BaseModel):
    prospect_name: str = Field(min_length=1, max_length=150)
    designation: str = Field(min_length=1, max_length=150)
    company: str = Field(min_length=1, max_length=150)
    company_website: Optional[str] = None

    sender_company: str = Field(min_length=1, max_length=150)
    product_or_service: str = Field(min_length=1, max_length=500)
    value_proposition: str = Field(min_length=1, max_length=1000)


@app.get("/")
def home():
    return {"message": "Welcome to ProspectIQ API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/outreach/generate")
def generate_outreach(request: OutreachRequest):
    try:
        prospect_data = request.model_dump()

        result = run_prospect_workflow(prospect_data)

        return {
            "success": True,
            "research": result["research_data"],
            "signals": result["analyzed_data"],
            "email": result["email_data"],
            "review": result["review_result"]
        }

    except Exception as e:
        print(f"Outreach generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Outreach generation failed. Please check the backend logs."
        )
