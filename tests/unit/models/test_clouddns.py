"""Unit tests for Cloud DNS models."""

from typing import Any

from sequel.models.clouddns import DNSRecord, ManagedZone


class TestManagedZone:
    """Tests for ManagedZone model."""

    def test_create_managed_zone(self) -> None:
        """Test creating a managed zone."""
        zone = ManagedZone(
            id="my-zone",
            name="my-zone",
            zone_name="my-zone",
            dns_name="example.com.",
            description="Test zone",
            visibility="public",
            name_servers=["ns1.example.com", "ns2.example.com"],
            creation_time="2023-01-01T00:00:00.000Z",
        )

        assert zone.id == "my-zone"
        assert zone.zone_name == "my-zone"
        assert zone.dns_name == "example.com."
        assert zone.description == "Test zone"
        assert zone.visibility == "public"
        assert len(zone.name_servers) == 2
        assert zone.creation_time == "2023-01-01T00:00:00.000Z"

    def test_from_api_response_full(self) -> None:
        """Test creating zone from full API response."""
        data = {
            "name": "example-zone",
            "dnsName": "example.com.",
            "description": "Production DNS zone",
            "visibility": "public",
            "nameServers": [
                "ns-cloud-a1.googledomains.com.",
                "ns-cloud-a2.googledomains.com.",
                "ns-cloud-a3.googledomains.com.",
                "ns-cloud-a4.googledomains.com.",
            ],
            "creationTime": "2023-06-15T10:30:00.000Z",
        }

        zone = ManagedZone.from_api_response(data)

        assert zone.zone_name == "example-zone"
        assert zone.dns_name == "example.com."
        assert zone.description == "Production DNS zone"
        assert zone.visibility == "public"
        assert len(zone.name_servers) == 4
        assert zone.creation_time == "2023-06-15T10:30:00.000Z"
        assert zone.raw_data == data

    def test_from_api_response_minimal(self) -> None:
        """Test creating zone from minimal API response."""
        data: dict[str, Any] = {
            "name": "minimal-zone",
            "dnsName": "minimal.com.",
        }

        zone = ManagedZone.from_api_response(data)

        assert zone.zone_name == "minimal-zone"
        assert zone.dns_name == "minimal.com."
        assert zone.description is None
        assert zone.visibility == "public"  # Default
        assert zone.name_servers == []
        assert zone.creation_time is None

    def test_from_api_response_private_zone(self) -> None:
        """Test creating private DNS zone."""
        data = {
            "name": "private-zone",
            "dnsName": "internal.example.com.",
            "visibility": "private",
            "description": "Internal DNS",
        }

        zone = ManagedZone.from_api_response(data)

        assert zone.zone_name == "private-zone"
        assert zone.visibility == "private"
        assert zone.description == "Internal DNS"


class TestDNSRecord:
    """Tests for DNSRecord model."""

    def test_create_dns_record(self) -> None:
        """Test creating a DNS record."""
        record = DNSRecord(
            id="example.com.:A",
            name="example.com.",
            record_name="example.com.",
            record_type="A",
            ttl=300,
            rrdatas=["192.0.2.1"],
        )

        assert record.id == "example.com.:A"
        assert record.record_name == "example.com."
        assert record.record_type == "A"
        assert record.ttl == 300
        assert record.rrdatas == ["192.0.2.1"]

    def test_from_api_response_a_record(self) -> None:
        """Test creating A record from API response."""
        data = {
            "name": "www.example.com.",
            "type": "A",
            "ttl": 300,
            "rrdatas": ["192.0.2.1", "192.0.2.2"],
        }

        record = DNSRecord.from_api_response(data)

        assert record.record_name == "www.example.com."
        assert record.record_type == "A"
        assert record.ttl == 300
        assert len(record.rrdatas) == 2
        assert record.id == "www.example.com.:A"
        assert record.raw_data == data

    def test_from_api_response_cname_record(self) -> None:
        """Test creating CNAME record from API response."""
        data = {
            "name": "blog.example.com.",
            "type": "CNAME",
            "ttl": 600,
            "rrdatas": ["example.com."],
        }

        record = DNSRecord.from_api_response(data)

        assert record.record_name == "blog.example.com."
        assert record.record_type == "CNAME"
        assert record.ttl == 600
        assert record.rrdatas == ["example.com."]

    def test_from_api_response_mx_record(self) -> None:
        """Test creating MX record from API response."""
        data = {
            "name": "example.com.",
            "type": "MX",
            "ttl": 3600,
            "rrdatas": ["10 mail1.example.com.", "20 mail2.example.com."],
        }

        record = DNSRecord.from_api_response(data)

        assert record.record_type == "MX"
        assert len(record.rrdatas) == 2

    def test_from_api_response_txt_record(self) -> None:
        """Test creating TXT record from API response."""
        data = {
            "name": "example.com.",
            "type": "TXT",
            "ttl": 300,
            "rrdatas": ['"v=spf1 include:_spf.example.com ~all"'],
        }

        record = DNSRecord.from_api_response(data)

        assert record.record_type == "TXT"
        assert len(record.rrdatas) == 1

    def test_from_api_response_minimal(self) -> None:
        """Test creating record from minimal API response."""
        data: dict[str, Any] = {
            "name": "test.example.com.",
            "type": "A",
        }

        record = DNSRecord.from_api_response(data)

        assert record.record_name == "test.example.com."
        assert record.record_type == "A"
        assert record.ttl == 300  # Default
        assert record.rrdatas == []

    def test_get_display_value_single(self) -> None:
        """Test get_display_value with single rrdata."""
        record = DNSRecord(
            id="test:A",
            name="test.com.",
            record_name="test.com.",
            record_type="A",
            rrdatas=["192.0.2.1"],
        )

        assert record.get_display_value() == "192.0.2.1"

    def test_get_display_value_multiple(self) -> None:
        """Test get_display_value with multiple rrdatas."""
        record = DNSRecord(
            id="test:A",
            name="test.com.",
            record_name="test.com.",
            record_type="A",
            rrdatas=["192.0.2.1", "192.0.2.2", "192.0.2.3"],
        )

        assert record.get_display_value() == "3 records"

    def test_get_display_value_empty(self) -> None:
        """Test get_display_value with no rrdatas."""
        record = DNSRecord(
            id="test:A",
            name="test.com.",
            record_name="test.com.",
            record_type="A",
            rrdatas=[],
        )

        assert record.get_display_value() == ""
