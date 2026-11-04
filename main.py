
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
            "extraction_status": "failed",
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
                "stage": "completed",
                "extraction_status": "failed",
                "analysis_status": "not_started",
                "safety_status": "not_started",
                "message": (
                    "The report could not be processed successfully. "
                    "Manual review is required."
                ),
                "details": document_result,
            }

        parsed_report = document_result.get("parsed_report")

        if not isinstance(parsed_report, dict):
            raise ValueError(
                "The parsed report has an invalid format."
            )

        document_metadata = {
            "extraction_method": document_result.get(
                "extraction_method"
            ),
            "extraction_warnings": document_result.get(
                "extraction_warnings", []
            ),
            "review_required": document_result.get(
                "review_required", True
            ),
            "quality_status": document_result.get(
                "quality_status"
            ),
            "fallback_attempted": document_result.get(
                "fallback_attempted", False
            ),
            "candidate_result_count": document_result.get(
                "candidate_result_count", 0
            ),
        }

        extraction_status = "success"

    except Exception as error:
        print("\n--- DOCUMENT READER ERROR ---")
        traceback.print_exc()
        print("-----------------------------\n")

        return {
            "status": "error",
            "stage": "document_reader",
            "extraction_status": "failed",
            "message": "An error occurred while reading the report.",
            "details": str(error),
        }

    # --------------------------------------------------
    # AGENT 2: MEDICAL ANALYSIS
    # --------------------------------------------------

    try:
        medical_analysis = medical_analysis_agent(
            parsed_report,
            document_metadata
        )

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
            "stage": "completed",
            "extraction_status": extraction_status,
            "analysis_status": "failed",
            "safety_status": "not_started",
            "message": (
                "Report extraction completed, but medical analysis "
                "failed or did not pass validation."
            ),
            "details": str(error),
            "parsed_report": parsed_report,
            "document_metadata": document_metadata,
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

        if not isinstance(safety_result.get("analysis"), dict):
            raise ValueError(
                "Safety Care did not return a valid analysis."
            )

    except Exception as error:
        print("\n--- SAFETY CARE ERROR ---")
        traceback.print_exc()
        print("-------------------------\n")

        return {
            "status": "needs_review",
            "stage": "completed",
            "extraction_status": extraction_status,
            "analysis_status": (
                "needs_review"
                if analysis_needs_review
                else "success"
            ),
            "safety_status": "failed",
            "message": (
                "Report extraction and medical analysis completed, "
                "but the safety check could not be completed."
            ),
            "details": str(error),
            "parsed_report": parsed_report,
            "document_metadata": document_metadata,
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

    final_analysis = safety_result["analysis"]

    # --------------------------------------------------
    # FINAL STATUS CALCULATION
    # --------------------------------------------------

    extraction_needs_review = document_metadata.get(
        "review_required", True
    )

    # Recheck analysis status after Safety Care.
    analysis_needs_review = (
        final_analysis.get("status") != "success"
    )

    safety_needs_review = (
        safety_check["review_required"]
        or safety_check["status"] != "passed_checks"
    )

    final_needs_review = (
        extraction_needs_review
        or analysis_needs_review
        or safety_needs_review
    )

    if analysis_needs_review:
        analysis_status = "needs_review"
    else:
        analysis_status = "success"

    if safety_needs_review:
        safety_status = "needs_review"
    else:
        safety_status = "passed_checks"

    common_result = {
        "stage": "completed",
        "extraction_status": extraction_status,
        "analysis_status": analysis_status,
        "safety_status": safety_status,
        "parsed_report": parsed_report,
        "document_metadata": document_metadata,
        "analysis": final_analysis,
        "safety_flags": safety_check["safety_flags"],
        "safety_check": safety_check,
    }

    if final_needs_review:

        review_reasons = []

        if extraction_needs_review:
            review_reasons.append(
                "Extracted report information requires "
                "verification against the original report."
            )

        if analysis_needs_review:
            review_reasons.append(
                "Medical analysis requires further review."
            )

        if safety_needs_review:
            review_reasons.append(
                "Safety checks identified concerns or "
                "could not be completed successfully."
            )

        return {
            "status": "needs_review",
            "message": " ".join(review_reasons),
            "review_reasons": review_reasons,
            **common_result,
        }

    return {
        "status": "success",
        "message": (
            "Report processing and safety checks completed. "
            "Extracted values and medical interpretations must "
            "still be verified by an appropriate healthcare professional."
        ),
        "review_reasons": [],
        **common_result,
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
            detail=(
                "Unsupported file format. Upload a PDF, PNG or JPG."
            ),
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
            detail=(
                "An unexpected error occurred while processing "
                "the report."
            ),
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
