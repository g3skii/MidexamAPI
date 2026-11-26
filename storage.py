"""storage.py — JSON ფაილში შენახვა/ჩატვირთვა."""
import json
import os

from decorators import retry
from exceptions import CorruptDataError, StorageError


class JsonStorage:
    EMPTY = {"next_id": 1, "tasks": []}

    def __init__(self, path):
        self.path = str(path)

    def load(self):
        """აბრუნებს dict-ს {"next_id": ..., "tasks": [...]}.
        ფაილი არ არსებობს -> ცარიელი მონაცემები (პირველი გაშვება)."""
        if not os.path.exists(self.path):
            return {"next_id": 1, "tasks": []}
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            raise self._quarantine("ფაილი დაზიანებულია") from None
        except OSError as error:
            raise StorageError(f"ფაილის წაკითხვა ვერ მოხერხდა: {error}") from error

        if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
            raise self._quarantine("ფაილის სტრუქტურა არასწორია")
        return data

    def _quarantine(self, reason):
        """დაზიანებულ ფაილს .bak-ად ინახავს, რომ მონაცემი არ დაიკარგოს."""
        backup = self.path + ".bak"
        try:
            os.replace(self.path, backup)
        except OSError as error:
            return StorageError(f"{reason}, ასლის შექმნა ვერ მოხერხდა: {error}")
        return CorruptDataError(f"{reason}. ძველი ფაილი შენახულია: {backup}")

    @retry(times=3, delay=0.2)
    def save(self, data):
        """ჯერ დროებით ფაილში წერს, მერე ანაცვლებს — ჩაწერის შუა გზაზე
        გაჩერებამ ძველი ფაილი არ უნდა დააზიანოს."""
        temp_path = self.path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.path)
