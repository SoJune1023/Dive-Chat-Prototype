# <---------- Custom Exception ---------->
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class AppError(Exception):
    message: str
    http_status: int
    err_code: str = "ERR_UNKNOWN"
    details: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {"error": self.message, "code": self.err_code}
        if self.details:
            payload["details"] = self.details
        return payload