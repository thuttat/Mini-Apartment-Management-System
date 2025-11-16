import hashlib
from datetime import datetime
from enum import Enum as AppEnum

from sqlalchemy import Column, Integer, String, Boolean, Float, Date, ForeignKey, Enum, Text, Double
from sqlalchemy.orm import relationship

from aapp import db, app
from flask_login import UserMixin

class BaseModel(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
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
    TENANT =1
    MANAGER =2
    TECHNICIAN =3
    ALL = 4



class Manager(BaseModel,UserMixin):


    manager_id = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(50), nullable=False)
    phone_number = Column(String(20))
    email = Column(String(50))
    avatar = Column(String(100), default="https://res.cloudinary.com/demo/image/upload/default_avatar.jpg")
    user_role = Column(Enum(UserRole), default=UserRole.MANAGER)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)


    def __str__(self):
        return self.full_name


class Tenant(BaseModel,UserMixin):
    tenant_id = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(50), nullable=False)
    phone_number = Column(String(20))
    email = Column(String(50))
    avatar = Column(String(100), default="https://res.cloudinary.com/demo/image/upload/default_avatar.jpg")
    user_role = Column(Enum(UserRole), default=UserRole.TENANT)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)



    contracts = relationship("Contract", backref="tenant", lazy=True)



class Apartment(BaseModel):
    apartment_id = Column(String(50), unique=True, nullable=False)
    room_type = Column(Enum(RoomType), nullable=False)
    status = Column(Enum(ApartmentStatus), default=ApartmentStatus.AVAILABLE)

    image_urls = Column(String(500),
                       default="https://res.cloudinary.com/demo/image/upload/default_apartment.jpg")

    floor = Column(Integer)
    area = Column(Float)
    price = Column(Float)


    contracts = relationship("Contract", backref="apartment", lazy=True)

    def __str__(self):
        return self.apartment_id


class Contract(BaseModel):
    contract_id = Column(String(50), unique=True, nullable=False)

    apartment_id = Column(String(50), ForeignKey("apartment.apartment_id"))
    tenant_id = Column(String(50), ForeignKey("tenant.tenant_id"))

    start_date = Column(Date)
    end_date = Column(Date)
    deposit = Column(Float)
    rent_price = Column(Float)
    status = Column(Enum(ContractStatus), default=ContractStatus.ACTIVE)


    invoices = relationship("Invoice", backref="contract", lazy=True)

