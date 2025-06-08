from dataclasses import dataclass

from .roles import Role

@dataclass
class PermissionMatrix:
    create = {
        'user': [Role.ADMIN, Role.RECEPTION, Role.PHARMACIST, Role.DOCTOR],
        'patient': [Role.ADMIN, Role.RECEPTION, Role.PHARMACIST, Role.DOCTOR],
        'drugstore': [Role.ADMIN, Role.RECEPTION, Role.PHARMACIST, Role.DOCTOR],
        'consultation': [Role.ADMIN, Role.DOCTOR],
        'appointment': [Role.SOCIAL_WORKER]
    }

    navbar = {
        'user': [Role.ADMIN],
        'patient': [Role.ADMIN, Role.RECEPTION, Role.SOCIAL_WORKER, Role.DOCTOR],
        'drugstore': [Role.ADMIN, Role.PHARMACIST]
    }


def can_create(user, table):
    allowed = PermissionMatrix.create.get(table, [])
    return user is not None and user.role in allowed


def can_view_nav(user, item):
    allowed = PermissionMatrix.navbar.get(item, [])
    return user is not None and user.role in allowed
