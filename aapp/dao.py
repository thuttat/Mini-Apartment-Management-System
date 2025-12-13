import hashlib
from datetime import datetime, timedelta

from sqlalchemy import func

from aapp.models import Manager, Tenant, Apartment, Contract, Invoice, Rule, UserRole, Technician, User, RuleKey, \
    ContractStatus, ApartmentStatus, PaymentStatus
from aapp import db
from aapp.utils import get_next_id, hash_password



# def auth_user(username, password, role: UserRole):
#     if role == UserRole.MANAGER:
#         return auth_manager(username, password)
#     elif role == UserRole.TENANT:
#         return auth_tenant(username, password)
#     else:
#         return None


UserRoleMapping = [
    (Manager, UserRole.MANAGER.value),
    (Tenant, UserRole.TENANT.value),
    (Technician, UserRole.TECHNICIAN.value) 
]

def auth_user(username, password):
    hashed = hashlib.md5(password.strip().encode('utf-8')).hexdigest()

    for Model, role in UserRoleMapping:
        user = Model.query.filter_by(username=username, password=hashed).first()


# ============================
# USER
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
# MANAGER
# ============================
def add_manager(name, username, password, avatar=None):
    new_id = get_next_id(Manager, "M", 3)

    user = Manager(
        id=new_id,
        full_name=name,
        username=username.strip(),
        password=hash_password(password),
        user_role=UserRole.MANAGER
    )
    if avatar:
        import cloudinary.uploader
        res = cloudinary.uploader.upload(avatar)
        user.avatar = res.get('secure_url')

    db.session.add(user)
    db.session.commit()
    return user

# ============================
# TECHNICIAN
# ============================
def add_technician(name, username, password, avatar=None):
    new_id = get_next_id(Technician, "TECH", 3)

    user = Technician(
        id=new_id,
        full_name=name,
        username=username.strip(),
        password=hash_password(password),
        user_role=UserRole.TECHNICIAN
    )
    if avatar:
        import cloudinary.uploader
        res = cloudinary.uploader.upload(avatar)
        user.avatar = res.get('secure_url')

    db.session.add(user)
    db.session.commit()
    return user

# def auth_manager(username, password):
#     password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
#     return Manager.query.filter(
#         Manager.username == username.strip(),
#         Manager.password == password
#     ).first()


# def auth_tenant(username, password):
#     password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
#     return Tenant.query.filter(
#         Tenant.username == username.strip(),
#         Tenant.password == password
#     ).first()

# ============================
# TENANT
# ============================
def add_tenant(name, username, password, avatar=None):
    new_id = get_next_id(Tenant, "T", 3)
    tenant = Tenant(
        id=new_id,
        full_name=name,
        username=username.strip(),
        password=hash_password(password),
        user_role=UserRole.TENANT
    )

    if avatar:
        import cloudinary.uploader
        res = cloudinary.uploader.upload(avatar)
        tenant.avatar = res.get('secure_url')

    db.session.add(tenant)
    db.session.commit()
    return tenant

# ============================
# APARTMENT
# ============================
def load_apartments(room_type=None, status=None, min_price=None, max_price=None,keyword=None):
    query = Apartment.query

    if room_type:
        query = query.filter(Apartment.room_type == room_type)

    if status:
        if isinstance(status, list):
            query = query.filter(Apartment.status.in_(status))
        else:
            query = query.filter(Apartment.status == status)
    if min_price:
        query = query.filter(Apartment.price >= min_price)

    if max_price:
        query = query.filter(Apartment.price <= max_price)
    if keyword:
        query = query.filter(Apartment.id.contains(keyword))

    return query.order_by(Apartment.id).all()


def get_apartment_by_id(apartment_id):
    return Apartment.query.filter(Apartment.id == apartment_id).first()


