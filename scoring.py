from config import FURNISHED_PREMIUM, NEIGHBORHOODS


def _clamp(value: float, lo: float = 1.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


def score_price(price: float, total_people: int, neighborhood: str) -> float:
    """Compare room price to estimated per-person share of neighborhood average."""
    info = NEIGHBORHOODS[neighborhood]
    avg_per_person = info["avg_rent"] / total_people
    ratio = price / avg_per_person
    # 0.7x average → 10, 1.6x average → 1
    return _clamp(10 - (ratio - 0.7) * 9 / 0.9)


def score_location(neighborhood: str) -> float:
    """Lookup location score from config."""
    return float(NEIGHBORHOODS[neighborhood]["location_score"])


def score_value(price: float, size: float) -> float:
    """Score based on price per m²."""
    price_per_sqm = price / size
    # 20 CHF/m² → 10, 35 CHF/m² → 1
    return _clamp(10 - (price_per_sqm - 20) * 9 / 15)


def score_student(neighborhood: str) -> float:
    """Lookup student-friendliness score from config."""
    return float(NEIGHBORHOODS[neighborhood]["student_score"])


def score_transit(neighborhood: str) -> float:
    """Lookup transit connectivity score from config."""
    return float(NEIGHBORHOODS[neighborhood]["transit_score"])


def score_furnishing(furnished: bool, price: float, neighborhood: str) -> float:
    """Furnished gets a bonus; unfurnished at high price gets a penalty."""
    info = NEIGHBORHOODS[neighborhood]
    avg = info["avg_rent"]
    if furnished:
        # Furnished is convenient — bonus, but less so if price is way above average
        over_premium = max(0, price - avg - FURNISHED_PREMIUM)
        return _clamp(8 - over_premium / 200)
    # Unfurnished — neutral, slight penalty if expensive
    if price > avg * 1.2:
        return 4.0
    return 6.0


DEFAULT_WEIGHTS = {
    "price": 0.25,
    "location": 0.20,
    "value": 0.20,
    "student": 0.10,
    "transit": 0.15,
    "furnishing": 0.10,
}


def score_total(scores: dict[str, float], weights: dict[str, float] = DEFAULT_WEIGHTS) -> float:
    """Weighted average of all scores."""
    total = sum(scores[k] * weights[k] for k in weights)
    return round(_clamp(total), 1)
