from datetime import date
from decimal import Decimal

import pytest

from app.domain.benefits import LifeBenefitCalculator, StdBenefitCalculator
from app.domain.claim_rules import ALLOWED_TRANSITIONS, can_transition, role_can_set
from app.domain.enums import ClaimStatus, Role


class TestStatusRules:
    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (ClaimStatus.RECEIVED, ClaimStatus.IN_REVIEW),
            (ClaimStatus.IN_REVIEW, ClaimStatus.APPROVED),
            (ClaimStatus.IN_REVIEW, ClaimStatus.DENIED),
            (ClaimStatus.DENIED, ClaimStatus.APPEALED),
            (ClaimStatus.APPEALED, ClaimStatus.IN_REVIEW),
            (ClaimStatus.APPROVED, ClaimStatus.CLOSED),
        ],
    )
    def test_allowed(self, current: ClaimStatus, target: ClaimStatus) -> None:
        assert can_transition(current, target)

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (ClaimStatus.RECEIVED, ClaimStatus.APPROVED),
            (ClaimStatus.CLOSED, ClaimStatus.IN_REVIEW),
            (ClaimStatus.APPROVED, ClaimStatus.DENIED),
        ],
    )
    def test_blocked(self, current: ClaimStatus, target: ClaimStatus) -> None:
        assert not can_transition(current, target)

    def test_every_status_has_rules(self) -> None:
        assert set(ALLOWED_TRANSITIONS) == set(ClaimStatus)

    def test_roles(self) -> None:
        assert role_can_set(Role.SUPERVISOR, ClaimStatus.APPROVED)
        assert not role_can_set(Role.ADJUSTER, ClaimStatus.APPROVED)
        assert role_can_set(Role.ADJUSTER, ClaimStatus.IN_REVIEW)
        assert not role_can_set(Role.VIEWER, ClaimStatus.IN_REVIEW)


class TestStdBenefit:
    calc = StdBenefitCalculator()

    def test_percent_of_salary(self) -> None:
        r = self.calc.calculate(
            Decimal("1000"), Decimal("60"), Decimal("1500"), date(2026, 3, 1), 7
        )
        assert r.weekly_benefit == Decimal("600.00")
        assert r.benefit_start_date == date(2026, 3, 8)

    def test_capped_at_policy_max(self) -> None:
        r = self.calc.calculate(
            Decimal("4000"), Decimal("60"), Decimal("1500"), date(2026, 3, 1), 0
        )
        assert r.weekly_benefit == Decimal("1500.00")

    def test_rounds_half_up(self) -> None:
        r = self.calc.calculate(
            Decimal("1000.25"), Decimal("66.67"), Decimal("5000"), date(2026, 1, 1), 0
        )
        assert r.weekly_benefit == Decimal("666.87")  # 666.866675 -> 666.87

    def test_rejects_bad_input(self) -> None:
        with pytest.raises(ValueError):
            self.calc.calculate(Decimal("0"), Decimal("60"), Decimal("1500"), date(2026, 1, 1), 7)


class TestLifeSplit:
    calc = LifeBenefitCalculator()

    def test_split_is_exact(self) -> None:
        amounts = self.calc.split(
            Decimal("100000.00"), [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
        )
        assert sum(amounts) == Decimal("100000.00")

    def test_rounding_cent_goes_to_first(self) -> None:
        amounts = self.calc.split(
            Decimal("100.00"), [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
        )
        assert amounts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
        amounts = self.calc.split(Decimal("0.10"), [Decimal("50"), Decimal("50")])
        assert sum(amounts) == Decimal("0.10")

    def test_shares_must_total_100(self) -> None:
        with pytest.raises(ValueError):
            self.calc.split(Decimal("1000"), [Decimal("50"), Decimal("40")])
