"""REST endpoints, version 1. Routers stay thin: HTTP in, call a service, HTTP out."""

from datetime import date

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.deps import (
    auth_service,
    can_write,
    claim_service,
    claimant_service,
    get_current_user,
    leave_service,
    policy_service,
)
from app.core.security import CurrentUser
from app.domain.enums import ClaimStatus, ClaimType, ProductType
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.claim import (
    ClaimDetailOut,
    ClaimStats,
    ClaimSummaryOut,
    LifeClaimCreate,
    PaymentOut,
    ReturnToWorkRequest,
    StatusChangeRequest,
    StdClaimCreate,
)
from app.schemas.claimant import ClaimantCreate, ClaimantOut, ClaimantUpdate
from app.schemas.common import ErrorResponse, Page
from app.schemas.leave import LeaveCreate, LeaveOut, LeaveUpdate
from app.schemas.policy import EmployerCreate, EmployerOut, PolicyCreate, PolicyOut
from app.services.auth_service import AuthService
from app.services.claim_service import ClaimService
from app.services.claimant_service import ClaimantService
from app.services.leave_service import LeaveService
from app.services.policy_service import PolicyService

ERRORS: dict[int | str, dict] = {
    code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422)
}

router = APIRouter(prefix="/api/v1", responses=ERRORS)

IdemKey = Header(default=None, alias="Idempotency-Key", max_length=100)


# ---------------- auth ----------------
@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(body: LoginRequest, svc: AuthService = Depends(auth_service)) -> TokenResponse:
    return svc.login(body.username, body.password)


