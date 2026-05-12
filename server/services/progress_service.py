from datetime import datetime, timezone

from fastapi import HTTPException
from models import Lesson, LessonProgress, Topic, User
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.profile_stats import ProfileStatsResponse


class ProgressService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_completed_lesson_ids_for_topic(
        self, *, user_id: int, topic_id: int
    ) -> list[int]:
        result = await self.db.execute(
            select(LessonProgress.lesson_id)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(LessonProgress.user_id == user_id)
            .where(Lesson.topic_id == topic_id)
            .where(LessonProgress.completed_at.is_not(None))
        )
        return list(result.scalars().all())

    async def mark_lesson_completed(self, *, user_id: int, lesson_id: int) -> None:
        lesson = await self.db.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Урок не найден")

        result = await self.db.execute(
            select(LessonProgress)
            .where(LessonProgress.user_id == user_id)
            .where(LessonProgress.lesson_id == lesson_id)
        )
        progress = result.scalar_one_or_none()

        if progress is None:
            progress = LessonProgress(user_id=user_id, lesson_id=lesson_id)
            self.db.add(progress)

        if progress.completed_at is None:
            progress.completed_at = datetime.now(timezone.utc)

        await self.db.commit()

    async def get_profile_stats(self, *, user_id: int) -> ProfileStatsResponse:
        total_users = await self.db.scalar(select(func.count(User.id))) or 0
        total_topics = await self.db.scalar(select(func.count(Topic.id))) or 0

        completed_lessons_count = (
            await self.db.scalar(
                select(func.count(LessonProgress.id))
                .where(LessonProgress.user_id == user_id)
                .where(LessonProgress.completed_at.is_not(None))
            )
            or 0
        )

        topic_progress_rows = await self.db.execute(
            select(
                Topic.id,
                func.count(Lesson.id).label("lessons_count"),
                func.count(
                    case(
                        (
                            (LessonProgress.user_id == user_id)
                            & (LessonProgress.completed_at.is_not(None)),
                            Lesson.id,
                        )
                    )
                ).label("completed_lessons_count"),
            )
            .select_from(Topic)
            .outerjoin(Lesson, Lesson.topic_id == Topic.id)
            .outerjoin(LessonProgress, LessonProgress.lesson_id == Lesson.id)
            .group_by(Topic.id)
        )

        topic_totals: dict[int, int] = {}
        started_topics_count = 0
        completed_topics_count = 0
        progress_sum = 0.0

        for topic_id, lessons_count, completed_count in topic_progress_rows.all():
            topic_id = int(topic_id)
            lessons_count = int(lessons_count or 0)
            completed_count = int(completed_count or 0)
            topic_totals[topic_id] = lessons_count

            if completed_count > 0:
                started_topics_count += 1

            if lessons_count > 0 and completed_count >= lessons_count:
                completed_topics_count += 1
                progress_sum += 1.0
            elif lessons_count > 0:
                progress_sum += completed_count / lessons_count

        average_progress_percent = (
            (progress_sum / started_topics_count * 100.0)
            if started_topics_count > 0
            else 0.0
        )

        user_completed_rows = await self.db.execute(
            select(
                User.id,
                Lesson.topic_id,
                func.count(LessonProgress.id).label("completed_lessons_count"),
            )
            .select_from(User)
            .outerjoin(
                LessonProgress,
                (LessonProgress.user_id == User.id)
                & (LessonProgress.completed_at.is_not(None)),
            )
            .outerjoin(Lesson, Lesson.id == LessonProgress.lesson_id)
            .group_by(User.id, Lesson.topic_id)
        )

        ranking_map: dict[int, dict[str, int]] = {
            int(row[0]): {"completed_lessons_count": 0, "completed_topics_count": 0}
            for row in (await self.db.execute(select(User.id))).all()
        }

        for rank_user_id, topic_id, completed_count in user_completed_rows.all():
            rank_user_id = int(rank_user_id)
            completed_count = int(completed_count or 0)
            ranking_map[rank_user_id]["completed_lessons_count"] += completed_count

            if topic_id is not None and completed_count > 0:
                topic_total = int(topic_totals.get(int(topic_id), 0))
                if topic_total > 0 and completed_count >= topic_total:
                    ranking_map[rank_user_id]["completed_topics_count"] += 1

        ranking_data = [
            (
                rank_user_id,
                values["completed_lessons_count"],
                values["completed_topics_count"],
            )
            for rank_user_id, values in ranking_map.items()
        ]
        ranking_data.sort(key=lambda row: (-row[1], -row[2], row[0]))

        rating_place = next(
            (
                index
                for index, (
                    rank_user_id,
                    _completed_lessons,
                    _completed_topics,
                ) in enumerate(ranking_data, start=1)
                if rank_user_id == user_id
            ),
            total_users if total_users > 0 else 1,
        )

        return ProfileStatsResponse(
            completed_lessons_count=int(completed_lessons_count),
            started_topics_count=started_topics_count,
            completed_topics_count=completed_topics_count,
            average_progress_percent=round(float(average_progress_percent), 1),
            rating_place=int(rating_place),
            total_users=int(total_users),
        )
