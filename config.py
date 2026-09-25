import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'portsense-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///portsense_local.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False