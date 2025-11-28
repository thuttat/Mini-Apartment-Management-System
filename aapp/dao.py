import hashlib

import cloudinary
from aapp.models import Manager, Tenant, Apartment, Contract, Invoice, Rule, UserRole
from aapp import db

# def auth_user(username, password, role: UserRole):
#     if role == UserRole.MANAGER:
#         return auth_manager(username, password)
#     elif role == UserRole.TENANT:
#         return auth_tenant(username, password)
#     else:
#         return None
    
def auth_user(username, password):
    """Xác thực người dùng bất kỳ role (Manager, Tenant, Technician)"""
    hashed = hashlib.md5(password.strip().encode('utf-8')).hexdigest()

    # Kiểm tra Manager
    user = Manager.query.filter_by(username=username.strip(), password=hashed).first()
    if user:
        return user, 2

    # Kiểm tra Tenant
    user = Tenant.query.filter_by(username=username.strip(), password=hashed).first()
    if user:
        return user, 1

    # Kiểm tra Technician (nếu có)
    # user = Technician.query.filter_by(username=username.strip(), password=hashed).first()
    # if user:
    #     return user, 'technician'

    return None, None

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


def get_manager_by_id(id):
    return Manager.query.get(id)


def get_tenant_by_id(id):
    return Tenant.query.get(id)


def add_tenant(name, username, password, avatar):
    tenant = Tenant(name=name, username=username.strip(), password=str(hashlib.md5(password.strip().encode('utf-8')).hexdigest()))

    if avatar:
        res = cloudinary.uploader.upload(avatar)
        tenant.avatar = res.get('secure_url')

    db.session.add(tenant)
    db.session.commit()


def load_apartments(room_type=None, status=None, min_price=None, max_price=None):
    query = Apartment.query

    if room_type:
        query = query.filter(Apartment.room_type == room_type)

    if status:
        query = query.filter(Apartment.status == status)

    if min_price:
        query = query.filter(Apartment.price >= min_price)

    if max_price:
        query = query.filter(Apartment.price <= max_price)

    return query.all()


def get_apartment_by_id(apartment_id):
    return Apartment.query.filter(Apartment.apartment_id == apartment_id).first()




def load_contracts(tenant_id=None, apartment_id=None, status=None):
    query = Contract.query

    if tenant_id:
        query = query.filter(Contract.tenant_id == tenant_id)

    if apartment_id:
        query = query.filter(Contract.apartment_id == apartment_id)

    if status:
        query = query.filter(Contract.status == status)

    return query.all()


def get_contract_by_id(cid):
    return Contract.query.filter(Contract.contract_id == cid).first()


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
    return Invoice.query.filter(Invoice.invoice_id == iid).first()



def load_rules():
    return Rule.query.all()


def update_rule(rule_name, new_value):
    rule = Rule.query.filter(Rule.rule_name == rule_name).first()

    if rule:
        rule.value = new_value
        db.session.commit()

    return rule
