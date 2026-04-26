from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Lesson, LessonProgress, Topic, User
from schemas.admin_stats import (
    AdminStatsResponse,
    AdminStatsSummary,
    CoursePopularityRow,
    CourseProgressRow,
    TimelinePoint,
)


class AdminStatsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(self, period_days: int) -> AdminStatsResponse:
        if period_days not in {7, 30, 90}:
            raise HTTPException(status_code=400, detail="Поддерживаются периоды 7, 30 или 90 дней")

        now = datetime.now(timezone.utc)
        start_dt = now - timedelta(days=period_days - 1)
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        total_courses = await self.db.scalar(select(func.count(Topic.id))) or 0
        total_lessons = await self.db.scalar(select(func.count(Lesson.id))) or 0
        total_users = await self.db.scalar(select(func.count(User.id))) or 0
        active_users = await self.db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0

        completions_in_period = await self.db.scalar(
            select(func.count(LessonProgress.id)).where(LessonProgress.completed_at >= start_dt)
        ) or 0

        popularity = await self._get_popularity_rows(start_dt)
        course_progress = await self._get_course_progress_rows()
        timeline = await self._get_timeline_rows(start_dt, period_days)

        completed_courses = sum(1 for row in course_progress if row.reached_100 > 0)
        avg_course_progress = (
            sum(row.average_progress for row in course_progress) / len(course_progress)
            if course_progress
            else 0.0
        )

        return AdminStatsResponse(
            period_days=period_days,
            summary=AdminStatsSummary(
                total_courses=int(total_courses),
                total_lessons=int(total_lessons),
                total_users=int(total_users),
                active_users=int(active_users),
                completions_in_period=int(completions_in_period),
                avg_course_progress=float(avg_course_progress),
                completed_courses=int(completed_courses),
            ),
            popularity=popularity,
            course_progress=course_progress,
            timeline=timeline,
        )

    async def _get_popularity_rows(self, start_dt: datetime) -> list[CoursePopularityRow]:
        result = await self.db.execute(
            select(
                Topic.id,
                Topic.name,
                func.count(LessonProgress.id).label("completions_count"),
            )
            .select_from(Topic)
            .outerjoin(Lesson, Lesson.topic_id == Topic.id)
            .outerjoin(
                LessonProgress,
                (LessonProgress.lesson_id == Lesson.id)
                & (LessonProgress.completed_at.is_not(None))
                & (LessonProgress.completed_at >= start_dt),
            )
            .group_by(Topic.id, Topic.name)
            .order_by(func.count(LessonProgress.id).desc(), Topic.name.asc())
        )

        rows = result.all()
        return [
            CoursePopularityRow(
                topic_id=int(topic_id),
                topic_name=topic_name,
                completions_count=int(completions_count or 0),
            )
            for topic_id, topic_name, completions_count in rows
        ]

    async def _get_course_progress_rows(self) -> list[CourseProgressRow]:
        topic_rows = await self.db.execute(
            select(Topic.id, Topic.name, func.count(Lesson.id).label("lessons_count"))
            .select_from(Topic)
            .outerjoin(Lesson, Lesson.topic_id == Topic.id)
            .group_by(Topic.id, Topic.name)
            .order_by(Topic.name.asc())
        )
        topics = topic_rows.all()

        progress_rows = await self.db.execute(
            select(
                Topic.id,
                Topic.name,
                LessonProgress.user_id,
                func.count(LessonProgress.id).label("completed_count"),
            )
            .select_from(Topic)
            .join(Lesson, Lesson.topic_id == Topic.id)
            .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
            .where(LessonProgress.completed_at.is_not(None))
            .group_by(Topic.id, Topic.name, LessonProgress.user_id)
        )

        progress_map: dict[int, list[int]] = {}
        for topic_id, _topic_name, _user_id, completed_count in progress_rows.all():
            progress_map.setdefault(int(topic_id), []).append(int(completed_count or 0))

        rows: list[CourseProgressRow] = []
        for topic_id, topic_name, lessons_count in topics:
            topic_id = int(topic_id)
            lessons_count = int(lessons_count or 0)
            completed_values = progress_map.get(topic_id, [])

            percentages = [
                completed_count / lessons_count
                for completed_count in completed_values
                if lessons_count > 0
            ]

            average_progress = sum(percentages) / len(percentages) if percentages else 0.0
            reached_25 = sum(1 for value in percentages if value >= 0.25)
            reached_50 = sum(1 for value in percentages if value >= 0.50)
            reached_75 = sum(1 for value in percentages if value >= 0.75)
            reached_100 = sum(1 for value in percentages if value >= 1.0)

            rows.append(
                CourseProgressRow(
                    topic_id=topic_id,
                    topic_name=topic_name,
                    lessons_count=lessons_count,
                    average_progress=float(average_progress),
                    learners_started=len(completed_values),
                    reached_25=reached_25,
                    reached_50=reached_50,
                    reached_75=reached_75,
                    reached_100=reached_100,
                )
            )

        return rows

    async def _get_timeline_rows(self, start_dt: datetime, period_days: int) -> list[TimelinePoint]:
        result = await self.db.execute(
            select(
                func.date(LessonProgress.completed_at).label("day"),
                func.count(LessonProgress.id).label("completions_count"),
            )
            .where(LessonProgress.completed_at.is_not(None))
            .where(LessonProgress.completed_at >= start_dt)
            .group_by(func.date(LessonProgress.completed_at))
            .order_by(func.date(LessonProgress.completed_at))
        )

        counts_by_day = {
            day: int(completions_count or 0)
            for day, completions_count in result.all()
            if day is not None
        }

        timeline: list[TimelinePoint] = []
        start_day = start_dt.date()
        for offset in range(period_days):
            current_day = start_day + timedelta(days=offset)
            timeline.append(
                TimelinePoint(
                    day=current_day,
                    label=current_day.strftime("%d.%m"),
                    completions_count=counts_by_day.get(current_day, 0),
                )
            )

        return timeline
