from sqlalchemy import Column, Integer, String, ForeignKey, Float, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

# Factory Method Pattern
class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    __mapper_args__ = {'polymorphic_on': type, 'polymorphic_identity': 'product'}

    @staticmethod
    def create_product(product_type, name, price, **kwargs):
        if product_type == 'phone':
            return Phone(name=name, price=price, **kwargs)
        elif product_type == 'computer':
            return Computer(name=name, price=price, **kwargs)
        else:
            raise ValueError('Unknown product type')

class Phone(Product):
    __tablename__ = 'phones'
    id = Column(Integer, ForeignKey('products.id'), primary_key=True)
    sim_count = Column(Integer, default=1)
    __mapper_args__ = {'polymorphic_identity': 'phone'}

class Computer(Product):
    __tablename__ = 'computers'
    id = Column(Integer, ForeignKey('products.id'), primary_key=True)
    cpu = Column(String)
    __mapper_args__ = {'polymorphic_identity': 'computer'}

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    orders = relationship('Order', back_populates='user')

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    status = Column(String, default='created')
    user = relationship('User', back_populates='orders')
    product = relationship('Product')

# SQLite engine and session
engine = create_engine('sqlite:///app.db', echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def seed_products():
    db = SessionLocal()
    if db.query(Product).count() == 0:
        phone = Product.create_product('phone', name='iPhone 15', price=35000, sim_count=2)
        computer = Product.create_product('computer', name='MacBook Air', price=50000, cpu='M2')
        db.add(phone)
        db.add(computer)
        db.commit()
    db.close()
