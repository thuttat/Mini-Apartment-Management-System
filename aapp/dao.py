import hashlib
from datetime import datetime, timedelta, date
from sqlalchemy import func
import cloudinary.uploader
from dateutil.relativedelta import relativedelta

from aapp import db, app
from aapp.models import (Manager, Tenant, Technician, Apartment, Contract, Invoice,
                         Rule, UserRole, RuleKey, ContractStatus, ApartmentStatus, PaymentStatus, ContractAssignment)
from .utils import get_next_id, hash_password


# ============================
# AUTH & USER
# ============================
def auth_user(username, password):
    hashed = hash_password(password)

    auth_sources = [
        (Manager, UserRole.MANAGER),
        (Tenant, UserRole.TENANT),
        (Technician, UserRole.TECHNICIAN)
    ]

    for Model, role in auth_sources:
        user = Model.query.filter_by(username=username.strip(), password=hashed).first()
        if user:
            if hasattr(user, 'active') and not user.active:
                return None, None
            return user, role
    return None, None


def get_user_by_id(id):
    user = Manager.query.get(id)
    if user: return user
    user = Tenant.query.get(id)
    if user: return user
    user = Technician.query.get(id)
    if user: return user
    return None


# ============================
# USER CREATION
# ============================
def add_manager(name, username, password, avatar=None):
    new_id = get_next_id(Manager, "M", 3)
    user = Manager(
        id=new_id, full_name=name, username=username.strip(),
        password=hash_password(password), user_role=UserRole.MANAGER, active=True
    )
    if avatar:
        res = cloudinary.uploader.upload(avatar)
        user.avatar = res.get('secure_url')
    db.session.add(user)
    db.session.commit()
    return user


def add_technician(name, username, password, avatar=None):
    new_id = get_next_id(Technician, "TECH", 3)
    user = Technician(
        id=new_id, full_name=name, username=username.strip(),
        password=hash_password(password), user_role=UserRole.TECHNICIAN, active=True
    )
    if avatar:
        res = cloudinary.uploader.upload(avatar)
        user.avatar = res.get('secure_url')
    db.session.add(user)
    db.session.commit()
    return user


def add_tenant(name, username, password, avatar=None):
    new_id = get_next_id(Tenant, "T", 3)
    tenant = Tenant(
        id=new_id, full_name=name, username=username.strip(),
        password=hash_password(password), user_role=UserRole.TENANT, active=True
    )
    if avatar:
        res = cloudinary.uploader.upload(avatar)
        tenant.avatar = res.get('secure_url')
    db.session.add(tenant)
    db.session.commit()
    return tenant


# ============================
# APARTMENT
# ============================
def _build_query(room_type=None, status=None, from_price=None, to_price=None, keyword=None):
    query = Apartment.query
    if room_type:
        query = query.filter(Apartment.room_type == room_type)
    if status:
        if isinstance(status, list):
            query = query.filter(Apartment.status.in_(status))
        else:
            query = query.filter(Apartment.status == status)
    if from_price:
        query = query.filter(Apartment.price.__ge__(float(from_price)))
    if to_price:
        query = query.filter(Apartment.price.__le__(float(to_price)))
    if keyword:
        query = query.filter(Apartment.id.contains(keyword))
    return query


def load_apartments(room_type=None, status=None, from_price=None, to_price=None, keyword=None, page=1):
    query = _build_query(room_type, status, from_price, to_price, keyword)
    query = query.order_by(Apartment.id.desc())
    if page is not None:
        start = (page - 1) * app.config["PAGE_SIZE"]
        query = query.slice(start, start + app.config["PAGE_SIZE"])
    return query.all()


def count_for_pagination(room_type=None, status=None, from_price=None, to_price=None, keyword=None):
    query = _build_query(room_type, status, from_price, to_price, keyword)
    return query.count()


def get_apartment_by_id(apartment_id):
    return Apartment.query.filter(Apartment.id == apartment_id).first()


