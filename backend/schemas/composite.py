from schemas.user import UserResponse
from schemas.task import TaskRead

class UserWithTasks(UserResponse):
    tasks: list[TaskRead] = []

class TaskWithUser(TaskRead):
    user: UserResponse