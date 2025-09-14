# <---------- Payload ---------->
from schemas.note import SummaryPayload

# <---------- Handles ---------->
def summary_handle(req: SummaryPayload) -> tuple[bool, int, dict]: ...