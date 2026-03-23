import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check if API key is set
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY environment variable is not set!")
    print("Available env vars:", [k for k in os.environ.keys() if 'GEMINI' in k.upper()])
else:
    print(f"Gemini API Key loaded: {GEMINI_API_KEY[:10]}...")
    genai.configure(api_key=GEMINI_API_KEY)

def generate_expert_prompt(job_description: str) -> str:
    prompt = f"""
    Analyze the following job description and create a detailed **Evaluation Rubric** for assessing resume alignment.

    Job Description:
    {job_description}

    **Instructions:**
    1.  **Ignore Location**: Do not factor in location/relocation.
    2.  **Analyze Key Requirements**: Identify the most critical skills, experience levels, and domain expertise required.
    3.  **Create a Rubric**: Define specific criteria for what constitutes a "High Match" (90-100), "Medium Match" (70-89), and "Low Match" (<70) for each of the following categories:
        -   Experience (Years & Relevance)
        -   Skills & Techstack
        -   Projects (Relevance & Impact)
        -   Education
        -   Profile (Career Trajectory)
        -   Industry/Domain Knowledge
        -   Certifications/Achievements

    Output the rubric clearly, specifying exactly what keywords, metrics, or qualifications would trigger a high score versus a low score. This rubric will be used by another AI to score resumes objectively.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(
        contents=[{"role": "user", "parts": [prompt]}],
        generation_config=genai.types.GenerationConfig(temperature=0.0)
    )
    return response.text

import re

def evaluate_resume_text(jd_text: str, resume_latex_code: str) -> str:
    expert_prompt = generate_expert_prompt(jd_text)
    score_guidelines = """
    **OBJECTIVE EVALUATION RUBRIC.** Evaluate the resume against the Job Description using the rubric above.

    **Instructions:**
    1.  **Ignore Location**: Do not factor in location/relocation.
    2.  **Use the Rubric**: For each section, assign a raw score (0-100) based strictly on the rubric criteria.
    3.  **Reasoning**: Provide specific evidence from the resume for the score.
    4.  **No Math**: Do NOT calculate an overall weighted score. Return `overall_match.score` as 0 (it will be calculated programmatically).

    **Output Format (JSON Only):**
    {
        "experience_match": { "score": integer, "reasoning": string },
        "skills_and_techstack_match": { "score": integer, "reasoning": string },
        "projects_match": { "score": integer, "reasoning": string },
        "education_match": { "score": integer, "reasoning": string },
        "profile_match": { "score": integer, "reasoning": string },
        "industry_and_domain_match": { "score": integer, "reasoning": string },
        "certifications_and_achievements_match": { "score": integer, "reasoning": string },
        "overall_match": { 
            "score": 0, 
            "reasoning": string, 
            "pros": string, 
            "cons": string, 
            "fit": { "decision": boolean, "reasoning": string }
        }
    }
    """
    prompt_content = f"{expert_prompt}\n\nEvaluate this resume LaTeX code:\n{resume_latex_code}\n\n{score_guidelines}"
    model = genai.GenerativeModel('gemini-2.5-flash')
    try:
        response = model.generate_content(
            contents=[{"role": "user", "parts": [prompt_content]}],
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )
        return response.text
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return None

def refine_resume(jd_text: str, original_resume_latex_code: str, evaluation: dict):
    import json
    print("Calling Gemini refine_resume with LaTeX code length:", len(original_resume_latex_code))
    prompt = f"""
You are a perfectionist resume writer with an eye for detail and a deep understanding of how to align resumes precisely with job descriptions. Your task is to optimize the *content* of this LaTeX resume for the given job description based on the evaluation results, while maintaining absolute honesty, especially regarding years of experience.

### Instructions:
- **Do NOT change the LaTeX template, structure, or commands.** Only modify the content within the existing LaTeX commands (e.g., text inside \resumeItem, \resumeSubheading, etc.).
- **Do NOT add, remove, or modify any LaTeX packages, documentclass, or formatting commands.**
- **Do NOT change section order, add new sections, or remove sections.**
- **Focus on Low-Scoring Areas**: Prioritize enhancing sections with low scores (Skills/Techstack, Projects, Certifications/Achievements) to better align with the job requirements, using strong action verbs and quantifiable achievements where possible.
- **Chain-of-Thought**: First, PLAN your changes. Identify the specific keywords from the JD that are missing in the resume. Then, determine the best place to insert them semantically.
- **Semantic Mapping**: Link JD concepts to Resume experience. (e.g., If JD asks for "CI/CD" and resume has "Jenkins", explicitly rewrite to "Implemented CI/CD pipelines using Jenkins").
- **LaTeX Safety**: **CRITICAL**: You must escape all special LaTeX characters (%, $, &, _, #, ~) unless they are part of a command. Do not break the code structure.
- **Maintain Honesty**: Do not alter years of experience, fabricate roles, or add fictitious projects/certifications.
- **Non-Editable Fields**: DO NOT change **College/University names**, **Degree titles**, **Company names**, **Job Titles**, or **Employment Dates**. The AI must optimization the *descriptions* and *skills* only.
- **Preserve High Scores**: If a section (e.g., Experience, Education) already scores high (>= 90), DO NOT make substantial changes unless it directly addresses a specific gap mentioned in the evaluation.
- **Targeted Improvements**: Focus ONLY on areas with scores < 90. Do not rewrite sections that are already strong just for the sake of rewriting.
- **Skills/Techstack**: Add missing skills from the JD if they are relevant to the candidate's background.
- **Experience Descriptions**: Rewrite bullet points to focus on technical keywords and relevant functional JD requirements.
- **Conservative Inferences**: Ensure all enhancements are directly supported by the existing resume content. Do not make assumptions beyond what is explicitly stated or reasonably implied.

### Job Description:
{jd_text}

### Original Resume LaTeX Code:
{original_resume_latex_code}

### Evaluation Results:
{json.dumps(evaluation)}

Please return the output in the following strict format (do NOT use JSON):

---LATEX_START---
[Insert the complete, refined LaTeX code here]
---LATEX_END---

---SUMMARY_START---
[Insert the brief summary of improvements here]
---SUMMARY_END---
"""
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        # Prepend system instruction to prompt since some models/versions don't support 'system' role
        full_prompt = "You are a perfectionist resume writer with an eye for detail and a deep understanding of how to align resumes precisely with job descriptions.\n\n" + prompt
        
        response = model.generate_content(
            contents=[{"role": "user", "parts": [full_prompt]}],
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )
        print("Gemini refine_resume FULL RESPONSE:", response)
        
        text = response.text
        
        refined_latex = ""
        summary = ""
        
        # Extract Latex
        latex_match = re.search(r'---LATEX_START---(.*?)---LATEX_END---', text, re.DOTALL)
        if latex_match:
            refined_latex = latex_match.group(1).strip()
            
        # Extract Summary
        summary_match = re.search(r'---SUMMARY_START---(.*?)---SUMMARY_END---', text, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
            
        if not refined_latex or not summary:
            print("Failed to extract sections from refine_resume response")
            # Fallback: try to see if it returned just latex if summary is missing or vice versa
            # But simpler to just return empty and let the user retry or see error
            
        return refined_latex, summary

    except Exception as e:
        print("Gemini refine_resume exception:", e)
        return "", ""
