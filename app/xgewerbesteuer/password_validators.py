"""Eigene Passwort-Validatoren fuer Komplexitaet und Benutzerbezug."""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

SPECIAL_CHARACTERS = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
MIN_USER_INFO_FRAGMENT_LENGTH = 3


class UppercaseValidator:
    """Verlangt mindestens einen Grossbuchstaben."""

    def validate(self, password, user=None):
        if not re.search(r"[A-ZÄÖÜ]", password):
            raise ValidationError(
                _("Das Passwort muss mindestens einen Großbuchstaben enthalten."),
                code="password_no_upper",
            )

    def get_help_text(self):
        return _("Das Passwort muss mindestens einen Großbuchstaben enthalten.")


class LowercaseValidator:
    """Verlangt mindestens einen Kleinbuchstaben."""

    def validate(self, password, user=None):
        if not re.search(r"[a-zäöü]", password):
            raise ValidationError(
                _("Das Passwort muss mindestens einen Kleinbuchstaben enthalten."),
                code="password_no_lower",
            )

    def get_help_text(self):
        return _("Das Passwort muss mindestens einen Kleinbuchstaben enthalten.")


class DigitValidator:
    """Verlangt mindestens eine Ziffer."""

    def validate(self, password, user=None):
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                _("Das Passwort muss mindestens eine Zahl enthalten."),
                code="password_no_digit",
            )

    def get_help_text(self):
        return _("Das Passwort muss mindestens eine Zahl enthalten.")


class SpecialCharacterValidator:
    """Verlangt mindestens ein Sonderzeichen."""

    def validate(self, password, user=None):
        if not any(character in SPECIAL_CHARACTERS for character in password):
            raise ValidationError(
                _("Das Passwort muss mindestens ein Sonderzeichen enthalten."),
                code="password_no_special_character",
            )

    def get_help_text(self):
        return _("Das Passwort muss mindestens ein Sonderzeichen enthalten.")


class NoUserInfoFragmentValidator:
    """Verhindert, dass das Passwort Teile des Benutzernamens oder der E-Mail enthaelt."""

    def validate(self, password, user=None):
        if user is None:
            return

        password_lower = password.lower()
        fragments = set()
        fragments.update(self._split_into_fragments(getattr(user, "username", "") or ""))

        email = getattr(user, "email", "") or ""
        fragments.update(self._split_into_fragments(email))
        fragments.update(self._split_into_fragments(email.split("@", 1)[0]))

        for fragment in fragments:
            if fragment in password_lower:
                raise ValidationError(
                    _(
                        "Das Passwort darf keinen Teil des Benutzernamens oder "
                        "der E-Mail-Adresse enthalten."
                    ),
                    code="password_contains_user_info",
                )

    def _split_into_fragments(self, value):
        fragments = re.split(r"[^a-zäöü0-9]+", value.lower())
        return [fragment for fragment in fragments if len(fragment) >= MIN_USER_INFO_FRAGMENT_LENGTH]

    def get_help_text(self):
        return _(
            "Das Passwort darf keinen Teil des Benutzernamens oder der "
            "E-Mail-Adresse enthalten."
        )
