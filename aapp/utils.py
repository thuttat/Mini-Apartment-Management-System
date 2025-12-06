from sqlalchemy import func
from aapp.models import Tenant, UserRole
from aapp import db
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