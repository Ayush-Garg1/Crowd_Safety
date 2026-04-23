from config import get_settings

def analyze_risk(persons, width, height):
    s = get_settings()
    count = len(persons)

    # Simple density calculation
    area = width * height
    density = count / area * 100000  # scaled density

    if count >= s.risk_high:
        level = "HIGH"
    elif count >= s.risk_medium:
        level = "MEDIUM"
    elif count > 0:
        level = "LOW"
    else:
        level = "NONE"

    # if count >= 1:
    #     level = "HIGH"
    # else:
    #     level = "LOW"

    return {
        "count": count,
        "level": level,
        "avg_density": density,
        "max_density": density
    }
