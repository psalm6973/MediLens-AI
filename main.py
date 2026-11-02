
from pathlib import Path
from tempfile import NamedTemporaryFile
import traceback

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agents.document_reader import document_reader_agent
from agents.medical_analysis import (
    medical_analysis_agent,
    validate_medical_analysis,
)
from agents.safety_care import safety_care_agent


# ==================================================
# APPLICATION SETUP
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="MediLens-AI",
    description="Medical Report Understanding System",
    version="1.0.0",
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)


# ==================================================
# MEDILENS-AI WORKFLOW
# ==================================================

def run_medilens(file_path: str) -> dict:

    report_path = Path(file_path)

    # --------------------------------------------------
    # AGENT 1: DOCUMENT READER
    # --------------------------------------------------

    if not report_path.is_file():
        return {
            "status": "error",
            "stage": "document_reader",
            "message": "The uploaded report could not be found.",
        }

    try:
        document_result = document_reader_agent(str(report_path))

        if not isinstance(document_result, dict):
            raise ValueError(
                "Document reader returned an invalid result."
            )

        if document_result.get("status") != "success":
            return {
                "status": "needs_review",
                "stage": "document_reader",
                "message": "The report could not be processed successfully.",
                "details": document_result,
            }

        parsed_report = document_result.get("parsed_report", {})

        if not isinstance(parsed_report, dict):
            raise ValueError(
                "The parsed report has an invalid format."
            )

    except Exception as error:
        print("\n--- DOCUMENT READER ERROR ---")
        traceback.print_exc()
        print("-----------------------------\n")

        return {
            "status": "error",
            "stage": "document_reader",
            "message": "An error occurred while reading the report.",
            "details": str(error),
        }

    # --------------------------------------------------
    # AGENT 2: MEDICAL ANALYSIS
    # --------------------------------------------------

    try:
        medical_analysis = medical_analysis_agent(parsed_report)

        if not isinstance(medical_analysis, dict):
            raise ValueError(
                "Medical analysis must return a dictionary."
            )

        medical_analysis = validate_medical_analysis(
            medical_analysis
        )

        analysis_needs_review = (
            medical_analysis.get("status") != "success"
        )

    except Exception as error:
        print("\n--- MEDICAL ANALYSIS ERROR ---")
        traceback.print_exc()
        print("------------------------------\n")

        return {
            "status": "needs_review",
            "stage": "medical_analysis",
            "message": "Medical analysis failed or did not pass validation.",
            "details": str(error),
        }

    # --------------------------------------------------
    # AGENT 3: SAFETY CARE
    # --------------------------------------------------

    try:
        safety_result = safety_care_agent(medical_analysis)

        if not isinstance(safety_result, dict):
            raise ValueError(
                "Safety check must return a dictionary."
            )

    except Exception as error:
        print("\n--- SAFETY CARE ERROR ---")
        traceback.print_exc()
        print("-------------------------\n")

        return {
            "status": "needs_review",
            "stage": "safety_care",
            "message": "The safety check could not be completed.",
            "details": str(error),
            "analysis": medical_analysis,
        }

    safety_check = {
        "status": safety_result.get("status"),
        "review_required": safety_result.get(
            "review_required", True
        ),
        "safety_flags": safety_result.get(
            "safety_flags", []
        ),
        "message": safety_result.get("message"),
    }

    final_analysis = safety_result.get(
        "analysis",
        medical_analysis
    )

    # --------------------------------------------------
    # FINAL WORKFLOW RESULT
    # --------------------------------------------------

    if safety_check["review_required"]:
        return {
            "status": "needs_review",
            "stage": "safety_care",
            "message": safety_check["message"],
            "parsed_report": parsed_report,
            "analysis": final_analysis,
            "safety_flags": safety_check["safety_flags"],
            "safety_check": safety_check,
        }

    if analysis_needs_review:
        return {
            "status": "needs_review",
            "stage": "medical_analysis",
            "message": (
                "Medical analysis requires further review. "
                "Safety checks completed."
            ),
            "parsed_report": parsed_report,
            "analysis": final_analysis,
            "safety_flags": safety_check["safety_flags"],
            "safety_check": safety_check,
        }

    return {
        "status": "success",
        "message": (
            "The report passed the basic processing and safety checks."
        ),
        "parsed_report": parsed_report,
        "analysis": final_analysis,
        "safety_check": safety_check,
    }


# ==================================================
# LANDING PAGE
# ==================================================

@app.get("/")
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


# ==================================================
# RESULTS PAGE
# ==================================================

@app.get("/results")
async def results_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={"result": None},
    )


@app.post("/results")
async def display_results(request: Request):

    result = await request.json()

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={"result": result},
    )


# ==================================================
# REPORT UPLOAD API
# ==================================================

@app.post("/api/analyze")
async def analyze_report(file: UploadFile = File(...)):

    allowed_extensions = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
    }

    max_file_size = 10 * 1024 * 1024

    extension = Path(file.filename or "").suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Upload a PDF, PNG or JPG.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(content) > max_file_size:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds the 10 MB limit.",
        )

    temporary_path = None

    try:
        with NamedTemporaryFile(
            mode="wb",
            suffix=extension,
            delete=False,
        ) as temporary_file:

            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)

        result = await run_in_threadpool(
            run_medilens,
            str(temporary_path),
        )

        return result

    except Exception as error:
        print("\n--- UPLOAD API ERROR ---")
        traceback.print_exc()
        print("-----------------------\n")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the report.",
        ) from error

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

        await file.close()


# ==================================================
# APPLICATION START
# ==================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
