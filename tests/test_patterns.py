import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from app.utils import Logger, SingletonType, OrderSubject, EmailNotifier, SMSNotifier
from app.models import Product, Phone, Computer, User, Order, SessionLocal
from app.builder import OrderBuilder
from app.facade import RegistrationFacade
from sqlalchemy.exc import IntegrityError

# --- Singleton ---
def test_logger_singleton():
    logger1 = Logger()
    logger2 = Logger()
    assert logger1 is logger2

def test_logger_log_output(capsys):
    Logger().log("Test log")
    captured = capsys.readouterr()
    assert "Test log" in captured.out

# --- Factory Method ---
def test_factory_method_phone():
    phone = Product.create_product('phone', name='TestPhone', price=1000, sim_count=2)
    assert isinstance(phone, Phone)
    assert phone.sim_count == 2

def test_factory_method_computer():
    computer = Product.create_product('computer', name='TestPC', price=2000, cpu='i7')
    assert isinstance(computer, Computer)
    assert computer.cpu == 'i7'

def test_factory_method_invalid():
    with pytest.raises(ValueError):
        Product.create_product('unknown', name='X', price=1)

# --- Builder ---
def test_order_builder():
    db = SessionLocal()
    user = User(email='builder@test.com', password='123', name='Builder')
    db.add(user)
    db.commit()
    product = Product.create_product('phone', name='BuilderPhone', price=999, sim_count=1)
    db.add(product)
    db.commit()
    builder = OrderBuilder()
    order = builder.create_order(user, product).set_status('paid').save()
    assert order.status == 'paid'
    db.delete(order)
    db.delete(product)
    db.delete(user)
    db.commit()
    db.close()

def test_order_builder_no_status():
    db = SessionLocal()
    user = User(email='builder2@test.com', password='123', name='Builder2')
    db.add(user)
    db.commit()
    product = Product.create_product('computer', name='BuilderPC', price=1999, cpu='i5')
    db.add(product)
    db.commit()
    builder = OrderBuilder()
    order = builder.create_order(user, product).save()
    assert order.status == 'created'
    db.delete(order)
    db.delete(product)
    db.delete(user)
    db.commit()
    db.close()

# --- Observer ---
def test_observer_notify(capsys):
    class TestOrder:
        id = 1
        status = 'created'
    subject = OrderSubject()
    email = EmailNotifier()
    sms = SMSNotifier()
    subject.attach(email)
    subject.attach(sms)
    subject.notify(TestOrder())
    captured = capsys.readouterr()
    assert "Email: Статус замовлення 1 змінено на created" in captured.out
    assert "SMS: Статус замовлення 1 змінено на created" in captured.out

def test_observer_detach(capsys):
    class TestOrder:
        id = 2
        status = 'paid'
    subject = OrderSubject()
    email = EmailNotifier()
    subject.attach(email)
    subject.notify(TestOrder())
    subject.detach(email)
    subject.notify(TestOrder())
    captured = capsys.readouterr()
    assert captured.out.count("Email: Статус замовлення 2 змінено на paid") == 1

# --- Facade (Registration) ---
def test_registration_facade(monkeypatch):
    # Mock email sending
    monkeypatch.setattr('app.facade.RegistrationFacade.send_confirmation_email', lambda email, name: None)
    db = SessionLocal()
    email = 'facade@test.com'
    user = db.query(User).filter_by(email=email).first()
    if user:
        db.delete(user)
        db.commit()
    success, msg = RegistrationFacade.register_user(email, '123', 'TestUser')
    assert success
    assert "Registration successful" in msg
    # Duplicate registration
    success, msg = RegistrationFacade.register_user(email, '123', 'TestUser')
    assert not success
    assert "already registered" in msg
    # Clean up
    user = db.query(User).filter_by(email=email).first()
    if user:
        db.delete(user)
        db.commit()
    db.close()

def test_registration_facade_invalid_email(monkeypatch):
    monkeypatch.setattr('app.facade.RegistrationFacade.send_confirmation_email', lambda email, name: None)
    success, msg = RegistrationFacade.register_user('not-an-email', '123', 'TestUser')
    assert not success
    assert "Invalid email" in msg

def test_registration_facade_empty_password(monkeypatch):
    monkeypatch.setattr('app.facade.RegistrationFacade.send_confirmation_email', lambda email, name: None)
    success, msg = RegistrationFacade.register_user('empty@pw.com', '', 'TestUser')
    assert not success
    assert "password" in msg.lower() or "invalid" in msg.lower() or "empty" in msg.lower()

# --- User/Order edge cases ---
def test_user_unique_email(monkeypatch):
    monkeypatch.setattr('app.facade.RegistrationFacade.send_confirmation_email', lambda email, name: None)
    db = SessionLocal()
    email = 'unique@test.com'
    # Видалити користувача, якщо вже є
    user = db.query(User).filter_by(email=email).first()
    if user:
        db.delete(user)
        db.commit()
    user1 = User(email=email, password='1', name='A')
    db.add(user1)
    db.commit()
    with pytest.raises(IntegrityError):
        user2 = User(email=email, password='2', name='B')
        db.add(user2)
        db.commit()
    db.rollback()
    db.delete(user1)
    db.commit()
    db.close()