def count_apartments():
    stats = db.session.query(Apartment.status, func.count(Apartment.id).label('count')).group_by(
        Apartment.status).all()
    status_map = {
        ApartmentStatus.AVAILABLE: "Blank",
        ApartmentStatus.RENTED: "Rented",
        ApartmentStatus.MAINTENANCE: "Maintaince",
        ApartmentStatus.LOOKING_FOR_ROOMMATE: "Looking for roommate"
    }
    stats_data = []
    for s in stats:
        display_name = status_map.get(s.status, s.status.value if s.status else "Invalid")
        stats_data.append({'name': display_name, 'count': s.count})
    return stats_data


# ============================
# CONTRACT
# ============================
def load_contracts(tenant_id=None, apartment_id=None, status=None):
    query = Contract.query
    if tenant_id: query = query.filter(Contract.tenant_id == tenant_id)
    if apartment_id: query = query.filter(Contract.apartment_id == apartment_id)
    if status: query = query.filter(Contract.status == status)
    return query.all()


def calculate_end_date(start_date, rental_period):
    return start_date + relativedelta(months=rental_period)


def get_contract_by_id(cid):
    return Contract.query.filter(Contract.id == cid).first()


def get_contract_expiration(day_limit=30):
    current_date = datetime.now().date()
    expiration_date = current_date + timedelta(days=day_limit)
    contract = Contract.query.filter(
        Contract.status == ContractStatus.ACTIVE,
        Contract.end_date >= current_date,
        Contract.end_date <= expiration_date
    )
    return contract.order_by(Contract.end_date.asc()).all()


def add_contract(tenant_id, apartment_id, start_date, rental_period, deposit, rent_price, member_count=1):
    end_date = calculate_end_date(start_date, rental_period)
    new_id = get_next_id(Contract, "C", 3)

    contract = Contract(
        id=new_id,
        tenant_id=tenant_id,
        apartment_id=apartment_id,
        start_date=start_date,
        rental_period=rental_period,
        end_date=end_date,
        deposit=deposit,
        rent_price=rent_price,
        status=ContractStatus.ACTIVE,
        member_count=member_count
    )
    db.session.add(contract)

    apt = Apartment.query.get(apartment_id)
    if apt:
        apt.status = ApartmentStatus.RENTED

    db.session.commit()

    # có hợp đồng => invoice đầu
    create_first_invoice(contract)

    return contract


def handle_assign_contract(contract_id, new_tenant_id, effective_date=None, note=None):
    id = get_next_id(ContractAssignment, "CA", "3"),
    contract = get_contract_by_id(contract_id)

    if contract.status != ContractStatus.ACTIVE and contract.status != ContractStatus.PENDING:
        raise ValueError("Only active and pending contract allowed!")

    # Check ngày hết hạn
    if contract.end_date - effective_date < timedelta(days=30):
        raise ValueError("You can only transfer the contract at least 30 days before the contract expires!")

    # Check nợ
    for inv in contract.invoices:
        if inv.status == PaymentStatus.UNPAID:
            raise Exception("Can't assign contract while there are outstanding invoices!")

    old_tenant_id = contract.tenant_id
    if old_tenant_id == new_tenant_id:
        raise ValueError("Can't assign contract to same tenant!")

    contract_assignment = ContractAssignment(
        id=id,
        contract_id=contract.id,
        old_tenant_id=old_tenant_id,
        new_tenant_id=new_tenant_id,
        effective_date=effective_date if effective_date else datetime.now(),
        note=note
    )
    contract.tenant_id = new_tenant_id  # Đổi người thuê

    db.session.add(contract_assignment)
    db.session.commit()
    return contract_assignment


def renew_contract(old_contract_id, rental_period):
    old_contract = Contract.query.get(old_contract_id)
    if not old_contract or old_contract.status != ContractStatus.ACTIVE:
        raise ValueError("Only active contract allowed!")

    if date.today() + timedelta(days=30) > old_contract.end_date:
        raise ValueError("You can only renew the contract at least 30 days before the contract expires!")

    new_contract = Contract(
        id=get_next_id(Contract, "C", "3"),
        apartment_id=old_contract.apartment_id,
        tenant_id=old_contract.tenant_id,
        start_date=old_contract.end_date + timedelta(days=1),
        rental_period=rental_period,
        member_count=old_contract.member_count,
        deposit=old_contract.deposit,
        rent_price=old_contract.rent_price,
        status=ContractStatus.PENDING,
    )
    new_contract.end_date = calculate_end_date(new_contract.start_date, new_contract.rental_period)
    db.session.add(new_contract)
    db.session.commit()
    return new_contract


