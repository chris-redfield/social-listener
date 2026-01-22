import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Post, Entity, PostEntity
from app.nlp.sentiment import analyze_sentiment, SentimentResult
from app.nlp.ner import extract_entities, EntityResult

logger = logging.getLogger(__name__)


@dataclass
class NLPResult:
    sentiment: SentimentResult
    entities: list[EntityResult]
    error: str | None = None


class NLPProcessor:
    """
    NLP Processor for analyzing post content.
    Handles sentiment analysis and named entity recognition.
    """

    async def process_post(self, post: Post, session: AsyncSession) -> bool:
        """
        Process a single post with NLP analysis.

        This method is designed to be failsafe - if NLP fails, it logs the error
        to the post's nlp_error field but doesn't raise an exception.

        Args:
            post: The Post object to process
            session: Database session

        Returns:
            True if processing succeeded, False if it failed
        """
        if not post.content:
            logger.debug(f"Post {post.id} has no content, skipping NLP")
            post.nlp_processed_at = datetime.utcnow()
            return True

        try:
            # Run sentiment analysis
            sentiment = analyze_sentiment(post.content)
            post.sentiment_score = sentiment.score
            post.sentiment_label = sentiment.label

            # Run NER
            entities = extract_entities(post.content)

            # Store entities with deduplication
            await self._store_entities(post, entities, session)

            # Mark as processed
            post.nlp_processed_at = datetime.utcnow()
            post.nlp_error = None

            logger.debug(
                f"Post {post.id} processed: sentiment={sentiment.label}, "
                f"entities={len(entities)}"
            )
            return True

        except Exception as e:
            error_msg = f"NLP processing failed: {str(e)}"
            logger.error(f"Post {post.id}: {error_msg}")
            post.nlp_error = error_msg
            post.nlp_processed_at = datetime.utcnow()
            return False

    async def _store_entities(
        self,
        post: Post,
        entities: list[EntityResult],
        session: AsyncSession
    ) -> None:
        """
        Store entities with deduplication.

        For each entity:
        1. Check if it already exists in the entities table (by type + normalized text)
        2. If not, create it
        3. Create the post_entity junction record
        """
        for entity_result in entities:
            # Upsert entity (insert or get existing)
            entity_id = await self._get_or_create_entity(
                entity_type=entity_result.entity_type,
                entity_text=entity_result.normalized_text,
                display_text=entity_result.text,
                session=session,
            )

            # Create post_entity junction record
            # Using insert with on_conflict_do_nothing to handle duplicates
            stmt = insert(PostEntity).values(
                post_id=post.id,
                entity_id=entity_id,
                confidence=entity_result.confidence,
                start_pos=entity_result.start_pos,
                end_pos=entity_result.end_pos,
            )
            stmt = stmt.on_conflict_do_nothing(
                constraint="uq_post_entity_pos"
            )
            await session.execute(stmt)

    async def _get_or_create_entity(
        self,
        entity_type: str,
        entity_text: str,
        display_text: str,
        session: AsyncSession,
    ) -> int:
        """
        Get existing entity or create new one.

        Uses PostgreSQL upsert to handle race conditions.

        Returns:
            The entity ID
        """
        # Try to insert, on conflict return existing
        stmt = insert(Entity).values(
            entity_type=entity_type,
            entity_text=entity_text,
            display_text=display_text,
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_entity_type_text"
        )
        await session.execute(stmt)
        await session.flush()

        # Now fetch the entity (either just inserted or existing)
        result = await session.execute(
            select(Entity).where(
                Entity.entity_type == entity_type,
                Entity.entity_text == entity_text,
            )
        )
        entity = result.scalar_one()
        return entity.id

    async def process_posts_batch(
        self,
        posts: list[Post],
        session: AsyncSession
    ) -> tuple[int, int]:
        """
        Process multiple posts.

        Args:
            posts: List of Post objects to process
            session: Database session

        Returns:
            Tuple of (success_count, error_count)
        """
        success_count = 0
        error_count = 0

        for post in posts:
            if await self.process_post(post, session):
                success_count += 1
            else:
                error_count += 1

        return success_count, error_count


# Global processor instance
nlp_processor = NLPProcessor()
