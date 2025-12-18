import json
import os
import hashlib
from datetime import datetime
from aapp import app, db
from aapp.models import (
    Manager, Tenant, Technician, Apartment, ApartmentDetail,
    Contract, Invoice, Rule,
    UserRole, RoomType, ApartmentStatus, ContractStatus, PaymentStatus, RuleKey
)

def get_enum(enum_class, value):
    try:
        return enum_class[value]
    except KeyError:
        return None


def seed_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'data', 'data.json')

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Rules
    print("Seeding Rules...")
    for item in data['rules']:
        r = Rule(
            id=item['id'],
            key=get_enum(RuleKey, item['key']),
            value=item['value'],
            name_display=item['name_display'],
            description=item['description']
        )
        db.session.add(r)

    # Users
    print("Seeding Users...")
    for item in data['managers']:
        m = Manager(
            id=item['id'], full_name=item['full_name'], phone_number=item['phone_number'],
            email=item['email'], username=item['username'],
            password=hashlib.md5(item['password'].encode()).hexdigest(),
            user_role=get_enum(UserRole, item['user_role']), active=item['active']
        )
        db.session.add(m)

    for item in data['technicians']:
        t = Technician(
            id=item['id'], full_name=item['full_name'], phone_number=item['phone_number'],
            email=item['email'], username=item['username'],
            password=hashlib.md5(item['password'].encode()).hexdigest(),
            user_role=get_enum(UserRole, item['user_role']), active=item['active']
        )
        db.session.add(t)

    for item in data['tenants']:
        t = Tenant(
            id=item['id'], full_name=item['full_name'], phone_number=item['phone_number'],
            email=item['email'], username=item['username'],
            password=hashlib.md5(item['password'].encode()).hexdigest(),
            dob=datetime.strptime(item['dob'], '%Y-%m-%d'),
            user_role=get_enum(UserRole, item['user_role']), active=item['active']
        )
        db.session.add(t)

    # Apartments
    print("Seeding Apartments...")
    for item in data['apartments']:
        a = Apartment(
            id=item['id'],
            room_type=get_enum(RoomType, item['room_type']),
            status=get_enum(ApartmentStatus, item['status']),
            floor=item['floor'], area=item['area'], price=item['price']
        )
        db.session.add(a)

    # Apartment Details
    print("Seeding Details...")
    for item in data['apartment_details']:
        ad = ApartmentDetail(
            id=item['id'], apartment_id=item['apartment_id'],
            manager_id=item['manager_id'], note=item['note']
        )
        db.session.add(ad)

    # Contracts
    print("Seeding Contracts...")

    occupied_apartments = set()

    for item in data['contracts']:
        status_enum = get_enum(ContractStatus, item['status'])

        if status_enum == ContractStatus.ACTIVE:
            if item['apartment_id'] in occupied_apartments:
                print(
                    f" WARNING: {item['apartment_id']} kiểm tra lại sl hợp đồng active")
                continue
            occupied_apartments.add(item['apartment_id'])

        c = Contract(
            id=item['id'],
            apartment_id=item['apartment_id'],
            tenant_id=item['tenant_id'],
            start_date=datetime.strptime(item['start_date'], '%Y-%m-%d'),
            rental_period=item['rental_period'],
            deposit=item['deposit'],
            rent_price=item['rent_price'],
            member_count=item['member_count'],
            status=status_enum
        )
        db.session.add(c)

    # Invoices
    print("Seeding Invoices...")
    for item in data['invoices']:
        inv = Invoice(
            id=item['id'],
            contract_id=item['contract_id'],
            month=item['month'],
            electric_usage=item['electric_usage'],
            water_usage=item['water_usage'],
            electric_end_reading=item['electric_end_reading'],
            water_end_reading=item['water_end_reading'],
            electric_fee=item['electric_fee'],
            water_fee=item['water_fee'],
            service_fee=item['service_fee'],
            total_amount=item['total_amount'],
            status=get_enum(PaymentStatus, item['status'])
        )
        db.session.add(inv)

    db.session.commit()
    print("DATA IMPORTED SUCCESSFULLY!")


if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_data()