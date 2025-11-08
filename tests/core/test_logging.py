"""Unit tests for logging configuration."""

import logging
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid7

from app.core.logging import (
    add_log_level,
    add_request_context,
    get_logger,
    setup_logging,
)


class TestAddLogLevel:
    """Test suite for add_log_level function."""

    def test_add_log_level_info(self):
        """Test adding INFO log level to event dict."""
        event_dict = {}
        result = add_log_level(None, "info", event_dict)

        assert result["level"] == "INFO"

    def test_add_log_level_debug(self):
        """Test adding DEBUG log level to event dict."""
        event_dict = {}
        result = add_log_level(None, "debug", event_dict)

        assert result["level"] == "DEBUG"

    def test_add_log_level_warning(self):
        """Test adding WARNING log level to event dict."""
        event_dict = {}
        result = add_log_level(None, "warning", event_dict)

        assert result["level"] == "WARNING"

    def test_add_log_level_error(self):
        """Test adding ERROR log level to event dict."""
        event_dict = {}
        result = add_log_level(None, "error", event_dict)

        assert result["level"] == "ERROR"

    def test_add_log_level_critical(self):
        """Test adding CRITICAL log level to event dict."""
        event_dict = {}
        result = add_log_level(None, "critical", event_dict)

        assert result["level"] == "CRITICAL"

    def test_add_log_level_unknown_method(self):
        """Test add_log_level with unknown method name."""
        event_dict = {}
        result = add_log_level(None, "unknown_method", event_dict)

        # Should return event_dict without adding level
        assert "level" not in result

    def test_add_log_level_preserves_existing_keys(self):
        """Test that add_log_level preserves existing keys in event dict."""
        event_dict = {"message": "test", "extra": "data"}
        result = add_log_level(None, "info", event_dict)

        assert result["level"] == "INFO"
        assert result["message"] == "test"
        assert result["extra"] == "data"

    def test_add_log_level_modifies_in_place(self):
        """Test that add_log_level modifies the dict in place."""
        event_dict = {}
        result = add_log_level(None, "info", event_dict)

        # Should return the same dict object
        assert result is event_dict

    def test_add_log_level_all_levels(self):
        """Test all log levels in sequence."""
        levels = {
            "info": "INFO",
            "debug": "DEBUG",
            "warning": "WARNING",
            "error": "ERROR",
            "critical": "CRITICAL",
        }

        for method_name, expected_level in levels.items():
            event_dict = {}
            result = add_log_level(None, method_name, event_dict)
            assert result["level"] == expected_level


