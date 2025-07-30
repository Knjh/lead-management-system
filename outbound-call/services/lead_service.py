# services/lead_service.py
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
import pytz # Import pytz explicitly for clarity with timezone usage

from services.firebase_service import FirebaseService
from services.retell_service import RetellService # Ensure this uses httpx now
from models.lead_models import Lead, CallStatus, DisconnectionReason, RetellCreateCallRequest
from config.settings import settings
from firebase_admin import firestore

class LeadService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = FirebaseService()
        self.retell_service = RetellService()
    
    async def process_csv_leads(self, csv_data: List[Dict[str, Any]]) -> List[str]:
        """Process and create leads from CSV data"""
        try:
            leads = []
            for row in csv_data:
                lead = Lead(
                    phone_number=row.get('phone_number', ''),
                    name=row.get('name', ''),
                    email=row.get('email', ''),
                    company=row.get('company', ''),
                    # Ensure custom_data is always a dict, even if missing in CSV
                    custom_data={k: v for k, v in row.items() 
                                 if k not in ['phone_number', 'name', 'email', 'company']}
                )
                leads.append(lead)
            
            # The bulk_create_leads method in FirebaseService should now handle deduplication.
            lead_ids = await self.firebase_service.bulk_create_leads(leads)
            self.logger.info(f"Successfully processed {len(lead_ids)} leads from CSV")
            return lead_ids
            
        except Exception as e:
            self.logger.error(f"Error processing CSV leads: {str(e)}")
            raise
    
    async def process_call_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Process incoming webhook from Retell after call completion"""
        try:
            event_type = webhook_data.get('event_type')
            if event_type != 'call_analyzed':
                self.logger.info(f"Ignoring webhook event type: {event_type}")
                return True
            
            call_id = webhook_data.get('call_id')
            phone_number = webhook_data.get('to_number') 
            disconnection_reason = webhook_data.get('disconnection_reason')
            
            # Find the lead by phone number
            lead = await self._find_lead_by_phone(phone_number)
            if not lead:
                self.logger.warning(f"No lead found for phone number: {phone_number} from call_id: {call_id}")
                return False
            
            # Update call completion data on the lead
            post_call_data = {
                'call_id': call_id,
                'disconnection_reason': disconnection_reason,
                'recording_url': webhook_data.get('recording_url'),
                'public_log_url': webhook_data.get('public_log_url'),
                'start_timestamp': webhook_data.get('start_timestamp'),
                'end_timestamp': webhook_data.get('end_timestamp'),
                'llm_dynamic_variables': webhook_data.get('llm_dynamic_variables', {}) 
            }
            
            # Update last_call_time and post_call_data on the main lead
            await self.firebase_service.update_lead(lead.id, {
                'post_call_data': post_call_data,
                'last_call_time': datetime.now(settings.app_timezone_obj) # Use timezone-aware datetime
            })
            
            # Determine next action based on disconnection reason and post-call data
            await self._handle_call_outcome(lead, disconnection_reason, post_call_data)
            
            self.logger.info(f"Successfully processed webhook for lead {lead.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing call webhook: {str(e)}")
            raise

    # --- LEAD PRIORITIZATION AND RETRIEVAL ---
    async def get_prioritized_leads_for_window(self, window_start: datetime, window_end: datetime) -> List[Lead]:
        """
        Get leads in priority order based on your document requirements:
        1. Callback requests for current window
        2. Callback requests from previous windows (missed)
        3. Retry calls for current day
        4. New leads
        
        Returns a list of Lead objects.
        """
        try:
            prioritized_leads: List[Lead] = []
            current_date = datetime.now(settings.app_timezone_obj).date() # Use timezone-aware date
            
            # Priority 1: Callback requests for current window
            current_window_callbacks = await self.firebase_service.get_callback_leads_for_window(window_start, window_end)
            for lead in current_window_callbacks:
                lead.priority = 1 
                lead.priority_reason = 'current_window_callback'
            prioritized_leads.extend(current_window_callbacks)
            
            # Priority 2: Missed callback requests from previous windows
            missed_callbacks = await self.firebase_service.get_missed_callback_leads(window_start)
            for lead in missed_callbacks:
                lead.priority = 2
                lead.priority_reason = 'missed_callback'
            prioritized_leads.extend(missed_callbacks)
            
            # Priority 3: Retry calls for current day
            today_retries = await self.firebase_service.get_retry_leads_for_date(current_date)
            for lead in today_retries:
                lead.priority = 3
                lead.priority_reason = 'retry_today'
            prioritized_leads.extend(today_retries)
            
            # Priority 4: New leads
            new_leads = await self.firebase_service.get_new_leads()
            for lead in new_leads:
                lead.priority = 4
                lead.priority_reason = 'new_lead'
            prioritized_leads.extend(new_leads)
            
            self.logger.info(f"Prioritized leads for window: {len(prioritized_leads)} total")
            self.logger.info(f"Current window callbacks: {len(current_window_callbacks)}")
            self.logger.info(f"Missed callbacks: {len(missed_callbacks)}")
            self.logger.info(f"Today retries: {len(today_retries)}")
            self.logger.info(f"New leads: {len(new_leads)}")
            
            return prioritized_leads
            
        except Exception as e:
            self.logger.error(f"Error getting prioritized leads: {str(e)}")
            raise

    # --- CALL EXECUTION ---
    async def execute_calling_batch(self) -> Dict[str, Any]:
        """Execute calling batch, respecting business hours and concurrency."""
        try:
            # Get current time in the application's configured timezone
            now_local = datetime.now(pytz.utc).astimezone(settings.app_timezone_obj)

            self.logger.info(f"Current local time: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
            
            # Check if it's within calling hours
            if not self._is_calling_hours(now_local):
                start_time_str = datetime(1,1,1,settings.calling_start_hour,0,0).strftime('%H:%M')
                end_time_str = datetime(1,1,1,settings.calling_end_hour,settings.calling_end_minute,0).strftime('%H:%M')
                self.logger.info(f"Outside calling hours ({start_time_str} - {end_time_str} {settings.app_timezone}). Skipping calling batch.")
                return {'status': 'skipped', 'reason': 'outside_calling_hours'}
            
            self.logger.info("Within calling hours. Proceeding with lead processing...")
            
            # Calculate current X-minute window (your _get_current_window method already does this)
            window_start, window_end = self._get_current_window(now_local)
            
            self.logger.info(f"Processing leads for window: {window_start.strftime('%H:%M:%S')} - {window_end.strftime('%H:%M:%S')}")

            # Get prioritized leads for this window
            prioritized_leads = await self.get_prioritized_leads_for_window(window_start, window_end)
            
            if not prioritized_leads:
                self.logger.info("No leads available for calling in this window")
                return {'status': 'completed', 'calls_made': 0, 'reason': 'no_leads'}
            
            # Execute calls with concurrency limit and time window
            calls_made = await self._execute_calls_with_concurrency(
                prioritized_leads, window_start, window_end
            )
            
            return {
                'status': 'completed',
                'calls_made': calls_made,
                'total_leads_available': len(prioritized_leads),
                'window_start': window_start.isoformat(),
                'window_end': window_end.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in calling batch execution: {str(e)}")
            raise
    
    def _get_current_window(self, current_time: datetime) -> tuple[datetime, datetime]:
        """Calculate current 10-minute window, ensuring timezone awareness."""
        # Round down to nearest 10-minute interval
        minute = (current_time.minute // settings.cron_interval_minutes) * settings.cron_interval_minutes # Use cron_interval_minutes here
        window_start = current_time.replace(minute=minute, second=0, microsecond=0)
        window_end = window_start + timedelta(minutes=settings.cron_interval_minutes)
        
        return window_start, window_end

    async def _execute_calls_with_concurrency(self, leads: List[Lead], window_start: datetime, window_end: datetime) -> int:
        """Execute calls while respecting concurrency limits and time window"""
        calls_made = 0
        
        # Use a list to hold active call tasks, managing concurrency
        active_call_tasks: List[asyncio.Task] = []
        
        for lead in leads: 
            # Check if window time has expired (using timezone-aware comparison)
            if datetime.now(settings.app_timezone_obj) >= window_end: 
                self.logger.info(f"Window time expired at {window_end.strftime('%H:%M:%S')}, stopping calls for this batch.")
                break
            
            # Filter out leads that are not in a callable status
            if lead.call_status not in [CallStatus.NEW, CallStatus.CALLBACK, CallStatus.RETRY]:
                self.logger.debug(f"Lead {lead.id} has status {lead.call_status.value}. Skipping for calling batch.")
                continue

            # Check concurrency limit before initiating a new call
            # Wait for any active call to finish if we hit the limit
            while len(active_call_tasks) >= settings.max_concurrent_calls:
                # Wait for the next task to complete
                done, pending = await asyncio.wait(active_call_tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    active_call_tasks.remove(task)
                    try:
                        task.result() # Propagate exceptions if any
                    except Exception as e:
                        self.logger.error(f"An active call task failed: {e}")
                
                # Re-check window time after waiting
                if datetime.now(settings.app_timezone_obj) >= window_end: 
                    self.logger.info(f"Window time expired after waiting for concurrency, stopping calls.")
                    break

            if datetime.now(settings.app_timezone_obj) >= window_end: 
                break # Break out of outer loop if window expired after waiting
            
            # Initiate the call and add to active tasks
            task = asyncio.create_task(self._make_individual_call(lead))
            active_call_tasks.append(task)
            calls_made += 1 # Count as 'made' when initiated
            
            # Small delay between initiating calls to avoid overwhelming Retell or your network
            await asyncio.sleep(0.5) 
        
        # Wait for any remaining active calls to complete before returning
        if active_call_tasks:
            self.logger.info(f"Waiting for {len(active_call_tasks)} remaining calls to finish.")
            await asyncio.gather(*active_call_tasks, return_exceptions=True) # Collect all results

        self.logger.info(f"Completed calling batch: {calls_made} calls initiated in window.")
        return calls_made
    
    async def _wait_for_available_slot(self, max_wait_seconds: int = 300) -> bool:
        """
        Wait for an available calling slot within concurrency limit from Retell API.
        This method is less critical now that _execute_calls_with_concurrency
        manages local task concurrency, but good for external API limits.
        """
        wait_start = datetime.now(settings.app_timezone_obj) 
        
        while (datetime.now(settings.app_timezone_obj) - wait_start).total_seconds() < max_wait_seconds: # Use total_seconds
            concurrency_info = await self.retell_service.get_concurrency()
            
            if not concurrency_info:
                self.logger.warning("Could not get concurrency info from Retell, retrying...")
                await asyncio.sleep(10)
                continue
            
            active_retell_calls = concurrency_info.get('active_calls', 0)
            
            # Here we check against Retell's backend limits, not just our local ones.
            # You might have an even higher limit on Retell, or need to manage
            # your account's rate limits.
            # For simplicity, let's assume settings.max_concurrent_calls is the limit.
            if active_retell_calls < settings.max_concurrent_calls: 
                self.logger.info(f"Available Retell slot found. Active Retell calls: {active_retell_calls}/{settings.max_concurrent_calls}")
                return True
            
            self.logger.info(f"Waiting for available Retell slot. Active Retell calls: {active_retell_calls}/{settings.max_concurrent_calls}")
            await asyncio.sleep(10) # Wait 10 seconds before re-checking
        
        self.logger.error(f"Max wait time of {max_wait_seconds} seconds exceeded for Retell API slot.")
        return False
    
    async def _make_individual_call(self, lead: Lead) -> bool: # Accept Lead object directly
        """Make a single call to a lead"""
        try:
            # Update lead status to CALLING before initiating the call
            await self.firebase_service.update_lead_status(lead.id, CallStatus.CALLING)
            self.logger.info(f"Updated lead {lead.id} status to CALLING before call initiation.")

            # assuming indian phone number, add +91 prefix
            formatted_phone_number = f"+91{lead.phone_number}"

            # Create call request for Retell
            call_request = RetellCreateCallRequest(
                from_number=settings.retell_phone_number,  # Use setting for your Retell phone number
                to_number=formatted_phone_number,
                retell_llm_id=settings.retell_agent_id, # Ensure this is passed
                # Dynamic variables to send to Retell LLM agent
                retell_llm_dynamic_variables={
                    'customer_name': lead.name or 'there',
                    'company': lead.company or 'their company', 
                    'custom_data': lead.custom_data or {} 
                }
            )
            
            # Make the call via RetellService
            call_result = await self.retell_service.create_call(call_request)
            
            if call_result and call_result.get('call_id'): # Check for both result and call_id
                # Update lead with Retell call ID. Status is already CALLING.
                await self.firebase_service.update_lead(lead.id, {
                    'retell_call_id': call_result.get('call_id') 
                })
                
                self.logger.info(f"Successfully initiated call for lead {lead.id} (Retell Call ID: {call_result.get('call_id')})")
                return True
            else:
                self.logger.error(f"Failed to create call for lead {lead.id}. Retell API response: {call_result}. Marking as FAILED.")
                # If call initiation fails, mark as failed right away.
                await self.firebase_service.update_lead_status(lead.id, CallStatus.FAILED)
                return False
                
        except Exception as e:
            self.logger.error(f"Error making individual call for lead {lead.id}: {str(e)}")
            # In case of an unexpected error, mark as failed
            await self.firebase_service.update_lead_status(lead.id, CallStatus.FAILED)
            return False

    # --- CALL OUTCOME HANDLING ---
    async def _handle_call_outcome(self, lead: Lead, disconnection_reason: str, post_call_data: Dict) -> None:
        """Handle the outcome of a call and determine next steps based on post-call analysis."""
        try:
            # Check for opt-out request first, as it's highest priority
            opt_out_requested = post_call_data.get('llm_dynamic_variables', {}).get('opt_out', False)
            if opt_out_requested:
                await self.firebase_service.update_lead_status(lead.id, CallStatus.OPTED_OUT)
                self.logger.info(f"Lead {lead.id} opted out and marked as {CallStatus.OPTED_OUT.value}.")
                return

            # If call was answered (user_hangup or agent_hangup)
            if disconnection_reason in [DisconnectionReason.USER_HANGUP.value, DisconnectionReason.AGENT_HANGUP.value]: 
                self.logger.info(f"Call answered for lead {lead.id}, disconnection: {disconnection_reason}")
                
                # Check for callback request (reschedule_time from Retell's post-call variables)
                reschedule_time_str = post_call_data.get('llm_dynamic_variables', {}).get('reschedule_time') 
                
                if reschedule_time_str:
                    callback_time = self._parse_callback_time(reschedule_time_str)
                    if callback_time:
                        await self.firebase_service.move_lead_to_callback(lead.id, callback_time)
                        self.logger.info(f"Lead {lead.id} scheduled for callback at {callback_time}")
                        return
                
                # If no opt-out and no callback, then call completed successfully
                self.logger.info(f"Lead {lead.id} call completed successfully, no callback/opt-out.")
                await self.firebase_service.update_lead_status(lead.id, CallStatus.COMPLETED)
                
            else:
                # Call was not answered (busy, no_answer, voicemail, etc.)
                self.logger.info(f"Call not answered for lead {lead.id}, disconnection: {disconnection_reason}")
                
                # Check retry attempts
                if lead.number_of_retries < settings.max_retries:
                    # Schedule for the next day, same time as current batch started
                    retry_date = (datetime.now(settings.app_timezone_obj) + timedelta(days=1)).date() 
                    await self.firebase_service.move_lead_to_retry(lead.id, lead.number_of_retries + 1, retry_date)
                    self.logger.info(f"Lead {lead.id} scheduled for retry on {retry_date} (attempt {lead.number_of_retries + 1})")
                else:
                    # Max retries reached
                    await self.firebase_service.update_lead_status(lead.id, CallStatus.FAILED)
                    self.logger.info(f"Lead {lead.id} marked as {CallStatus.FAILED.value} after {settings.max_retries} attempts")
            
        except Exception as e:
            self.logger.error(f"Error handling call outcome for lead {lead.id}: {str(e)}")
            raise

    # --- UTILITY FUNCTIONS ---
    async def _find_lead_by_phone(self, phone_number: str) -> Optional[Lead]:
        """Find a lead by phone number in the main LEADS_COLLECTION."""
        try:
            # This method in FirebaseService already handles the async.to_thread for stream()
            lead = await self.firebase_service.get_lead_by_phone_number(phone_number)
            if lead:
                return lead
            
            self.logger.info(f"No lead found for phone number: {phone_number}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding lead by phone: {str(e)}")
            raise
    
    def _is_calling_hours(self, current_time: datetime) -> bool: 
        """
        Check if current time (timezone-aware) is within calling hours.
        The current_time passed to this function *must* be timezone-aware.
        """
        # Define start and end datetimes for today based on settings and current_time's date
        start_of_calling_day = current_time.replace(
            hour=settings.calling_start_hour, 
            minute=0, 
            second=0, 
            microsecond=0
        )
        end_of_calling_day = current_time.replace(
            hour=settings.calling_end_hour, 
            minute=settings.calling_end_minute, 
            second=0, 
            microsecond=0
        )
        
        # Adjust if end_hour is numerically smaller than start_hour (e.g., 10 AM to 2 AM next day)
        # This case is unlikely with 10 AM to 11:30 PM, but good for robustness
        if settings.calling_end_hour < settings.calling_start_hour:
             # If end time is before start time (e.g., 10 PM - 6 AM), it spans two days.
             # We assume calling_end_hour means end of the *next* day for such cases.
             # For 10 AM - 11:30 PM, this block won't typically run as 23 > 10.
            if current_time < start_of_calling_day: # e.g., 4 AM when start is 10 AM
                # This could be the tail end of yesterday's calling hours
                yesterday_end_of_calling_day = end_of_calling_day - timedelta(days=1)
                return current_time >= yesterday_end_of_calling_day
        
        # Simple check for cases where start <= end (e.g., 10 AM to 11:30 PM)
        is_within_hours = (current_time >= start_of_calling_day) and \
                          (current_time <= end_of_calling_day) # Use <= to include end minute
                                                    
        self.logger.debug(f"Calling hours check: Current {current_time.strftime('%H:%M')}, "
                          f"Window: {start_of_calling_day.strftime('%H:%M')} - {end_of_calling_day.strftime('%H:%M')}. "
                          f"Result: {is_within_hours}")
        return is_within_hours

    def _parse_callback_time(self, callback_time_str: str) -> Optional[datetime]:
        """Parse callback time string into datetime object, ensuring timezone awareness."""
        try:
            # Try to parse common formats
            for fmt in ['%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', 
                        '%Y-%m-%dT%H:%M:%S.%f', '%H:%M']: # Added %H:%M for simple time
                try:
                    dt_obj = datetime.strptime(callback_time_str, fmt)
                    # If only time was provided, assume today's date
                    if fmt == '%H:%M':
                        today = datetime.now(settings.app_timezone_obj)
                        dt_obj = today.replace(hour=dt_obj.hour, minute=dt_obj.minute, 
                                               second=0, microsecond=0)
                    # Make it timezone-aware if not already (replace will add it if naive)
                    if dt_obj.tzinfo is None:
                        dt_obj = dt_obj.replace(tzinfo=settings.app_timezone_obj)
                    return dt_obj
                except ValueError:
                    continue
            
            # Handle relative terms like "tomorrow"
            if callback_time_str.lower() in ['tomorrow', 'next day']:
                # For "tomorrow", set to a default time like 10 AM (start of business day) in the app's timezone
                tomorrow = datetime.now(settings.app_timezone_obj) + timedelta(days=1)
                return tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
            
            self.logger.warning(f"Could not parse callback time string into datetime: '{callback_time_str}'")
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing callback time '{callback_time_str}': {str(e)}")
            return None