def update_apartment_info(apartment_id, status=None, room_type=None, price=None):
    apt = Apartment.query.get(apartment_id)
    if not apt:
        return False
    if status == ApartmentStatus.LOOKING_FOR_ROOMMATE:
        max_people = get_rule_value(RuleKey.MAX_PER_ROOM)
        current_people = count_people_in_apartment(apartment_id)

        if current_people >= int(max_people):
            return False, f"Enough members ({current_people}/{int(max_people)})"

    change_made = False
    if status:
        apt.status = status
        change_made = True
    if room_type:
        apt.room_type = room_type
        change_made = True
    if price:
        apt.price = price
        change_made = True

    if change_made:
        db.session.commit()
        return True

    return False

# ============================
# CONSTRACT
# ============================
def load_contracts(tenant_id=None, apartment_id=None, status=None):
    query = Contract.query

    if tenant_id:
        query = query.filter(Contract.tenant_id == tenant_id)

    if apartment_id:
        query = query.filter(Contract.apartment_id == apartment_id)

    if status:
        query = query.filter(Contract.status == status)

    return query.all()


def count_people_in_apartment(apartment_id):
    contract = Contract.query.filter(
        Contract.apartment_id == apartment_id,
        Contract.status == ContractStatus.ACTIVE
    ).first()
    if contract:
        return contract.member_count
    return 0


def add_contract(tenant_id, apartment_id, start_date, end_date, deposit, rent_price, member_count=1):
    max_people = get_rule_value(RuleKey.MAX_PER_ROOM)
    if member_count > int(max_people):
        raise Exception(f"The quanity is ({member_count})/({int(max_people)})")

    current_active = Contract.query.filter_by(apartment_id=apartment_id, status=ContractStatus.ACTIVE).first()
    if current_active:
        raise Exception("This room is active")

    new_id = get_next_id(Contract, "C", 3)
    contract = Contract(
        id=new_id,
        tenant_id=tenant_id,
        apartment_id=apartment_id,
        start_date=start_date,
        end_date=end_date,
        deposit=deposit,
        rent_price=rent_price,
        status=ContractStatus.ACTIVE,
        member_count=member_count
    )

    db.session.add(contract)
    db.session.commit()
    return contract

def terminate_contract(contract_id):
    c = Contract.query.get(contract_id)
    if c and c.status == ContractStatus.ACTIVE:
        c.status = ContractStatus.EXPIRED
        db.session.commit()
        return True
    return False

def get_contract_by_id(cid):
    return Contract.query.filter(Contract.id == cid).first()


# ============================
# INVOICE
# ============================

def load_invoices(contract_id=None, month=None, status=None):
    query = Invoice.query

    if contract_id:
        query = query.filter(Invoice.contract_id == contract_id)

    if month:
        query = query.filter(Invoice.month == month)

    if status:
        query = query.filter(Invoice.status == status)

    return query.all()


def get_invoice_by_id(iid):
    return Invoice.query.filter(Invoice.id == iid).first()


def create_monthly_invoice(contract_id, month_str, electric_usage, water_usage):
    contract = Contract.query.get(contract_id)
    if not contract:
        raise Exception("? Contract")

    # Rule -> unit_price
    e_price = get_rule_value(RuleKey.PRICE_ELECTRIC)
    w_price = get_rule_value(RuleKey.PRICE_WATER)
    s_price = get_rule_value(RuleKey.PRICE_SERVICE)

    e_fee = electric_usage * e_price
    w_fee = water_usage * w_price

    # amount
    total = e_fee + w_fee + s_price

    new_id = get_next_id(Invoice, "INV", 6)
    inv = Invoice(
        id=new_id,
        contract_id=contract_id,
        month=month_str,
        electric_usage=electric_usage,
        water_usage=water_usage,
        electric_fee=e_fee,
        water_fee=w_fee,
        service_fee=s_price,
        total_amount=total,
        status=PaymentStatus.UNPAID
    )

    db.session.add(inv)
    db.session.commit()
    return inv

# ============================
# RULE
# ============================

def get_rule_value(key: RuleKey):
    rule = Rule.query.filter(Rule.key == key).first()
    if not rule:
        return 0

    try:
        return float(rule.value)
    except ValueError:
        return rule.value


