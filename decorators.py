"""decorators.py — დეკორატორები იქ, სადაც ლოგიკურია."""
import time
from functools import wraps

from exceptions import TaskManagerError


def handle_errors(func):
    """მენიუს მოქმედებას იცავს: შეცდომაზე პროგრამა კი არ ვარდება,
    მომხმარებელს მკაფიო შეტყობინება ეჩვენება."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (TaskManagerError, ValueError) as error:
            print(f"❌ {error}")
        except OSError as error:
            print(f"❌ ფაილთან მუშაობის შეცდომა: {error}")

    return wrapper


def retry(times=3, delay=0.2, exceptions=(OSError,)):
    """ოპერაციას რამდენჯერმე ცდის (მაგ. ფაილი დროებით დაკავებულია).
    ბოლო მცდელობაზე შეცდომა გადაეცემა გამომძახებელს."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == times:
                        raise
                    time.sleep(delay)

        return wrapper

    return decorator


def confirm(question):
    """საშიში მოქმედების წინ მომხმარებელს ადასტურებინებს."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            answer = input(f"{question} (კი/არა): ").strip().lower()
            if answer not in ("კი", "ki", "yes", "y"):
                print("↩ გაუქმდა")
                return None
            return func(*args, **kwargs)

        return wrapper

    return decorator
