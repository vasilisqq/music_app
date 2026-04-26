from pydantic import BaseModel


class ProfileStatsResponse(BaseModel):
    completed_lessons_count: int
    started_topics_count: int
    completed_topics_count: int
    average_progress_percent: float
    rating_place: int
    total_users: int