# Tự động cập nhật trạng thái hợp đồng
def auto_update_contract_status():
    with app.app_context():
        # Pending -> Active
        pending_contracts = Contract.query.filter(Contract.status == ContractStatus.PENDING,
                                                  Contract.start_date <= date.today()).all()
        for contract in pending_contracts:
            contract.status = ContractStatus.ACTIVE
            contract.apartment.status = ApartmentStatus.RENTED

        # Active -> Expired
        expired_contracts = Contract.query.filter(Contract.status == ContractStatus.ACTIVE,
                                                  Contract.end_date < date.today()).all()
        for contract in expired_contracts:
            contract.status = ContractStatus.EXPIRED
            contract.apartment.status = ApartmentStatus.AVAILABLE

        db.session.commit()


# ============================
# INVOICE
# ============================
def build_invoice_query(contract_id=None, month=None, status=None):
    query = Invoice.query
    if contract_id: query = query.filter(Invoice.contract_id == contract_id)
    if month: query = query.filter(Invoice.month == month)
    if status: query = query.filter(Invoice.status == status)
    return query

def load_invoices(contract_id=None, month=None, status=None, page=1):
    query = build_invoice_query(contract_id, month, status)
    query = query.order_by(Invoice.month.desc())

    if page is not None:
        page_size = app.config["PAGE_SIZE"]
        start = (page - 1) * page_size
        query = query.slice(start, start + page_size)

    return query.all()

def count_invoices(contract_id=None, month=None, status=None):
    query = build_invoice_query(contract_id, month, status)
    return query.count()

def calculate_unpaid_invoices(contract_id=None):
    query = build_invoice_query(contract_id, status=PaymentStatus.UNPAID).all()
    total_unpaid = 0
    for invoice in query:
        total_unpaid += invoice.total_amount
    return total_unpaid

def get_invoice_by_id(iid):
    return Invoice.query.filter(Invoice.id == iid).first()


def get_invoice(contract_id, month_str):
    return Invoice.query.filter(Invoice.contract_id == contract_id, Invoice.month == month_str).first()


def calculate_usage(contract_id, current_month, electric_end, water_end):
    prev_invoice = Invoice.query.filter(
        Invoice.contract_id == contract_id,
        Invoice.month < current_month,
        Invoice.active == True
    ).order_by(Invoice.month.desc()).first()

    if prev_invoice:
        start_elec = prev_invoice.electric_end_reading
        start_water = prev_invoice.water_end_reading
    else:
        start_elec = 0.0
        start_water = 0.0

    e_end = float(electric_end) if electric_end is not None else 0.0
    w_end = float(water_end) if water_end is not None else 0.0
    new_elec_usage = e_end - start_elec
    new_water_usage = w_end - start_water

    return {
        'electric_usage': new_elec_usage if new_elec_usage > 0 else 0.0,
        'water_usage': new_water_usage if new_water_usage > 0 else 0.0
    }


def calculate_monthly_invoice(contract, electric_usage, water_usage, service_fee=None):
    e_price = get_rule_value(RuleKey.PRICE_ELECTRIC)
    w_price = get_rule_value(RuleKey.PRICE_WATER)

    s_price = get_rule_value(RuleKey.PRICE_SERVICE)
    if service_fee is not None:
        try:
            s_price = float(service_fee)
        except:
            pass

    usage_e = float(electric_usage) if electric_usage else 0.0
    usage_w = float(water_usage) if water_usage else 0.0

    e_fee = usage_e * e_price
    w_fee = usage_w * w_price
    total_price = e_fee + w_fee + s_price + contract.rent_price

    return {
        "electric_fee": e_fee,
        "water_fee": w_fee,
        "service_fee": s_price,
        "total_price": total_price
    }


