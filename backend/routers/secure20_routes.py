"""
XLR8 SECURE 2.0 Analysis API Endpoint
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import shutil
from pathlib import Path
import logging
from datetime import datetime

# Import our analysis modules
import sys
sys.path.append('/mnt/user-data/outputs')
from secure_20_analyzer import SECURE20Analyzer
from excel_generator import generate_report

router = APIRouter(prefix="/api/secure20", tags=["SECURE 2.0"])
logger = logging.getLogger(__name__)

TEMP_DIR = Path("/tmp/xlr8_secure20")
TEMP_DIR.mkdir(exist_ok=True)


@router.post("/analyze")
async def analyze_secure_20(
    company_name: str,
    file: UploadFile = File(...)
):
    """
    Analyze customer data for SECURE 2.0 compliance.
    
    Expects Excel file with 5 tabs:
    - Wages Hire Date Pay Freq DOB
    - Earnings
    - Deductions
    - Employee Deductions
    - Employee Earnings
    
    Returns: Download link to comprehensive implementation plan
    """
    try:
        # Save uploaded file
        file_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_path = TEMP_DIR / f"input_{file_id}.xlsx"
        
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Processing SECURE 2.0 analysis for {company_name}")
        
        # Run analysis
        analyzer = SECURE20Analyzer(str(input_path))
        results = analyzer.analyze()
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Generate report
        output_filename = f"{company_name.replace(' ', '_')}_SECURE_20_Implementation_Plan.xlsx"
        output_path = TEMP_DIR / output_filename
        
        generate_report(
            company_name=company_name,
            analysis_results=results,
            output_path=str(output_path)
        )
        
        # Return results and file
        return {
            "success": True,
            "company": company_name,
            "statistics": results["statistics"],
            "download_url": f"/api/secure20/download/{output_filename}",
            "message": f"Analysis complete! Found {results['statistics']['high_priority']} employees needing immediate action."
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup input file
        if input_path.exists():
            input_path.unlink()


@router.get("/download/{filename}")
async def download_report(filename: str):
    """Download generated implementation plan"""
    file_path = TEMP_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/health")
async def health_check():
    """Check if SECURE 2.0 analysis is operational"""
    return {
        "status": "operational",
        "service": "SECURE 2.0 Analysis",
        "version": "1.0"
    }
