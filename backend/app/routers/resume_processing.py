from fastapi import APIRouter, Form, HTTPException
from app.models.schemas import ResumeInput, RefinementInput, EvaluationOutput, RefinedResumeOutput
from app.core.gemini_service import evaluate_resume_text, refine_resume
from typing import Dict, Any
import json

router = APIRouter()

def calculate_overall_score(eval_json: Dict[str, Any]) -> int:
    """
    Calculate the weighted overall score based on individual section scores.
    Weights are approximate and can be adjusted based on role type if needed.
    """
    try:
        scores = {
            "experience": eval_json.get("experience_match", {}).get("score", 0),
            "skills": eval_json.get("skills_and_techstack_match", {}).get("score", 0),
            "projects": eval_json.get("projects_match", {}).get("score", 0),
            "education": eval_json.get("education_match", {}).get("score", 0),
            "profile": eval_json.get("profile_match", {}).get("score", 0),
            "industry": eval_json.get("industry_and_domain_match", {}).get("score", 0),
            "certs": eval_json.get("certifications_and_achievements_match", {}).get("score", 0),
        }
        
        # Default Weights (Mid-level / General)
        weights = {
            "experience": 0.35,
            "skills": 0.25,
            "projects": 0.20,
            "education": 0.10,
            "profile": 0.05,
            "industry": 0.03,
            "certs": 0.02
        }
        
        total_score = sum(scores[k] * weights[k] for k in scores)
        return int(round(total_score))
    except Exception as e:
        print(f"Error calculating score: {e}")
        return 0

@router.post("/evaluate", response_model=EvaluationOutput)
async def evaluate_resume(
    job_description: str = Form(...),
    resume_latex_code: str = Form(...)
):
    """
    Evaluate a LaTeX resume against a job description.
    """
    if not job_description:
        raise HTTPException(status_code=400, detail="Job description is required.")
    if not resume_latex_code or not resume_latex_code.strip():
        raise HTTPException(status_code=400, detail="Resume LaTeX code is required.")

    eval_json_str = evaluate_resume_text(job_description, resume_latex_code)
    if not eval_json_str:
        raise HTTPException(status_code=500, detail="Failed to get a valid response from the Gemini API.")
    
    try:
        eval_json = json.loads(eval_json_str)
        
        # Calculate overall score in Python
        calculated_score = calculate_overall_score(eval_json)
        
        # Update the overall_match score
        if "overall_match" in eval_json:
            eval_json["overall_match"]["score"] = calculated_score
            
            # Update fit decision based on calculated score
            if "fit" in eval_json["overall_match"]:
                 # Simple logic: Good fit if score >= 75
                 eval_json["overall_match"]["fit"]["decision"] = calculated_score >= 75

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse evaluation result from Gemini.")

    return eval_json

@router.post("/refine", response_model=RefinedResumeOutput)
async def refine_resume_endpoint(input: RefinementInput):
    """
    Refine a LaTeX resume based on job description and evaluation.
    """
    try:
        refined_latex, summary = refine_resume(
            input.job_description,
            input.original_resume_latex_code,
            input.evaluation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refine resume: {e}")

    return {"refined_latex_code": refined_latex, "overall_improvements_summary": summary}
