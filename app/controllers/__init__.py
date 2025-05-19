from fastapi import APIRouter, Form, Request, Response, status, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from app.facade import RegistrationFacade
import os
from app.models import SessionLocal, Product, User, Order
from app.builder import OrderBuilder
from app.utils import OrderSubject, EmailNotifier, SMSNotifier
import smtplib
from email.mime.text import MIMEText

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '../views/templates'))

class RegisterForm(BaseModel):
    email: EmailStr
    password: str
    name: str

SESSION_COOKIE = 'user_email'

@router.get('/register', response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse('register.html', {"request": request})

@router.post('/register', response_class=HTMLResponse)
def register_user(request: Request, email: str = Form(...), password: str = Form(...), name: str = Form(...)):
    success, message = RegistrationFacade.register_user(email, password, name)
    if success:
        resp = RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)
        return resp
    return templates.TemplateResponse('register.html', {"request": request, "message": message, "success": success})

@router.get('/login', response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse('login.html', {"request": request})

@router.post('/login', response_class=HTMLResponse)
def login_user(request: Request, response: Response, email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter_by(email=email, password=password).first()
    db.close()
    if user:
        resp = RedirectResponse(url='/products', status_code=status.HTTP_302_FOUND)
        resp.set_cookie(key=SESSION_COOKIE, value=email, httponly=True)
        return resp
    return templates.TemplateResponse('login.html', {"request": request, "message": "Невірний email або пароль", "success": False})

@router.get('/logout')
def logout(response: Response):
    resp = RedirectResponse(url='/', status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(SESSION_COOKIE)
    return resp

@router.get('/products', response_class=HTMLResponse)
def product_list(request: Request, user_email: str = Cookie(None)):
    if not user_email:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)
    db = SessionLocal()
    products = db.query(Product).all()
    db.close()
    return templates.TemplateResponse('products.html', {"request": request, "products": products, "user_email": user_email})

@router.post('/order', response_class=HTMLResponse)
def create_order(request: Request, product_id: int = Form(...), user_email: str = Cookie(None)):
    if not user_email:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)
    db = SessionLocal()
    user = db.query(User).filter_by(email=user_email).first()
    product = db.query(Product).filter_by(id=product_id).first()
    db.close()
    if not user or not product:
        return templates.TemplateResponse('products.html', {"request": request, "products": [], "message": "User or product not found", "success": False, "user_email": user_email})
    # Builder
    builder = OrderBuilder()
    order = builder.create_order(user, product).save()
    # Observer
    subject = OrderSubject()
    subject.attach(EmailNotifier())
    subject.attach(SMSNotifier())
    subject.notify(order)
    # Надсилання email користувачу
    send_order_email(user.email, user.name, product.name)
    # Перенаправлення на сторінку успішного замовлення
    return RedirectResponse(url=f'/order_success/{order.id}', status_code=status.HTTP_302_FOUND)

@router.get('/order_success/{order_id}', response_class=HTMLResponse)
def order_success(request: Request, order_id: int, user_email: str = Cookie(None)):
    if not user_email:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)
    db = SessionLocal()
    order = db.query(Order).filter_by(id=order_id).first()
    product = db.query(Product).filter_by(id=order.product_id).first() if order else None
    db.close()
    if not order or not product:
        return RedirectResponse(url='/products', status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse('order_success.html', {"request": request, "order": order, "product": product, "user_email": user_email})

# Email при купівлі товару
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'xchangeua@gmail.com'
EMAIL_HOST_PASSWORD = 'bcqv mmid toxp dxiq'
EMAIL_USE_TLS = True

def send_order_email(email: str, name: str, product: str):
    subject = "Підтвердження замовлення"
    body = f"Вітаємо, {name}! Ви успішно замовили товар: {product}. Дякуємо за покупку!"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_HOST_USER
    msg['To'] = email
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        if EMAIL_USE_TLS:
            server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.sendmail(EMAIL_HOST_USER, [email], msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Order email send error: {e}")
