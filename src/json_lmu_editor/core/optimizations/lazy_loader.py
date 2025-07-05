"""
Lazy loading system for the LMU Configuration Editor.

Provides on-demand loading of UI components to improve startup performance.
"""

from typing import Dict, Set, Optional, Callable, Any
import logging
from dataclasses import dataclass
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget


@dataclass
class LoadableComponent:
    """Represents a component that can be loaded on demand."""

    category: str
    widget_factory: Callable[[], QWidget]
    is_loaded: bool = False
    widget: Optional[QWidget] = None
    priority: int = 0  # Higher priority loads first
    dependencies: Set[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = set()


class LazyLoader(QObject):
    """Manages lazy loading of UI components."""

    # Signals
    component_loaded = pyqtSignal(str)  # component_name
    category_loading = pyqtSignal(str)  # category_name
    category_loaded = pyqtSignal(str)  # category_name
    loading_progress = pyqtSignal(int, int)  # current, total

    def __init__(self):
        """Initialize the lazy loader."""
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.components: Dict[str, LoadableComponent] = {}
        self.loaded_categories: Set[str] = set()
        self.loading_queue: list = []
        self.is_loading = False

        # Loading timer for background loading
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self._process_loading_queue)

        # Preload timer for preloading visible components
        self.preload_timer = QTimer()
        self.preload_timer.setSingleShot(True)
        self.preload_timer.timeout.connect(self._preload_next_components)

    def register_component(
        self,
        name: str,
        category: str,
        widget_factory: Callable[[], QWidget],
        priority: int = 0,
        dependencies: Set[str] = None,
    ) -> None:
        """
        Register a component for lazy loading.

        Args:
            name: Unique component name
            category: Category name (e.g., tab name)
            widget_factory: Function that creates the widget
            priority: Loading priority (higher = load first)
            dependencies: Set of component names this depends on
        """
        self.components[name] = LoadableComponent(
            category=category,
            widget_factory=widget_factory,
            priority=priority,
            dependencies=dependencies or set(),
        )

        self.logger.debug(f"Registered component '{name}' in category '{category}'")

    def load_category_on_demand(self, category: str) -> None:
        """
        Load all components for a category immediately.

        Args:
            category: Category to load
        """
        if category in self.loaded_categories:
            self.logger.debug(f"Category '{category}' already loaded")
            return

        self.logger.info(f"Loading category '{category}' on demand")
        self.category_loading.emit(category)

        # Get components for this category
        category_components = [
            (name, comp)
            for name, comp in self.components.items()
            if comp.category == category and not comp.is_loaded
        ]

        if not category_components:
            self.loaded_categories.add(category)
            self.category_loaded.emit(category)
            return

        # Sort by priority
        category_components.sort(key=lambda x: x[1].priority, reverse=True)

        # Load components
        total_components = len(category_components)
        for i, (name, component) in enumerate(category_components):
            self._load_component_immediate(name, component)
            self.loading_progress.emit(i + 1, total_components)

        self.loaded_categories.add(category)
        self.category_loaded.emit(category)
        self.logger.info(f"Category '{category}' loaded successfully")

    def preload_visible_widgets(self, visible_categories: list) -> None:
        """
        Preload widgets for visible categories in background.

        Args:
            visible_categories: List of category names that are visible
        """
        self.logger.debug(f"Preloading visible categories: {visible_categories}")

        # Add visible categories to preload queue
        for category in visible_categories:
            if category not in self.loaded_categories:
                self._queue_category_for_loading(category, high_priority=True)

        # Start background loading if not already running
        if not self.is_loading and self.loading_queue:
            self._start_background_loading()

    def unload_hidden_widgets(self, hidden_categories: list) -> None:
        """
        Unload widgets from hidden categories to save memory.

        Args:
            hidden_categories: List of category names that are hidden
        """
        self.logger.debug(f"Considering unload for categories: {hidden_categories}")

        for category in hidden_categories:
            if category in self.loaded_categories:
                self._unload_category_if_appropriate(category)

    def get_component_widget(self, name: str) -> Optional[QWidget]:
        """
        Get a component widget, loading it if necessary.

        Args:
            name: Component name

        Returns:
            Widget instance or None if not found/failed to load
        """
        if name not in self.components:
            self.logger.warning(f"Component '{name}' not registered")
            return None

        component = self.components[name]

        if not component.is_loaded:
            # Load immediately if requested
            self._load_component_immediate(name, component)

        return component.widget

    def is_category_loaded(self, category: str) -> bool:
        """
        Check if a category is fully loaded.

        Args:
            category: Category name

        Returns:
            True if category is loaded
        """
        return category in self.loaded_categories

    def is_component_loaded(self, name: str) -> bool:
        """
        Check if a component is loaded.

        Args:
            name: Component name

        Returns:
            True if component is loaded
        """
        return name in self.components and self.components[name].is_loaded

    def get_loading_stats(self) -> Dict[str, Any]:
        """
        Get loading statistics.

        Returns:
            Dictionary with loading statistics
        """
        total_components = len(self.components)
        loaded_components = sum(
            1 for comp in self.components.values() if comp.is_loaded
        )

        category_stats = {}
        for category in set(comp.category for comp in self.components.values()):
            category_components = [
                comp for comp in self.components.values() if comp.category == category
            ]
            category_loaded = sum(1 for comp in category_components if comp.is_loaded)
            category_stats[category] = {
                "total": len(category_components),
                "loaded": category_loaded,
                "percentage": (category_loaded / len(category_components)) * 100
                if category_components
                else 0,
            }

        return {
            "total_components": total_components,
            "loaded_components": loaded_components,
            "overall_percentage": (loaded_components / total_components) * 100
            if total_components
            else 0,
            "loaded_categories": len(self.loaded_categories),
            "total_categories": len(
                set(comp.category for comp in self.components.values())
            ),
            "category_stats": category_stats,
            "queue_size": len(self.loading_queue),
            "is_loading": self.is_loading,
        }

    def _load_component_immediate(
        self, name: str, component: LoadableComponent
    ) -> bool:
        """
        Load a component immediately.

        Args:
            name: Component name
            component: Component to load

        Returns:
            True if loaded successfully
        """
        if component.is_loaded:
            return True

        try:
            # Check dependencies
            for dep_name in component.dependencies:
                if (
                    dep_name in self.components
                    and not self.components[dep_name].is_loaded
                ):
                    self.logger.debug(f"Loading dependency '{dep_name}' for '{name}'")
                    self._load_component_immediate(dep_name, self.components[dep_name])

            # Create widget
            self.logger.debug(f"Creating widget for component '{name}'")
            widget = component.widget_factory()

            component.widget = widget
            component.is_loaded = True

            self.component_loaded.emit(name)
            self.logger.debug(f"Component '{name}' loaded successfully")

            return True

        except Exception as e:
            self.logger.error(f"Failed to load component '{name}': {e}")
            return False

    def _queue_category_for_loading(
        self, category: str, high_priority: bool = False
    ) -> None:
        """Queue a category for background loading."""
        if category in self.loaded_categories:
            return

        # Get components for this category
        category_components = [
            (name, comp)
            for name, comp in self.components.items()
            if comp.category == category and not comp.is_loaded
        ]

        # Add to queue
        for name, component in category_components:
            queue_item = (name, component, high_priority)
            if queue_item not in self.loading_queue:
                if high_priority:
                    self.loading_queue.insert(0, queue_item)
                else:
                    self.loading_queue.append(queue_item)

    def _start_background_loading(self) -> None:
        """Start background loading process."""
        if self.is_loading or not self.loading_queue:
            return

        self.is_loading = True
        self.logger.debug("Starting background loading")

        # Start with a small delay to avoid blocking UI
        self.load_timer.start(50)

    def _process_loading_queue(self) -> None:
        """Process items in the loading queue."""
        if not self.loading_queue:
            self.is_loading = False
            self.logger.debug("Background loading completed")
            return

        # Load next item
        name, component, high_priority = self.loading_queue.pop(0)

        if not component.is_loaded:
            self._load_component_immediate(name, component)

        # Continue with next item after a small delay
        if self.loading_queue:
            self.load_timer.start(10 if high_priority else 25)
        else:
            self.is_loading = False
            self.logger.debug("Background loading completed")

    def _preload_next_components(self) -> None:
        """Preload components that are likely to be needed next."""
        # TODO: Implement smart preloading based on user behavior patterns
        pass

    def _unload_category_if_appropriate(self, category: str) -> None:
        """
        Unload a category if it's appropriate to do so.

        Args:
            category: Category to potentially unload
        """
        # TODO: Implement unloading of unused components for memory optimization
        pass

    def clear_all(self) -> None:
        """Clear all loaded components and reset state."""
        self.logger.info("Clearing all loaded components")

        for component in self.components.values():
            if component.widget:
                component.widget.deleteLater()
            component.widget = None
            component.is_loaded = False

        self.loaded_categories.clear()
        self.loading_queue.clear()
        self.is_loading = False

        # Stop timers
        self.load_timer.stop()
        self.preload_timer.stop()


# Convenience decorator for registering components
def lazy_component(
    loader: LazyLoader,
    name: str,
    category: str,
    priority: int = 0,
    dependencies: Set[str] = None,
):
    """
    Decorator to register a widget factory as a lazy component.

    Args:
        loader: LazyLoader instance
        name: Component name
        category: Category name
        priority: Loading priority
        dependencies: Component dependencies
    """

    def decorator(widget_factory: Callable[[], QWidget]):
        loader.register_component(
            name, category, widget_factory, priority, dependencies
        )
        return widget_factory

    return decorator
