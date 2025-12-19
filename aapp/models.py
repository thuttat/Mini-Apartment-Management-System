import hashlib
from datetime import datetime
from enum import Enum as AppEnum
from dateutil.relativedelta import relativedelta
from sqlalchemy import Column, Integer, String, Boolean, Float, Date, ForeignKey, Enum, Text, DateTime
from sqlalchemy.orm import relationship

from aapp import db
from flask_login import UserMixin


class BaseModel(db.Model):
    __abstract__ = True
    id = Column(String(50), primary_key=True, unique=True, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class RoomType(AppEnum):
    STUDIO = "STUDIO"
    ONE_BEDROOM = "ONE_BEDROOM"
    TWO_BEDROOM = "TWO_BEDROOM"
    DUPLEX = "DUPLEX"
    PENTHOUSE = "PENTHOUSE"


class ApartmentStatus(AppEnum):
    AVAILABLE = "AVAILABLE"
    RENTED = "RENTED"
    MAINTENANCE = "MAINTENANCE"
    LOOKING_FOR_ROOMMATE = "LOOKING_FOR_ROOMMATE"


class ContractStatus(AppEnum):
    PENDING = "PENDING"  # Trạng thái chờ kích hoạt (cho hợp đồng gia hạn)
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class PaymentStatus(AppEnum):
    PAID = "PAID"
    UNPAID = "UNPAID"


class UserRole(AppEnum):
    TENANT = 1
    MANAGER = 2
    TECHNICIAN = 3
    ALL = 4


class RuleKey(AppEnum):
    MAX_PER_ROOM = "MAX_PER_ROOM"
    PRICE_ELECTRIC = "PRICE_ELECTRIC"
    PRICE_WATER = "PRICE_WATER"
    PRICE_SERVICE = "PRICE_SERVICE"
    DEPOSIT_MONTHS = "DEPOSIT_MONTHS"


# ============================
# USERS
# ============================
class User(BaseModel, UserMixin):
    __abstract__ = True
    full_name = Column(String(50), nullable=False)
    phone_number = Column(String(20))
    email = Column(String(50))
    avatar = Column(String(100),
                    default="https://res.cloudinary.com/dt3btnnxy/image/upload/v1763293575/bifgdnpwfsixbur45xun.png")
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    user_role = Column(Enum(UserRole))


class Manager(User):
    def __str__(self):
        return self.full_name


class Tenant(User):
    dob = Column(Date)

    def __str__(self):
        return self.full_name


class Technician(User):
    def __str__(self):
        return self.full_name


# ============================
# APARTMENT
# ============================
class Apartment(BaseModel):
    room_type = Column(Enum(RoomType), nullable=False)
    status = Column(Enum(ApartmentStatus), default=ApartmentStatus.AVAILABLE)
    image_urls = Column(String(500),
                        default="https://res.cloudinary.com/dt3btnnxy/image/upload/v1763293575/bifgdnpwfsixbur45xun.png")
    floor = Column(Float)
    area = Column(Float)
    price = Column(Float)

    def __str__(self):
        return self.id


class ApartmentDetail(BaseModel):
    apartment_id = Column(String(50), ForeignKey("apartment.id"))
    manager_id = Column(String(50), ForeignKey("manager.id"))
    note = Column(String(225))

    apartment = relationship("Apartment", backref="details", lazy=True)
    manager = relationship("Manager", backref="details", lazy=True)

    def __str__(self):
        return f"{self.apartment_id} - {self.manager_id}"


# ============================
# CONTRACT
# ============================
class Contract(BaseModel):
    apartment_id = Column(String(50), ForeignKey("apartment.id"), nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenant.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    rental_period = Column(Integer, nullable=False)
    end_date = Column(Date, nullable=False)
    deposit = Column(Float)
    rent_price = Column(Float)
    member_count = Column(Integer, default=1)
    status = Column(Enum(ContractStatus), default=ContractStatus.ACTIVE)

    apartment = relationship("Apartment", backref="contracts", lazy=True)
    tenant = relationship("Tenant", backref="contracts", lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.start_date and self.rental_period:
            self.end_date = self.start_date + relativedelta(months=self.rental_period)


class ContractAssignment(BaseModel):
    contract_id = Column(String(50), ForeignKey("contract.id"), nullable=False)
    old_tenant_id = Column(String(50), ForeignKey("tenant.id"), nullable=False)
    new_tenant_id = Column(String(50), ForeignKey("tenant.id"), nullable=False)
    effective_date = Column(Date, default=datetime.now)
    note = Column(String(225))

    contract = relationship("Contract", backref="assignments")
    old_tenant = relationship("Tenant", foreign_keys=[old_tenant_id])
    new_tenant = relationship("Tenant", foreign_keys=[new_tenant_id])

    def __str__(self):
        return f"Transfer history of contract {self.contract_id}"


# ============================
# INVOICE
# ============================
class Invoice(BaseModel):
    contract_id = Column(String(50), ForeignKey("contract.id"))
    month = Column(String(20), default=f"{datetime.now().year}-{datetime.now().month}")

    # Chỉ số tiêu thụ
    electric_usage = Column(Float, default=0)
    water_usage = Column(Float, default=0)

    # Chỉ số cuối
    electric_end_reading = Column(Float, default=0)
    water_end_reading = Column(Float, default=0)
    electric_image = Column(String(255))
    water_image = Column(String(255))

    # Thành tiền
    electric_fee = Column(Float, default=0)
    water_fee = Column(Float, default=0)
    service_fee = Column(Float, default=0)

    total_amount = Column(Float, default=0)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID)

    contract = relationship("Contract", backref="invoices", lazy=True)

    @property
    def rent_price(self):
        if self.contract:
            return self.contract.rent_price
        return 0

    @property
    def apartment_id(self):
        if self.contract:
            return self.contract.apartment_id
        return None


# ============================
# RULE
# ============================
class Rule(BaseModel):
    key = Column(Enum(RuleKey), unique=True, nullable=False)
    value = Column(String(50), nullable=False)
    name_display = Column(String(100))
    description = Column(Text)
    last_updated = Column(DateTime, default=datetime.now)

    def __str__(self):
        return f"{self.name_display}: {self.value}"