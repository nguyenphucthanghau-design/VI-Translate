from pathlib import Path
import shutil
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from scripts.translate_pdf import TranslationError, translate_pdf


app = FastAPI(
    title="VI Translate API",
    description="API wrapper for VI-Translate",
    version="1.1.0",
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "VI Translate API"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post(
    "/translate-upload",
    operation_id="translatePdfUpload",
    summary="Translate a PDF while preserving layout",
)
async def translate_upload(
    file: UploadFile = File(...),
    target_language: str = Form("vi"),
    source_language: str = Form("auto"),
    pages: str | None = Form(None),
    threads: int = Form(1),
):
    filename = Path(file.filename or "input.pdf").name

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    if threads < 1 or threads > 4:
        raise HTTPException(
            status_code=400,
            detail="threads must be between 1 and 4."
        )

    job_dir = Path(
        tempfile.mkdtemp(prefix="vi-translate-api-")
    )

    input_pdf = job_dir / filename

    try:
        with input_pdf.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = translate_pdf(
            input_pdf,
            job_dir,
            target_language=target_language,
            source_language=source_language,
            pages=pages or None,
            threads=threads,
            overwrite=True,
            engine="google",
        )

        if result.path is None or not result.path.exists():
            raise HTTPException(
                status_code=500,
                detail="Translation completed but no PDF was produced."
            )

        return FileResponse(
            path=str(result.path),
            media_type="application/pdf",
            filename=result.path.name,
            background=BackgroundTask(
                shutil.rmtree,
                job_dir,
                ignore_errors=True
            ),
        )

    except TranslationError as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise

    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {exc}"
        ) from exc
