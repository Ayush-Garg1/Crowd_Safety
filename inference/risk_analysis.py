import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import get_settings

def analyze_risk(persons, width, height, room_area_m2):
    s = get_settings()
    count = len(persons)

    if room_area_m2 <= 0 or count == 0:
        return {
            "count": count,
            "level": "NONE",
            "density": 0.0,
            "room_area_m2": room_area_m2,
        }

    # Density = people per square metre
    density = count / room_area_m2

    if density >= float(s.density_high):
        level = "HIGH"
    elif density >= float(s.density_medium):
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "count": count,
        "level": level,
        "density": round(density, 3),
        "room_area_m2": room_area_m2,
    }