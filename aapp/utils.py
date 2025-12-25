import hashlib
from datetime import datetime, timedelta
import cloudinary.uploader
from flask import session
from flask_login import current_user
from flask_apscheduler import APScheduler

from aapp import db, app,dao
from aapp.models import ContractStatus, Apartment, ApartmentStatus


def get_next_id(model, prefix, id_length=3):
    with db.session.no_autoflush:
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


def get_months_list(num_months=12):
    months_list = []
    today = datetime.now()
    for i in range(num_months):
        target_date = today.replace(day=1) - timedelta(days=30 * i)
        months_list.append(target_date.strftime('%Y-%m'))
    return months_list


def get_tenant_context():
    from aapp import dao

    contracts = dao.load_contracts(tenant_id=current_user.id, status=ContractStatus.ACTIVE)
    contract = None
    apartment = None

    if contracts:
        current_contract_id = session.get("current_contract_id")
        contract = next(
            (c for c in contracts if c.id == current_contract_id),
            contracts[0]
        )
        session["current_contract_id"] = contract.id

        apartment = dao.get_apartment_by_id(contract.apartment_id)

    return {
        'contract': contract,
        'contracts': contracts,
        'apartment': apartment
    }


def process_upload(image):
    if image:
        try:
            res = cloudinary.uploader.upload(image)
            return res.get('secure_url'), res.get('public_id')
        except Exception as e:
            print(f"Faill to upload img: {e}")
            return None
    return None


def require_delete_uploaded_image(public_id):
    try:
        result = cloudinary.uploader.destroy(public_id)
        if result.get('result') == 'ok':
            return True
        return False
    except Exception as e:
        return False


def validate_reading(apartment_id, reading_type, new_reading):
    last_month, last_reading = dao.get_last_reading_values(apartment_id, reading_type)
    if last_reading is None:
        last_reading = 0.0

    usage = new_reading - last_reading
    if usage < 0:
        err_msg = str(f"New index ({new_reading}) is smaller than the old once ({last_reading})!")
        return False, 0.0, err_msg
    return True, usage, ""


def handle_meter_reading(data):
    apartment_id = data['apartment_id']
    month = data['month']
    new_reading_str = data['new_reading_str']
    image = data['image_file']
    reading_type = data['reading_type']

    try:
        new_reading = float(new_reading_str)
    except ValueError:
        return False, 'The new index need to be a float'

    image_url = None
    image_public_id = None

    try:
        upload_result = process_upload(image)
        if upload_result:
            image_url, image_public_id = upload_result
    except Exception as e:
        print(f"Upload fail: {e}")
        return False

    if not image_url:
        return False, 'Cannot upload img (force to upload img)'

    is_valid, usage, validation_msg = validate_reading(
        apartment_id=apartment_id,
        reading_type=reading_type,
        new_reading=new_reading
    )

    if not is_valid:
        require_delete_uploaded_image(image_public_id)
        return False, validation_msg

    electric_usage = usage if reading_type == 'electric' else 0.0
    water_usage = usage if reading_type == 'water' else 0.0

    success, message = dao.save_new_reading(
        apartment_id=apartment_id,
        reading_type=reading_type,
        month=month,
        electric_usage=electric_usage,
        water_usage=water_usage,
        new_reading=new_reading,
        image=image_url
    )

    if not success:
        try:
            require_delete_uploaded_image(image_public_id)
        except Exception as e:
            print(f"Cannot delete the img: {image_public_id}. Err {e}")
        return False, message

    return True, message


scheduler = APScheduler()


def init_scheduler(app):
    if not scheduler.running:
        scheduler.init_app(app)
        from .dao import auto_update_contract_status
        scheduler.add_job(
            id="auto_contract_status",
            func=auto_update_contract_status,
            trigger="cron",
            hour=0,
            minute=0
        )
        scheduler.start()