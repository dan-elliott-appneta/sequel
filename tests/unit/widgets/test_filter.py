"""Tests for filter functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.widgets import Input

from sequel.models.cloudsql import CloudSQLInstance
from sequel.models.compute import InstanceGroup
from sequel.models.gke import GKECluster
from sequel.models.iam import ServiceAccount
from sequel.models.project import Project
from sequel.models.secrets import Secret
from sequel.screens.main import MainScreen
from sequel.state.resource_state import reset_resource_state
from sequel.widgets.resource_tree import ResourceTree


class TestFilterLogic:
    """Test filter logic in ResourceTree."""

    @pytest.fixture
    def resource_tree(self) -> ResourceTree:
        """Create a ResourceTree instance."""
        # Reset the singleton state before each test
        reset_resource_state()
        return ResourceTree()

    @pytest.fixture
    def sample_projects(self) -> list[Project]:
        """Create sample projects."""
        return [
            Project(
                id="proj-grafana",
                name="Grafana Project",
                project_id="proj-grafana",
                display_name="Grafana Project",
                project_number="111",
                state="ACTIVE",
                labels={},
            ),
            Project(
                id="proj-other",
                name="Other Project",
                project_id="proj-other",
                display_name="Other Project",
                project_number="222",
                state="ACTIVE",
                labels={},
            ),
        ]

    def test_matches_filter_case_insensitive(self, resource_tree: ResourceTree) -> None:
        """Test that filter matching is case-insensitive."""
        resource_tree._filter_text = "grafana"

        assert resource_tree._matches_filter("GRAFANA")
        assert resource_tree._matches_filter("Grafana")
        assert resource_tree._matches_filter("grafana")
        assert resource_tree._matches_filter("my-grafana-instance")

    def test_matches_filter_partial_match(self, resource_tree: ResourceTree) -> None:
        """Test that filter matches partial strings."""
        resource_tree._filter_text = "graf"

        assert resource_tree._matches_filter("grafana")
        assert resource_tree._matches_filter("my-graf-server")
        assert not resource_tree._matches_filter("hello")

    def test_matches_filter_empty_filter(self, resource_tree: ResourceTree) -> None:
        """Test that empty filter doesn't match anything."""
        resource_tree._filter_text = ""

        assert not resource_tree._matches_filter("anything")
        assert not resource_tree._matches_filter("grafana")

    def test_matches_filter_empty_text(self, resource_tree: ResourceTree) -> None:
        """Test that empty text doesn't match."""
        resource_tree._filter_text = "grafana"

        assert not resource_tree._matches_filter("")
        assert not resource_tree._matches_filter(None)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_apply_filter_empty_clears_filter(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test that empty filter string clears the filter."""
        # Set up state with projects
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        # Set a filter first
        resource_tree._filter_text = "grafana"

        # Clear filter
        with patch.object(resource_tree, "load_projects") as mock_load:
            await resource_tree.apply_filter("")

            # Should reload projects normally
            mock_load.assert_called_once()
            assert resource_tree._filter_text == ""

    @pytest.mark.asyncio
    async def test_apply_filter_shows_matching_projects(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test that filter shows projects with matching names."""
        # Set up state
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        # Mock config and app
        mock_config = MagicMock()
        mock_config.project_filter_regex = None
        mock_app = MagicMock()

        with (
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
        ):
            # Apply filter
            await resource_tree.apply_filter("grafana")

            # Should only show matching project
            assert len(resource_tree.root.children) == 1
            assert "Grafana" in str(resource_tree.root.children[0].label)

    @pytest.mark.asyncio
    async def test_apply_filter_shows_matching_cloudsql(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test that filter shows CloudSQL instances with matching names."""
        # Set up state
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        # Add CloudSQL instance
        grafana_instance = CloudSQLInstance(
            id="grafana-db",
            name="grafana-db",
            project_id="proj-other",
            instance_name="grafana-db",
            database_version="POSTGRES_14",
            region="us-central1",
            tier="db-f1-micro",
            state="RUNNABLE",
            ip_addresses=[],
        )
        resource_tree._state._cloudsql["proj-other"] = [grafana_instance]
        resource_tree._state._loaded.add(("proj-other", "cloudsql"))

        mock_config = MagicMock()
        mock_config.project_filter_regex = None
        mock_app = MagicMock()

        with (
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
        ):
            # Apply filter
            await resource_tree.apply_filter("grafana")

            # Should show both: project with "grafana" in name + project with grafana-db
            assert len(resource_tree.root.children) == 2

            # Find the "Other Project" node
            other_project_node = None
            for child in resource_tree.root.children:
                if "Other" in str(child.label):
                    other_project_node = child
                    break

            assert other_project_node is not None
            # Should have CloudSQL child
            assert len(other_project_node.children) == 1
            assert "Cloud SQL" in str(other_project_node.children[0].label)

    @pytest.mark.asyncio
    async def test_apply_filter_shows_matching_secrets(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test that filter shows secrets with matching names."""
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        # Add secret
        grafana_secret = Secret(
            id="grafana-api-key",
            name="grafana-api-key",
            project_id="proj-other",
            secret_name="grafana-api-key",
            replication_policy="automatic",
            create_time="2024-01-01T00:00:00Z",
        )
        resource_tree._state._secrets["proj-other"] = [grafana_secret]
        resource_tree._state._loaded.add(("proj-other", "secrets"))

        mock_config = MagicMock()
        mock_config.project_filter_regex = None
        mock_app = MagicMock()

        with (
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
        ):
            await resource_tree.apply_filter("grafana")

            # Find the "Other Project" node
            other_project_node = None
            for child in resource_tree.root.children:
                if "Other" in str(child.label):
                    other_project_node = child
                    break

            assert other_project_node is not None
            # Should have Secrets child
            assert len(other_project_node.children) == 1
            assert "Secrets" in str(other_project_node.children[0].label)

    @pytest.mark.asyncio
    async def test_apply_filter_shows_matching_compute_groups(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test that filter shows compute groups with matching names."""
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        # Add compute group
        grafana_group = InstanceGroup(
            id="grafana-workers",
            name="grafana-workers",
            project_id="proj-other",
            group_name="grafana-workers",
            zone="us-central1-a",
            size=3,
            is_managed=True,
            template_url="https://...",
        )
        resource_tree._state._compute_groups["proj-other"] = [grafana_group]
        resource_tree._state._loaded.add(("proj-other", "compute_groups"))

        mock_config = MagicMock()
        mock_config.project_filter_regex = None
        mock_app = MagicMock()

        with (
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
        ):
            await resource_tree.apply_filter("grafana")

            # Find the "Other Project" node
            other_project_node = None
            for child in resource_tree.root.children:
                if "Other" in str(child.label):
                    other_project_node = child
                    break

            assert other_project_node is not None
            assert len(other_project_node.children) == 1
            assert "Instance Groups" in str(other_project_node.children[0].label)

    @pytest.mark.asyncio
    async def test_apply_filter_shows_matching_gke_clusters(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test that filter shows GKE clusters with matching names."""
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        # Add GKE cluster
        grafana_cluster = GKECluster(
            id="grafana-cluster",
            name="grafana-cluster",
            project_id="proj-other",
            cluster_name="grafana-cluster",
            location="us-central1-a",
            status="RUNNING",
            endpoint="1.2.3.4",
            node_count=3,
        )
        resource_tree._state._gke_clusters["proj-other"] = [grafana_cluster]
        resource_tree._state._loaded.add(("proj-other", "gke_clusters"))

        mock_config = MagicMock()
        mock_config.project_filter_regex = None
        mock_app = MagicMock()

        with (
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
        ):
            await resource_tree.apply_filter("grafana")

            # Find the "Other Project" node
            other_project_node = None
            for child in resource_tree.root.children:
                if "Other" in str(child.label):
                    other_project_node = child
                    break

            assert other_project_node is not None
            assert len(other_project_node.children) == 1
            assert "GKE Clusters" in str(other_project_node.children[0].label)

    @pytest.mark.asyncio
    async def test_apply_filter_shows_matching_iam_accounts(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test that filter shows IAM accounts with matching names."""
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        # Add IAM account
        grafana_account = ServiceAccount(
            id="grafana@project.iam.gserviceaccount.com",
            name="Grafana Service Account",
            project_id="proj-other",
            email="grafana@project.iam.gserviceaccount.com",
            display_name="Grafana Service Account",
            disabled=False,
        )
        resource_tree._state._iam_accounts["proj-other"] = [grafana_account]
        resource_tree._state._loaded.add(("proj-other", "iam_accounts"))

        mock_config = MagicMock()
        mock_config.project_filter_regex = None
        mock_app = MagicMock()

        with (
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
        ):
            await resource_tree.apply_filter("grafana")

            # Find the "Other Project" node
            other_project_node = None
            for child in resource_tree.root.children:
                if "Other" in str(child.label):
                    other_project_node = child
                    break

            assert other_project_node is not None
            assert len(other_project_node.children) == 1
            assert "Service Accounts" in str(other_project_node.children[0].label)

    @pytest.mark.asyncio
    async def test_apply_filter_multiple_resource_types(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test filter shows multiple matching resource types in same project."""
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        # Add multiple resources with "grafana" in name
        resource_tree._state._cloudsql["proj-other"] = [
            CloudSQLInstance(
                id="grafana-db",
                name="grafana-db",
                project_id="proj-other",
                instance_name="grafana-db",
                database_version="POSTGRES_14",
                region="us-central1",
                tier="db-f1-micro",
                state="RUNNABLE",
                ip_addresses=[],
            )
        ]
        resource_tree._state._loaded.add(("proj-other", "cloudsql"))

        resource_tree._state._secrets["proj-other"] = [
            Secret(
                id="grafana-secret",
                name="grafana-secret",
                project_id="proj-other",
                secret_name="grafana-secret",
                replication_policy="automatic",
                create_time="2024-01-01T00:00:00Z",
            )
        ]
        resource_tree._state._loaded.add(("proj-other", "secrets"))

        mock_config = MagicMock()
        mock_config.project_filter_regex = None
        mock_app = MagicMock()

        with (
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
        ):
            await resource_tree.apply_filter("grafana")

            # Find the "Other Project" node
            other_project_node = None
            for child in resource_tree.root.children:
                if "Other" in str(child.label):
                    other_project_node = child
                    break

            assert other_project_node is not None
            # Should have 2 resource type children: CloudSQL + Secrets
            assert len(other_project_node.children) == 2

    @pytest.mark.asyncio
    async def test_apply_filter_no_matches(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test filter shows nothing when no matches found."""
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        mock_app = MagicMock()
        with patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)):
            await resource_tree.apply_filter("nonexistent")

            # Should show no projects
            assert len(resource_tree.root.children) == 0

    @pytest.mark.asyncio
    async def test_apply_filter_sends_notification(
        self, resource_tree: ResourceTree, sample_projects: list[Project]
    ) -> None:
        """Test that applying filter sends a notification."""
        resource_tree._state._projects = {p.project_id: p for p in sample_projects}
        resource_tree._state._loaded.add(("projects",))

        mock_config = MagicMock()
        mock_config.project_filter_regex = None
        mock_app = MagicMock()

        with (
            patch("sequel.state.resource_state.get_config", return_value=mock_config),
            patch.object(type(resource_tree), "app", new_callable=lambda: property(lambda self: mock_app)),
        ):
            await resource_tree.apply_filter("grafana")

            # Should send notification
            mock_app.notify.assert_called_once()
            call_args = mock_app.notify.call_args
            assert "grafana" in call_args[0][0].lower()


class TestFilterUI:
    """Test filter UI interactions in MainScreen."""

    @pytest.mark.asyncio
    async def test_action_toggle_filter_shows_input(self) -> None:
        """Test that toggle_filter action shows the filter input."""
        screen = MainScreen()

        # Mock the filter input and container
        screen.filter_input = MagicMock(spec=Input)
        mock_container = MagicMock()
        mock_container.has_class.return_value = False

        with patch.object(screen, "query_one", return_value=mock_container):
            await screen.action_toggle_filter()

            # Should add visible class
            mock_container.add_class.assert_called_once_with("visible")
            screen.filter_input.focus.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_toggle_filter_hides_input(self) -> None:
        """Test that toggle_filter action hides the filter input when visible."""
        screen = MainScreen()

        screen.filter_input = MagicMock(spec=Input)
        screen.resource_tree = MagicMock()
        mock_container = MagicMock()
        mock_container.has_class.return_value = True  # Already visible

        with patch.object(screen, "query_one", return_value=mock_container):
            await screen.action_toggle_filter()

            # Should remove visible class
            mock_container.remove_class.assert_called_once_with("visible")
            screen.resource_tree.focus.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_clear_filter(self) -> None:
        """Test that clear_filter action clears and hides filter."""
        screen = MainScreen()

        screen.filter_input = MagicMock(spec=Input)
        screen.filter_input.value = "grafana"
        screen.resource_tree = MagicMock()
        screen.resource_tree.apply_filter = AsyncMock()

        mock_container = MagicMock()

        with patch.object(screen, "query_one", return_value=mock_container):
            await screen.action_clear_filter()

            # Should clear input
            assert screen.filter_input.value == ""
            # Should hide container
            mock_container.remove_class.assert_called_once_with("visible")
            # Should apply empty filter
            screen.resource_tree.apply_filter.assert_called_once_with("")
            # Should focus tree
            screen.resource_tree.focus.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_input_changed_debounces(self) -> None:
        """Test that filter input is debounced."""
        screen = MainScreen()
        screen.resource_tree = MagicMock()

        # Create mock event
        mock_input = MagicMock(spec=Input)
        mock_input.id = "filter-input"
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "grafana"

        with patch("sequel.screens.main.asyncio.get_event_loop") as mock_loop:
            mock_event_loop = MagicMock()
            mock_loop.return_value = mock_event_loop

            await screen.on_input_changed(mock_event)

            # Should call call_later with 400ms delay
            mock_event_loop.call_later.assert_called_once()
            assert mock_event_loop.call_later.call_args[0][0] == 0.4

    @pytest.mark.asyncio
    async def test_on_input_changed_cancels_previous_timer(self) -> None:
        """Test that new input cancels previous debounce timer."""
        screen = MainScreen()
        screen.resource_tree = MagicMock()

        # Set up previous timer
        mock_previous_timer = MagicMock()
        screen._filter_timer = mock_previous_timer

        mock_input = MagicMock(spec=Input)
        mock_input.id = "filter-input"
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "graf"

        with patch("sequel.screens.main.asyncio.get_event_loop"):
            await screen.on_input_changed(mock_event)

            # Should cancel previous timer
            mock_previous_timer.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_filter_debounced(self) -> None:
        """Test that debounced filter application works."""
        screen = MainScreen()
        screen.resource_tree = MagicMock()
        screen.resource_tree.apply_filter = AsyncMock()

        await screen._apply_filter_debounced("grafana")

        # Should call resource_tree.apply_filter
        screen.resource_tree.apply_filter.assert_called_once_with("grafana")
