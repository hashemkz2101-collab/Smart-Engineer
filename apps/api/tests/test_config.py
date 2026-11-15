import unittest

from smart_engineer_api.config import ConfigurationError, Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_when_environment_is_empty(self) -> None:
        settings = Settings.from_env({})

        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.log_level, "INFO")

    def test_valid_values_are_read_and_normalized(self) -> None:
        settings = Settings.from_env(
            {"SMART_ENGINEER_ENV": " Production ", "SMART_ENGINEER_LOG_LEVEL": "warning"}
        )

        self.assertEqual(settings.environment, "production")
        self.assertEqual(settings.log_level, "WARNING")

    def test_invalid_environment_is_rejected_explicitly(self) -> None:
        with self.assertRaises(ConfigurationError) as context:
            Settings.from_env({"SMART_ENGINEER_ENV": "staging"})

        self.assertIn("SMART_ENGINEER_ENV", str(context.exception))

    def test_invalid_log_level_is_rejected_explicitly(self) -> None:
        with self.assertRaises(ConfigurationError) as context:
            Settings.from_env({"SMART_ENGINEER_LOG_LEVEL": "LOUD"})

        self.assertIn("SMART_ENGINEER_LOG_LEVEL", str(context.exception))

    def test_settings_are_immutable(self) -> None:
        settings = Settings()

        with self.assertRaises(AttributeError):
            settings.environment = "production"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
