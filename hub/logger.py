import logging
import logging.handlers
import json
import os
from datetime import datetime, timezone

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy ingestion into Datadog, ELK, etc."""
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        
        # Add any extra kwargs passed to the log call
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def setup_logger(name: str, log_file: str, level=logging.INFO, json_format=True) -> logging.Logger:
    """Setup a rotating file logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if setup is called multiple times
    if logger.handlers:
        return logger
        
    # Rotate at 10MB, keep last 30 files
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, log_file), 
        maxBytes=10*1024*1024, 
        backupCount=30
    )
    
    if json_format:
        file_handler.setFormatter(JSONFormatter())
    else:
        # Standard text format for audit trails or simple logs
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
    logger.addHandler(file_handler)
    
    # Also log to console for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)
    
    return logger

# --- Hub Loggers ---
hub_logger = setup_logger("mep.hub", "hub.json")

# --- Audit Logger ---
# The Audit Trail is strictly append-only text to reconstruct the ledger if needed
audit_logger = setup_logger("mep.audit", "ledger_audit.log", json_format=False)

def log_event(event: str, message: str, **kwargs):
    """Helper to log JSON events with extra fields."""
    hub_logger.info(message, extra={"extra_fields": {"event": event, **kwargs}})

def log_audit(action: str, node_id: str, amount: float, new_balance: float, ref_id: str = ""):
    """Helper to strictly log SECONDS moving in the ledger."""
    sign = "+" if amount >= 0 else ""
    audit_logger.info(f"AUDIT | {action} | Node: {node_id} | Amount: {sign}{amount:.6f} | Balance: {new_balance:.6f} | Ref: {ref_id}")
