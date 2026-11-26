"""exceptions.py — ჩვენი საკუთარი შეცდომები (მემკვიდრეობით Exception-დან)."""


class TaskManagerError(Exception):
    """აპლიკაციის ყველა შეცდომის საერთო მშობელი."""


class TaskNotFoundError(TaskManagerError):
    """დავალება ასეთი ID-ით არ არსებობს."""


class StorageError(TaskManagerError):
    """ფაილის წაკითხვა/ჩაწერა ვერ მოხერხდა."""


class CorruptDataError(StorageError):
    """JSON ფაილი დაზიანებულია."""