@router.get("/auth/me", tags=["auth"])
def me(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    return {"username": user.username, "role": user.role.value, "full_name": user.full_name}


# ---------------- employers & policies ----------------
@router.post("/employers", response_model=EmployerOut, status_code=201, tags=["employers"])
def create_employer(
    body: EmployerCreate,
    user: CurrentUser = Depends(can_write),
    svc: PolicyService = Depends(policy_service),
) -> object:
    return svc.create_employer(body, user)


@router.get("/employers", response_model=list[EmployerOut], tags=["employers"])
def list_employers(
    _: CurrentUser = Depends(get_current_user), svc: PolicyService = Depends(policy_service)
) -> object:
    return svc.list_employers()


@router.post("/policies", response_model=PolicyOut, status_code=201, tags=["policies"])
def create_policy(
    body: PolicyCreate,
    user: CurrentUser = Depends(can_write),
    svc: PolicyService = Depends(policy_service),
) -> object:
    return svc.create_policy(body, user)


@router.get("/policies", response_model=list[PolicyOut], tags=["policies"])
def list_policies(
    employer_id: int | None = None,
    product_type: ProductType | None = None,
    _: CurrentUser = Depends(get_current_user),
    svc: PolicyService = Depends(policy_service),
) -> object:
    return svc.list_policies(employer_id, product_type.value if product_type else None)


# ---------------- claimants ----------------
@router.post("/claimants", response_model=ClaimantOut, status_code=201, tags=["claimants"])
def create_claimant(
    body: ClaimantCreate,
    user: CurrentUser = Depends(can_write),
    svc: ClaimantService = Depends(claimant_service),
) -> object:
    return svc.create(body, user)


@router.get("/claimants", response_model=Page[ClaimantOut], tags=["claimants"])
def search_claimants(
    q: str | None = Query(default=None, max_length=60),
    employer_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: CurrentUser = Depends(get_current_user),
    svc: ClaimantService = Depends(claimant_service),
) -> object:
    items, total = svc.search(q, employer_id, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/claimants/{claimant_id}", response_model=ClaimantOut, tags=["claimants"])
def get_claimant(
    claimant_id: int,
    _: CurrentUser = Depends(get_current_user),
    svc: ClaimantService = Depends(claimant_service),
) -> object:
    return svc.get(claimant_id)


@router.patch("/claimants/{claimant_id}", response_model=ClaimantOut, tags=["claimants"])
def update_claimant(
    claimant_id: int,
    body: ClaimantUpdate,
    user: CurrentUser = Depends(can_write),
    svc: ClaimantService = Depends(claimant_service),
) -> object:
    return svc.update(claimant_id, body, user)


@router.get("/claimants/{claimant_id}/leaves", response_model=list[LeaveOut], tags=["leaves"])
def claimant_leaves(
    claimant_id: int,
    _: CurrentUser = Depends(get_current_user),
    svc: LeaveService = Depends(leave_service),
) -> object:
    return svc.for_claimant(claimant_id)


# ---------------- claims ----------------
@router.post("/claims/std", response_model=ClaimDetailOut, status_code=201, tags=["claims"])
def file_std_claim(
    body: StdClaimCreate,
    response: Response,
    idempotency_key: str | None = IdemKey,
    user: CurrentUser = Depends(can_write),
    svc: ClaimService = Depends(claim_service),
) -> object:
    claim, created = svc.file_std(body, user, idempotency_key)
    if not created:
        response.status_code = status.HTTP_200_OK
    return claim


@router.post("/claims/life", response_model=ClaimDetailOut, status_code=201, tags=["claims"])
def file_life_claim(
    body: LifeClaimCreate,
    response: Response,
    idempotency_key: str | None = IdemKey,
    user: CurrentUser = Depends(can_write),
    svc: ClaimService = Depends(claim_service),
) -> object:
    claim, created = svc.file_life(body, user, idempotency_key)
    if not created:
        response.status_code = status.HTTP_200_OK
    return claim


@router.get("/claims", response_model=Page[ClaimSummaryOut], tags=["claims"])
def search_claims(
    status_: ClaimStatus | None = Query(default=None, alias="status"),
    claim_type: ClaimType | None = None,
    claimant_id: int | None = None,
    claim_number: str | None = Query(default=None, max_length=30),
    received_from: date | None = None,
    received_to: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(claim_service),
) -> object:
    items, total = svc.search(
        status=status_.value if status_ else None,
        claim_type=claim_type.value if claim_type else None,
        claimant_id=claimant_id,
        claim_number=claim_number,
        received_from=received_from,
        received_to=received_to,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/claims/stats", response_model=ClaimStats, tags=["claims"])
def claim_stats(
    _: CurrentUser = Depends(get_current_user), svc: ClaimService = Depends(claim_service)
) -> object:
    return svc.stats()


@router.get("/claims/{claim_id}", response_model=ClaimDetailOut, tags=["claims"])
def get_claim(
    claim_id: int,
    _: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(claim_service),
) -> object:
    return svc.get(claim_id)


@router.post("/claims/{claim_id}/status", response_model=ClaimDetailOut, tags=["claims"])
def change_claim_status(
    claim_id: int,
    body: StatusChangeRequest,
    user: CurrentUser = Depends(can_write),
    svc: ClaimService = Depends(claim_service),
) -> object:
    return svc.change_status(claim_id, body, user)


@router.post("/claims/{claim_id}/calculate-benefit", response_model=ClaimDetailOut, tags=["claims"])
def calculate_benefit(
    claim_id: int,
    user: CurrentUser = Depends(can_write),
    svc: ClaimService = Depends(claim_service),
) -> object:
    return svc.calculate_benefit(claim_id, user)


@router.put("/claims/{claim_id}/return-to-work", response_model=ClaimDetailOut, tags=["claims"])
def set_return_to_work(
    claim_id: int,
    body: ReturnToWorkRequest,
    user: CurrentUser = Depends(can_write),
    svc: ClaimService = Depends(claim_service),
) -> object:
    return svc.set_return_to_work(claim_id, body, user)


@router.get("/claims/{claim_id}/payments", response_model=list[PaymentOut], tags=["claims"])
def claim_payments(
    claim_id: int,
    _: CurrentUser = Depends(get_current_user),
    svc: ClaimService = Depends(claim_service),
) -> object:
    return svc.payments(claim_id)


# ---------------- leaves ----------------
@router.post("/leaves", response_model=LeaveOut, status_code=201, tags=["leaves"])
def create_leave(
    body: LeaveCreate,
    user: CurrentUser = Depends(can_write),
    svc: LeaveService = Depends(leave_service),
) -> object:
    return svc.create(body, user)


@router.get("/leaves/{leave_id}", response_model=LeaveOut, tags=["leaves"])
def get_leave(
    leave_id: int,
    _: CurrentUser = Depends(get_current_user),
    svc: LeaveService = Depends(leave_service),
) -> object:
    return svc.get(leave_id)


@router.patch("/leaves/{leave_id}", response_model=LeaveOut, tags=["leaves"])
def update_leave(
    leave_id: int,
    body: LeaveUpdate,
    user: CurrentUser = Depends(can_write),
    svc: LeaveService = Depends(leave_service),
) -> object:
    return svc.update(leave_id, body, user)
