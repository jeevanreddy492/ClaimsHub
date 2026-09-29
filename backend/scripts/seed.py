"""Load FAKE demo data (Faker). Never real people.

Usage:
  python -m scripts.seed                     # demo users + 3 employers + ~60 claims
  python -m scripts.seed --claims 50000      # big data set for performance work

Demo logins (password for all: Passw0rd!):
  adjuster1 (ADJUSTER)   supervisor1 (SUPERVISOR)   viewer1 (VIEWER)
"""

import argparse
import random
from datetime import date, timedelta
from decimal import Decimal

from faker import Faker
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import (
    AppUser,
    Beneficiary,
    Claim,
    Claimant,
    ClaimStatusHistory,
    Employer,
    LeaveRequest,
    LifeClaimDetail,
    Policy,
    StdClaimDetail,
)
from app.repositories.claim_repository import ClaimRepository

fake = Faker("en_US")
Faker.seed(42)
random.seed(42)

DEMO_PASSWORD = "Passw0rd!"  # noqa: S105  (demo only, documented in README)
CONDITIONS = ["MUSCULOSKELETAL", "SURGERY", "MATERNITY", "INJURY", "CARDIAC", "MENTAL_HEALTH"]
STATUSES = ["RECEIVED", "IN_REVIEW", "APPROVED", "DENIED", "CLOSED"]


def seed_users(s: Session) -> None:
    users = [
        ("adjuster1", "Alex Adjuster", "ADJUSTER"),
        ("adjuster2", "Sam Adjuster", "ADJUSTER"),
        ("supervisor1", "Pat Supervisor", "SUPERVISOR"),
        ("viewer1", "Vic Viewer", "VIEWER"),
    ]
    hashed = hash_password(DEMO_PASSWORD)
    for username, name, role in users:
        if s.scalar(select(AppUser).where(AppUser.username == username)) is None:
            s.add(AppUser(username=username, full_name=name, role=role, password_hash=hashed))
    s.commit()


def seed_employers(s: Session) -> list[tuple[Employer, Policy, Policy]]:
    result = []
    for i, name in enumerate(["Acme Logistics", "Blue Harbor Health", "Summit Retail Group"], 1):
        emp = s.scalar(select(Employer).where(Employer.name == name))
        if emp is None:
            emp = Employer(name=name, tax_id=f"{10 + i}-{random.randint(1000000, 9999999)}")
            s.add(emp)
            s.flush()
            s.add_all(
                [
                    Policy(
                        policy_number=f"STD-{emp.employer_id:04d}-001",
                        employer_id=emp.employer_id,
                        product_type="STD",
                        benefit_pct=Decimal("60"),
                        max_weekly_benefit=Decimal("1500"),
                        elimination_days=7,
                        max_benefit_weeks=26,
                        effective_date=date(2020, 1, 1),
                    ),
                    Policy(
                        policy_number=f"LIFE-{emp.employer_id:04d}-001",
                        employer_id=emp.employer_id,
                        product_type="LIFE",
                        face_amount=Decimal("100000"),
                        effective_date=date(2020, 1, 1),
                    ),
                ]
            )
            s.flush()
        std = s.scalar(
            select(Policy).where(
                Policy.employer_id == emp.employer_id, Policy.product_type == "STD"
            )
        )
        life = s.scalar(
            select(Policy).where(
                Policy.employer_id == emp.employer_id, Policy.product_type == "LIFE"
            )
        )
        assert std and life
        result.append((emp, std, life))
    s.commit()
    return result


def seed_claims(s: Session, employers: list[tuple[Employer, Policy, Policy]], count: int) -> None:
    start_id = s.scalar(select(Claim.claim_id).order_by(Claim.claim_id.desc()).limit(1)) or 0
    claims_repo = ClaimRepository(s)  # same numbering as the API (Oracle sequence)
    batch = 0
    for n in range(count):
        emp, std, life = random.choice(employers)
        hire = fake.date_between(date(2008, 1, 1), date(2023, 12, 31))
        claimant = Claimant(
            employer_id=emp.employer_id,
            employee_number=f"E{start_id + n + 1:07d}",
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            date_of_birth=fake.date_between(date(1960, 1, 1), date(2000, 12, 31)),
            hire_date=hire,
            weekly_salary=Decimal(random.randrange(700, 3500)),
            email=fake.email(),
        )
        s.add(claimant)
        s.flush()

        is_life = random.random() < 0.15
        received = fake.date_between(date.today() - timedelta(days=720), date.today())
        status = random.choices(STATUSES, weights=[15, 25, 30, 15, 15])[0]
        claim_type = "LIFE" if is_life else "STD"
        claim = Claim(
            claim_number=claims_repo.next_claim_number(claim_type, received.year),
            claimant_id=claimant.claimant_id,
            policy_id=(life if is_life else std).policy_id,
            claim_type=claim_type,
            status=status,
            received_date=received,
            closed_date=received + timedelta(days=90) if status == "CLOSED" else None,
            assigned_to=random.choice(["adjuster1", "adjuster2"]),
            created_by="seed",
        )
        if is_life:
            claim.life_detail = LifeClaimDetail(
                date_of_death=received - timedelta(days=random.randint(3, 30)),
                cause_category=random.choice(["NATURAL", "ACCIDENT", "ILLNESS"]),
                payout_amount=life.face_amount or Decimal("100000"),
            )
            claim.beneficiaries = [
                Beneficiary(
                    full_name=fake.name(), relationship_type="SPOUSE", share_pct=Decimal("60")
                ),
                Beneficiary(
                    full_name=fake.name(), relationship_type="CHILD", share_pct=Decimal("40")
                ),
            ]
        else:
            dis_start = received - timedelta(days=random.randint(1, 20))
            weekly = min(claimant.weekly_salary * Decimal("0.6"), Decimal("1500"))
            claim.std_detail = StdClaimDetail(
                disability_start_date=dis_start,
                condition_category=random.choice(CONDITIONS),
                elimination_days=7,
                weekly_benefit=weekly.quantize(Decimal("0.01")) if status != "RECEIVED" else None,
                benefit_start_date=dis_start + timedelta(days=7) if status != "RECEIVED" else None,
            )
            if random.random() < 0.5:
                s.add(
                    LeaveRequest(
                        claimant_id=claimant.claimant_id,
                        leave_type="MEDICAL",
                        start_date=dis_start,
                        end_date=dis_start + timedelta(days=42),
                        status="APPROVED",
                        created_by="seed",
                    )
                )
        s.add(claim)
        s.flush()
        s.add(
            ClaimStatusHistory(
                claim_id=claim.claim_id,
                from_status=None,
                to_status="RECEIVED",
                reason="Claim filed",
                changed_by="seed",
            )
        )
        if status != "RECEIVED":
            s.add(
                ClaimStatusHistory(
                    claim_id=claim.claim_id,
                    from_status="RECEIVED",
                    to_status=status,
                    reason="Seed data",
                    changed_by="seed",
                )
            )
        batch += 1
        if batch >= 500:
            s.commit()
            batch = 0
            print(f"  {n + 1} claims...")
    s.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims", type=int, default=60)
    args = parser.parse_args()
    with SessionLocal() as s:
        seed_users(s)
        employers = seed_employers(s)
        seed_claims(s, employers, args.claims)
    print(f"Seed done: {args.claims} claims. Demo password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
