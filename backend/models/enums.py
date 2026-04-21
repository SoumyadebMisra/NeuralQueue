import enum

class TaskStatus(enum.Enum):
    QUEUED = "queued"
    SCORING = "scoring"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskType(enum.Enum):
    INFERENCE = "inference"
    TRAINING = "training"
    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"
    IMAGE_PROCESSING = "image_processing"

class TaskPriority(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class AttachmentType(enum.Enum):
    LINK = "link"
    FILE = "file"
    PHOTO = "photo"