"""Pub/Sub service for managing topics and subscriptions."""

import asyncio
from typing import Any, cast

from googleapiclient import discovery

from sequel.cache.memory import get_cache
from sequel.config import get_config
from sequel.models.pubsub import Subscription, Topic
from sequel.services.auth import get_auth_manager
from sequel.services.base import BaseService
from sequel.utils.logging import get_logger

logger = get_logger(__name__)


class PubSubService(BaseService):
    """Service for interacting with Google Cloud Pub/Sub API."""

    def __init__(self) -> None:
        """Initialize PubSub service."""
        super().__init__()
        self._client: Any | None = None
        self._cache = get_cache()

    async def _get_client(self) -> Any:
        """Get or create Pub/Sub API client.

        Returns:
            Pub/Sub API client
        """
        if self._client is None:
            auth_manager = await get_auth_manager()
            self._client = discovery.build(
                "pubsub",
                "v1",
                credentials=auth_manager.credentials,
                cache_discovery=False,
            )
        return self._client

    async def list_topics(
        self, project_id: str, use_cache: bool = True
    ) -> list[Topic]:
        """List all topics in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of Topic instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"pubsub:topics:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} topics from cache")
                return cast("list[Topic]", cached)

        async def _list_topics() -> list[Topic]:
            """Internal function to list topics."""
            client = await self._get_client()

            logger.info(f"Listing Pub/Sub topics in project: {project_id}")

            try:
                # Format: projects/{project}
                project_path = f"projects/{project_id}"

                topics: list[Topic] = []
                next_page_token = None

                # Handle pagination
                while True:
                    # Call the API with pagination token
                    request = client.projects().topics().list(
                        project=project_path,
                        pageToken=next_page_token
                    )
                    # Run blocking execute() in thread to avoid blocking event loop
                    response = await asyncio.to_thread(request.execute)

                    # Process topics from this page
                    for item in response.get("topics", []):
                        topic = Topic.from_api_response(item)
                        topics.append(topic)
                        logger.debug(f"Loaded topic: {topic.topic_name}")

                    # Check for more pages
                    next_page_token = response.get("nextPageToken")
                    if not next_page_token:
                        break

                    logger.debug(f"Fetching next page of topics (current count: {len(topics)})")

                logger.info(f"Found {len(topics)} topics")
                return topics

            except Exception as e:
                logger.error(f"Failed to list topics: {e}")
                # Return empty list instead of raising for API not enabled case
                return []

        # Execute with retry logic
        topics = await self._execute_with_retry(
            operation=_list_topics,
            operation_name=f"list_topics({project_id})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            topics,
            ttl=config.cache_ttl_resources,
        )

        return topics

    async def list_subscriptions(
        self, project_id: str, use_cache: bool = True
    ) -> list[Subscription]:
        """List all subscriptions in a project.

        Args:
            project_id: GCP project ID
            use_cache: Whether to use cached results

        Returns:
            List of Subscription instances

        Raises:
            AuthError: If authentication fails
            PermissionError: If user lacks permission
            ServiceError: If API call fails
        """
        cache_key = f"pubsub:subscriptions:{project_id}"

        # Check cache first
        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.info(f"Returning {len(cached)} subscriptions from cache")
                return cast("list[Subscription]", cached)

        async def _list_subscriptions() -> list[Subscription]:
            """Internal function to list subscriptions."""
            client = await self._get_client()

            logger.info(f"Listing Pub/Sub subscriptions in project: {project_id}")

            try:
                # Format: projects/{project}
                project_path = f"projects/{project_id}"

                subscriptions: list[Subscription] = []
                next_page_token = None

                # Handle pagination
                while True:
                    # Call the API with pagination token
                    request = client.projects().subscriptions().list(
                        project=project_path,
                        pageToken=next_page_token
                    )
                    # Run blocking execute() in thread to avoid blocking event loop
                    response = await asyncio.to_thread(request.execute)

                    # Process subscriptions from this page
                    for item in response.get("subscriptions", []):
                        subscription = Subscription.from_api_response(item)
                        subscriptions.append(subscription)
                        logger.debug(
                            f"Loaded subscription: {subscription.subscription_name} -> "
                            f"topic: {subscription.topic_name}"
                        )

                    # Check for more pages
                    next_page_token = response.get("nextPageToken")
                    if not next_page_token:
                        break

                    logger.debug(f"Fetching next page of subscriptions (current count: {len(subscriptions)})")

                logger.info(f"Found {len(subscriptions)} subscriptions")
                return subscriptions

            except Exception as e:
                logger.error(f"Failed to list subscriptions: {e}")
                # Return empty list instead of raising for API not enabled case
                return []

        # Execute with retry logic
        subscriptions = await self._execute_with_retry(
            operation=_list_subscriptions,
            operation_name=f"list_subscriptions({project_id})",
        )

        # Cache the results
        config = get_config()
        await self._cache.set(
            cache_key,
            subscriptions,
            ttl=config.cache_ttl_resources,
        )

        return subscriptions


# Singleton instance
_pubsub_service: PubSubService | None = None


async def get_pubsub_service() -> PubSubService:
    """Get the singleton PubSubService instance.

    Returns:
        PubSubService instance
    """
    global _pubsub_service
    if _pubsub_service is None:
        _pubsub_service = PubSubService()
    return _pubsub_service
