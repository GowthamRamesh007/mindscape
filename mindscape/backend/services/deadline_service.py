import pytz
from datetime import datetime

# Standard Timezone for MINDSCAPE: Asia/Kolkata
IST = pytz.timezone("Asia/Kolkata")

# Official Competition Deadlines
REGISTRATION_DEADLINE_STR = "2026-10-07 23:59:59+05:30"
SUBMISSION_DEADLINE_STR = "2026-11-08 23:59:59+05:30"

def get_current_ist_time() -> datetime:
    return datetime.now(IST)

def parse_ist_timestamp(ts_str: str) -> datetime:
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(IST)

def is_registration_open(custom_deadline_str: str = None) -> bool:
    now = get_current_ist_time()
    deadline = parse_ist_timestamp(custom_deadline_str or REGISTRATION_DEADLINE_STR)
    return now <= deadline

def is_submission_open(custom_deadline_str: str = None) -> bool:
    now = get_current_ist_time()
    deadline = parse_ist_timestamp(custom_deadline_str or SUBMISSION_DEADLINE_STR)
    return now <= deadline

def get_competition_deadline_status():
    now = get_current_ist_time()
    reg_dl = parse_ist_timestamp(REGISTRATION_DEADLINE_STR)
    sub_dl = parse_ist_timestamp(SUBMISSION_DEADLINE_STR)

    reg_diff = (reg_dl - now).total_seconds()
    sub_diff = (sub_dl - now).total_seconds()

    return {
        "current_time_ist": now.isoformat(),
        "registration_deadline": reg_dl.isoformat(),
        "submission_deadline": sub_dl.isoformat(),
        "is_registration_open": reg_diff > 0,
        "is_submission_open": sub_diff > 0,
        "days_to_registration_deadline": max(0, int(reg_diff // 86400)),
        "days_to_submission_deadline": max(0, int(sub_diff // 86400)),
        "registration_remaining_seconds": max(0, int(reg_diff)),
        "submission_remaining_seconds": max(0, int(sub_diff)),
    }
