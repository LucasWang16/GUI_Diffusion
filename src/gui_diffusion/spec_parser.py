from __future__ import annotations

import re

from .models import AppSpec, Component, Screen, Task


DOMAIN_KEYWORDS = {
    "finance": ["expense", "budget", "spend", "invoice", "payment", "记账", "预算", "支出"],
    "todo": ["todo", "task", "kanban", "project", "待办", "任务"],
    "health": ["fitness", "health", "workout", "medication", "健康", "运动"],
    "commerce": ["shop", "cart", "order", "product", "商城", "购物"],
}


def parse_app_description(description: str) -> AppSpec:
    cleaned = " ".join(description.strip().split())
    if not cleaned:
        raise ValueError("description cannot be empty")

    domain = _detect_domain(cleaned)
    app_name = _make_app_name(cleaned, domain)

    if domain == "finance":
        return _finance_spec(app_name, cleaned)
    if domain == "todo":
        return _todo_spec(app_name, cleaned)
    return _generic_spec(app_name, domain, cleaned)


def _detect_domain(description: str) -> str:
    lowered = description.lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword.lower() in lowered)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best_domain, best_score = max(scores.items(), key=lambda item: item[1])
    return best_domain if best_score else "productivity"


def _make_app_name(description: str, domain: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", description)
    if len(words) >= 2:
        return f"{words[0].title()} {words[1].title()}"
    return {
        "finance": "Expense Studio",
        "todo": "Task Studio",
        "health": "Health Studio",
        "commerce": "Shop Studio",
    }.get(domain, "Workflow Studio")


def _finance_spec(app_name: str, description: str) -> AppSpec:
    screens = [
        Screen(
            id="home",
            title="Overview",
            purpose="Show recent spending and entry points.",
            components=[
                Component("title", "heading", app_name, (24, 28, 360, 68)),
                Component("summary_card", "card", "This month: $842", (24, 92, 360, 168)),
                Component("add_expense", "button", "Add expense", (204, 620, 360, 672), target_screen="add_expense"),
                Component("open_stats", "button", "View stats", (24, 620, 188, 672), target_screen="stats"),
            ],
        ),
        Screen(
            id="add_expense",
            title="Add Expense",
            purpose="Collect a new expense.",
            components=[
                Component("amount_input", "textbox", "Amount", (24, 112, 360, 164)),
                Component("merchant_input", "textbox", "Merchant", (24, 184, 360, 236)),
                Component("category_picker", "button", "Choose category", (24, 256, 360, 308), target_screen="category"),
                Component("save_expense", "button", "Save expense", (204, 620, 360, 672), target_screen="confirmation"),
                Component("cancel", "button", "Cancel", (24, 620, 188, 672), target_screen="home"),
            ],
        ),
        Screen(
            id="category",
            title="Category",
            purpose="Pick a spending category.",
            components=[
                Component("food_category", "listitem", "Food", (24, 118, 360, 166), target_screen="add_expense"),
                Component("transport_category", "listitem", "Transport", (24, 178, 360, 226), target_screen="add_expense"),
                Component("shopping_category", "listitem", "Shopping", (24, 238, 360, 286), target_screen="add_expense"),
            ],
        ),
        Screen(
            id="stats",
            title="Statistics",
            purpose="Show spending trends.",
            components=[
                Component("stats_chart", "card", "Food 42% | Transport 18% | Shopping 16%", (24, 116, 360, 268)),
                Component("back_home", "button", "Back", (24, 620, 188, 672), target_screen="home"),
            ],
        ),
        Screen(
            id="confirmation",
            title="Saved",
            purpose="Confirm the expense was saved.",
            components=[
                Component("saved_status", "status", "Expense saved", (24, 132, 360, 188)),
                Component("done", "button", "Done", (204, 620, 360, 672), target_screen="home"),
            ],
        ),
    ]
    tasks = [
        Task(
            id="add_food_expense",
            instruction="Add a $12 coffee expense under Food and save it.",
            start_screen="home",
            success_screen="confirmation",
            success_message="Expense saved",
        ),
        Task(
            id="inspect_stats",
            instruction="Open the statistics view from the overview screen.",
            start_screen="home",
            success_screen="stats",
            success_message="Statistics",
        ),
    ]
    return AppSpec(app_name, "finance", description, ["expense", "category", "budget"], screens, tasks)


def _todo_spec(app_name: str, description: str) -> AppSpec:
    screens = [
        Screen(
            id="home",
            title="Tasks",
            purpose="Show active tasks.",
            components=[
                Component("title", "heading", app_name, (24, 28, 360, 68)),
                Component("task_card", "card", "Review weekly plan", (24, 106, 360, 164)),
                Component("add_task", "button", "Add task", (204, 620, 360, 672), target_screen="add_task"),
            ],
        ),
        Screen(
            id="add_task",
            title="Add Task",
            purpose="Create a new task.",
            components=[
                Component("task_input", "textbox", "Task title", (24, 128, 360, 180)),
                Component("save_task", "button", "Save task", (204, 620, 360, 672), target_screen="confirmation"),
                Component("cancel", "button", "Cancel", (24, 620, 188, 672), target_screen="home"),
            ],
        ),
        Screen(
            id="confirmation",
            title="Saved",
            purpose="Confirm task creation.",
            components=[
                Component("saved_status", "status", "Task saved", (24, 132, 360, 188)),
                Component("done", "button", "Done", (204, 620, 360, 672), target_screen="home"),
            ],
        ),
    ]
    tasks = [
        Task("add_task", "Create a task called Submit report.", "home", "confirmation", "Task saved"),
    ]
    return AppSpec(app_name, "todo", description, ["task", "project"], screens, tasks)


def _generic_spec(app_name: str, domain: str, description: str) -> AppSpec:
    screens = [
        Screen(
            id="home",
            title="Home",
            purpose="Main dashboard.",
            components=[
                Component("title", "heading", app_name, (24, 28, 360, 68)),
                Component("primary_card", "card", "Recent activity", (24, 104, 360, 184)),
                Component("new_item", "button", "New item", (204, 620, 360, 672), target_screen="create"),
            ],
        ),
        Screen(
            id="create",
            title="Create",
            purpose="Create a new item.",
            components=[
                Component("name_input", "textbox", "Name", (24, 128, 360, 180)),
                Component("save_item", "button", "Save", (204, 620, 360, 672), target_screen="confirmation"),
                Component("cancel", "button", "Cancel", (24, 620, 188, 672), target_screen="home"),
            ],
        ),
        Screen(
            id="confirmation",
            title="Saved",
            purpose="Confirm item creation.",
            components=[
                Component("saved_status", "status", "Item saved", (24, 132, 360, 188)),
                Component("done", "button", "Done", (204, 620, 360, 672), target_screen="home"),
            ],
        ),
    ]
    tasks = [
        Task("create_item", "Create a new item called Demo.", "home", "confirmation", "Item saved"),
    ]
    return AppSpec(app_name, domain, description, ["item"], screens, tasks)
