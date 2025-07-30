# utils/csv_parser.py
import pandas as pd
import logging
from typing import List, Dict, Any
from io import StringIO

class CSVParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def parse_csv_content(self, csv_content: str) -> List[Dict[str, Any]]:
        """Parse CSV content and return list of dictionaries"""
        try:
            # Read CSV content
            df = pd.read_csv(StringIO(csv_content), dtype={'phone': str, 'phone_number': str, 'number': str, 'contact': str})
            
            # Clean column names (strip whitespace)
            df.columns = df.columns.str.strip()
            
            # Convert to list of dictionaries
            records = df.to_dict('records')
            
            # Clean up None/NaN values
            cleaned_records = []
            for record in records:
                cleaned_record = {k: (v if pd.notna(v) else '') for k, v in record.items()}
                cleaned_records.append(cleaned_record)
            
            self.logger.info(f"Successfully parsed {len(cleaned_records)} records from CSV")
            return cleaned_records
            
        except Exception as e:
            self.logger.error(f"Error parsing CSV: {str(e)}")
            raise
    
    async def parse_csv_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse CSV file and return list of dictionaries"""
        try:
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.strip()
            
            records = df.to_dict('records')
            cleaned_records = []
            for record in records:
                cleaned_record = {k: (v if pd.notna(v) else '') for k, v in record.items()}
                cleaned_records.append(cleaned_record)
            
            self.logger.info(f"Successfully parsed {len(cleaned_records)} records from file: {file_path}")
            return cleaned_records
            
        except Exception as e:
            self.logger.error(f"Error parsing CSV file {file_path}: {str(e)}")
            raise
    
    def validate_required_fields(self, records: List[Dict[str, Any]], required_fields: List[str]) -> bool:
        """Validate that all records have required fields"""
        try:
            for i, record in enumerate(records):
                for field in required_fields:
                    if field not in record or not record[field]:
                        self.logger.error(f"Missing required field '{field}' in record {i+1}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating CSV fields: {str(e)}")
            return False