class Invoice(BaseModel):
    invoice_id = Column(String(50), unique=True, nullable=False)
    contract_id = Column(String(50), ForeignKey("contract.contract_id"))

    month = Column(String(20))
    electric_fee = Column(Float, default=0)
    water_fee = Column(Float, default=0)
    service_fee = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID)

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
            manager_id="M001",
            full_name="Quản lý hệ thống",
            phone_number="0909123456",
            email="admin@system.com",
            avatar="https://res.cloudinary.com/demo/image/upload/default_avatar.jpg",
            user_role=UserRole.MANAGER,

            username="admin",
            password=hashlib.md5("123456".encode()).hexdigest()
        )

        # Tenants
        t1 = Tenant(
            tenant_id="T101",
            full_name="Nguyễn Văn An",
            phone_number="0908000111",
            email="annguyen@gmail.com",
            avatar="https://res.cloudinary.com/demo/image/upload/default_avatar.jpg",
            user_role=UserRole.TENANT,

            username="an123",
            password=hashlib.md5("123456".encode()).hexdigest()
        )

        t2 = Tenant(
            tenant_id="T102",
            full_name="Trần Thị Bình",
            phone_number="0908222333",
            email="binhtran@mail.com",
            avatar="https://res.cloudinary.com/demo/image/upload/default_avatar.jpg",
            user_role=UserRole.TENANT,

            username="binhtran",
            password=hashlib.md5("654321".encode()).hexdigest()
        )

        t3 = Tenant(
            tenant_id="T103",
            full_name="Lê Hoàng Minh",
            phone_number="0933444555",
            email="minhle@gmail.com",
            avatar="https://res.cloudinary.com/demo/image/upload/default_avatar.jpg",
            user_role=UserRole.TENANT,

            username="minhle",
            password=hashlib.md5("abcdef".encode()).hexdigest()
        )

        # Apartments
        a1 = Apartment(
            apartment_id="A101",
            room_type=RoomType.ONE_BEDROOM,
            status=ApartmentStatus.AVAILABLE,
            image_urls="https://res.cloudinary.com/demo/image/upload/a1.jpg",
            floor=1, area=40, price=4500000
        )

        a2 = Apartment(
            apartment_id="A102",
            room_type=RoomType.STUDIO,
            status=ApartmentStatus.AVAILABLE,
            image_urls="https://res.cloudinary.com/demo/image/upload/a2.jpg",
            floor=1, area=30, price=3500000
        )

        a3 = Apartment(
            apartment_id="A201",
            room_type=RoomType.TWO_BEDROOM,
            status=ApartmentStatus.RENTED,
            image_urls="https://res.cloudinary.com/demo/image/upload/a3.jpg",
            floor=2, area=55, price=6000000
        )

        a4 = Apartment(
            apartment_id="A202",
            room_type=RoomType.DUPLEX,
            status=ApartmentStatus.MAINTENANCE,
            image_urls="https://res.cloudinary.com/demo/image/upload/a4.jpg",
            floor=2, area=75, price=9000000
        )

        a5 = Apartment(
            apartment_id="A301",
            room_type=RoomType.PENTHOUSE,
            status=ApartmentStatus.LOOKING_FOR_ROOMMATE,
            image_urls="https://res.cloudinary.com/demo/image/upload/a5.jpg",
            floor=3, area=95, price=15000000
        )

        # Contracts
        c1 = Contract(
            contract_id="C001",
            apartment_id="A102",
            tenant_id="T101",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 1),
            deposit=5000000,
            rent_price=3500000,
            status=ContractStatus.ACTIVE
        )

        c2 = Contract(
            contract_id="C002",
            apartment_id="A201",
            tenant_id="T102",
            start_date=datetime(2024, 3, 1),
            end_date=datetime(2025, 3, 1),
            deposit=6000000,
            rent_price=6500000,
            status=ContractStatus.ACTIVE
        )

        c3 = Contract(
            contract_id="C003",
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
            Invoice(invoice_id="I001", contract_id="C001", month="2024-01",
                    electric_fee=300000, water_fee=80000, service_fee=150000, total_amount=4730000),
            Invoice(invoice_id="I002", contract_id="C001", month="2024-02",
                    electric_fee=250000, water_fee=75000, service_fee=150000, total_amount=4725000),
            Invoice(invoice_id="I003", contract_id="C002", month="2024-03",
                    electric_fee=320000, water_fee=90000, service_fee=200000, total_amount=7110000),
            Invoice(invoice_id="I004", contract_id="C002", month="2024-04",
                    electric_fee=310000, water_fee=80000, service_fee=200000, total_amount=7080000),
            Invoice(invoice_id="I005", contract_id="C003", month="2024-05",
                    electric_fee=280000, water_fee=85000, service_fee=200000, total_amount=7065000),
            Invoice(invoice_id="I006", contract_id="C003", month="2024-06",
                    electric_fee=270000, water_fee=82000, service_fee=200000, total_amount=7052000),
        ]

        # Rules
        r1 = Rule(rule_name="MAX_TENANTS", value="4", description="Tối đa 4 người ở một căn hộ.")
        r2 = Rule(rule_name="MIN_RENT_MONTHS", value="6", description="Hợp đồng tối thiểu 6 tháng.")
        r3 = Rule(rule_name="LATE_FEE", value="150000", description="Phí phạt trễ hạn đóng tiền.")

        db.session.add_all([m1, t1, t2, t3, a1, a2, a3, a4, a5, c1, c2, c3] + inv + [r1, r2, r3])
        db.session.commit()



