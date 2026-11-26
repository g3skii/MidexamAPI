"""manager.py — ბიზნეს-ლოგიკა (კონსოლისგან დამოუკიდებელი)."""
from exceptions import CorruptDataError, TaskNotFoundError
from models import (FIELD_PARSERS, PRIORITIES, RecurringTask, Task, parse_status,
                    task_from_dict)


class TaskManager:
    def __init__(self, storage):
        self._storage = storage
        self._tasks = {}      # id -> Task
        self._next_id = 1
        self.load_warning = None

    # ------------------------------------------------ ჩატვირთვა / შენახვა
    def load(self):
        try:
            data = self._storage.load()
        except CorruptDataError as error:
            self.load_warning = f"{error}. იწყება ცარიელი სიით."
            return  # სხვა StorageError-ს main.py დაიჭერს

        tasks, skipped = {}, 0
        for item in data["tasks"]:
            try:
                task = task_from_dict(item)
                tasks[task.id] = task
            except ValueError:
                skipped += 1  # ერთი დაზიანებული ჩანაწერი მთლიან ფაილს არ ანგრევს
        self._tasks = tasks
        self._next_id = max(data.get("next_id", 1), max(tasks, default=0) + 1)
        if skipped:
            self.load_warning = f"{skipped} დაზიანებული ჩანაწერი გამოტოვებულია."

    def save(self):
        self._storage.save({
            "next_id": self._next_id,
            "tasks": [task.to_dict() for task in self._tasks.values()],
        })

    # ------------------------------------------------ CRUD
    def add_task(self, title, description="", deadline=None, priority="medium",
                 project="", repeat_days=None):
        if repeat_days:
            task = RecurringTask(self._next_id, title, description, deadline,
                                 priority, "pending", project, repeat_days)
        else:
            task = Task(self._next_id, title, description, deadline,
                        priority, "pending", project)
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def get(self, task_id):
        try:
            return self._tasks[task_id]
        except KeyError:
            raise TaskNotFoundError(f"დავალება #{task_id} ვერ მოიძებნა") from None

    def update(self, task_id, **fields):
        task = self.get(task_id)
        # ჯერ ყველა ველს ვამოწმებთ, მერე ვცვლით — ნახევრად შეცვლილი დავალება არ დარჩება
        cleaned = {}
        for name, value in fields.items():
            if name not in FIELD_PARSERS:
                raise ValueError(f"ველი '{name}' არ რედაქტირდება")
            cleaned[name] = FIELD_PARSERS[name](value)
        for name, value in cleaned.items():
            setattr(task, name, value)
        return task

    def change_status(self, task_id, status):
        """აბრუნებს (დავალება, ახალი_განმეორებადი_დავალება ან None)."""
        status = parse_status(status)
        task = self.get(task_id)
        was_completed = task.status == "completed"
        task.status = status

        next_task = None
        if status == "completed" and not was_completed:
            next_task = task.spawn_next(self._next_id)  # Task -> None, RecurringTask -> ახალი
            if next_task is not None:
                self._tasks[next_task.id] = next_task
                self._next_id += 1
        return task, next_task

    def delete(self, task_id):
        self.get(task_id)
        del self._tasks[task_id]

    # ------------------------------------------------ ნახვა / ძებნა / ჯგუფები
    @staticmethod
    def _sort_key(task):
        # ვადიანები ჯერ (ადრეული ვადა წინ), შემდეგ პრიორიტეტი (high წინ)
        return (task.deadline is None, task.deadline or 0,
                -PRIORITIES.index(task.priority))

    def list_tasks(self, status=None):
        tasks = [t for t in self._tasks.values() if status is None or t.status == status]
        return sorted(tasks, key=self._sort_key)

    def search(self, text):
        text = text.strip().lower()
        found = [t for t in self._tasks.values()
                 if text in t.title.lower() or text in t.description.lower()]
        return sorted(found, key=self._sort_key)

    def by_project(self):
        """{პროექტი: [დავალებები]} — ანბანის მიხედვით დალაგებული."""
        groups = {}
        for task in self.list_tasks():
            groups.setdefault(task.project, []).append(task)
        return dict(sorted(groups.items()))
