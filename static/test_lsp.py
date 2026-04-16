from dataclasses import dataclass
from typing import Optional


@dataclass
class Task:
    id: int
    title: str
    completed: bool = False
    description: Optional[str] = None

    def complete(self) -> None:
        self.completed = True


tasks: list[Task] = []


def add_task(title: str, description: str = "") -> Task:
    task = Task(id=len(tasks) + 1, title=title, description=description)
    tasks.append(task)
    return task


def show_pending() -> list[Task]:
    return [t for t in tasks if not t.completed]


add_task("Setup project", "Initialize the repository")
add_task("Write tests")
pending = show_pending()
print(f"Pending: {len(pending)} tasks")

# Error intencional: show_pending no existe con este nombre
print(f"Pending: {len(show_peding())} tasks")