def test_order_with_nonexistent_user():
    db = SessionLocal()
    product = Product.create_product('phone', name='GhostPhone', price=123, sim_count=1)
    db.add(product)
    db.commit()
    builder = OrderBuilder()
    with pytest.raises(Exception):
        builder.create_order(None, product).save()
    db.delete(product)
    db.commit()
    db.close()

def test_order_with_nonexistent_product():
    db = SessionLocal()
    user = User(email='ghost@user.com', password='1', name='Ghost')
    db.add(user)
    db.commit()
    builder = OrderBuilder()
    with pytest.raises(Exception):
        builder.create_order(user, None).save()
    db.delete(user)
    db.commit()
    db.close()

# --- Додаткові тести ---
def test_login_success(monkeypatch):
    from app.models import SessionLocal, User
    db = SessionLocal()
    email = 'login@test.com'
    password = 'pw123'
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(email=email, password=password, name='LoginUser')
        db.add(user)
        db.commit()
    db.close()
    # Симуляція логіну
    db = SessionLocal()
    user = db.query(User).filter_by(email=email, password=password).first()
    db.close()
    assert user is not None

def test_login_fail(monkeypatch):
    from app.models import SessionLocal
    db = SessionLocal()
    user = db.query(User).filter_by(email='notfound@test.com', password='wrong').first()
    db.close()
    assert user is None

def test_logout_cookie():
    # Симуляція видалення cookie (логічний тест)
    cookies = {'user_email': 'test@logout.com'}
    cookies.pop('user_email', None)
    assert 'user_email' not in cookies

def test_builder_multiple_orders():
    db = SessionLocal()
    user = User(email='multiorder@test.com', password='1', name='Multi')
    db.add(user)
    db.commit()
    product1 = Product.create_product('phone', name='MultiPhone', price=111, sim_count=1)
    product2 = Product.create_product('computer', name='MultiPC', price=222, cpu='i3')
    db.add(product1)
    db.add(product2)
    db.commit()
    builder = OrderBuilder()
    order1 = builder.create_order(user, product1).save()
    order2 = builder.create_order(user, product2).save()
    assert order1.id != order2.id
    db.delete(order1)
    db.delete(order2)
    db.delete(product1)
    db.delete(product2)
    db.delete(user)
    db.commit()
    db.close()

def test_observer_no_observers():
    class TestOrder:
        id = 99
        status = 'created'
    subject = OrderSubject()
    # No observers attached
    try:
        subject.notify(TestOrder())
    except Exception:
        pytest.fail("Observer notify failed with no observers")

def test_facade_email_send(monkeypatch):
    from app.models import SessionLocal, User
    called = {}
    def fake_send(email, name):
        called['sent'] = (email, name)
    monkeypatch.setattr('app.facade.RegistrationFacade.send_confirmation_email', fake_send)
    db = SessionLocal()
    email = 'facade2@test.com'
    user = db.query(User).filter_by(email=email).first()
    if user:
        db.delete(user)
        db.commit()
    db.close()
    RegistrationFacade.register_user(email, 'pw', 'User2')
    assert 'sent' in called
    assert called['sent'][0] == email

def test_factory_method_kwargs():
    phone = Product.create_product('phone', name='KWP', price=1, sim_count=5)
    assert phone.sim_count == 5
    computer = Product.create_product('computer', name='KWC', price=2, cpu='Ryzen')
    assert computer.cpu == 'Ryzen'

def test_logger_multiple_logs(capsys):
    logger = Logger()
    logger.log("First")
    logger.log("Second")
    captured = capsys.readouterr()
    assert "First" in captured.out and "Second" in captured.out

def test_builder_set_status_none():
    builder = OrderBuilder()
    builder._order = None
    # set_status should not fail if _order is None
    try:
        builder.set_status('paid')
    except Exception:
        pytest.fail("set_status failed when _order is None")

def test_observer_update_not_implemented():
    from app.utils import OrderObserver
    class Dummy(OrderObserver):
        pass
    dummy = Dummy()
    try:
        dummy.update(None)
    except Exception:
        pytest.fail("update() should be a no-op")

def test_facade_duplicate_email(monkeypatch):
    monkeypatch.setattr('app.facade.RegistrationFacade.send_confirmation_email', lambda email, name: None)
    db = SessionLocal()
    email = 'dupemail@test.com'
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(email=email, password='1', name='Dup')
        db.add(user)
        db.commit()
    success, msg = RegistrationFacade.register_user(email, 'pw', 'Dup')
    assert not success
    assert "already registered" in msg
    db.delete(user)
    db.commit()
    db.close() 