def get_all_rules_as_dict():

    rules = Rule.query.all()
    # {'PRICE_ELECTRIC': 3500.0, 'MAX_PER_ROOM': 4.0 ...}
    return {r.key.name: float(r.value) if r.value.replace('.', '', 1).isdigit() else r.value for r in rules}


def update_rule(key: RuleKey, new_value):
    rule = Rule.query.filter(Rule.key == key).first()
    if rule:
        rule.value = str(new_value)
        rule.last_updated = datetime.utcnow()
        db.session.commit()
        return True
    return False


def get_last_reading_values(apartment_id, reading_type):
    contract = Contract.query.filter_by(apartment_id=apartment_id,status=ContractStatus.ACTIVE).first()
    if not contract:
        return None

    if reading_type == 'electric':
        end_reading_column = Invoice.electric_end_reading
    elif reading_type == 'water':
        end_reading_column = Invoice.water_end_reading
    else:
        raise Exception("Chỉ số bắt buộc là điện hoặc nước")

    last_invoice = (Invoice.query.filter(Invoice.contract_id==contract.id,end_reading_column.isnot(None))
                    .order_by(Invoice.month.desc()).first())

    if last_invoice:
        if reading_type == 'electric':
            return (last_invoice.month, last_invoice.electric_end_reading)
        else:
            return (last_invoice.month, last_invoice.water_end_reading)
    print(f"Last_invoice={last_invoice.month} và {last_invoice.electric_end_reading}")
    return (None, None)

def get_invoice(contract_id, month_str):
    return Invoice.query.filter(Invoice.contract_id==contract_id,Invoice.month==month_str).first()

def save_new_reading(apartment_id, reading_type, month, electric_usage, water_usage,new_reading, image):
    contract = Contract.query.filter_by(apartment_id=apartment_id,status=ContractStatus.ACTIVE).first()
    if not contract:
        return False,"Không tìm thấy hợp đồng!"
    invoice=get_invoice(contract.id, month)
    if not invoice:
        new_id = get_next_id(Invoice, "INV", 6)
        invoice=Invoice(id=new_id,contract_id=contract.id,month=month)
        db.session.add(invoice)
    try:
        if reading_type == 'electric':
            invoice.electric_usage = electric_usage
            invoice.electric_end_reading = new_reading
            invoice.electric_image = image
        elif reading_type == 'water':
            invoice.water_usage = water_usage
            invoice.water_end_reading = new_reading
            invoice.water_image = image
        else:
            return False, "Loại chỉ số không xác định."

        db.session.commit()
        return True, f"Lưu chỉ số {reading_type.capitalize()} thành công."
    except Exception as e:
        db.session.rollback()
        return False, f"Lỗi CSDL: {str(e)}"


def count_apartments():
    stats = db.session.query(Apartment.status, func.count(Apartment.id).label('count')).group_by(
        Apartment.status).all()
    stats_data = []

    for s in stats:
        status_name = s.status.value
        display_name = status_name
        if status_name == ApartmentStatus.AVAILABLE.value:
            display_name = "Còn Trống"
        elif status_name == ApartmentStatus.RENTED.value:
            display_name = "Đã Thuê"
        elif status_name == ApartmentStatus.MAINTENANCE.value:
            display_name = "Đang Bảo Trì"
        elif status_name == ApartmentStatus.LOOKING_FOR_ROOMMATE.value:
            display_name = "Tìm Người Ở Ghép"

        stats_data.append({
            'name': display_name,
            'count': s.count
        })
    return stats_data

def get_contract_expiration(day_limit=30):
    current_date=datetime.now().date()
    print(f"DEBUG: Ngày hiện tại của server là: {current_date}")
    expiration_date = current_date + timedelta(days=day_limit)

    contract=Contract.query.filter(Contract.status== ContractStatus.ACTIVE,Contract.end_date>current_date,
                                   Contract.end_date<=expiration_date)
    return contract.order_by(Contract.end_date.asc()).all()







