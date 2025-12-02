import hashlib
from datetime import datetime
from enum import Enum as AppEnum

from sqlalchemy import Column, Integer, String, Boolean, Float, Date, ForeignKey, Enum, Text, Double
from sqlalchemy.ext.baked import bakery
from sqlalchemy.orm import relationship

from aapp import db, app
from flask_login import UserMixin

class BaseModel(db.Model):
    __abstract__ = True
    id = Column(String(50),primary_key=True, unique=True, nullable=False)
    active = Column(Boolean, default=True)


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
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class PaymentStatus(AppEnum):
    PAID = "PAID"
    UNPAID = "UNPAID"

class TargetGroup(AppEnum):
    RESIDENT = "RESIDENT"
    MANAGER = "MANAGER"
    TECHNICIAN = "TECHNICIAN"
    ALL = "ALL"

class UserRole(AppEnum):
    TENANT = 1
    MANAGER = 2
    TECHNICIAN = 3
    ALL = 4


class User(BaseModel,UserMixin):
    __abstract__ = True
    full_name = Column(String(50), nullable=False)
    phone_number=Column(String(20))
    email = Column(String(50))
    avatar = Column(String(100), default="https://res.cloudinary.com/dt3btnnxy/image/upload/v1763293575/bifgdnpwfsixbur45xun.png")
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    user_role = Column(Enum(UserRole))

class Manager(User):

    def __str__(self):
        return self.full_name


class Tenant(User):
    #contracts = relationship("Contract", backref="tenant", lazy=True)
    def __str__(self):
        return self.full_name

class Technician(User):
    def __str__(self):
        return self.full_name

class Apartment(BaseModel):
    room_type = Column(Enum(RoomType), nullable=False)
    status = Column(Enum(ApartmentStatus), default=ApartmentStatus.AVAILABLE)

    image_urls = Column(String(500),
                       default="https://res.cloudinary.com/demo/image/upload/default_apartment.jpg")

    floor = Column(Integer)
    area = Column(Float)
    price = Column(Float)

    # contracts = relationship("Contract", backref="apartment", lazy=True)

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


class Contract(BaseModel):

    apartment_id = Column(String(50), ForeignKey("apartment.id"))
    tenant_id = Column(String(50), ForeignKey("tenant.id"))

    start_date = Column(Date)
    end_date = Column(Date)
    deposit = Column(Float)
    rent_price = Column(Float)
    status = Column(Enum(ContractStatus), default=ContractStatus.ACTIVE)


    apartment = relationship("Apartment", backref="contracts", lazy=True)
    tenant = relationship("Tenant", backref="contracts", lazy=True)

class Invoice(BaseModel):
    contract_id = Column(String(50), ForeignKey("contract.id"))

    month = Column(String(20))
    electric_fee = Column(Float, default=0)
    water_fee = Column(Float, default=0)
    service_fee = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID)

    contract = relationship("Contract", backref="invoices", lazy=True)

class Rule(BaseModel):
    rule_name = Column(String(100), nullable=False)
    value = Column(String(50), nullable=False)
    description = Column(Text)
    last_updated = Column(Date, default=datetime.utcnow)


