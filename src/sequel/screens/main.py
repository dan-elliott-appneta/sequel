"""Main application screen with tree and detail pane layout."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header, Input

from sequel.state.resource_state import get_resource_state
from sequel.utils.logging import get_logger
from sequel.widgets.detail_pane import DetailPane
from sequel.widgets.loading_progress import LoadingProgress
from sequel.widgets.refresh_modal import RefreshModal
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

    BINDINGS: ClassVar = [
        # VIM-style navigation
        Binding("j", "cursor_down", "Move down", show=False),
        Binding("k", "cursor_up", "Move up", show=False),
        Binding("h", "collapse_node", "Collapse/Parent", show=False),
        Binding("l", "expand_node", "Expand/Child", show=False),
        Binding("g", "cursor_top", "Go to top", show=False),
        Binding("G", "cursor_bottom", "Go to bottom", show=False),
        # Arrow keys for tree navigation
        Binding("up", "cursor_up", "Move up", show=False),
        Binding("down", "cursor_down", "Move down", show=False),
        Binding("left", "collapse_node", "Collapse/Parent", show=False),
        Binding("right", "expand_node", "Expand/Child", show=False),
        # Filter
        Binding("f", "toggle_filter", "Filter", show=False),
        Binding("escape", "clear_filter", "Clear filter", show=False),
        # Refresh
        Binding("r", "show_refresh_modal", "Refresh", show=False),
    ]

    CSS = """
    MainScreen {
        layout: vertical;
    }

    #filter-container {
        height: 0;
        background: $panel;
        padding: 0 1;
        overflow: hidden;
    }

    #filter-container.visible {
        height: 3;
    }

    #filter-input {
        width: 100%;
        height: 1;
        border: none;
    }

    #main-container {
        height: 1fr;
        layout: horizontal;
    }

    #tree-container {
        width: 40%;
        height: 100%;
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
        overflow-y: auto;
        scrollbar-size: 1 1;
    }

    StatusBar {
        dock: bottom;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }

    LoadingProgress {
        layer: overlay;
        display: none;
    }

    LoadingProgress.visible {
        display: block;
    }
    """

    def __init__(self, *args: any, **kwargs: any) -> None:  # type: ignore[valid-type]
        """Initialize the main screen."""
        super().__init__(*args, **kwargs)
        self.resource_tree: ResourceTree | None = None
        self.detail_pane: DetailPane | None = None
        self.status_bar: StatusBar | None = None
        self.filter_input: Input | None = None
        self.filter_active: bool = False
        self.loading_progress: LoadingProgress | None = None

    def compose(self) -> ComposeResult:
        """Compose the screen layout.

        Yields:
            Widget components
        """
        yield Header()

        # Filter input (hidden by default)
        with Vertical(id="filter-container"):
            self.filter_input = Input(
                placeholder="Filter resources... (type to filter, Esc to clear)",
                id="filter-input",
            )
            yield self.filter_input

        with Horizontal(id="main-container"):
            with Vertical(id="tree-container"):
                self.resource_tree = ResourceTree()
                yield self.resource_tree

            with Vertical(id="detail-container"):
                self.detail_pane = DetailPane()
                yield self.detail_pane

        self.status_bar = StatusBar()
        yield self.status_bar

        # Loading progress overlay (hidden by default)
        self.loading_progress = LoadingProgress()
        yield self.loading_progress

    async def on_mount(self) -> None:
        """Handle screen mount event."""
        import asyncio
        import os

        logger.info("Main screen mounted")

        # Check if eager loading is enabled (default: False for better UX)
        eager_load = os.getenv("SEQUEL_EAGER_LOAD", "false").lower() == "true"

        if eager_load and self.resource_tree and self.loading_progress:
            # Eager load all projects and resources with progress indicator
            try:
                logger.info("Eager loading enabled - loading all projects and resources")

                # Show loading progress
                self.loading_progress.show_loading("Loading all resources...")
                self.loading_progress.add_class("visible")

                # Yield to let the UI update
                await asyncio.sleep(0.1)

                # Define progress callback
                def update_progress(current: int, total: int, message: str) -> None:
                    if self.loading_progress:
                        logger.debug(f"Progress update: {current}/{total} - {message}")
                        self.loading_progress.update_progress(current, total, message)

                # Eagerly load all projects and their resources
                await self.resource_tree.load_all_projects_with_resources(
                    force_refresh=False,
                    progress_callback=update_progress,
                )

                # Hide loading progress
                self.loading_progress.remove_class("visible")
                self.loading_progress.hide_loading()

                if self.status_bar:
                    self.status_bar.update_last_refresh()

                logger.info("Eager load complete - UI ready")

            except Exception as e:
                logger.error(f"Failed to load projects and resources: {e}", exc_info=True)
                if self.loading_progress:
                    self.loading_progress.remove_class("visible")
                    self.loading_progress.hide_loading()
                raise

        else:
            # Lazy loading mode (default) - just load projects
            if self.resource_tree:
                try:
                    logger.info("Lazy loading mode - loading projects only")

                    if self.status_bar:
                        self.status_bar.set_loading(True, "Loading projects...")

                    # Yield to let the UI update and show loading indicator
                    await asyncio.sleep(0.1)

                    await self.resource_tree.load_projects()

                    if self.status_bar:
                        self.status_bar.set_loading(False)
                        self.status_bar.update_last_refresh()

                    logger.info("Project list loaded - resources will load on demand")

                except Exception as e:
                    logger.error(f"Failed to load projects: {e}", exc_info=True)
                    if self.status_bar:
                        self.status_bar.set_loading(False)
                    raise

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

    def show_toast(self, message: str, toast_type: str = "info", duration: float = 3.0) -> None:
        """Show a toast notification.

        Args:
            message: Message to display
            toast_type: Type of toast (info, success, warning)
            duration: Duration in seconds before auto-dismiss
        """
        # TODO: Toasts temporarily disabled due to layout issues
        # if self.toast_container:
        #     self.toast_container.show_toast(message, toast_type, duration)
        pass

    async def refresh_tree(self) -> None:
        """Refresh the resource tree."""
        if not self.resource_tree:
            return

        logger.info("Refreshing resource tree")

        try:
            if self.status_bar:
                self.status_bar.set_loading(True, "Refreshing resources...")

            await self.resource_tree.load_projects()

            if self.status_bar:
                self.status_bar.set_loading(False)
                self.status_bar.update_last_refresh()

        except Exception as e:
            logger.error(f"Failed to refresh tree: {e}")
            if self.status_bar:
                self.status_bar.set_loading(False)

    # VIM-style navigation actions

    async def action_cursor_down(self) -> None:
        """Move cursor down in tree (VIM 'j' key)."""
        if self.resource_tree:
            self.resource_tree.action_cursor_down()

    async def action_cursor_up(self) -> None:
        """Move cursor up in tree (VIM 'k' key)."""
        if self.resource_tree:
            self.resource_tree.action_cursor_up()

    async def action_collapse_node(self) -> None:
        """Collapse current node or move to parent (VIM 'h' / Left arrow).

        Behavior:
        - If node is expanded: collapse it
        - If node is already collapsed: move to parent node
        """
        if not self.resource_tree:
            return

        node = self.resource_tree.cursor_node
        if not node:
            return

        # If node is expanded, collapse it
        if node.is_expanded:
            node.collapse()
            logger.debug(f"Collapsed node: {node.label}")
        # If node is collapsed and has a parent, move to parent
        elif node.parent and node.parent != self.resource_tree.root:
            self.resource_tree.select_node(node.parent)
            logger.debug(f"Moved to parent node: {node.parent.label}")

    async def action_expand_node(self) -> None:
        """Expand current node or move to first child (VIM 'l' / Right arrow).

        Behavior:
        - If node can expand and is collapsed: expand it
        - If node is already expanded and has children: move to first child
        """
        if not self.resource_tree:
            return

        node = self.resource_tree.cursor_node
        if not node:
            return

        # If node is not expanded and can expand, expand it
        if not node.is_expanded and node.allow_expand:
            node.expand()
            logger.debug(f"Expanded node: {node.label}")
        # If node is expanded and has children, move to first child
        elif node.is_expanded and node.children:
            first_child = node.children[0]
            self.resource_tree.select_node(first_child)
            logger.debug(f"Moved to first child: {first_child.label}")

    async def action_cursor_top(self) -> None:
        """Move cursor to top of tree (VIM 'g' key)."""
        if not self.resource_tree:
            return

        # Move to first child of root (first project)
        if self.resource_tree.root.children:
            first_node = self.resource_tree.root.children[0]
            self.resource_tree.select_node(first_node)
            logger.debug("Moved to top of tree")

    async def action_cursor_bottom(self) -> None:
        """Move cursor to bottom of tree (VIM 'G' key)."""
        if not self.resource_tree:
            return

        # Find the last visible node in the tree
        last_node = self._get_last_visible_node(self.resource_tree.root)
        if last_node:
            self.resource_tree.select_node(last_node)
            logger.debug(f"Moved to bottom of tree: {last_node.label}")  # type: ignore[attr-defined]

    def _get_last_visible_node(self, node: any) -> any:  # type: ignore[valid-type]
        """Recursively find the last visible node in the tree.

        Args:
            node: Starting node

        Returns:
            Last visible node
        """
        # If node has children and is expanded, recurse into last child
        if node.children and node.is_expanded:  # type: ignore[attr-defined]
            return self._get_last_visible_node(node.children[-1])  # type: ignore[attr-defined]
        # Otherwise, this is the last visible node
        return node

    async def action_toggle_filter(self) -> None:
        """Toggle the filter input visibility (triggered by 'f' key)."""
        import os

        if not self.filter_input or not self.resource_tree:
            return

        # Only check if initial load is complete in eager load mode
        eager_load = os.getenv("SEQUEL_EAGER_LOAD", "false").lower() == "true"
        if eager_load and not self.resource_tree._initial_load_complete:
            logger.warning("Filter disabled until eager load completes")
            return

        filter_container = self.query_one("#filter-container")

        if self.filter_active:
            # Hide filter
            filter_container.remove_class("visible")
            self.filter_active = False
            # Clear filter and refocus tree
            self.filter_input.value = ""
            if self.resource_tree:
                await self.resource_tree.apply_filter("")
                self.resource_tree.focus()
            logger.debug("Filter hidden")
        else:
            # Show filter
            filter_container.add_class("visible")
            self.filter_active = True
            self.filter_input.focus()
            logger.debug("Filter shown")

    async def action_clear_filter(self) -> None:
        """Clear the filter (triggered by Esc key)."""
        if not self.filter_input or not self.filter_active:
            return

        # Clear the input
        self.filter_input.value = ""
        # Clear filter in tree
        if self.resource_tree:
            await self.resource_tree.apply_filter("")
        # Hide filter container
        filter_container = self.query_one("#filter-container")
        filter_container.remove_class("visible")
        self.filter_active = False
        # Refocus tree
        if self.resource_tree:
            self.resource_tree.focus()
        logger.debug("Filter cleared and hidden")

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes.

        Args:
            event: Input changed event
        """
        if event.input.id == "filter-input" and self.resource_tree:
            filter_text = event.value.strip()
            await self.resource_tree.apply_filter(filter_text)
            logger.debug(f"Applied filter: '{filter_text}'")

    async def action_show_refresh_modal(self) -> None:
        """Show refresh confirmation modal (triggered by 'r' key)."""
        logger.info("Showing refresh modal")

        # Show modal and get user choice
        result = await self.app.push_screen_wait(RefreshModal())

        if result == "all":
            logger.info("User chose to refresh all projects")
            await self.refresh_all()
        elif result == "visible":
            logger.info("User chose to refresh visible resources")
            await self.refresh_visible()
        else:
            logger.info("User canceled refresh")

    async def refresh_all(self) -> None:
        """Refresh all projects and resources from API."""
        if not self.resource_tree or not self.loading_progress:
            return

        logger.info("Refreshing all projects and resources")

        try:
            # Show loading progress
            self.loading_progress.show_loading("Refreshing all resources...")
            self.loading_progress.add_class("visible")

            # Define progress callback
            def update_progress(current: int, total: int, message: str) -> None:
                if self.loading_progress:
                    self.loading_progress.update_progress(current, total, message)

            # Invalidate all state
            state = get_resource_state()
            state.invalidate_all()

            # Reload all projects and resources
            await self.resource_tree.load_all_projects_with_resources(
                force_refresh=True,
                progress_callback=update_progress,
            )

            # Hide loading progress
            self.loading_progress.remove_class("visible")
            self.loading_progress.hide_loading()

            if self.status_bar:
                self.status_bar.update_last_refresh()

            logger.info("Refresh complete")

        except Exception as e:
            logger.error(f"Failed to refresh all resources: {e}")
            if self.loading_progress:
                self.loading_progress.remove_class("visible")
                self.loading_progress.hide_loading()

    async def refresh_visible(self) -> None:
        """Refresh only currently visible resources."""
        if not self.resource_tree or not self.loading_progress:
            return

        logger.info("Refreshing visible resources")

        try:
            # Get currently visible project IDs from tree
            visible_project_ids = set()
            for child in self.resource_tree.root.children:
                if child.data and child.data.resource_id:
                    visible_project_ids.add(child.data.resource_id)

            if not visible_project_ids:
                logger.warning("No visible projects to refresh")
                return

            # Show loading progress
            self.loading_progress.show_loading("Refreshing visible resources...")
            self.loading_progress.add_class("visible")

            # Invalidate state for visible projects
            state = get_resource_state()
            for project_id in visible_project_ids:
                state.invalidate_project(project_id)

            # Reload projects (will include only visible ones)
            await self.resource_tree.load_projects(force_refresh=True)

            # Hide loading progress
            self.loading_progress.remove_class("visible")
            self.loading_progress.hide_loading()

            if self.status_bar:
                self.status_bar.update_last_refresh()

            logger.info(f"Refreshed {len(visible_project_ids)} visible projects")

        except Exception as e:
            logger.error(f"Failed to refresh visible resources: {e}")
            if self.loading_progress:
                self.loading_progress.remove_class("visible")
                self.loading_progress.hide_loading()

