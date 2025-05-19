from app.models import SessionLocal, User
from email_validator import validate_email, EmailNotValidError
import smtplib
from email.mime.text import MIMEText
from sqlalchemy.exc import IntegrityError

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'xchangeua@gmail.com'
EMAIL_HOST_PASSWORD = 'XXX'
EMAIL_USE_TLS = True

class RegistrationFacade:
    @staticmethod
    def register_user(email: str, password: str, name: str):
        # 1. Перевірка email
        try:
            validate_email(email)
        except EmailNotValidError as e:
            return False, f"Invalid email: {str(e)}"
        # 2. Збереження у БД
        db = SessionLocal()
        user = User(email=email, password=password, name=name)
        try:
            db.add(user)
            db.commit()
        except IntegrityError:
            db.rollback()
            return False, "Email already registered."
        finally:
            db.close()
        # 3. Надсилання email
        RegistrationFacade.send_confirmation_email(email, name)
        return True, "Registration successful. Confirmation email sent."

    @staticmethod
    def send_confirmation_email(email: str, name: str):
        subject = "Підтвердження реєстрації"
        body = f"Вітаємо, {name}! Ви успішно зареєстровані у Tech Store."
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
            print(f"Email send error: {e}")
