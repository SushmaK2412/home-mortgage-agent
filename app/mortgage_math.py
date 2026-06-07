"""Deterministic P&I amortization used by the first-time buyer assistant tools."""


def monthly_principal_interest(loan_amount: float, annual_rate_percent: float, years: int) -> float:
    """Fixed-rate amortizing loan: principal + interest only (no taxes/insurance)."""
    if loan_amount <= 0 or years <= 0:
        raise ValueError("loan_amount and years must be positive")
    n = years * 12
    r = (annual_rate_percent / 100.0) / 12.0
    if r == 0:
        return round(loan_amount / n, 2)
    payment = loan_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    return round(payment, 2)
