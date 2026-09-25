import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'portsense-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'mysql+pymysql://root:Cklif*2005@localhost/portsense'
    SQLALCHEMY_TRACK_MODIFICATIONS = False