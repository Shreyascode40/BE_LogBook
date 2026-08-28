from __future__ import annotations

from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class Role(models.TextChoices):
    HOD = "HOD", _("HOD")
    FACULTY = "FACULTY", _("Faculty")
    STUDENT = "STUDENT", _("Student")


class User(AbstractUser):
    """Custom user model for BE Logbook. Email is the login identifier."""

    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name=_("System role"),
        help_text=_("HOD, Faculty or Student. Reviewer access is assignment-based."),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def __str__(self) -> str:
        return self.email

    def get_absolute_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.id})

    @property
    def is_hod(self) -> bool:
        return self.role == Role.HOD

    @property
    def is_faculty(self) -> bool:
        return self.role == Role.FACULTY

    @property
    def is_student(self) -> bool:
        return self.role == Role.STUDENT


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.PROTECT, related_name="student_profile"
    )
    roll_number = models.CharField(max_length=30, unique=True)
    department = models.ForeignKey(
        "academics.Department", on_delete=models.PROTECT, related_name="students"
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.PROTECT,
        related_name="students",
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=20, blank=True)
    te_result = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Third-year (TE) examination result / percentage."),
    )
    exam_seat_number = models.CharField(
        max_length=30,
        blank=True,
        help_text=_("University examination seat number."),
    )
    photo = models.ImageField(
        upload_to="student_photos/",
        null=True,
        blank=True,
        help_text=_("Passport-style photograph used in the log book."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Student Profile")
        verbose_name_plural = _("Student Profiles")

    def __str__(self) -> str:
        return f"{self.user.name or self.user.email} ({self.roll_number})"


class FacultyProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.PROTECT, related_name="faculty_profile"
    )
    employee_id = models.CharField(max_length=30, unique=True)
    designation = models.CharField(max_length=100, blank=True)
    department = models.ForeignKey(
        "academics.Department",
        on_delete=models.PROTECT,
        related_name="faculty",
    )
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Faculty Profile")
        verbose_name_plural = _("Faculty Profiles")

    def __str__(self) -> str:
        return f"{self.user.name or self.user.email} ({self.employee_id})"
