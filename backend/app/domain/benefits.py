"""Benefit calculators (strategy pattern).

Oracle runs the same STD formula in CLAIMS_PKG.calculate_std_benefit. This Python
version is used for previews, for tests and to document the rule in one place.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


@dataclass(frozen=True)
class StdBenefit:
    weekly_benefit: Decimal
    benefit_start_date: date


class BenefitCalculator(ABC):
    @abstractmethod
    def describe(self) -> str: ...


class StdBenefitCalculator(BenefitCalculator):
    """weekly benefit = weekly salary x benefit % (capped at the policy max).

    Benefits start after the elimination (waiting) period.
    """

    def calculate(
        self,
        weekly_salary: Decimal,
        benefit_pct: Decimal,
        max_weekly_benefit: Decimal,
        disability_start: date,
        elimination_days: int,
    ) -> StdBenefit:
        if weekly_salary <= 0:
            raise ValueError("weekly salary must be positive")
        if not Decimal(0) < benefit_pct <= Decimal(100):
            raise ValueError("benefit percent must be between 0 and 100")
        raw = weekly_salary * benefit_pct / Decimal(100)
        weekly = min(raw, max_weekly_benefit).quantize(CENT, rounding=ROUND_HALF_UP)
        return StdBenefit(weekly, disability_start + timedelta(days=elimination_days))

    def describe(self) -> str:
        return "STD: salary x benefit %, capped at policy max, after elimination period"


class LifeBenefitCalculator(BenefitCalculator):
    """Life payout = policy face amount, split by beneficiary share %."""

    def split(self, face_amount: Decimal, shares_pct: list[Decimal]) -> list[Decimal]:
        if sum(shares_pct) != Decimal(100):
            raise ValueError("beneficiary shares must add up to 100")
        amounts = [
            (face_amount * s / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
            for s in shares_pct
        ]
        # Put any rounding cent on the first beneficiary so the total is exact
        # (same rule as CLAIMS_PKG.approve_life_claim).
        amounts[0] += face_amount - sum(amounts)
        return amounts

    def describe(self) -> str:
        return "LIFE: face amount split by beneficiary share"
