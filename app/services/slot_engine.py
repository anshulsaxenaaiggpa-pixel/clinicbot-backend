"""
Core Scheduling Engine - Production-ready slot generation
This is the CRITICAL PATH component - the brain of ClinicBot.ai
"""
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional
import pytz
import uuid


def parse_hm(hm: str) -> time:
    """Parse HH:MM string to time object"""
    return datetime.strptime(hm, "%H:%M").time()


def localize_dt(d: date, t: time, tz: pytz.timezone):
    """Combine date + time and localize to timezone"""
    return tz.localize(datetime.combine(d, t))


def utc_ts(dt_with_tz):
    """Convert timezone-aware datetime to UTC timestamp"""
    return int(dt_with_tz.astimezone(pytz.utc).timestamp())


def generate_free_slots_for_day(
    config: Dict,
    target_date: date,
    existing_appointments: Optional[List[Dict]] = None,
    doctor_id_filter: Optional[str] = None
) -> List[Dict]:
    """
    Generate all free slots for a specific day.
    
    Args:
        config: Clinic configuration (timing, doctors, services)
        target_date: Target date for slot generation
        existing_appointments: List of existing appointments
        doctor_id_filter: Optional doctor ID filter
        
    Returns:
        List of free slot dictionaries with UTC timestamps
    """
    if existing_appointments is None:
        existing_appointments = []
        
    tz = pytz.timezone(config.get("timezone", "Asia/Kolkata"))
    timing = _get_timing_for_day(config["clinic_timing"], target_date.strftime("%A").lower())
    
    if timing is None or timing.get("closed", False):
        return []
    
    # Get slot configuration
    appt_cfg = config.get("appointment_config", {})
    slot_interval = appt_cfg.get("slot_interval_mins") or (60 // appt_cfg.get("slots_per_hour", 4))
    buffer_mins = appt_cfg.get("buffer_mins", 0)
    
    # Get time blocks (respecting lunch break)
    blocks = _get_time_blocks_for_day(timing)
    
    # Get available doctors
    doctors = config.get("doctors", [])
    candidate_doctors = [d for d in doctors if (not doctor_id_filter) or d.get("id") == doctor_id_filter]
    
    if not candidate_doctors:
        return []
    
    # Organize existing appointments by doctor
    appts_by_doctor = {}
    for ap in existing_appointments:
        did = ap.get("doctor_id")
        appts_by_doctor.setdefault(did, []).append({
            "start": int(ap["start_utc_ts"]),
            "end": int(ap["end_utc_ts"])
        })
    
    free_slots = []
    
    # Generate slots for each doctor
    for doc in candidate_doctors:
        for (block_start, block_end) in blocks:
            block_start_dt = localize_dt(target_date, block_start, tz)
            block_end_dt = localize_dt(target_date, block_end, tz)
            
            cursor = block_start_dt
            while cursor + timedelta(minutes=slot_interval) <= block_end_dt:
                slot_end = cursor + timedelta(minutes=slot_interval)
                s_utc = utc_ts(cursor)
                e_utc = utc_ts(slot_end)
                
                # Check for conflicts
                conflict = False
                for ap in appts_by_doctor.get(doc.get("id"), []):
                    if not (ap["end"] <= s_utc or ap["start"] >= e_utc):
                        conflict = True
                        break
                
                if not conflict:
                    free_slots.append({
                        "slot_id": f"{target_date.strftime('%Y%m%d')}_{doc['id']}_{uuid.uuid4().hex[:6]}",
                        "doctor_id": doc["id"],
                        "start_local": cursor.strftime("%Y-%m-%dT%H:%M:%z"),
                        "end_local": slot_end.strftime("%Y-%m-%dT%H:%M:%z"),
                        "start_utc_ts": s_utc,
                        "end_utc_ts": e_utc,
                        "duration_mins": slot_interval
                    })
                
                cursor = cursor + timedelta(minutes=(slot_interval + buffer_mins))
    
    free_slots.sort(key=lambda x: (x["start_utc_ts"], x["doctor_id"]))
    return free_slots


def reserve_consecutive_slots(day_slots: List[Dict], service_duration: int) -> Optional[List[Dict]]:
    """
    Find first sequence of consecutive available slots matching service duration.
    
    Args:
        day_slots: List of available slots for the day (sorted by start time)
        service_duration: Duration in minutes (e.g., 15, 30, 45, 60)
        
    Returns:
        List of consecutive slot dicts or None if not found
    """
    if not day_slots:
        return None
    
    required_blocks = service_duration // 15  # Assuming 15-min base slots
    current_chain = []
    
    for slot in day_slots:
        if slot.get("available", True):  # Default to available if not specified
            if not current_chain:
                current_chain = [slot]
            else:
                # Check if slots are consecutive
                prev = current_chain[-1]
                if slot["start_utc_ts"] == prev["end_utc_ts"]:
                    current_chain.append(slot)
                else:
                    current_chain = [slot]
        else:
            current_chain = []
        
        if len(current_chain) == required_blocks:
            return current_chain
    
    return None


def _get_timing_for_day(clinic_timing: Dict, day_name: str):
    """Get timing configuration for specific day"""
    if day_name == "sunday":
        return None if clinic_timing.get("sunday_closed", True) else clinic_timing.get("weekdays")
    if day_name == "saturday":
        sat = clinic_timing.get("saturday", {"closed": True})
        return None if sat.get("closed", True) else sat
    return clinic_timing.get("weekdays")


def _get_time_blocks_for_day(timing: Dict):
    """Get time blocks for day, splitting on lunch break"""
    start = parse_hm(timing["start"])
    end = parse_hm(timing["end"])
    lunch = timing.get("lunch_break", {"enabled": False})
    
    if lunch.get("enabled"):
        lstart = parse_hm(lunch["start"])
        lend = parse_hm(lunch["end"])
        blocks = []
        if start < lstart:
            blocks.append((start, min(lstart, end)))
        if lend < end:
            blocks.append((max(lend, start), end))
        return blocks
    else:
        return [(start, end)]
