import hashlib
from datetime import datetime
from enum import Enum as AppEnum
from dateutil.relativedelta import relativedelta
from sqlalchemy import Column, Integer, String, Boolean, Float, Date, ForeignKey, Enum, Text, DateTime
from sqlalchemy.orm import relationship

from aapp import db, app
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
    dob = Column(Date)  # Bổ sung ngày sinh

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
        # Tự động tính ngày kết thúc dựa trên Start Date + Rental Period
        if self.start_date and self.rental_period:
            self.end_date = self.start_date + relativedelta(months=self.rental_period)


# bang de luu lich su chuyen nhuong contract
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


# =================================================================
# SEED DATA
# =================================================================
if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Manager
        m1 = Manager(
            id="M001", full_name="Quản lý hệ thống", phone_number="0909123456",
            email="admin@system.com", user_role=UserRole.MANAGER,
            username="admin", password=hashlib.md5("123456".encode()).hexdigest(), active=True
        )

        # Technician
        te1 = Technician(
            id="TE001", full_name="Nhân viên kỹ thuật", phone_number="097267921",
            email="technician@system.com", user_role=UserRole.TECHNICIAN,
            username="technician", password=hashlib.md5("123456".encode()).hexdigest(), active=True
        )

        # Tenants
        t1 = Tenant(id="T101", full_name="Nguyễn Văn An", phone_number="0908000111", email="an123@gmail.com",
                    user_role=UserRole.TENANT, username="an123",
                    password=hashlib.md5("123456".encode()).hexdigest(), dob=datetime(1997, 11, 15), active=True)
        t2 = Tenant(id="T102", full_name="Trần Thị Bình", phone_number="0908222333", email="binh@mail.com",
                    user_role=UserRole.TENANT, username="binhtran",
                    password=hashlib.md5("654321".encode()).hexdigest(), dob=datetime(1990, 8, 9), active=True)
        t3 = Tenant(id="T103", full_name="Lê Hoàng Minh", phone_number="0933444555", email="minh@gmail.com",
                    user_role=UserRole.TENANT, username="minhle",
                    password=hashlib.md5("abcdef".encode()).hexdigest(), dob=datetime(2000, 7, 29), active=True)

        # Apartments
        a1 = Apartment(id="A101", room_type=RoomType.ONE_BEDROOM, status=ApartmentStatus.AVAILABLE, floor=1, area=40,
                       price=4500000)
        a2 = Apartment(id="A102", room_type=RoomType.STUDIO, status=ApartmentStatus.AVAILABLE, floor=1, area=30,
                       price=3500000)
        a3 = Apartment(id="A201", room_type=RoomType.TWO_BEDROOM, status=ApartmentStatus.RENTED, floor=2, area=55,
                       price=6000000)
        a4 = Apartment(id="A202", room_type=RoomType.DUPLEX, status=ApartmentStatus.MAINTENANCE, floor=2, area=75,
                       price=9000000)
        a5 = Apartment(id="A301", room_type=RoomType.PENTHOUSE, status=ApartmentStatus.LOOKING_FOR_ROOMMATE, floor=3,
                       area=95, price=15000000)

        # Details
        ad1 = ApartmentDetail(id="AD001", apartment_id="A101", manager_id="M001", note="Main manager")
        ad2 = ApartmentDetail(id="AD002", apartment_id="A102", manager_id="M001", note="Backup manager")

        # Contracts
        c1 = Contract(id="C001", apartment_id="A102", tenant_id="T101", start_date=datetime(2024, 2, 29),
                      deposit=5000000, rent_price=3500000, member_count=1,
                      status=ContractStatus.ACTIVE, rental_period=12)

        c2 = Contract(id="C002", apartment_id="A201", tenant_id="T102", start_date=datetime(2024, 3, 1),
                      deposit=6000000, rent_price=6500000, member_count=2,
                      status=ContractStatus.ACTIVE, rental_period=24)

        c3 = Contract(id="C003", apartment_id="A301", tenant_id="T103", start_date=datetime(2024, 5, 1),
                      deposit=6000000, rent_price=6500000, member_count=1,
                      status=ContractStatus.ACTIVE, rental_period=12)

        # Rules
        rules_list = [
            Rule(id="R1", key=RuleKey.MAX_PER_ROOM, value="4", name_display="Số người tối đa",
                 description="Số người tối đa trong 1 phòng"),
            Rule(id="R2", key=RuleKey.PRICE_ELECTRIC, value="3500", name_display="Giá điện",
                 description="Đơn giá VND/kwh"),
            Rule(id="R3", key=RuleKey.PRICE_WATER, value="20000", name_display="Giá nước",
                 description="Đơn giá VND/m3"),
            Rule(id="R4", key=RuleKey.DEPOSIT_MONTHS, value="1", name_display="Số tháng cọc",
                 description="Số tháng tiền cọc bắt buộc"),
            Rule(id="R5", key=RuleKey.PRICE_SERVICE, value="150000", name_display="Phí dịch vụ",
                 description="Phí quản lý hàng tháng"),
        ]

        # Invoices
        inv = [
            Invoice(id="I001", contract_id="C001", month="2024-01",
                    electric_usage=85.7, water_usage=4,
                    electric_fee=300000, water_fee=80000, service_fee=150000, total_amount=4730000,
                    status=PaymentStatus.PAID),
            Invoice(id="I002", contract_id="C001", month="2024-02",
                    electric_usage=71.4, water_usage=3.75,
                    electric_fee=250000, water_fee=75000, service_fee=150000, total_amount=4725000),
            Invoice(id="I003", contract_id="C002", month="2024-03",
                    electric_usage=91.4, water_usage=4.5,
                    electric_fee=320000, water_fee=90000, service_fee=200000, total_amount=7110000),
            Invoice(id="I004", contract_id="C002", month="2024-04",
                    electric_usage=88.5, water_usage=4,
                    electric_fee=310000, water_fee=80000, service_fee=200000, total_amount=7080000),
        ]

        db.session.add_all([
            m1, te1,
            t1, t2, t3,
            a1, a2, a3, a4, a5,
            ad1, ad2,
            c1, c2, c3,
            *inv,
            *rules_list
        ])
        db.session.commit()