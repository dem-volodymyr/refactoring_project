from typing import List

class SingletonType(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonType, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Logger(metaclass=SingletonType):
    def log(self, message: str):
        print(f"[LOG] {message}")

class OrderObserver:
    def update(self, order):
        pass

class EmailNotifier(OrderObserver):
    def update(self, order):
        Logger().log(f"Email: Статус замовлення {order.id} змінено на {order.status}")
        # Тут можна додати реальне надсилання email

class SMSNotifier(OrderObserver):
    def update(self, order):
        Logger().log(f"SMS: Статус замовлення {order.id} змінено на {order.status}")
        # Тут можна додати реальне надсилання SMS

class OrderSubject:
    def __init__(self):
        self._observers: List[OrderObserver] = []

    def attach(self, observer: OrderObserver):
        self._observers.append(observer)

    def detach(self, observer: OrderObserver):
        self._observers.remove(observer)

    def notify(self, order):
        for observer in self._observers:
            observer.update(order)
