from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Boolean, Text, DateTime, Date
from sqlalchemy.orm import declarative_base
from datetime import datetime


Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String, nullable=False)
    city = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    status = Column(Boolean)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    city = Column(String, nullable=False)
    text = Column(Text, nullable=True)
    image_file_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    author_id = Column(BigInteger, nullable=True)


class Promo(Base):
    __tablename__ = "promos"

    id = Column(Integer, primary_key=True)
    city = Column(String, nullable=False)
    text = Column(Text, nullable=True)
    image_file_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    date_expire = Column(Date, nullable=False)

    author_id = Column(BigInteger, nullable=True)
