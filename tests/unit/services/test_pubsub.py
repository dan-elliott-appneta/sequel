"""Unit tests for Pub/Sub service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.pubsub import Subscription, Topic
from sequel.services.pubsub import (
    PubSubService,
    get_pubsub_service,
)


@pytest.fixture
def mock_credentials() -> MagicMock:
    """Create mock credentials."""
    creds = MagicMock()
    creds.valid = True
    return creds


@pytest.fixture
def mock_auth_manager(mock_credentials: MagicMock) -> AsyncMock:
    """Create mock auth manager."""
    manager = AsyncMock()
    manager.credentials = mock_credentials
    manager.project_id = "test-project"
    return manager


@pytest.fixture
def mock_pubsub_client() -> MagicMock:
    """Create mock Pub/Sub API client."""
    return MagicMock()


@pytest.fixture
def pubsub_service() -> PubSubService:
    """Create PubSub service instance."""
    return PubSubService()


class TestPubSubService:
    """Tests for PubSubService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, pubsub_service: PubSubService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Pub/Sub client."""
        with (
            patch("sequel.services.pubsub.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.pubsub.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await pubsub_service._get_client()

            mock_build.assert_called_once_with(
                "pubsub",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert pubsub_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, pubsub_service: PubSubService
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        pubsub_service._client = mock_client

        client = await pubsub_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_topics_success(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test listing topics successfully."""
        mock_response = {
            "topics": [
                {
                    "name": "projects/test-project/topics/topic-1",
                    "labels": {"env": "prod"},
                },
                {
                    "name": "projects/test-project/topics/topic-2",
                    "messageRetentionDuration": "86400s",
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_pubsub_client.projects().topics().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        topics = await pubsub_service.list_topics("test-project", use_cache=False)

        assert len(topics) == 2
        assert isinstance(topics[0], Topic)
        assert topics[0].topic_name == "topic-1"
        assert topics[0].labels_count == 1
        assert topics[1].topic_name == "topic-2"

    @pytest.mark.asyncio
    async def test_list_topics_empty(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test listing topics when none exist."""
        mock_response: dict[str, Any] = {"topics": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_pubsub_client.projects().topics().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        topics = await pubsub_service.list_topics("test-project", use_cache=False)

        assert len(topics) == 0

    @pytest.mark.asyncio
    async def test_list_topics_no_topics_key(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test listing topics when response has no topics key."""
        mock_response: dict[str, Any] = {}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_pubsub_client.projects().topics().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        topics = await pubsub_service.list_topics("test-project", use_cache=False)

        assert len(topics) == 0

    @pytest.mark.asyncio
    async def test_list_topics_error(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test error handling when listing topics."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_pubsub_client.projects().topics().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        topics = await pubsub_service.list_topics("test-project", use_cache=False)

        # Should return empty list on error
        assert len(topics) == 0

    @pytest.mark.asyncio
    async def test_list_topics_with_cache(
        self, pubsub_service: PubSubService
    ) -> None:
        """Test listing topics with caching."""
        mock_topic = Topic(
            id="cached-topic",
            name="cached-topic",
            topic_name="cached-topic",
        )

        with patch.object(pubsub_service._cache, "get", return_value=[mock_topic]):
            topics = await pubsub_service.list_topics("test-project", use_cache=True)

            assert len(topics) == 1
            assert topics[0] == mock_topic

    @pytest.mark.asyncio
    async def test_list_topics_caching(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test that results are cached."""
        mock_response = {
            "topics": [
                {
                    "name": "projects/test-project/topics/test-topic",
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_pubsub_client.projects().topics().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        with patch.object(pubsub_service._cache, "set") as mock_set:
            await pubsub_service.list_topics("test-project", use_cache=False)

            # Verify cache.set was called
            mock_set.assert_called_once()
            # First argument should be cache key
            assert mock_set.call_args[0][0] == "pubsub:topics:test-project"
            # Second argument should be the topics list
            assert len(mock_set.call_args[0][1]) == 1

    @pytest.mark.asyncio
    async def test_list_subscriptions_success(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test listing subscriptions successfully."""
        mock_response = {
            "subscriptions": [
                {
                    "name": "projects/test-project/subscriptions/sub-1",
                    "topic": "projects/test-project/topics/topic-1",
                    "ackDeadlineSeconds": 10,
                },
                {
                    "name": "projects/test-project/subscriptions/sub-2",
                    "topic": "projects/test-project/topics/topic-2",
                    "pushConfig": {
                        "pushEndpoint": "https://example.com/push",
                    },
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_pubsub_client.projects().subscriptions().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        subscriptions = await pubsub_service.list_subscriptions("test-project", use_cache=False)

        assert len(subscriptions) == 2
        assert isinstance(subscriptions[0], Subscription)
        assert subscriptions[0].subscription_name == "sub-1"
        assert subscriptions[0].topic_name == "topic-1"
        assert subscriptions[1].subscription_name == "sub-2"
        assert subscriptions[1].is_push() is True

    @pytest.mark.asyncio
    async def test_list_subscriptions_empty(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test listing subscriptions when none exist."""
        mock_response: dict[str, Any] = {"subscriptions": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_pubsub_client.projects().subscriptions().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        subscriptions = await pubsub_service.list_subscriptions("test-project", use_cache=False)

        assert len(subscriptions) == 0

    @pytest.mark.asyncio
    async def test_list_subscriptions_no_subscriptions_key(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test listing subscriptions when response has no subscriptions key."""
        mock_response: dict[str, Any] = {}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_pubsub_client.projects().subscriptions().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        subscriptions = await pubsub_service.list_subscriptions("test-project", use_cache=False)

        assert len(subscriptions) == 0

    @pytest.mark.asyncio
    async def test_list_subscriptions_error(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test error handling when listing subscriptions."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_pubsub_client.projects().subscriptions().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        subscriptions = await pubsub_service.list_subscriptions("test-project", use_cache=False)

        # Should return empty list on error
        assert len(subscriptions) == 0

    @pytest.mark.asyncio
    async def test_list_subscriptions_with_cache(
        self, pubsub_service: PubSubService
    ) -> None:
        """Test listing subscriptions with caching."""
        mock_subscription = Subscription(
            id="cached-sub",
            name="cached-sub",
            subscription_name="cached-sub",
            topic_name="test-topic",
        )

        with patch.object(pubsub_service._cache, "get", return_value=[mock_subscription]):
            subscriptions = await pubsub_service.list_subscriptions("test-project", use_cache=True)

            assert len(subscriptions) == 1
            assert subscriptions[0] == mock_subscription

    @pytest.mark.asyncio
    async def test_list_subscriptions_caching(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test that results are cached."""
        mock_response = {
            "subscriptions": [
                {
                    "name": "projects/test-project/subscriptions/test-sub",
                    "topic": "projects/test-project/topics/test-topic",
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_pubsub_client.projects().subscriptions().list.return_value = mock_request

        pubsub_service._client = mock_pubsub_client

        with patch.object(pubsub_service._cache, "set") as mock_set:
            await pubsub_service.list_subscriptions("test-project", use_cache=False)

            # Verify cache.set was called
            mock_set.assert_called_once()
            # First argument should be cache key
            assert mock_set.call_args[0][0] == "pubsub:subscriptions:test-project"
            # Second argument should be the subscriptions list
            assert len(mock_set.call_args[0][1]) == 1

    @pytest.mark.asyncio
    async def test_list_topics_pagination(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test listing topics with pagination."""
        # Mock paginated responses
        mock_response_page1 = {
            "topics": [
                {"name": "projects/test-project/topics/topic-1"},
                {"name": "projects/test-project/topics/topic-2"},
            ],
            "nextPageToken": "page2token",
        }
        mock_response_page2 = {
            "topics": [
                {"name": "projects/test-project/topics/topic-3"},
            ],
            # No nextPageToken means this is the last page
        }

        # Create mock requests for each page
        mock_request_page1 = MagicMock()
        mock_request_page1.execute = MagicMock(return_value=mock_response_page1)

        mock_request_page2 = MagicMock()
        mock_request_page2.execute = MagicMock(return_value=mock_response_page2)

        # Mock the list() method to return different requests based on pageToken
        def mock_list(**kwargs: Any) -> MagicMock:
            if kwargs.get("pageToken") == "page2token":
                return mock_request_page2
            return mock_request_page1

        mock_pubsub_client.projects().topics().list.side_effect = mock_list
        pubsub_service._client = mock_pubsub_client

        topics = await pubsub_service.list_topics("test-project", use_cache=False)

        # Should have all 3 topics from both pages
        assert len(topics) == 3
        assert topics[0].topic_name == "topic-1"
        assert topics[1].topic_name == "topic-2"
        assert topics[2].topic_name == "topic-3"

        # Verify both API calls were made
        assert mock_pubsub_client.projects().topics().list.call_count == 2

    @pytest.mark.asyncio
    async def test_list_subscriptions_pagination(
        self, pubsub_service: PubSubService, mock_pubsub_client: MagicMock
    ) -> None:
        """Test listing subscriptions with pagination."""
        # Mock paginated responses
        mock_response_page1 = {
            "subscriptions": [
                {
                    "name": "projects/test-project/subscriptions/sub-1",
                    "topic": "projects/test-project/topics/topic-1",
                },
                {
                    "name": "projects/test-project/subscriptions/sub-2",
                    "topic": "projects/test-project/topics/topic-1",
                },
            ],
            "nextPageToken": "page2token",
        }
        mock_response_page2 = {
            "subscriptions": [
                {
                    "name": "projects/test-project/subscriptions/sub-3",
                    "topic": "projects/test-project/topics/topic-2",
                },
            ],
            # No nextPageToken means this is the last page
        }

        # Create mock requests for each page
        mock_request_page1 = MagicMock()
        mock_request_page1.execute = MagicMock(return_value=mock_response_page1)

        mock_request_page2 = MagicMock()
        mock_request_page2.execute = MagicMock(return_value=mock_response_page2)

        # Mock the list() method to return different requests based on pageToken
        def mock_list(**kwargs: Any) -> MagicMock:
            if kwargs.get("pageToken") == "page2token":
                return mock_request_page2
            return mock_request_page1

        mock_pubsub_client.projects().subscriptions().list.side_effect = mock_list
        pubsub_service._client = mock_pubsub_client

        subscriptions = await pubsub_service.list_subscriptions("test-project", use_cache=False)

        # Should have all 3 subscriptions from both pages
        assert len(subscriptions) == 3
        assert subscriptions[0].subscription_name == "sub-1"
        assert subscriptions[1].subscription_name == "sub-2"
        assert subscriptions[2].subscription_name == "sub-3"

        # Verify both API calls were made
        assert mock_pubsub_client.projects().subscriptions().list.call_count == 2


class TestGetPubSubService:
    """Tests for get_pubsub_service function."""

    @pytest.mark.asyncio
    async def test_get_pubsub_service_creates_instance(self) -> None:
        """Test that get_pubsub_service creates a global instance."""
        service1 = await get_pubsub_service()
        service2 = await get_pubsub_service()

        assert service1 is service2
        assert isinstance(service1, PubSubService)
