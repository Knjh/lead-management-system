# services/firebase_service.py
import firebase_admin
from firebase_admin import credentials, firestore
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, date, timedelta
from config.settings import settings
import asyncio 
from models.lead_models import Lead, CallStatus 

class FirebaseService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialize_firebase()
        # self.db is the synchronous Firestore client
        self.db = firestore.client() 
        
        self.LEADS_COLLECTION = "leads"
        
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK (synchronous)"""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(settings.firebase_service_account_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': settings.firebase_project_id,
                })
            self.logger.info("Firebase initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise
    
    # All methods that interact with self.db need to use asyncio.to_thread
    
    async def create_lead(self, lead: Lead) -> str:
        """Create a new lead in Firestore (synchronous operation run in thread)"""
        try:
            lead_dict = lead.model_dump(exclude_none=True)
            lead_dict['created_at'] = firestore.SERVER_TIMESTAMP
            lead_dict['updated_at'] = firestore.SERVER_TIMESTAMP
            lead_dict['call_status'] = CallStatus.NEW.value
            lead_dict['number_of_retries'] = 0
            lead_dict['last_call_time'] = None 
            lead_dict['callback_time'] = None 
            lead_dict['retry_date'] = None
            
            # Use asyncio.to_thread to run the blocking Firestore call
            doc_ref = await asyncio.to_thread(self.db.collection(self.LEADS_COLLECTION).document)
            await asyncio.to_thread(doc_ref.set, lead_dict) 
            
            lead_id = doc_ref.id
            
            self.logger.info(f"Created lead with ID: {lead_id}")
            return lead_id
            
        except Exception as e:
            self.logger.error(f"Error creating lead: {str(e)}")
            raise
    
    # async def bulk_create_leads(self, leads: List[Lead]) -> List[str]:
        """Create multiple leads in batch (synchronous operation run in thread)"""
        try:
            if not leads:
                self.logger.info("No leads to bulk create.")
                return []

            # Create the batch object synchronously
            batch = self.db.batch()
            lead_ids = []
            
            for lead in leads:
                lead_dict = lead.model_dump(exclude_none=True)
                lead_dict['created_at'] = firestore.SERVER_TIMESTAMP
                lead_dict['updated_at'] = firestore.SERVER_TIMESTAMP
                lead_dict['call_status'] = CallStatus.NEW.value
                lead_dict['number_of_retries'] = 0
                lead_dict['last_call_time'] = None
                lead_dict['callback_time'] = None
                lead_dict['retry_date'] = None
                
                # Get document reference synchronously
                doc_ref = self.db.collection(self.LEADS_COLLECTION).document()
                batch.set(doc_ref, lead_dict)
                lead_ids.append(doc_ref.id)
                
            # --- This is the key change: AWAITING the synchronous batch.commit() operation ---
            await asyncio.to_thread(batch.commit)
            self.logger.info(f"Created {len(lead_ids)} leads in batch")
            return lead_ids
            
        except Exception as e:
            self.logger.error(f"Error in bulk create leads: {str(e)}")
            raise

##################################################################
    async def get_lead_by_phone_number(self, phone_number: str) -> Optional[Lead]:
        """
        Retrieves a lead by phone number.
        Since phone numbers are indexed, this should be efficient.
        """
        try:
            # Firestore doesn't enforce uniqueness, so it's possible to have multiple.
            # We'll just take the first one found.
            query = (self.db.collection(self.LEADS_COLLECTION)
                     .where(filter=firestore.FieldFilter('phone_number', '==', phone_number))
                     .limit(1))
            
            # Run the synchronous query in a thread
            docs_stream = await asyncio.to_thread(query.stream)
            
            for doc in docs_stream:
                data = doc.to_dict()
                data['id'] = doc.id
                return Lead(**data)
            return None # No lead found
        except Exception as e:
            self.logger.error(f"Error getting lead by phone number {phone_number}: {str(e)}")
            raise

    async def bulk_create_leads(self, leads: List[Lead]) -> List[str]:
        """Create multiple leads in batch, handling potential duplicates."""
        try:
            if not leads:
                self.logger.info("No leads to bulk create.")
                return []

            batch = self.db.batch()
            created_lead_ids = []
            updated_lead_ids = [] # To keep track of updated leads 
            skipped_leads_count = 0
            
            for lead in leads:
                # 1. Check if a lead with this phone number already exists
                existing_lead = await self.get_lead_by_phone_number(lead.phone_number)

                if existing_lead:
                    # OPTION 1: Skip 
                    self.logger.info(f"Skipping lead with phone number {lead.phone_number} (ID: {existing_lead.id}) as it already exists.")
                    skipped_leads_count += 1
                    
                    # OPTION 2: we might choose to update it instead:
                    # update_data = lead.model_dump(exclude={'id', 'created_at'}, exclude_none=True)
                    # update_data['updated_at'] = firestore.SERVER_TIMESTAMP
                    # batch.update(self.db.collection(self.LEADS_COLLECTION).document(existing_lead.id), update_data)
                    # updated_lead_ids.append(existing_lead.id)
                else:
                    # 2. If it doesn't exist, create a new one
                    lead_dict = lead.model_dump(exclude_none=True)
                    lead_dict['created_at'] = firestore.SERVER_TIMESTAMP
                    lead_dict['updated_at'] = firestore.SERVER_TIMESTAMP
                    lead_dict['call_status'] = CallStatus.NEW.value
                    lead_dict['number_of_retries'] = 0
                    lead_dict['last_call_time'] = None
                    lead_dict['callback_time'] = None
                    lead_dict['retry_date'] = None
                    
                    doc_ref = self.db.collection(self.LEADS_COLLECTION).document()
                    batch.set(doc_ref, lead_dict)
                    created_lead_ids.append(doc_ref.id)
            
            # Commit the batch operation
            await asyncio.to_thread(batch.commit)
            
            total_processed = len(created_lead_ids) + len(updated_lead_ids) + skipped_leads_count
            self.logger.info(f"Bulk lead processing complete: Created {len(created_lead_ids)} new leads, updated {len(updated_lead_ids)} existing leads, skipped {skipped_leads_count} leads. Total processed from batch: {total_processed}")
            
            return created_lead_ids # Return IDs of newly created leads
            
        except Exception as e:
            self.logger.error(f"Error in bulk create leads: {str(e)}")
            raise

###############################################################################################3
    async def update_lead(self, lead_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a lead document (synchronous operation run in thread)"""
        try:
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            # Use asyncio.to_thread to run the blocking Firestore call
            await asyncio.to_thread(
                self.db.collection(self.LEADS_COLLECTION).document(lead_id).update,
                update_data
            )
            self.logger.info(f"Updated lead {lead_id} with data: {update_data.keys()}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating lead {lead_id}: {str(e)}")
            raise # Important to raise here for proper error handling upstream
    
    async def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get a lead by ID (synchronous operation run in thread)"""
        try:
            # Use asyncio.to_thread to run the blocking Firestore call
            doc = await asyncio.to_thread(self.db.collection(self.LEADS_COLLECTION).document(lead_id).get)
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return Lead(**data)
            self.logger.warning(f"Lead with ID {lead_id} not found in {self.LEADS_COLLECTION}.")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting lead {lead_id}: {str(e)}")
            raise

    async def get_callback_leads_for_window(self, window_start: datetime, window_end: datetime) -> List[Lead]:
        """Get callback leads scheduled for the current time window (synchronous operation run in thread)."""
        try:
            leads_list: List[Lead] = []
            query = (self.db.collection(self.LEADS_COLLECTION)
                     .where(filter=firestore.FieldFilter('call_status', '==', CallStatus.CALLBACK.value))
                     .where(filter=firestore.FieldFilter('callback_time', '>=', window_start))
                     .where(filter=firestore.FieldFilter('callback_time', '<', window_end))
                     .order_by('callback_time')
                     .limit(settings.firebase_query_limit))
            
            # --- IMPORTANT: Use asyncio.to_thread for the synchronous .stream() call ---
            docs_stream = await asyncio.to_thread(query.stream)
            
            for doc in docs_stream: 
                try:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    leads_list.append(Lead(**data))
                except Exception as e:
                    self.logger.warning(f"Skipping malformed callback lead document {doc.id}: {e}")

            self.logger.debug(f"Retrieved {len(leads_list)} callback leads for window {window_start} - {window_end}")
            return leads_list
            
        except Exception as e:
            self.logger.error(f"Error getting current window callbacks: {str(e)}")
            raise

    async def get_missed_callback_leads(self, current_window_start: datetime) -> List[Lead]:
        """Get callback leads that were scheduled before current window but not called yet (synchronous operation run in thread)."""
        try:
            leads_list: List[Lead] = []
            query = (self.db.collection(self.LEADS_COLLECTION)
                     .where(filter=firestore.FieldFilter('call_status', '==', CallStatus.CALLBACK.value))
                     .where(filter=firestore.FieldFilter('callback_time', '<', current_window_start))
                     .order_by('callback_time')
                     .limit(settings.firebase_query_limit))
            
            # --- IMPORTANT: Use asyncio.to_thread for the synchronous .stream() call ---
            docs_stream = await asyncio.to_thread(query.stream)
            
            for doc in docs_stream: 
                try:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    leads_list.append(Lead(**data))
                except Exception as e:
                    self.logger.warning(f"Skipping malformed missed callback lead document {doc.id}: {e}")

            self.logger.debug(f"Retrieved {len(leads_list)} missed callback leads before {current_window_start}")
            return leads_list
            
        except Exception as e:
            self.logger.error(f"Error getting missed callbacks: {str(e)}")
            raise

    async def get_retry_leads_for_date(self, target_date: date) -> List[Lead]:
        """Get retry leads scheduled for a specific date (synchronous operation run in thread)."""
        try:
            leads_list: List[Lead] = []
            start_of_day = datetime.combine(target_date, datetime.min.time(), tzinfo=settings.app_timezone_obj)
            end_of_day = datetime.combine(target_date, datetime.max.time(), tzinfo=settings.app_timezone_obj)

            query = (self.db.collection(self.LEADS_COLLECTION)
                     .where(filter=firestore.FieldFilter('call_status', '==', CallStatus.RETRY.value))
                     .where(filter=firestore.FieldFilter('retry_date', '>=', start_of_day))
                     .where(filter=firestore.FieldFilter('retry_date', '<=', end_of_day))
                     .order_by('retry_date')
                     .limit(settings.firebase_query_limit))
            
            # --- IMPORTANT: Use asyncio.to_thread for the synchronous .stream() call ---
            docs_stream = await asyncio.to_thread(query.stream)
            
            for doc in docs_stream: 
                try:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    leads_list.append(Lead(**data))
                except Exception as e:
                    self.logger.warning(f"Skipping malformed retry lead document {doc.id}: {e}")

            self.logger.debug(f"Retrieved {len(leads_list)} retry leads for date {target_date.strftime('%Y-%m-%d')}.")
            return leads_list
            
        except Exception as e:
            self.logger.error(f"Error getting retry leads for date {target_date.strftime('%Y-%m-%d')}: {str(e)}")
            raise

    async def get_new_leads(self) -> List[Lead]:
        """Get new leads that haven't been called yet (synchronous operation run in thread)."""
        try:
            leads_list: List[Lead] = []
            query = (self.db.collection(self.LEADS_COLLECTION)
                     .where(filter=firestore.FieldFilter('call_status', '==', CallStatus.NEW.value))
                     .order_by('created_at')
                     .limit(settings.firebase_query_limit))
            
            # --- IMPORTANT: Use asyncio.to_thread for the synchronous .stream() call ---
            docs_stream = await asyncio.to_thread(query.stream)
            
            for doc in docs_stream: 
                try:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    leads_list.append(Lead(**data))
                except Exception as e:
                    self.logger.warning(f"Skipping malformed new lead document {doc.id}: {e}")

            self.logger.debug(f"Retrieved {len(leads_list)} new leads.")
            return leads_list
            
        except Exception as e:
            self.logger.error(f"Error getting new leads: {str(e)}")
            raise

    async def update_lead_status(self, lead_id: str, new_status: CallStatus) -> bool:
        """Update the call_status of a lead (synchronous operation run in thread)."""
        try:
            update_data = {
                'call_status': new_status.value,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            if new_status == CallStatus.CALLING:
                update_data['last_call_time'] = firestore.SERVER_TIMESTAMP
            
            # Use asyncio.to_thread to run the blocking Firestore call
            await asyncio.to_thread(
                self.db.collection(self.LEADS_COLLECTION).document(lead_id).update,
                update_data
            )
            self.logger.info(f"Updated lead {lead_id} status to {new_status.value}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating status for lead {lead_id}: {str(e)}")
            return False

    async def move_lead_to_retry(self, lead_id: str, retry_count: int, retry_date: date) -> bool:
        """Updates a lead's status to RETRY and sets retry details (synchronous operation run in thread)."""
        try:
            update_data = {
                'call_status': CallStatus.RETRY.value,
                'number_of_retries': retry_count,
                'retry_date': datetime.combine(retry_date, datetime.min.time(), tzinfo=settings.app_timezone_obj),
                'updated_at': firestore.SERVER_TIMESTAMP,
                'last_call_time': firestore.SERVER_TIMESTAMP
            }
            # This calls update_lead, which is now also using asyncio.to_thread
            await self.update_lead(lead_id, update_data) 
            self.logger.info(f"Moved lead {lead_id} to retry (attempt {retry_count}) for {retry_date.strftime('%Y-%m-%d')}")
            return True
        except Exception as e:
            self.logger.error(f"Error moving lead {lead_id} to retry: {str(e)}")
            return False
    
    async def move_lead_to_callback(self, lead_id: str, callback_time: datetime) -> bool:
        """Updates a lead's status to CALLBACK and sets callback time (synchronous operation run in thread)."""
        try:
            update_data = {
                'call_status': CallStatus.CALLBACK.value,
                'callback_time': callback_time,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            # This calls update_lead, which is now also using asyncio.to_thread
            await self.update_lead(lead_id, update_data)
            self.logger.info(f"Moved lead {lead_id} to callback for {callback_time}")
            return True
        except Exception as e:
            self.logger.error(f"Error moving lead {lead_id} to callback: {str(e)}")
            return False

    async def remove_lead_entry_from_queue_collection(self, collection_name: str, lead_id_to_find: str) -> None:
        """
        Removes a document from a specific queue collection that refers to a given main lead_id.
        (Synchronous operation run in thread).
        """
        self.logger.debug(f"Attempting to remove lead_id {lead_id_to_find} from {collection_name} queue.")
        try:
            query = self.db.collection(collection_name).where(filter=firestore.FieldFilter('lead_id', '==', lead_id_to_find))
            
            # --- IMPORTANT: Use asyncio.to_thread for the synchronous .stream() call ---
            docs_stream = await asyncio.to_thread(query.stream)
            
            for doc in docs_stream: 
                # doc.reference.delete() is also synchronous, needs to be awaited via to_thread
                await asyncio.to_thread(doc.reference.delete)
                self.logger.debug(f"Removed queue entry {doc.id} for lead {lead_id_to_find} from {collection_name}.")
        except Exception as e:
            self.logger.warning(f"Failed to remove lead {lead_id_to_find} from {collection_name} queue: {e}")