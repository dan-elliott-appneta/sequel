"""Unit tests for Cloud DNS service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sequel.models.clouddns import DNSRecord, ManagedZone
from sequel.services.clouddns import (
    CloudDNSService,
    get_clouddns_service,
    reset_clouddns_service,
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
def mock_clouddns_client() -> MagicMock:
    """Create mock Cloud DNS API client."""
    return MagicMock()


@pytest.fixture
def clouddns_service() -> CloudDNSService:
    """Create CloudDNS service instance."""
    reset_clouddns_service()
    return CloudDNSService()


class TestCloudDNSService:
    """Tests for CloudDNSService class."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(
        self, clouddns_service: CloudDNSService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client creates Cloud DNS client."""
        with (
            patch("sequel.services.clouddns.get_auth_manager", return_value=mock_auth_manager),
            patch("sequel.services.clouddns.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            client = await clouddns_service._get_client()

            mock_build.assert_called_once_with(
                "dns",
                "v1",
                credentials=mock_auth_manager.credentials,
                cache_discovery=False,
            )
            assert client is not None
            assert clouddns_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_returns_cached(
        self, clouddns_service: CloudDNSService, mock_auth_manager: AsyncMock
    ) -> None:
        """Test that _get_client returns cached client."""
        mock_client = MagicMock()
        clouddns_service._client = mock_client

        client = await clouddns_service._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_list_zones_success(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test listing DNS zones successfully."""
        mock_response = {
            "managedZones": [
                {
                    "name": "example-zone",
                    "dnsName": "example.com.",
                    "description": "Example zone",
                    "visibility": "public",
                    "nameServers": ["ns1.example.com", "ns2.example.com"],
                    "creationTime": "2023-01-01T00:00:00.000Z",
                },
                {
                    "name": "test-zone",
                    "dnsName": "test.com.",
                    "description": "Test zone",
                    "visibility": "private",
                    "nameServers": ["ns1.test.com"],
                    "creationTime": "2023-02-01T00:00:00.000Z",
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_clouddns_client.managedZones().list.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        zones = await clouddns_service.list_zones("test-project", use_cache=False)

        assert len(zones) == 2
        assert isinstance(zones[0], ManagedZone)
        assert zones[0].zone_name == "example-zone"
        assert zones[0].visibility == "public"
        assert zones[1].zone_name == "test-zone"
        assert zones[1].visibility == "private"

    @pytest.mark.asyncio
    async def test_list_zones_empty(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test listing zones when none exist."""
        mock_response: dict[str, Any] = {"managedZones": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_clouddns_client.managedZones().list.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        zones = await clouddns_service.list_zones("test-project", use_cache=False)

        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_list_zones_error(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test error handling when listing zones."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_clouddns_client.managedZones().list.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        zones = await clouddns_service.list_zones("test-project", use_cache=False)

        # Should return empty list on error
        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_list_zones_with_cache(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test listing zones with caching."""
        mock_zone = ManagedZone(
            id="cached-zone",
            name="cached-zone",
            zone_name="cached-zone",
            dns_name="cached.com.",
        )

        with patch.object(clouddns_service._cache, "get", return_value=[mock_zone]):
            zones = await clouddns_service.list_zones("test-project", use_cache=True)

            assert len(zones) == 1
            assert zones[0] == mock_zone

    @pytest.mark.asyncio
    async def test_get_zone_success(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test getting a specific DNS zone."""
        mock_response = {
            "name": "my-zone",
            "dnsName": "myzone.com.",
            "description": "My zone",
            "visibility": "public",
            "nameServers": ["ns1.example.com", "ns2.example.com"],
            "creationTime": "2023-03-15T12:00:00.000Z",
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_clouddns_client.managedZones().get.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        zone = await clouddns_service.get_zone("test-project", "my-zone", use_cache=False)

        assert zone is not None
        assert isinstance(zone, ManagedZone)
        assert zone.zone_name == "my-zone"
        assert zone.dns_name == "myzone.com."

    @pytest.mark.asyncio
    async def test_get_zone_not_found(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test getting a zone that doesn't exist."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("Not found"))
        mock_clouddns_client.managedZones().get.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        zone = await clouddns_service.get_zone("test-project", "nonexistent", use_cache=False)

        assert zone is None

    @pytest.mark.asyncio
    async def test_get_zone_with_cache(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test getting zone with caching."""
        mock_zone = ManagedZone(
            id="cached-zone",
            name="cached-zone",
            zone_name="cached-zone",
            dns_name="cached.com.",
        )

        with patch.object(clouddns_service._cache, "get", return_value=mock_zone):
            zone = await clouddns_service.get_zone("test-project", "cached-zone", use_cache=True)

            assert zone == mock_zone

    @pytest.mark.asyncio
    async def test_list_records_success(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test listing DNS records successfully."""
        mock_response = {
            "rrsets": [
                {
                    "name": "example.com.",
                    "type": "A",
                    "ttl": 300,
                    "rrdatas": ["192.0.2.1"],
                },
                {
                    "name": "www.example.com.",
                    "type": "CNAME",
                    "ttl": 600,
                    "rrdatas": ["example.com."],
                },
                {
                    "name": "example.com.",
                    "type": "MX",
                    "ttl": 3600,
                    "rrdatas": ["10 mail.example.com."],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_clouddns_client.resourceRecordSets().list.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        records = await clouddns_service.list_records(
            "test-project", "example-zone", use_cache=False
        )

        assert len(records) == 3
        assert isinstance(records[0], DNSRecord)
        assert records[0].record_type == "A"
        assert records[1].record_type == "CNAME"
        assert records[2].record_type == "MX"

    @pytest.mark.asyncio
    async def test_list_records_empty(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test listing records when none exist."""
        mock_response: dict[str, Any] = {"rrsets": []}

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_clouddns_client.resourceRecordSets().list.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        records = await clouddns_service.list_records(
            "test-project", "example-zone", use_cache=False
        )

        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_list_records_error(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test error handling when listing records."""
        mock_request = MagicMock()
        mock_request.execute = MagicMock(side_effect=Exception("API Error"))
        mock_clouddns_client.resourceRecordSets().list.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        records = await clouddns_service.list_records(
            "test-project", "example-zone", use_cache=False
        )

        # Should return empty list on error
        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_list_records_with_cache(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test listing records with caching."""
        mock_record = DNSRecord(
            id="cached:A",
            name="cached.com.",
            record_name="cached.com.",
            record_type="A",
            rrdatas=["192.0.2.1"],
        )

        with patch.object(clouddns_service._cache, "get", return_value=[mock_record]):
            records = await clouddns_service.list_records(
                "test-project", "example-zone", use_cache=True
            )

            assert len(records) == 1
            assert records[0] == mock_record

    @pytest.mark.asyncio
    async def test_get_record_success(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test getting a specific DNS record."""
        # Mock list_records to return a record
        mock_response = {
            "rrsets": [
                {
                    "name": "www.example.com.",
                    "type": "A",
                    "ttl": 300,
                    "rrdatas": ["192.0.2.1"],
                },
                {
                    "name": "www.example.com.",
                    "type": "AAAA",
                    "ttl": 300,
                    "rrdatas": ["2001:db8::1"],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_clouddns_client.resourceRecordSets().list.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        record = await clouddns_service.get_record(
            "test-project", "example-zone", "www.example.com.", "A", use_cache=False
        )

        assert record is not None
        assert isinstance(record, DNSRecord)
        assert record.record_name == "www.example.com."
        assert record.record_type == "A"

    @pytest.mark.asyncio
    async def test_get_record_not_found(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test getting a record that doesn't exist."""
        mock_response = {
            "rrsets": [
                {
                    "name": "example.com.",
                    "type": "A",
                    "ttl": 300,
                    "rrdatas": ["192.0.2.1"],
                },
            ]
        }

        mock_request = MagicMock()
        mock_request.execute = MagicMock(return_value=mock_response)
        mock_clouddns_client.resourceRecordSets().list.return_value = mock_request

        clouddns_service._client = mock_clouddns_client

        record = await clouddns_service.get_record(
            "test-project", "example-zone", "nonexistent.com.", "A", use_cache=False
        )

        assert record is None

    @pytest.mark.asyncio
    async def test_get_record_with_cache(
        self, clouddns_service: CloudDNSService, mock_clouddns_client: MagicMock
    ) -> None:
        """Test getting record with caching."""
        mock_record = DNSRecord(
            id="cached:A",
            name="cached.com.",
            record_name="cached.com.",
            record_type="A",
            rrdatas=["192.0.2.1"],
        )

        with patch.object(clouddns_service._cache, "get", return_value=mock_record):
            record = await clouddns_service.get_record(
                "test-project", "example-zone", "cached.com.", "A", use_cache=True
            )

            assert record == mock_record


class TestGetCloudDNSService:
    """Tests for get_clouddns_service function."""

    @pytest.mark.asyncio
    async def test_get_clouddns_service_creates_instance(self) -> None:
        """Test that get_clouddns_service creates a global instance."""
        reset_clouddns_service()

        service1 = await get_clouddns_service()
        service2 = await get_clouddns_service()

        assert service1 is service2
        assert isinstance(service1, CloudDNSService)

    @pytest.mark.asyncio
    async def test_reset_clouddns_service(self) -> None:
        """Test that reset_clouddns_service clears the global instance."""
        service1 = await get_clouddns_service()
        reset_clouddns_service()
        service2 = await get_clouddns_service()

        assert service1 is not service2
