import logging
from datetime import datetime

from atproto import Client
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.config import settings
from app.models import Listener, Post
from app.nlp.processor import nlp_processor

logger = logging.getLogger(__name__)

# Pagination settings
INITIAL_SCRAPE_MAX_POSTS = 500  # Max posts to fetch on first scrape (uses pagination)
REGULAR_SCRAPE_LIMIT = 100      # Posts per regular scrape (no pagination, API max is 100)
PAGE_SIZE = 100                  # Posts per page when paginating


class BlueskyCollector(BaseCollector):
    """Collector for Bluesky posts using the AT Protocol."""

    platform = "bluesky"

    def __init__(self):
        self._client: Client | None = None

    def _get_client(self) -> Client:
        """Get or create an authenticated Bluesky client."""
        if self._client is None:
            self._client = Client()
            self._client.login(settings.bluesky_handle, settings.bluesky_app_password)
        return self._client

    async def is_configured(self) -> bool:
        """Check if Bluesky credentials are configured."""
        return bool(settings.bluesky_handle and settings.bluesky_app_password)

    async def test_connection(self) -> bool:
        """Test connection to Bluesky API."""
        try:
            client = self._get_client()
            # Try to get our own profile as a connection test
            profile = client.get_profile(settings.bluesky_handle)
            logger.info(f"Connected as: {profile.display_name} (@{profile.handle})")
            return True
        except Exception as e:
            logger.error(f"Bluesky connection test failed: {e}")
            return False

    async def collect(self, listener: Listener, session: AsyncSession) -> int:
        """
        Collect posts matching the listener's rule.

        Args:
            listener: The listener configuration
            session: Database session

        Returns:
            Number of new posts collected
        """
        if not await self.is_configured():
            logger.warning("Bluesky not configured, skipping collection")
            return 0

        client = self._get_client()
        posts_collected = 0

        try:
            if listener.rule_type == "keyword":
                posts_collected = await self._collect_keyword(client, listener, session)
            elif listener.rule_type == "mention":
                posts_collected = await self._collect_mention(client, listener, session)
            elif listener.rule_type == "hashtag":
                # Hashtags are just keywords with # prefix
                posts_collected = await self._collect_keyword(client, listener, session)
            else:
                logger.warning(f"Unknown rule type: {listener.rule_type}")

        except Exception as e:
            logger.error(f"Error collecting for listener {listener.id}: {e}")
            raise

        return posts_collected

    async def _collect_keyword(
        self, client: Client, listener: Listener, session: AsyncSession
    ) -> int:
        """Collect posts matching a keyword search."""
        search_term = listener.rule_value
        if listener.rule_type == "hashtag" and not search_term.startswith("#"):
            search_term = f"#{search_term}"

        # Determine if this is initial scrape or regular scrape
        is_initial = not listener.initial_scrape_completed
        max_posts = INITIAL_SCRAPE_MAX_POSTS if is_initial else REGULAR_SCRAPE_LIMIT
        use_pagination = is_initial

        logger.info(
            f"Searching Bluesky for: {search_term} "
            f"({'initial scrape, max ' + str(max_posts) + ' posts' if is_initial else 'regular scrape'})"
        )

        posts_collected = 0
        cursor = None

        while posts_collected < max_posts:
            # Calculate limit for this page
            remaining = max_posts - posts_collected
            limit = min(PAGE_SIZE, remaining)

            # Search for posts
            params = {"q": search_term, "limit": limit}
            if cursor:
                params["cursor"] = cursor

            response = client.app.bsky.feed.search_posts(params=params)

            if not response.posts:
                break

            for post_view in response.posts:
                try:
                    saved = await self._save_post(post_view, listener, session)
                    if saved:
                        posts_collected += 1
                except Exception as e:
                    logger.error(f"Error saving post {post_view.uri}: {e}")

            # Check if we should continue paginating
            cursor = getattr(response, 'cursor', None)
            if not use_pagination or not cursor:
                break

            logger.info(f"Fetched {posts_collected} posts so far, continuing pagination...")

        # Mark initial scrape as completed
        if is_initial and posts_collected > 0:
            listener.initial_scrape_completed = True
            await session.flush()
            logger.info(f"Initial scrape completed for listener {listener.id}, collected {posts_collected} posts")

        return posts_collected

    async def _collect_mention(
        self, client: Client, listener: Listener, session: AsyncSession
    ) -> int:
        """Collect posts mentioning a specific handle."""
        handle = listener.rule_value
        if handle.startswith("@"):
            handle = handle[1:]

        # Determine if this is initial scrape or regular scrape
        is_initial = not listener.initial_scrape_completed
        max_posts = INITIAL_SCRAPE_MAX_POSTS if is_initial else REGULAR_SCRAPE_LIMIT
        use_pagination = is_initial

        logger.info(
            f"Searching Bluesky for mentions of: @{handle} "
            f"({'initial scrape, max ' + str(max_posts) + ' posts' if is_initial else 'regular scrape'})"
        )

        posts_collected = 0
        cursor = None

        while posts_collected < max_posts:
            # Calculate limit for this page
            remaining = max_posts - posts_collected
            limit = min(PAGE_SIZE, remaining)

            # Search for posts mentioning the handle
            params = {"q": f"@{handle}", "limit": limit}
            if cursor:
                params["cursor"] = cursor

            response = client.app.bsky.feed.search_posts(params=params)

            if not response.posts:
                break

            for post_view in response.posts:
                try:
                    saved = await self._save_post(post_view, listener, session)
                    if saved:
                        posts_collected += 1
                except Exception as e:
                    logger.error(f"Error saving post {post_view.uri}: {e}")

            # Check if we should continue paginating
            cursor = getattr(response, 'cursor', None)
            if not use_pagination or not cursor:
                break

            logger.info(f"Fetched {posts_collected} posts so far, continuing pagination...")

        # Mark initial scrape as completed
        if is_initial and posts_collected > 0:
            listener.initial_scrape_completed = True
            await session.flush()
            logger.info(f"Initial scrape completed for listener {listener.id}, collected {posts_collected} posts")

        return posts_collected

    async def _save_post(
        self, post_view, listener: Listener, session: AsyncSession
    ) -> bool:
        """
        Save a post to the database and run NLP processing.

        NLP processing is failsafe - errors are logged but don't break the pipeline.

        Returns:
            True if post was newly inserted, False if it already existed
        """
        # Extract post ID from URI (format: at://did:plc:xxx/app.bsky.feed.post/xxx)
        platform_post_id = post_view.uri

        # Extract author info
        author = post_view.author
        author_handle = author.handle
        author_display_name = author.display_name
        author_avatar_url = author.avatar

        # Extract post content
        record = post_view.record
        content = record.text if hasattr(record, "text") else None

        # Build post URL
        # Format: https://bsky.app/profile/{handle}/post/{post_id}
        post_rkey = post_view.uri.split("/")[-1]
        post_url = f"https://bsky.app/profile/{author_handle}/post/{post_rkey}"

        # Extract engagement metrics
        likes_count = post_view.like_count or 0
        replies_count = post_view.reply_count or 0
        reposts_count = post_view.repost_count or 0
        quotes_count = post_view.quote_count or 0 if hasattr(post_view, "quote_count") else 0

        # Parse post creation time (strip timezone for naive datetime storage)
        post_created_at = None
        if hasattr(record, "created_at"):
            try:
                dt = datetime.fromisoformat(record.created_at.replace("Z", "+00:00"))
                # Convert to naive UTC datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
                post_created_at = dt.replace(tzinfo=None)
            except Exception:
                pass

        # Check if post already exists (to determine if we need to run NLP)
        existing = await session.execute(
            select(Post).where(
                Post.platform == "bluesky",
                Post.platform_post_id == platform_post_id,
            )
        )
        existing_post = existing.scalar_one_or_none()
        is_new_post = existing_post is None

        # Use PostgreSQL upsert to handle duplicates
        stmt = insert(Post).values(
            listener_id=listener.id,
            platform="bluesky",
            platform_post_id=platform_post_id,
            author_handle=author_handle,
            author_display_name=author_display_name,
            author_avatar_url=author_avatar_url,
            content=content,
            post_url=post_url,
            likes_count=likes_count,
            replies_count=replies_count,
            reposts_count=reposts_count,
            quotes_count=quotes_count,
            post_created_at=post_created_at,
            collected_at=datetime.utcnow(),
        )

        # On conflict, update engagement metrics (they may have changed)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_platform_post",
            set_={
                "likes_count": stmt.excluded.likes_count,
                "replies_count": stmt.excluded.replies_count,
                "reposts_count": stmt.excluded.reposts_count,
                "quotes_count": stmt.excluded.quotes_count,
            },
        )

        await session.execute(stmt)
        await session.flush()

        # Run NLP processing for new posts only
        if is_new_post:
            # Fetch the post we just inserted
            result = await session.execute(
                select(Post).where(
                    Post.platform == "bluesky",
                    Post.platform_post_id == platform_post_id,
                )
            )
            post = result.scalar_one()

            # Process with NLP (failsafe - won't raise exceptions)
            try:
                await nlp_processor.process_post(post, session)
                await session.flush()
            except Exception as e:
                # This shouldn't happen as process_post is failsafe,
                # but just in case, log and continue
                logger.error(f"Unexpected NLP error for post {post.id}: {e}")
                post.nlp_error = f"Unexpected error: {str(e)}"

        return is_new_post
