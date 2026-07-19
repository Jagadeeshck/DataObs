def baseline_confidence(sample_count: int, minimum_samples: int, missing_ratio: float = 0.0) -> float:
    maturity = min(1.0, sample_count / max(1, minimum_samples))
    return round(max(0.0, maturity * (1 - min(1.0, max(0.0, missing_ratio)))), 4)
