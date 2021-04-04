import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

class DevelopmentConfig:
    USER = os.environ.get('USER_DEV')
    PASSWORD = os.environ.get('PASSWORD_DEV')
    DB = os.environ.get('DB_DEV')
    HOST = os.environ.get('HOST_DEV')
    SALT = os.environ.get('SALT_DEV')

class ProductionConfig:
    USER = os.environ.get('USER_PROD')
    PASSWORD = os.environ.get('PASSWORD')
    DB = os.environ.get('DB')
    HOST = os.environ.get('HOST')
    SALT = os.environ.get('SALT')

class Config(DevelopmentConfig):
    pass