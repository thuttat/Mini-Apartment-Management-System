import cloudinary
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user, LoginManager
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = 'iqiwqu3e735ehwsnsio274687928dhgtu'
app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql+pymysql://root:%s@localhost/apartmentdb' % quote('admin123@')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config['SQLALCHEMY_ECHO'] = True
# cloudinary.config(cloud_name='djviyyvzu',
#                   api_key='516671461397882',
#                   api_secret='oqcwKadypdGiiyJreDZprPf2K10')

cloudinary.config(cloud_name='dyupzyqwj',
                  api_key='497522642724389',
                  api_secret='1qiLwjHVPTBX9_BYZKsRB2FfWJA')

db = SQLAlchemy(app=app)
login = LoginManager(app=app)