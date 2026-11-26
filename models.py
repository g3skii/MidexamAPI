"""models.py — მონაცემთა მოდელები: Entity -> Task -> RecurringTask."""
from datetime import date, timedelta

PRIORITIES = ("low", "medium", "high")
STATUSES = ("pending", "in-progress", "completed")
DEFAULT_PROJECT = "General"

STATUS_ICONS = {"pending": "⏳", "in-progress": "🔄", "completed": "✅"}
PRIORITY_ICONS = {"low": "🟢", "medium": "🟡", "high": "🔴"}


# ------------------------------------------------ ვალიდაციის ფუნქციები
# ერთი და იგივე წესებით სარგებლობს როგორც მოდელი, ისე კონსოლის ინტერფეისი.
def parse_title(value):
    value = str(value).strip()
    if not value:
        raise ValueError("სათაური ცარიელი ვერ იქნება")
    if len(value) > 60:
        raise ValueError("სათაური 60 სიმბოლოზე გრძელი ვერ იქნება")
    return value


def parse_description(value):
    return str(value).strip()


def parse_project(value):
    return str(value).strip() or DEFAULT_PROJECT


def parse_priority(value):
    value = str(value).strip().lower()
    if value not in PRIORITIES:
        raise ValueError(f"პრიორიტეტი უნდა იყოს: {', '.join(PRIORITIES)}")
    return value


def parse_status(value):
    value = str(value).strip().lower()
    if value not in STATUSES:
        raise ValueError(f"სტატუსი უნდა იყოს: {', '.join(STATUSES)}")
    return value


def parse_deadline(value):
    """None / ცარიელი ტექსტი = ვადა არ არის. სხვა შემთხვევაში YYYY-MM-DD."""
    if value is None or isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("თარიღი უნდა იყოს YYYY-MM-DD ფორმატში (მაგ. 2026-12-31)") from None


def parse_repeat_days(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError("გამეორების დღეები მთელი რიცხვი უნდა იყოს") from None
    if number < 1:
        raise ValueError("გამეორების დღეები 1-ზე ნაკლები ვერ იქნება")
    return number


# რედაქტირებადი ველები და მათი ვალიდატორები
FIELD_PARSERS = {
    "title": parse_title,
    "description": parse_description,
    "deadline": parse_deadline,
    "priority": parse_priority,
    "project": parse_project,
}


# ------------------------------------------------ კლასები
class Entity:
    """საბაზო კლასი: ყველა ობიექტს აქვს უცვლელი ID და to_dict()."""

    def __init__(self, entity_id):
        if isinstance(entity_id, bool) or not isinstance(entity_id, int):
            raise ValueError("ID მთელი რიცხვი უნდა იყოს")
        self._id = entity_id

    @property
    def id(self):
        return self._id  # setter არ გვაქვს — ID-ის შეცვლა შეუძლებელია

    def to_dict(self):
        raise NotImplementedError


class Task(Entity):
    TYPE = "task"

    def __init__(self, task_id, title, description="", deadline=None,
                 priority="medium", status="pending", project=DEFAULT_PROJECT):
        super().__init__(task_id)
        self.title = title
        self.description = description
        self.deadline = deadline
        self.priority = priority
        self.status = status
        self.project = project

    # --- დაცული ველები და მათი setter-ები (ინკაფსულაცია)
    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = parse_title(value)

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = parse_description(value)

    @property
    def deadline(self):
        return self._deadline

    @deadline.setter
    def deadline(self, value):
        self._deadline = parse_deadline(value)

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, value):
        self._priority = parse_priority(value)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = parse_status(value)

    @property
    def project(self):
        return self._project

    @project.setter
    def project(self, value):
        self._project = parse_project(value)

    @property
    def is_overdue(self):
        return (self._deadline is not None
                and self._status != "completed"
                and self._deadline < date.today())

    # --- ქცევა
    def _extra_info(self):
        return ""  # შვილობილი კლასი გადაწერს

    def describe(self):
        deadline = self.deadline.isoformat() if self.deadline else "—"
        overdue = " ⚠ ვადაგასულია" if self.is_overdue else ""
        return (f"#{self.id} {STATUS_ICONS[self.status]} [{self.status}] "
                f"{PRIORITY_ICONS[self.priority]} {self.priority} | {self.title} | "
                f"ვადა: {deadline}{overdue} | 📁 {self.project}{self._extra_info()}")

    def spawn_next(self, new_id):
        """ჩვეულებრივ დავალებას გაგრძელება არ აქვს."""
        return None

    # --- JSON-ისთვის (სერიალიზაცია / დესერიალიზაცია)
    def to_dict(self):
        return {
            "type": self.TYPE,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "priority": self.priority,
            "status": self.status,
            "project": self.project,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["id"], data["title"], data.get("description", ""),
                   data.get("deadline"), data.get("priority", "medium"),
                   data.get("status", "pending"), data.get("project", DEFAULT_PROJECT))


class RecurringTask(Task):
    """განმეორებადი დავალება: დასრულებისას ავტომატურად იქმნება შემდეგი."""

    TYPE = "recurring"

    def __init__(self, task_id, title, description="", deadline=None,
                 priority="medium", status="pending", project=DEFAULT_PROJECT,
                 repeat_days=7):
        super().__init__(task_id, title, description, deadline, priority, status, project)
        self.repeat_days = repeat_days

    @property
    def repeat_days(self):
        return self._repeat_days

    @repeat_days.setter
    def repeat_days(self, value):
        self._repeat_days = parse_repeat_days(value)

    def _extra_info(self):
        return f" | 🔁 ყოველ {self.repeat_days} დღეში"

    def spawn_next(self, new_id):  # პოლიმორფიზმი: Task-ზე None იყო, აქ ახალი დავალება
        start = self.deadline or date.today()
        return RecurringTask(new_id, self.title, self.description,
                             start + timedelta(days=self.repeat_days),
                             self.priority, "pending", self.project, self.repeat_days)

    def to_dict(self):
        data = super().to_dict()
        data["repeat_days"] = self.repeat_days
        return data

    @classmethod
    def from_dict(cls, data):
        task = super().from_dict(data)
        task.repeat_days = data.get("repeat_days", 7)
        return task


TASK_TYPES = {Task.TYPE: Task, RecurringTask.TYPE: RecurringTask}


def task_from_dict(data):
    """ფაბრიკა: JSON ჩანაწერიდან სწორი ტიპის ობიექტს ქმნის."""
    if not isinstance(data, dict):
        raise ValueError("ჩანაწერი ობიექტი უნდა იყოს")
    task_class = TASK_TYPES.get(data.get("type", "task"))
    if task_class is None:
        raise ValueError(f"უცნობი ტიპი: {data.get('type')}")
    try:
        return task_class.from_dict(data)
    except KeyError as error:
        raise ValueError(f"ჩანაწერს აკლია ველი {error}") from None
