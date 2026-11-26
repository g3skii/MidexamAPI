"""main.py — კონსოლის ინტერფეისი. გაშვება: python main.py"""
import os
import sys
from pathlib import Path

from decorators import confirm, handle_errors
from exceptions import StorageError
from manager import TaskManager
from models import (DEFAULT_PROJECT, parse_deadline, parse_description, parse_priority,
                    parse_project, parse_repeat_days, parse_status, parse_title)
from storage import JsonStorage

DATA_FILE = Path(os.environ.get("TASKS_FILE", Path(__file__).with_name("tasks.json")))


def ask(prompt, parser, default=None):
    """სვამს კითხვას, სანამ parser-ი სწორ მნიშვნელობას არ მიიღებს.
    default — რას დაუბრუნებს, თუ მომხმარებელმა უბრალოდ Enter დააჭირა."""
    hint = f" [{default}]" if default else ""
    while True:
        raw = input(f"{prompt}{hint}: ").strip()
        if raw == "" and default is not None:
            raw = default
        try:
            return parser(raw)
        except ValueError as error:
            print(f"❌ {error}")


def parse_id(text):
    try:
        return int(text)
    except ValueError:
        raise ValueError("ID მთელი რიცხვი უნდა იყოს") from None


def optional_status(text):
    return parse_status(text) if text else None


def optional_repeat(text):
    return parse_repeat_days(text) if text else None


def deadline_or_clear(text):
    return None if text == "-" else parse_deadline(text)


def non_empty(text):
    if not text:
        raise ValueError("ველი ცარიელი ვერ იქნება")
    return text


def print_tasks(tasks, heading):
    print(f"\n=== {heading} ({len(tasks)}) ===")
    if not tasks:
        print("  (ცარიელია)")
    for task in tasks:
        print(" ", task.describe())
        if task.description:
            print("     └", task.description)


class TaskApp:
    def __init__(self, manager):
        self.manager = manager
        self.actions = {
            "1": self.add_task,
            "2": self.list_tasks,
            "3": self.search_tasks,
            "4": self.edit_task,
            "5": self.change_status,
            "6": self.delete_task,
            "7": self.show_projects,
        }

    @handle_errors
    def add_task(self):
        title = ask("სათაური", parse_title)
        description = ask("აღწერა (Enter — გამოტოვება)", parse_description, default="")
        deadline = ask("ვადა YYYY-MM-DD (Enter — გამოტოვება)", parse_deadline, default="")
        priority = ask("პრიორიტეტი (low/medium/high)", parse_priority, default="medium")
        project = ask("პროექტი", parse_project, default=DEFAULT_PROJECT)
        repeat = ask("გამეორება დღეებში (Enter — არ მეორდება)", optional_repeat, default="")
        task = self.manager.add_task(title, description, deadline, priority, project, repeat)
        print("✅ დაემატა:", task.describe())

    @handle_errors
    def list_tasks(self):
        status = ask("სტატუსი (pending/in-progress/completed, Enter — ყველა)",
                     optional_status, default="")
        print_tasks(self.manager.list_tasks(status), "დავალებები")

    @handle_errors
    def search_tasks(self):
        text = ask("საძიებო სიტყვა", non_empty)
        print_tasks(self.manager.search(text), f"ძებნა: '{text}'")

    @handle_errors
    def edit_task(self):
        task = self.manager.get(ask("რედაქტირებადი დავალების ID", parse_id))
        print("მიმდინარე:", task.describe())
        print("(Enter — მიმდინარე მნიშვნელობის დატოვება)")
        current_deadline = task.deadline.isoformat() if task.deadline else ""
        changes = {
            "title": ask("სათაური", parse_title, default=task.title),
            "description": ask("აღწერა", parse_description, default=task.description),
            "deadline": ask("ვადა ('-' — წასაშლელად)", deadline_or_clear,
                            default=current_deadline),
            "priority": ask("პრიორიტეტი", parse_priority, default=task.priority),
            "project": ask("პროექტი", parse_project, default=task.project),
        }
        self.manager.update(task.id, **changes)
        print("✅ განახლდა:", task.describe())

    @handle_errors
    def change_status(self):
        task_id = ask("დავალების ID", parse_id)
        status = ask("ახალი სტატუსი (pending/in-progress/completed)", parse_status)
        task, next_task = self.manager.change_status(task_id, status)
        print("✅", task.describe())
        if next_task:
            print("🔁 შეიქმნა შემდეგი განმეორება:", next_task.describe())

    @handle_errors
    def delete_task(self):
        task = self.manager.get(ask("წასაშლელი დავალების ID", parse_id))
        self._delete_confirmed(task)

    @confirm("ნამდვილად წავშალო?")
    def _delete_confirmed(self, task):
        self.manager.delete(task.id)
        print(f"🗑 წაიშალა: {task.title}")

    @handle_errors
    def show_projects(self):
        groups = self.manager.by_project()
        if not groups:
            print("დავალებები არ არის")
        for project, tasks in groups.items():
            done = sum(1 for t in tasks if t.status == "completed")
            print_tasks(tasks, f"📁 {project} — დასრულებული {done}/{len(tasks)}")

    def run(self):
        print("📋 პერსონალური Task Manager")
        if self.manager.load_warning:
            print("⚠", self.manager.load_warning)
        try:
            while True:
                print("\n1 დამატება | 2 სია | 3 ძებნა | 4 რედაქტირება | 5 სტატუსი | "
                      "6 წაშლა | 7 პროექტები | 0 გასვლა")
                choice = input("არჩევანი: ").strip()
                if choice == "0":
                    break
                action = self.actions.get(choice)
                if action is None:
                    print("❌ აირჩიეთ 0-დან 7-მდე")
                    continue
                action()
        except (KeyboardInterrupt, EOFError):
            print()
        finally:
            self._save_on_exit()  

    def _save_on_exit(self):
        try:
            self.manager.save()
            print("💾 მონაცემები შენახულია. ნახვამდის!")
        except (StorageError, OSError) as error:
            print(f"❌ შენახვა ვერ მოხერხდა: {error}")


def main():
    for stream in (sys.stdout, sys.stdin):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    manager = TaskManager(JsonStorage(DATA_FILE))
    try:
        manager.load()
    except StorageError as error:
        print(f"❌ {error}")
        sys.exit(1)
    TaskApp(manager).run()


if __name__ == "__main__":
    main()
