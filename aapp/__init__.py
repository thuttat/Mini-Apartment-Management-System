import cloudinary
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user, LoginManager
from urllib.parse import quote

from aapp.vnpay import VNPay

app = Flask(__name__)
app.secret_key = 'iqiwqu3e735ehwsnsio274687928dhgtu'
app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql+pymysql://root:%s@localhost/apartmentdb' % quote('admin123@')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config['SQLALCHEMY_ECHO'] = True
app.config['PAGE_SIZE'] = 6
# cloudinary.config(cloud_name='djviyyvzu',
#                   api_key='516671461397882',
#                   api_secret='oqcwKadypdGiiyJreDZprPf2K10')

cloudinary.config(cloud_name='dyupzyqwj',
                  api_key='497522642724389',
                  api_secret='1qiLwjHVPTBX9_BYZKsRB2FfWJA')

vnpay_client = VNPay(
    tmn_code='QPTUJLUJ',
    hash_secret='U29VMF3ERO9SCYQWPEGMGHELZZQ5YADY',
    payment_url=' https://sandbox.vnpayment.vn/paymentv2/vpcpay.html'
)

db = SQLAlchemy(app=app)
login = LoginManager(app=app)