from datetime import timedelta
from flask_login import current_user
from aapp.models import Tenant, UserRole, ContractStatus, RuleKey
from aapp import db, dao
import hashlib


def get_next_id(model, prefix, id_length=3):
    with db.session.no_autoflush:# looix 1364 chít tịt
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

# ham de lay cac obj lien quan den current-user (dung chung cho cac man hinh tenant)
def get_tenant_context():
    contracts = dao.load_contracts(tenant_id=current_user.id, status=ContractStatus.ACTIVE)
    invoices = []
    contract = None
    apartment = None

    if contracts:
        contract = contracts[0]
        apartment = dao.get_apartment_by_id(contract.apartment_id)
        invoices = dao.load_invoices(contract_id=contract.id)
        invoices.sort(key=lambda x: x.month, reverse=True)

    total_unpaid = 0
    due_date = None
    if invoices:
        for i in invoices:
            due_date = i.created_at + timedelta(days=30)
            if i.status.name != 'PAID':
                total_unpaid += i.total_amount

    return {
        'contract': contract,
        'apartment': apartment,
        'invoices': invoices,
        'total_unpaid': total_unpaid,
        'due_date': due_date
    }