"""
Error handling and recovery system for the LMU Configuration Editor.

Provides user-friendly error messages with recovery options and detailed logging.
"""

import os
import logging
import traceback
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import json


class ErrorType(Enum):
    """Types of errors that can occur."""

    FILE_ACCESS = "file_access"
    PARSING = "parsing"
    VALIDATION = "validation"
    SYSTEM = "system"
    GAME_STATE = "game_state"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for an error."""

    operation: str
    file_path: Optional[Path] = None
    configuration_name: Optional[str] = None
    user_action: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


@dataclass
class RecoveryOption:
    """A recovery option for an error."""

    name: str
    description: str
    action: Callable[[], bool]
    is_default: bool = False
    icon: Optional[str] = None


@dataclass
class ErrorResponse:
    """Response to an error with user message and recovery options."""

    user_message: str
    technical_message: str
    error_type: ErrorType
    severity: ErrorSeverity
    recovery_options: List[RecoveryOption]
    should_log: bool = True
    should_show_dialog: bool = True


class ErrorHandler:
    """Handles errors with user-friendly messages and recovery options."""

    def __init__(self):
        """Initialize the error handler."""
        self.logger = logging.getLogger(__name__)

        # Error type mappings
        self.error_type_mapping = {
            # File access errors
            PermissionError: ErrorType.FILE_ACCESS,
            FileNotFoundError: ErrorType.FILE_ACCESS,
            IsADirectoryError: ErrorType.FILE_ACCESS,
            OSError: ErrorType.FILE_ACCESS,
            # Parsing errors
            json.JSONDecodeError: ErrorType.PARSING,
            UnicodeDecodeError: ErrorType.PARSING,
            ValueError: ErrorType.VALIDATION,
            # System errors
            MemoryError: ErrorType.SYSTEM,
            SystemError: ErrorType.SYSTEM,
        }

        # User-friendly messages
        self.user_messages = {
            ErrorType.FILE_ACCESS: {
                PermissionError: "Access denied to configuration files. Please check file permissions.",
                FileNotFoundError: "Configuration file not found. The file may have been moved or deleted.",
                IsADirectoryError: "Expected a file but found a directory instead.",
                OSError: "Unable to access the file system. Please check if the drive is available.",
            },
            ErrorType.PARSING: {
                json.JSONDecodeError: "The configuration file contains invalid JSON format.",
                UnicodeDecodeError: "The configuration file contains invalid characters and cannot be read.",
            },
            ErrorType.VALIDATION: {
                ValueError: "The configuration contains invalid values."
            },
            ErrorType.GAME_STATE: {
                "game_running": "Le Mans Ultimate is currently running and has locked the configuration files.",
                "files_in_use": "Configuration files are currently being used by another application.",
            },
            ErrorType.SYSTEM: {
                MemoryError: "Insufficient memory to complete the operation.",
                SystemError: "A system error occurred while processing the request.",
            },
        }

    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorResponse:
        """
        Handle an error and provide user-friendly response with recovery options.

        Args:
            error: The exception that occurred
            context: Context information about the error

        Returns:
            ErrorResponse with user message and recovery options
        """
        # Determine error type
        error_type = self._get_error_type(error)

        # Get user-friendly message
        user_message = self._get_user_message(error, error_type, context)

        # Get technical message
        technical_message = self._get_technical_message(error, context)

        # Determine severity
        severity = self._get_error_severity(error, error_type)

        # Get recovery options
        recovery_options = self._get_recovery_options(error, error_type, context)

        # Create response
        response = ErrorResponse(
            user_message=user_message,
            technical_message=technical_message,
            error_type=error_type,
            severity=severity,
            recovery_options=recovery_options,
        )

        # Log the error
        if response.should_log:
            self._log_error(error, context, response)

        return response

    def _get_error_type(self, error: Exception) -> ErrorType:
        """Determine the error type from the exception."""
        error_class = type(error)

        # Check specific error codes for Windows file access
        if isinstance(error, OSError):
            if hasattr(error, "winerror"):
                if error.winerror == 32:  # File in use by another process
                    return ErrorType.GAME_STATE
                elif error.winerror == 5:  # Access denied
                    return ErrorType.FILE_ACCESS

        return self.error_type_mapping.get(error_class, ErrorType.UNKNOWN)

    def _get_user_message(
        self, error: Exception, error_type: ErrorType, context: ErrorContext
    ) -> str:
        """Get user-friendly error message."""
        error_class = type(error)

        # Check for specific game state errors
        if error_type == ErrorType.GAME_STATE:
            if (
                isinstance(error, OSError)
                and hasattr(error, "winerror")
                and error.winerror == 32
            ):
                return (
                    "Cannot save configuration files because Le Mans Ultimate is currently running.\n\n"
                    "Please close the game and try again."
                )

        # Get base message from mapping
        if error_type in self.user_messages:
            type_messages = self.user_messages[error_type]
            if error_class in type_messages:
                base_message = type_messages[error_class]
            else:
                # Use first message as fallback
                base_message = next(iter(type_messages.values()), "An error occurred.")
        else:
            base_message = "An unexpected error occurred."

        # Add context-specific information
        if context.operation:
            base_message = f"Failed to {context.operation.lower()}.\n\n{base_message}"

        if context.file_path:
            base_message += f"\n\nFile: {context.file_path}"

        if context.configuration_name:
            base_message += f"\n\nConfiguration: {context.configuration_name}"

        return base_message

    def _get_technical_message(self, error: Exception, context: ErrorContext) -> str:
        """Get technical error message for logging."""
        message_parts = [
            f"Exception: {type(error).__name__}: {str(error)}",
            f"Operation: {context.operation}",
        ]

        if context.file_path:
            message_parts.append(f"File: {context.file_path}")

        if context.configuration_name:
            message_parts.append(f"Configuration: {context.configuration_name}")

        if context.user_action:
            message_parts.append(f"User Action: {context.user_action}")

        if context.additional_info:
            message_parts.append(f"Additional Info: {context.additional_info}")

        # Add stack trace for debugging
        message_parts.append(f"Stack Trace:\n{traceback.format_exc()}")

        return "\n".join(message_parts)

    def _get_error_severity(
        self, error: Exception, error_type: ErrorType
    ) -> ErrorSeverity:
        """Determine error severity."""
        if isinstance(error, (MemoryError, SystemError)):
            return ErrorSeverity.CRITICAL
        elif error_type in (ErrorType.FILE_ACCESS, ErrorType.PARSING):
            return ErrorSeverity.ERROR
        elif error_type == ErrorType.GAME_STATE:
            return ErrorSeverity.WARNING
        else:
            return ErrorSeverity.ERROR

    def _get_recovery_options(
        self, error: Exception, error_type: ErrorType, context: ErrorContext
    ) -> List[RecoveryOption]:
        """Get recovery options for the error."""
        options = []

        if error_type == ErrorType.GAME_STATE:
            # Game is running - offer retry after closing
            options.append(
                RecoveryOption(
                    name="Retry",
                    description="Try again after closing Le Mans Ultimate",
                    action=lambda: True,  # Placeholder - actual retry logic handled by caller
                    is_default=True,
                    icon="refresh",
                )
            )

        elif error_type == ErrorType.FILE_ACCESS:
            if isinstance(error, PermissionError):
                options.append(
                    RecoveryOption(
                        name="Run as Administrator",
                        description="Restart the application with administrator privileges",
                        action=lambda: self._suggest_admin_restart(),
                        icon="shield",
                    )
                )

            if isinstance(error, FileNotFoundError):
                options.append(
                    RecoveryOption(
                        name="Browse for File",
                        description="Manually locate the configuration file",
                        action=lambda: True,  # Handled by caller
                        is_default=True,
                        icon="folder",
                    )
                )

                options.append(
                    RecoveryOption(
                        name="Use Default",
                        description="Create a new configuration file with default settings",
                        action=lambda: self._create_default_config(context),
                        icon="document",
                    )
                )

        elif error_type == ErrorType.PARSING:
            options.append(
                RecoveryOption(
                    name="Open in Text Editor",
                    description="Open the file in a text editor to fix manually",
                    action=lambda: self._open_in_editor(context.file_path),
                    icon="edit",
                )
            )

            options.append(
                RecoveryOption(
                    name="Restore Backup",
                    description="Restore from backup file if available",
                    action=lambda: self._restore_backup(context.file_path),
                    icon="backup",
                )
            )

        # Always offer basic options
        options.append(
            RecoveryOption(
                name="Cancel",
                description="Cancel the current operation",
                action=lambda: False,
                icon="cancel",
            )
        )

        options.append(
            RecoveryOption(
                name="Report Issue",
                description="Copy error details to clipboard for support",
                action=lambda: self._copy_error_to_clipboard(error, context),
                icon="clipboard",
            )
        )

        return options

    def _log_error(
        self, error: Exception, context: ErrorContext, response: ErrorResponse
    ) -> None:
        """Log the error with appropriate level."""
        (f"Error in {context.operation}: {type(error).__name__}: {str(error)}")

        if response.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(response.technical_message)
        elif response.severity == ErrorSeverity.ERROR:
            self.logger.error(response.technical_message)
        elif response.severity == ErrorSeverity.WARNING:
            self.logger.warning(response.technical_message)
        else:
            self.logger.info(response.technical_message)

    def _suggest_admin_restart(self) -> bool:
        """Suggest restarting application as administrator."""
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            None,
            "Administrator Rights Required",
            "This operation requires administrator privileges.\n\n"
            "Would you like to restart the application as administrator?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Implementation would restart app with admin rights
            # For now, just show message
            QMessageBox.information(
                None,
                "Manual Restart Required",
                "Please close the application and restart it by right-clicking "
                "and selecting 'Run as administrator'.",
            )

        return False

    def _create_default_config(self, context: ErrorContext) -> bool:
        """Create a default configuration file."""
        if not context.file_path:
            return False

        try:
            # Create a basic default configuration
            if context.file_path.suffix.lower() == ".json":
                default_config = {"DEFAULT": {"Created": "by LMU Config Editor"}}
                with open(context.file_path, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=2)
            else:
                # INI file
                with open(context.file_path, "w", encoding="utf-8") as f:
                    f.write("[DEFAULT]\nCreated=by LMU Config Editor\n")

            return True
        except Exception as e:
            self.logger.error(f"Failed to create default config: {e}")
            return False

    def _open_in_editor(self, file_path: Optional[Path]) -> bool:
        """Open file in system text editor."""
        if not file_path or not file_path.exists():
            return False

        try:
            import subprocess
            import platform

            if platform.system() == "Windows":
                os.startfile(str(file_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(file_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(file_path)])

            return True
        except Exception as e:
            self.logger.error(f"Failed to open file in editor: {e}")
            return False

    def _restore_backup(self, file_path: Optional[Path]) -> bool:
        """Restore file from backup."""
        if not file_path:
            return False

        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        if not backup_path.exists():
            return False

        try:
            import shutil

            shutil.copy2(backup_path, file_path)
            return True
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            return False

    def _copy_error_to_clipboard(self, error: Exception, context: ErrorContext) -> bool:
        """Copy error details to clipboard."""
        try:
            from PyQt6.QtWidgets import QApplication

            error_details = (
                f"LMU Configuration Editor Error Report\n"
                f"=====================================\n\n"
                f"Operation: {context.operation}\n"
                f"Error: {type(error).__name__}: {str(error)}\n"
            )

            if context.file_path:
                error_details += f"File: {context.file_path}\n"
            if context.configuration_name:
                error_details += f"Configuration: {context.configuration_name}\n"

            error_details += f"\nTechnical Details:\n{traceback.format_exc()}"

            clipboard = QApplication.clipboard()
            clipboard.setText(error_details)

            return True
        except Exception as e:
            self.logger.error(f"Failed to copy to clipboard: {e}")
            return False


# Convenience functions for common error scenarios
def handle_file_access_error(file_path: Path, operation: str) -> ErrorResponse:
    """Handle file access errors."""
    handler = ErrorHandler()
    context = ErrorContext(operation=operation, file_path=file_path)
    try:
        # Try to access the file to trigger the actual error
        file_path.open("r")
    except Exception as e:
        return handler.handle_error(e, context)

    # Shouldn't reach here, but just in case
    return ErrorResponse(
        user_message="File access succeeded",
        technical_message="No error occurred",
        error_type=ErrorType.UNKNOWN,
        severity=ErrorSeverity.INFO,
        recovery_options=[],
    )


def handle_parsing_error(
    file_path: Path, operation: str, error: Exception
) -> ErrorResponse:
    """Handle parsing errors."""
    handler = ErrorHandler()
    context = ErrorContext(operation=operation, file_path=file_path)
    return handler.handle_error(error, context)


def handle_game_state_error(
    operation: str, configuration_name: Optional[str] = None
) -> ErrorResponse:
    """Handle game state errors (game running, files locked)."""
    handler = ErrorHandler()
    context = ErrorContext(operation=operation, configuration_name=configuration_name)

    # Create a mock Windows file-in-use error
    error = OSError("File in use")
    if hasattr(error, "winerror"):
        error.winerror = 32
    else:
        # Simulate the Windows error code
        class MockWinError(OSError):
            def __init__(self, message):
                super().__init__(message)
                self.winerror = 32

        error = MockWinError("File in use")

    return handler.handle_error(error, context)
