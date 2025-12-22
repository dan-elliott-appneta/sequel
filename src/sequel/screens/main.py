"""Main application screen with tree and detail pane layout."""

import asyncio
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header, Input

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
    """

    def __init__(self, *args: any, **kwargs: any) -> None:  # type: ignore[valid-type]
        """Initialize the main screen."""
        super().__init__(*args, **kwargs)
        self.resource_tree: ResourceTree | None = None
        self.detail_pane: DetailPane | None = None
        self.status_bar: StatusBar | None = None
        self.filter_input: Input | None = None
        self._filter_timer: asyncio.TimerHandle | None = None

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

    async def on_mount(self) -> None:
        """Handle screen mount event."""
        logger.info("Main screen mounted")

        # TODO: Toast container temporarily disabled due to layout issues
        # self.toast_container = ToastContainer()
        # await self.mount(self.toast_container)

        # Load projects into tree
        if self.resource_tree:
            try:
                if self.status_bar:
                    self.status_bar.set_loading(True, "Loading projects...")

                await self.resource_tree.load_projects()

                if self.status_bar:
                    self.status_bar.set_loading(False)
                    self.status_bar.update_last_refresh()

            except Exception as e:
                logger.error(f"Failed to load projects: {e}")
                if self.status_bar:
                    self.status_bar.set_loading(False)

    async def on_unmount(self) -> None:
        """Handle screen unmount event.

        Cleanup any pending timers to prevent callbacks on destroyed widgets.
        """
        logger.info("Main screen unmounting - cleaning up resources")

        # Cancel pending filter timer if any
        if self._filter_timer:
            self._filter_timer.cancel()
            self._filter_timer = None
            logger.debug("Cancelled pending filter timer")

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
        """Toggle filter input visibility (triggered by 'f' key)."""
        if not self.filter_input:
            return

        filter_container = self.query_one("#filter-container")

        if filter_container.has_class("visible"):
            # Hide filter
            filter_container.remove_class("visible")
            if self.resource_tree:
                self.resource_tree.focus()
            logger.debug("Filter hidden")
        else:
            # Show filter
            filter_container.add_class("visible")
            self.filter_input.focus()
            logger.debug("Filter shown")

    async def action_clear_filter(self) -> None:
        """Clear filter and hide input (triggered by Esc key)."""
        if not self.filter_input or not self.resource_tree:
            return

        # Clear filter text
        self.filter_input.value = ""

        # Hide filter container
        filter_container = self.query_one("#filter-container")
        filter_container.remove_class("visible")

        # Clear filter in tree (rebuild from full state)
        await self.resource_tree.apply_filter("")

        # Focus back on tree
        self.resource_tree.focus()
        logger.debug("Filter cleared and hidden")

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes with debouncing.

        Args:
            event: Input changed event
        """
        if event.input.id == "filter-input" and self.resource_tree:
            # Cancel any pending filter operation
            if self._filter_timer:
                self._filter_timer.cancel()

            filter_text = event.value.strip()

            # Debounce: wait 400ms after user stops typing before filtering
            # This prevents UI hangs when typing quickly
            loop = asyncio.get_event_loop()
            self._filter_timer = loop.call_later(
                0.4,  # 400ms delay
                lambda: asyncio.create_task(self._apply_filter_debounced(filter_text))
            )

    async def _apply_filter_debounced(self, filter_text: str) -> None:
        """Apply filter after debounce delay.

        Args:
            filter_text: Text to filter by
        """
        if self.resource_tree:
            await self.resource_tree.apply_filter(filter_text)
            logger.debug(f"Applied filter: '{filter_text}'")
