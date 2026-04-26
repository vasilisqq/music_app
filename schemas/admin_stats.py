from datetime import date

from pydantic import BaseModel


class AdminStatsSummary(BaseModel):
    total_courses: int
    total_lessons: int
    total_users: int
    active_users: int
    completions_in_period: int
    avg_course_progress: float
    completed_courses: int


class CoursePopularityRow(BaseModel):
    topic_id: int
    topic_name: str
    completions_count: int


class CourseProgressRow(BaseModel):
    topic_id: int
    topic_name: str
    lessons_count: int
    average_progress: float
    learners_started: int
    reached_25: int
    reached_50: int
    reached_75: int
    reached_100: int


class TimelinePoint(BaseModel):
    day: date
    label: str
    completions_count: int


class AdminStatsResponse(BaseModel):
    period_days: int
    summary: AdminStatsSummary
    popularity: list[CoursePopularityRow]
    course_progress: list[CourseProgressRow]
    timeline: list[TimelinePoint]
