import logging
from datetime import datetime

from atproto import Client
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.config import settings
from app.models import Listener, Post

logger = logging.getLogger(__name__)


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

        logger.info(f"Searching Bluesky for: {search_term}")

        # Search for posts
        response = client.app.bsky.feed.search_posts(
            params={"q": search_term, "limit": 50}
        )

        posts_collected = 0
        for post_view in response.posts:
            try:
                saved = await self._save_post(post_view, listener, session)
                if saved:
                    posts_collected += 1
            except Exception as e:
                logger.error(f"Error saving post {post_view.uri}: {e}")

        return posts_collected

    async def _collect_mention(
        self, client: Client, listener: Listener, session: AsyncSession
    ) -> int:
        """Collect posts mentioning a specific handle."""
        handle = listener.rule_value
        if handle.startswith("@"):
            handle = handle[1:]

        logger.info(f"Searching Bluesky for mentions of: @{handle}")

        # Search for posts mentioning the handle
        response = client.app.bsky.feed.search_posts(
            params={"q": f"@{handle}", "limit": 50}
        )

        posts_collected = 0
        for post_view in response.posts:
            try:
                saved = await self._save_post(post_view, listener, session)
                if saved:
                    posts_collected += 1
            except Exception as e:
                logger.error(f"Error saving post {post_view.uri}: {e}")

        return posts_collected

    async def _save_post(
        self, post_view, listener: Listener, session: AsyncSession
    ) -> bool:
        """
        Save a post to the database, handling duplicates.

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

        result = await session.execute(stmt)
        await session.flush()

        # Check if this was an insert or update
        # rowcount will be 1 for both insert and update with ON CONFLICT
        # We need to check if the row was actually inserted
        return result.rowcount > 0