if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Manager
        m1 = Manager(
            id="M001",
            full_name="Quản lý hệ thống",
            phone_number="0909123456",
            email="admin@system.com",
            user_role=UserRole.MANAGER,
            username="admin",
            password=hashlib.md5("123456".encode()).hexdigest(),
            active=True
        )

        # Tenants
        t1 = Tenant(
            id="T101",
            full_name="Nguyễn Văn An",
            phone_number="0908000111",
            email="annguyen@gmail.com",
            user_role=UserRole.TENANT,
            username="an123",
            password=hashlib.md5("123456".encode()).hexdigest(),
            active=True
        )

        t2 = Tenant(
            id="T102",
            full_name="Trần Thị Bình",
            phone_number="0908222333",
            email="binhtran@mail.com",
            user_role=UserRole.TENANT,
            username="binhtran",
            password=hashlib.md5("654321".encode()).hexdigest(),
            active=True
        )

        t3 = Tenant(
            id="T103",
            full_name="Lê Hoàng Minh",
            phone_number="0933444555",
            email="minhle@gmail.com",
            user_role=UserRole.TENANT,
            username="minhle",
            password=hashlib.md5("abcdef".encode()).hexdigest(),
            active=True
        )

        # Apartments
        a1 = Apartment(
            id="A101",
            room_type=RoomType.ONE_BEDROOM,
            status=ApartmentStatus.AVAILABLE,
            floor=1, area=40, price=4500000,
            active=True
        )

        a2 = Apartment(
            id="A102",
            room_type=RoomType.STUDIO,
            status=ApartmentStatus.AVAILABLE,
            floor=1, area=30, price=3500000,
            active=True
        )

        a3 = Apartment(
            id="A201",
            room_type=RoomType.TWO_BEDROOM,
            status=ApartmentStatus.RENTED,
            floor=2, area=55, price=6000000,
            active=True
        )

        a4 = Apartment(
            id="A202",
            room_type=RoomType.DUPLEX,
            status=ApartmentStatus.MAINTENANCE,
            floor=2, area=75, price=9000000,
            active=True
        )

        a5 = Apartment(
            id="A301",
            room_type=RoomType.PENTHOUSE,
            status=ApartmentStatus.LOOKING_FOR_ROOMMATE,
            floor=3, area=95, price=15000000,
            active=True
        )

        # Apartment Details
        ad1 = ApartmentDetail(id="AD001", apartment_id="A101", manager_id="M001", note="Main manager")
        ad2 = ApartmentDetail(id="AD002", apartment_id="A102", manager_id="M001", note="Backup manager")

        # Contracts
        c1 = Contract(
            id="C001",
            apartment_id="A102",
            tenant_id="T101",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 1),
            deposit=5000000,
            rent_price=3500000,
            status=ContractStatus.ACTIVE
        )

        c2 = Contract(
            id="C002",
            apartment_id="A201",
            tenant_id="T102",
            start_date=datetime(2024, 3, 1),
            end_date=datetime(2025, 3, 1),
            deposit=6000000,
            rent_price=6500000,
            status=ContractStatus.ACTIVE
        )

        c3 = Contract(
            id="C003",
            apartment_id="A201",
            tenant_id="T103",
            start_date=datetime(2024, 5, 1),
            end_date=datetime(2025, 5, 1),
            deposit=6000000,
            rent_price=6500000,
            status=ContractStatus.ACTIVE
        )

        # Invoices
        inv = [
            Invoice(id="I001", contract_id="C001", month="2024-01", electric_fee=300000, water_fee=80000,
                    service_fee=150000, total_amount=4730000),
            Invoice(id="I002", contract_id="C001", month="2024-02", electric_fee=250000, water_fee=75000,
                    service_fee=150000, total_amount=4725000),
            Invoice(id="I003", contract_id="C002", month="2024-03", electric_fee=320000, water_fee=90000,
                    service_fee=200000, total_amount=7110000),
            Invoice(id="I004", contract_id="C002", month="2024-04", electric_fee=310000, water_fee=80000,
                    service_fee=200000, total_amount=7080000),
            Invoice(id="I005", contract_id="C003", month="2024-05", electric_fee=280000, water_fee=85000,
                    service_fee=200000, total_amount=7065000),
            Invoice(id="I006", contract_id="C003", month="2024-06", electric_fee=270000, water_fee=82000,
                    service_fee=200000, total_amount=7052000),
        ]

        # Rules
        r1 = Rule(id="R001", rule_name="MAX_TENANTS", value="4", description="Tối đa 4 người ở một căn hộ.")
        r2 = Rule(id="R002", rule_name="MIN_RENT_MONTHS", value="6", description="Hợp đồng tối thiểu 6 tháng.")
        r3 = Rule(id="R003", rule_name="LATE_FEE", value="150000", description="Phí phạt trễ hạn đóng tiền.")

        db.session.add_all([m1, t1, t2, t3, a1, a2, a3, a4, a5, ad1, ad2, c1, c2, c3, *inv, r1, r2, r3])
        db.session.commit()




