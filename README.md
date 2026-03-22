# Refine - AI Resume Optimizer

Refine is a full-stack web application that leverages the power of AI to help users evaluate and optimize their resumes based on specific job descriptions. Users can upload their resume (in LaTeX format) and a job description, receive a detailed evaluation with scores and feedback for different sections, and get a refined version of their resume aimed at better alignment with the job requirements.

## Features

*   **Resume Evaluation:** Get a score and detailed feedback on how well your resume matches a job description across various categories (Experience, Skills, Projects, Education, etc.).
*   **AI-Powered Refinement:** Receive an optimized version of your resume (in LaTeX format) with content adjusted to better highlight relevant experience and skills based on the job description and evaluation feedback.
*   **Step-by-Step Process:** A clear, guided workflow from uploading your documents to viewing the refined resume.

## Application Screenshots

Screenshots will be added soon.

### Resume Evaluation 

The evaluation screen provides detailed insights on how well your resume matches the target job description. Users receive:

- **Overall Match Score**: A comprehensive percentage showing resume-job alignment (39% in this example)
- **Category Breakdown**: Detailed scores across key areas:
  - Experience (40%)
  - Skills/Techstack (30%) 
  - Projects (30%)
  - Education (85%)
  - Profile (40%)
  - Industry/Domain (30%)
  - Certifications/Achievements (70%)

- **Assessment Summary**: Clear feedback on fit level with specific insights about gaps and requirements
- **Strengths & Areas for Improvement**: Actionable feedback highlighting what's working well and what needs enhancement

### AI-Optimized Resume 

After the AI refinement process, users can review their optimized resume with:


- **Improvement Summary**: Detailed explanation of changes made to enhance clarity and impact
- **Before/After Comparison**: 
  - Original Score: 39%
  - Refined Score: 58%
  - **+19% Improvement** in overall match rating

- **Enhanced Content**: The AI strategically improves descriptions in Skills/Techstack, Projects, and Achievements sections to better emphasize quantifiable achievements and relevant technical depth
- **Category Performance**: Updated scores showing improvement across different resume sections

### User-Friendly Workflow
Both screenshots demonstrate the clean, intuitive 4-step process:
1. **Upload** - Submit your resume and job description
2. **Preview** - Review uploaded documents
3. **Evaluation** - Receive detailed scoring and feedback  
4. **Refinement** - Get your AI-optimized resume

The interface uses clear visual indicators (checkmarks, progress bars, and color-coded scores) to guide users through the optimization process seamlessly.

## Technologies Used

**Backend:**
*   Python
*   FastAPI
*   OpenAI API

**Frontend:**
*   React
*   TypeScript
*   Vite
*   Tailwind CSS

## Prerequisites

Before you begin, ensure you have the following installed:
*   Python 3.7+
*   pip (Python package installer)
*   Node.js (LTS version recommended)
*   npm or yarn (Node.js package manager)
*   Git

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/MukundC25/Refine.git
    cd Refine
    ```

2.  **Backend Setup:**
    *   Navigate to the `backend` directory:
        ```bash
        cd backend
        ```
    *   Install the required Python dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    *   Create a `.env` file in the `backend` directory.
    *   Add your OpenAI API key to the `.env` file:
        ```env
        OPENAI_API_KEY="your_openai_api_key_here"
        ```
        Replace `"your_openai_api_key_here"` with your actual OpenAI API key.

3.  **Frontend Setup:**
    *   Navigate to the `frontend` directory:
        ```bash
        cd ../frontend
        ```
    *   Install the required Node.js dependencies:
        ```bash
        npm install
        # or yarn install
        ```
    *   (Optional) If your backend is running on a different URL than `http://localhost:8000`, create a `.env` file in the `frontend` directory and add the backend API base URL:
        ```env
        VITE_API_BASE_URL="your_backend_api_url"
        ```

## Running the Application

You need to run both the backend and the frontend concurrently.

1.  **Run the Backend:**
    *   Open a new terminal window.
    *   Navigate to the `backend` directory:
        ```bash
        cd backend
        ```
    *   Start the FastAPI server:
        ```bash
        uvicorn app.main:app --reload
        ```
    The backend will run on `http://127.0.0.1:8000` by default.

2.  **Run the Frontend:**
    *   Open another terminal window.
    *   Navigate to the `frontend` directory:
        ```bash
        cd frontend
        ```
    *   Start the Vite development server:
        ```bash
        npm run dev
        # or yarn dev
        ```
    The frontend will typically run on `http://localhost:5173/`. Open this URL in your web browser to access the application.

## How It Works

1. **Upload**: Users upload their resume (LaTeX format) and paste the target job description
2. **Evaluation**: The AI analyzes the resume against the job requirements and provides detailed scoring across multiple categories
3. **Refinement**: Based on the evaluation feedback, the AI generates an optimized version of the resume with enhanced content and better keyword alignment
4. **Review**: Users can compare the original and refined versions, along with the improvement metrics

## API Endpoints

- `POST /evaluate` - Evaluates resume against job description
- `POST /refine` - Generates optimized resume based on evaluation results
- `GET /health` - Health check endpoint




