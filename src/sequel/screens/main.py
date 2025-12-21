"""Main application screen with tree and detail pane layout."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header

from sequel.utils.logging import get_logger
from sequel.widgets.detail_pane import DetailPane
from sequel.widgets.resource_tree import ResourceTree, ResourceTreeNode
from sequel.widgets.status_bar import StatusBar

logger = get_logger(__name__)


class MainScreen(Screen[None]):
    """Main application screen with tree and detail pane layout.

    Layout:
    +------------------------------------------+
    |  Header                                  |
    +------------------+----------------------+
    |                  |                      |
    |  Resource Tree   |   Detail Pane        |
    |  (40%)           |   (60%)              |
    |                  |                      |
    +------------------+----------------------+
    |  Status Bar                              |
    +------------------------------------------+
    """

    CSS = """
    MainScreen {
        layout: vertical;
    }

    #main-container {
        height: 1fr;
        layout: horizontal;
    }

    #tree-container {
        width: 40%;
        height: 100%;
        border-right: tall $primary;
    }

    #detail-container {
        width: 60%;
        height: 100%;
    }

    ResourceTree {
        height: 100%;
        width: 100%;
    }

    DetailPane {
        height: 100%;
        width: 100%;
        padding: 1 2;
    }

    StatusBar {
        dock: bottom;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(self, *args: any, **kwargs: any) -> None:  # type: ignore[valid-type]
        """Initialize the main screen."""
        super().__init__(*args, **kwargs)
        self.resource_tree: ResourceTree | None = None
        self.detail_pane: DetailPane | None = None
        self.status_bar: StatusBar | None = None

    def compose(self) -> ComposeResult:
        """Compose the screen layout.

        Yields:
            Widget components
        """
        yield Header()

        with Horizontal(id="main-container"):
            with Vertical(id="tree-container"):
                self.resource_tree = ResourceTree()
                yield self.resource_tree

            with Vertical(id="detail-container"):
                self.detail_pane = DetailPane()
                yield self.detail_pane

        self.status_bar = StatusBar()
        yield self.status_bar

    async def on_mount(self) -> None:
        """Handle screen mount event."""
        logger.info("Main screen mounted")

        # Load projects into tree
        if self.resource_tree:
            try:
                if self.status_bar:
                    self.status_bar.set_loading(True)

                await self.resource_tree.load_projects()

                if self.status_bar:
                    self.status_bar.set_loading(False)

            except Exception as e:
                logger.error(f"Failed to load projects: {e}")
                if self.status_bar:
                    self.status_bar.set_loading(False)

    async def on_tree_node_highlighted(self, event: ResourceTree.NodeHighlighted[ResourceTreeNode]) -> None:
        """Handle tree node selection.

        Args:
            event: Node highlighted event
        """
        if not self.detail_pane:
            return

        # Update detail pane with selected resource
        if event.node.data and event.node.data.resource_data:
            self.detail_pane.update_content(event.node.data.resource_data)

            # Update status bar with project info
            if self.status_bar and event.node.data.project_id:
                self.status_bar.set_project(event.node.data.project_id)
        else:
            self.detail_pane.clear_content()

    async def refresh_tree(self) -> None:
        """Refresh the resource tree."""
        if not self.resource_tree:
            return

        logger.info("Refreshing resource tree")

        try:
            if self.status_bar:
                self.status_bar.set_loading(True)

            await self.resource_tree.load_projects()

            if self.status_bar:
                self.status_bar.set_loading(False)

        except Exception as e:
            logger.error(f"Failed to refresh tree: {e}")
            if self.status_bar:
                self.status_bar.set_loading(False)