# ============================
# CREATE FIRST INVOICE
# ============================
def create_first_invoice(contract):
    deposit_fee = contract.deposit
    service_fee = get_rule_value(RuleKey.PRICE_SERVICE)

    inv = Invoice(
        id=get_next_id(Invoice, "I", 3),
        contract_id=contract.id,
        month=f"{contract.start_date.year}-{contract.start_date.month}",
        electric_usage=0,
        water_usage=0,
        electric_fee=0,
        water_fee=0,
        service_fee=service_fee,
        total_amount=contract.rent_price + service_fee + deposit_fee,
        status=PaymentStatus.UNPAID
    )

    db.session.add(inv)
    db.session.commit()


# ============================
# RULES & READINGS
# ============================
def get_rule_value(key: RuleKey):
    rule = Rule.query.filter(Rule.key == key).first()
    if not rule: return 0
    try:
        return float(rule.value)
    except ValueError:
        return rule.value


def get_all_rules_as_dict():
    rules = Rule.query.all()
    return {r.key.name: float(r.value) if r.value.replace('.', '', 1).isdigit() else r.value for r in rules}


def get_last_reading_values(apartment_id, reading_type):
    contract = Contract.query.filter_by(apartment_id=apartment_id, status=ContractStatus.ACTIVE).first()
    if not contract: return None, None

    col = Invoice.electric_end_reading if reading_type == 'electric' else Invoice.water_end_reading
    last_invoice = Invoice.query.filter(Invoice.contract_id == contract.id, col.isnot(None)) \
        .order_by(Invoice.month.desc()).first()

    if last_invoice:
        val = last_invoice.electric_end_reading if reading_type == 'electric' else last_invoice.water_end_reading
        return (last_invoice.month, val)
    return (None, None)



def save_new_reading(apartment_id, reading_type, month, electric_usage, water_usage, new_reading, image):
    contract = Contract.query.filter_by(apartment_id=apartment_id, status=ContractStatus.ACTIVE).first()
    if not contract: return False, "Can not find the constract!"

    invoice = get_invoice(contract.id, month)
    if not invoice:
        new_id = get_next_id(Invoice, "I", 3)
        invoice = Invoice(id=new_id, contract_id=contract.id, month=month)
        db.session.add(invoice)
        invoice.electric_usage = 0
        invoice.water_usage = 0

    try:
        if reading_type == 'electric':
            invoice.electric_usage = electric_usage
            invoice.electric_end_reading = new_reading
            invoice.electric_image = image
        elif reading_type == 'water':
            invoice.water_usage = water_usage
            invoice.water_end_reading = new_reading
            invoice.water_image = image

        curr_elec = invoice.electric_usage if invoice.electric_usage else 0
        curr_water = invoice.water_usage if invoice.water_usage else 0
        curr_service = invoice.service_fee

        money_data = calculate_monthly_invoice(
            contract=contract,
            electric_usage=curr_elec,
            water_usage=curr_water,
            service_fee=curr_service
        )
        invoice.electric_fee = money_data['electric_fee']
        invoice.water_fee = money_data['water_fee']
        invoice.service_fee = money_data['service_fee']
        invoice.total_amount = money_data['total_price']

        db.session.commit()
        return True, f"Save the index {reading_type.capitalize()} and update the invoice successfully."
    except Exception as e:
        db.session.rollback()
        return False, f"Error SQL: {str(e)}"


# ============================
# STATS
# ============================
def stats_revenue(kw=None, month=None):
    query = db.session.query(
        Contract.apartment_id,Invoice.month,func.sum(Invoice.total_amount),Invoice.status
    ).join(Invoice, Invoice.contract_id == Contract.id)

    if kw: query = query.filter(Contract.apartment_id.contains(kw))
    if month: query = query.filter(Invoice.month == month)

    return query.group_by(Contract.apartment_id, Invoice.month, Invoice.status).all()

def stats_revenue_by_year(year):
    return (db.session.query(Invoice.month, func.sum(Invoice.total_amount))
            .filter(Invoice.month.contains(str(year)),Invoice.status == PaymentStatus.PAID)
            .group_by(Invoice.month).order_by(Invoice.month).all())