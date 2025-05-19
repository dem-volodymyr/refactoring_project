from app.models import Order, User, Product, SessionLocal

class OrderBuilder:
    def __init__(self):
        self._order = None

    def create_order(self, user: User, product: Product):
        self._order = Order(user_id=user.id, product_id=product.id, status='created')
        return self

    def set_status(self, status: str):
        if self._order:
            self._order.status = status
        return self

    def save(self):
        db = SessionLocal()
        db.add(self._order)
        db.commit()
        db.refresh(self._order)
        db.close()
        return self._order

    def get_order(self):
        return self._order