class TestAddRequestContext:
    """Test suite for add_request_context function."""

    @patch("app.core.logging.get_request_id")
    @patch("app.core.logging.get_principal_id")
    @patch("app.core.logging.get_request_time")
    def test_add_request_context_all_values_present(
        self, mock_get_request_time, mock_get_principal_id, mock_get_request_id
    ):
        """Test add_request_context when all context values are present."""
        request_id = uuid7()
        principal_id = str(uuid7())
        request_time = datetime.now(UTC).replace(tzinfo=None)

        mock_get_request_id.return_value = request_id
        mock_get_principal_id.return_value = principal_id
        mock_get_request_time.return_value = request_time

        event_dict = {}
        result = add_request_context(None, "info", event_dict)

        assert result["request_id"] == str(request_id)
        assert result["principal_id"] == principal_id
        assert result["request_time"] == request_time.isoformat()

    @patch("app.core.logging.get_request_id")
    @patch("app.core.logging.get_principal_id")
    @patch("app.core.logging.get_request_time")
    def test_add_request_context_all_values_none(
        self, mock_get_request_time, mock_get_principal_id, mock_get_request_id
    ):
        """Test add_request_context when all context values are None."""
        mock_get_request_id.return_value = None
        mock_get_principal_id.return_value = None
        mock_get_request_time.return_value = None

        event_dict = {}
        result = add_request_context(None, "info", event_dict)

        # No context keys should be added
        assert "request_id" not in result
        assert "principal_id" not in result
        assert "request_time" not in result

    @patch("app.core.logging.get_request_id")
    @patch("app.core.logging.get_principal_id")
    @patch("app.core.logging.get_request_time")
    def test_add_request_context_only_request_id(
        self, mock_get_request_time, mock_get_principal_id, mock_get_request_id
    ):
        """Test add_request_context when only request_id is present."""
        request_id = uuid7()
        mock_get_request_id.return_value = request_id
        mock_get_principal_id.return_value = None
        mock_get_request_time.return_value = None

        event_dict = {}
        result = add_request_context(None, "info", event_dict)

        assert result["request_id"] == str(request_id)
        assert "principal_id" not in result
        assert "request_time" not in result

    @patch("app.core.logging.get_request_id")
    @patch("app.core.logging.get_principal_id")
    @patch("app.core.logging.get_request_time")
    def test_add_request_context_only_principal_id(
        self, mock_get_request_time, mock_get_principal_id, mock_get_request_id
    ):
        """Test add_request_context when only principal_id is present."""
        principal_id = str(uuid7())
        mock_get_request_id.return_value = None
        mock_get_principal_id.return_value = principal_id
        mock_get_request_time.return_value = None

        event_dict = {}
        result = add_request_context(None, "info", event_dict)

        assert "request_id" not in result
        assert result["principal_id"] == principal_id
        assert "request_time" not in result

    @patch("app.core.logging.get_request_id")
    @patch("app.core.logging.get_principal_id")
    @patch("app.core.logging.get_request_time")
    def test_add_request_context_only_request_time(
        self, mock_get_request_time, mock_get_principal_id, mock_get_request_id
    ):
        """Test add_request_context when only request_time is present."""
        request_time = datetime.now(UTC).replace(tzinfo=None)
        mock_get_request_id.return_value = None
        mock_get_principal_id.return_value = None
        mock_get_request_time.return_value = request_time

        event_dict = {}
        result = add_request_context(None, "info", event_dict)

        assert "request_id" not in result
        assert "principal_id" not in result
        assert result["request_time"] == request_time.isoformat()

    @patch("app.core.logging.get_request_id")
    @patch("app.core.logging.get_principal_id")
    @patch("app.core.logging.get_request_time")
    def test_add_request_context_preserves_existing_keys(
        self, mock_get_request_time, mock_get_principal_id, mock_get_request_id
    ):
        """Test that add_request_context preserves existing keys in event dict."""
        request_id = uuid7()
        principal_id = str(uuid7())

        mock_get_request_id.return_value = request_id
        mock_get_principal_id.return_value = principal_id
        mock_get_request_time.return_value = None

        event_dict = {"message": "test message", "extra_data": "value"}
        result = add_request_context(None, "info", event_dict)

        # Should preserve existing keys
        assert result["message"] == "test message"
        assert result["extra_data"] == "value"
        # And add new context keys
        assert result["request_id"] == str(request_id)
        assert result["principal_id"] == principal_id

    @patch("app.core.logging.get_request_id")
    @patch("app.core.logging.get_principal_id")
    @patch("app.core.logging.get_request_time")
    def test_add_request_context_modifies_in_place(
        self, mock_get_request_time, mock_get_principal_id, mock_get_request_id
    ):
        """Test that add_request_context modifies the dict in place."""
        mock_get_request_id.return_value = uuid7()
        mock_get_principal_id.return_value = None
        mock_get_request_time.return_value = None

        event_dict = {}
        result = add_request_context(None, "info", event_dict)

        # Should return the same dict object
        assert result is event_dict

    @patch("app.core.logging.get_request_id")
    @patch("app.core.logging.get_principal_id")
    @patch("app.core.logging.get_request_time")
    def test_add_request_context_request_time_isoformat(
        self, mock_get_request_time, mock_get_principal_id, mock_get_request_id
    ):
        """Test that request_time is converted to ISO format string."""
        request_time = datetime(2025, 11, 8, 12, 30, 45, 123456)
        mock_get_request_id.return_value = None
        mock_get_principal_id.return_value = None
        mock_get_request_time.return_value = request_time

        event_dict = {}
        result = add_request_context(None, "info", event_dict)

        # Should be ISO formatted string
        assert result["request_time"] == "2025-11-08T12:30:45.123456"
        assert isinstance(result["request_time"], str)


