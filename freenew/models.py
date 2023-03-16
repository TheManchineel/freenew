from pydantic import BaseModel
from enum import Enum


class RenewError(Exception):
    pass


class LoginError(Exception):
    pass


class Status(str, Enum):
    ACTIVE = "Active"
    CANCELLED = "Cancelled"
    SUSPENDED = "Suspended"


class Domain(BaseModel):
    domain_name: str
    status: Status
    days_until_expiry: int
    renewable: bool = False
    domain_id: str


class Account(BaseModel):
    username: str
    password: str
    excluded_domains: list[str]
