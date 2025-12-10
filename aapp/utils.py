from sqlalchemy import func

from aapp.models import Tenant, UserRole, Apartment, Invoice, Contract, PaymentStatus
from aapp import db
import hashlib

def get_next_id(model, prefix, id_length=3):
    with db.session.no_autoflush:# loi 1364 chít tịt
        last_obj = model.query.filter(model.id.like(f"{prefix}%")) \
            .order_by(model.id.desc()) \
            .first()

    if not last_obj:
        return f"{prefix}{1:0{id_length}d}"

    try:
        current_id_str = last_obj.id[len(prefix):]
        new_number = int(current_id_str) + 1
    except ValueError:
        new_number = 1

    return f"{prefix}{new_number:0{id_length}d}"

def hash_password(password):
    return hashlib.md5(password.strip().encode('utf-8')).hexdigest()

def revenue_stats(kw =None, month=None):
    query = db.session.query(
        Apartment.id,
        Invoice.month,
        func.sum(Invoice.total_amount),
        Invoice.status
    )
    query = query.join(Contract, Contract.apartment_id == Apartment.id) \
        .join(Invoice, Invoice.contract_id == Contract.id)
    #[('A102', '2024-01', 529950.0, <PaymentStatus.PAID: 'PAID'>), ('A102', '2024-02', 474900.0, <PaymentStatus.PAID: 'PAID'>)]
    # query = query.filter(Invoice.status == PaymentStatus.PAID)
    if month:
        query = query.filter(Invoice.month == month)
    if kw:
        query = query.filter(Apartment.id.contains(kw))
    query = query.group_by(Invoice.month, Apartment.id,Invoice.status)
    query = query.order_by(Invoice.month)
    return query.all()