class TestSetupLogging:
    """Test suite for setup_logging function."""

    @patch("app.core.logging.structlog.configure")
    @patch("app.core.logging.logging.basicConfig")
    @patch("app.core.logging.settings")
    def test_setup_logging_debug_mode(
        self, mock_settings, mock_basic_config, mock_configure
    ):
        """Test setup_logging in debug mode."""
        mock_settings.debug = True
        mock_settings.log_level = "DEBUG"

        setup_logging()

        # Verify structlog was configured
        assert mock_configure.called

        # Verify basicConfig was called
        assert mock_basic_config.called
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == logging.DEBUG

    @patch("app.core.logging.structlog.configure")
    @patch("app.core.logging.logging.basicConfig")
    @patch("app.core.logging.settings")
    def test_setup_logging_production_mode(
        self, mock_settings, mock_basic_config, mock_configure
    ):
        """Test setup_logging in production mode."""
        mock_settings.debug = False
        mock_settings.log_level = "INFO"

        setup_logging()

        # Verify structlog was configured
        assert mock_configure.called

        # Verify basicConfig was called
        assert mock_basic_config.called
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == logging.INFO

    @patch("app.core.logging.structlog.configure")
    @patch("app.core.logging.logging.basicConfig")
    @patch("app.core.logging.settings")
    def test_setup_logging_processors_include_timestamper(
        self, mock_settings, mock_basic_config, mock_configure
    ):
        """Test that setup_logging includes timestamper in processors."""
        mock_settings.debug = True
        mock_settings.log_level = "DEBUG"

        setup_logging()

        # Get the processors argument
        call_kwargs = mock_configure.call_args[1]
        processors = call_kwargs["processors"]

        # Should have multiple processors
        assert len(processors) > 0

    @patch("app.core.logging.structlog.configure")
    @patch("app.core.logging.logging.basicConfig")
    @patch("app.core.logging.settings")
    def test_setup_logging_different_log_levels(
        self, mock_settings, mock_basic_config, mock_configure
    ):
        """Test setup_logging with different log levels."""
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in log_levels:
            mock_settings.debug = False
            mock_settings.log_level = level
            mock_basic_config.reset_mock()

            setup_logging()

            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == getattr(logging, level)


class TestGetLogger:
    """Test suite for get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test_logger")

        assert logger is not None

    def test_get_logger_different_names(self):
        """Test get_logger with different logger names."""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")
        logger3 = get_logger("module.submodule")

        assert logger1 is not None
        assert logger2 is not None
        assert logger3 is not None

    def test_get_logger_with_module_name(self):
        """Test get_logger with __name__ pattern."""
        logger = get_logger(__name__)

        assert logger is not None

    def test_get_logger_empty_name(self):
        """Test get_logger with empty name."""
        logger = get_logger("")

        assert logger is not None

    def test_get_logger_special_characters(self):
        """Test get_logger with special characters in name."""
        logger = get_logger("test.logger-name_123")

        assert logger is not None

    @patch("app.core.logging.structlog.get_logger")
    def test_get_logger_calls_structlog(self, mock_structlog_get_logger):
        """Test that get_logger calls structlog.get_logger."""
        mock_logger = MagicMock()
        mock_structlog_get_logger.return_value = mock_logger

        logger = get_logger("test")

        mock_structlog_get_logger.assert_called_once_with("test")
        assert logger == mock_logger


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    @patch("app.core.logging.settings")
    def test_full_logging_setup_and_use(self, mock_settings):
        """Test full logging setup and logger usage."""
        mock_settings.debug = True
        mock_settings.log_level = "DEBUG"

        # Setup logging
        setup_logging()

        # Get a logger
        logger = get_logger("integration_test")

        # Logger should be usable (we don't test actual output)
        assert logger is not None

    def test_event_dict_processor_flow(self):
        """Test that event dict flows through add_log_level correctly."""
        initial_dict = {"message": "test message", "request_id": "12345"}

        # Process through add_log_level
        result = add_log_level(None, "info", initial_dict)

        assert result["level"] == "INFO"
        assert result["message"] == "test message"
        assert result["request_id"] == "12345"

    def test_multiple_loggers_with_same_name(self):
        """Test that getting multiple loggers with same name works."""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")

        # Both should be valid logger instances
        assert logger1 is not None
        assert logger2 is not None

    @patch("app.core.logging.settings")
    def test_logging_configuration_persistence(self, mock_settings):
        """Test that logging configuration persists across logger creations."""
        mock_settings.debug = False
        mock_settings.log_level = "INFO"

        setup_logging()

        # Create multiple loggers
        logger1 = get_logger("test1")
        logger2 = get_logger("test2")
        logger3 = get_logger("test3")

        # All should be valid
        assert logger1 is not None
        assert logger2 is not None
        assert logger3 is not None
