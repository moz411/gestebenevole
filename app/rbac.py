from dataclasses import dataclass

from .roles import Role

@dataclass
class PermissionMatrix:
    create = {
        'user': [Role.ADMIN],
        'patient': [Role.RECEPTION, Role.DOCTOR],
        'drugstore': [Role.PHARMACIST],
        'consultation': [Role.DOCTOR],
        'appointment': [Role.SOCIAL_WORKER]
    }

    read = {
        'user': [Role.ADMIN],
        'patient': [Role.ADMIN, Role.RECEPTION, Role.SOCIAL_WORKER, Role.DOCTOR, Role.PHARMACIST],
        'drugstore': [Role.PHARMACIST],
        'consultation': [Role.DOCTOR],
        'appointment': [Role.SOCIAL_WORKER]
    }

def can_create(user, table):
    allowed = PermissionMatrix.create.get(table, [])
    return user is not None and user.role in allowed

def can_read(user, table):
    allowed = PermissionMatrix.read.get(table, [])
    return user is not None and user.role in allowed

def can_write(user, table):
    return can_create(user, table)

