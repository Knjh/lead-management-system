# api/routes.py
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
import logging
from services.lead_service import LeadService
from utils.csv_parser import CSVParser
from models.lead_models import Lead, CallWebhookEvent
import datetime

# Initialize router and services
router = APIRouter(prefix="/api/v1")
lead_service = LeadService()
csv_parser = CSVParser()
logger = logging.getLogger(__name__)

@router.post("/upload-leads")
async def upload_leads(file: UploadFile = File(...)):
    """Upload CSV file with leads"""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Parse CSV
        records = await csv_parser.parse_csv_content(csv_content)
        
        # Validate required fields
        required_fields = ['phone_number']
        if not csv_parser.validate_required_fields(records, required_fields):
            raise HTTPException(status_code=400, detail="Missing required fields in CSV")
        
        # Process leads
        lead_ids = await lead_service.process_csv_leads(records)
        
        return {
            "status": "success",
            "message": f"Successfully uploaded {len(lead_ids)} leads",
            "lead_ids": lead_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading leads: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook/retell")
async def receive_retell_webhook(webhook_data: Dict[str, Any]):
    """Receive webhook events from Retell API"""
    try:
        logger.info(f"Received webhook: {webhook_data.get('event_type')}")
        
        # Process the webhook
        success = await lead_service.process_call_webhook(webhook_data)
        
        if success:
            return {"status": "success", "message": "Webhook processed successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to process webhook")
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/leads")
async def create_lead(lead: Lead):
    """Create a single lead"""
    try:
        firebase_service = lead_service.firebase_service
        lead_id = await firebase_service.create_lead(lead)
        
        return {
            "status": "success",
            "message": "Lead created successfully",
            "lead_id": lead_id
        }
        
    except Exception as e:
        logger.error(f"Error creating lead: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str):
    """Get a specific lead by ID"""
    try:
        firebase_service = lead_service.firebase_service
        lead = await firebase_service.get_lead(lead_id)
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        return lead.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lead: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/manual-call-batch")
async def trigger_manual_call_batch(background_tasks: BackgroundTasks):
    """Manually trigger a calling batch (for testing)"""
    try:
        background_tasks.add_task(lead_service.execute_calling_batch)
        
        return {
            "status": "success",
            "message": "Calling batch triggered successfully"
        }
        
    except Exception as e:
        logger.error(f"Error triggering manual call batch: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/stats/concurrency")
async def get_concurrency_stats():
    """Get current Retell API concurrency information"""
    try:
        retell_service = lead_service.retell_service
        concurrency_info = await retell_service.get_concurrency()
        
        if not concurrency_info:
            raise HTTPException(status_code=503, detail="Could not fetch concurrency information")
        
        return concurrency_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting concurrency stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/stats/leads")
async def get_lead_stats():
    """Get lead statistics"""
    try:
        firebase_service = lead_service.firebase_service
        
        # Get counts from different collections
        stats = {
            "total_leads": 0,
            "new_calls": 0,
            "retry_calls": 0,
            "callback_calls": 0,
            "completed_calls": 0,
            "failed_calls": 0
        }
        
        # Count documents in each collection
        # Note: In production, you might want to use more efficient counting methods
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting lead stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Lead Management Backend"
    }
