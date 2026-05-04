"""
Public (unauthenticated) views for the SomaMange marketing site.

These views are intentionally light on dependencies and never touch tenant data.
They serve the landing page and accept inbound school applications (leads).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from .models import PlatformLead

logger = logging.getLogger(__name__)

# ── validation ────────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^[+0-9][0-9\s\-()]{6,30}$")
MAX_FIELD_LEN = 2_000


def _client_ip(request: HttpRequest) -> Optional[str]:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _clean(value: str, max_len: int = 255) -> str:
    return (value or "").strip()[:max_len]


# ── views ─────────────────────────────────────────────────────────────────────
@require_GET
def landing(request: HttpRequest) -> HttpResponse:
    """Public marketing homepage. Authenticated users are sent to their dashboard."""
    if request.user.is_authenticated:
        return redirect(reverse("home"))
    context = {
        "plan_choices":       PlatformLead.PLAN_CHOICES,
        "school_type_choices": PlatformLead.SCHOOL_TYPE_CHOICES,
    }
    return render(request, "landing/home.html", context)


@require_POST
@csrf_protect
def apply(request: HttpRequest) -> JsonResponse:
    """
    Accept a school application / demo request from the marketing site.
    Returns JSON for fetch-based submission and saves a PlatformLead row.
    """
    # Basic body-size guard (Django already caps, this is defense-in-depth).
    if int(request.META.get("CONTENT_LENGTH") or 0) > 20_000:
        return JsonResponse({"success": False, "message": "Request too large."}, status=413)

    # Accept both form-encoded and JSON bodies.
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"success": False, "message": "Invalid JSON."}, status=400)
    else:
        data = request.POST

    # Honeypot — silently reject bots.
    if _clean(data.get("website", ""), 255):
        return JsonResponse({"success": True, "message": "Thank you."})

    school_name  = _clean(data.get("school_name", ""), 255)
    contact_name = _clean(data.get("contact_name", ""), 150)
    email        = _clean(data.get("email", ""), 254).lower()
    phone        = _clean(data.get("phone", ""), 32)
    district     = _clean(data.get("district", ""), 100)
    school_type  = _clean(data.get("school_type", "primary"), 20)
    plan         = _clean(data.get("plan_interest", "unsure"), 20)
    message      = _clean(data.get("message", ""), MAX_FIELD_LEN)

    try:
        student_count_raw = _clean(str(data.get("student_count", "")), 10)
        student_count: Optional[int] = int(student_count_raw) if student_count_raw else None
        if student_count is not None and (student_count < 0 or student_count > 1_000_000):
            student_count = None
    except (TypeError, ValueError):
        student_count = None

    # Whitelist choice fields — never trust the client.
    valid_types = {c[0] for c in PlatformLead.SCHOOL_TYPE_CHOICES}
    valid_plans = {c[0] for c in PlatformLead.PLAN_CHOICES}
    if school_type not in valid_types:
        school_type = "primary"
    if plan not in valid_plans:
        plan = "unsure"

    errors: dict[str, str] = {}
    if len(school_name) < 2:
        errors["school_name"] = "Please enter the full school name."
    if len(contact_name) < 2:
        errors["contact_name"] = "Please enter the contact person's name."
    if not EMAIL_RE.match(email):
        errors["email"] = "Please enter a valid email."
    if not PHONE_RE.match(phone):
        errors["phone"] = "Please enter a valid phone number."

    if errors:
        return JsonResponse(
            {"success": False, "message": "Please fix the highlighted fields.", "errors": errors},
            status=400,
        )

    try:
        lead = PlatformLead.objects.create(
            school_name=school_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            district=district,
            school_type=school_type,
            student_count=student_count,
            plan_interest=plan,
            message=message,
            source_ip=_client_ip(request),
            user_agent=_clean(request.META.get("HTTP_USER_AGENT", ""), 255),
            referrer=_clean(request.META.get("HTTP_REFERER", ""), 2000),
        )
    except IntegrityError:
        logger.exception("PlatformLead create failed")
        return JsonResponse({"success": False, "message": "Could not save your request. Please retry."}, status=500)

    logger.info("New PlatformLead %s from %s", lead.pk, email)

    # Optional email notification — never fatal if email is unconfigured.
    try:
        from django.core.mail import mail_admins
        mail_admins(
            subject=f"[SomaMange] New application: {school_name}",
            message=(
                f"School: {school_name}\n"
                f"Contact: {contact_name} <{email}>\n"
                f"Phone: {phone}\nDistrict: {district}\n"
                f"Type: {school_type}  Plan: {plan}  Students: {student_count}\n\n"
                f"Message:\n{message}\n"
            ),
            fail_silently=True,
        )
    except Exception:  # noqa: BLE001
        logger.debug("Admin email notification skipped.", exc_info=True)

    return JsonResponse(
        {
            "success": True,
            "message": "Thank you! We'll reach out within one working day.",
        }
    )
