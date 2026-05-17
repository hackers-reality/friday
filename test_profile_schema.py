"""
Tests for Friday Profile Schema validation.
"""
import sys, os, json, unittest, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from friday.profile_schema import (
    validate_profile,
    validate_profile_file,
    PROFILE_SCHEMA,
)


class TestProfileSchema(unittest.TestCase):
    def test_schema_is_dict(self):
        self.assertIsInstance(PROFILE_SCHEMA, dict)
        self.assertIn("properties", PROFILE_SCHEMA)

    def test_valid_minimal_profile(self):
        profile = {"name": "Tony Stark"}
        valid, errors = validate_profile(profile)
        self.assertTrue(valid, f"Unexpected errors: {errors}")

    def test_valid_full_profile(self):
        profile = {
            "name": "Tony Stark",
            "age": 40,
            "location": "Malibu",
            "occupation": "Engineer",
            "interests": [{"item": "Engineering", "confidence": 0.9}],
            "_version": 5,
            "_profile_confidence": 0.85,
        }
        valid, errors = validate_profile(profile)
        self.assertTrue(valid, f"Unexpected errors: {errors}")

    def test_missing_name(self):
        profile = {"age": 30}
        valid, errors = validate_profile(profile)
        self.assertFalse(valid)
        self.assertTrue(any("name" in e for e in errors))

    def test_wrong_type_name(self):
        profile = {"name": 42}
        valid, errors = validate_profile(profile)
        self.assertFalse(valid)
        self.assertTrue(any("name" in e for e in errors))

    def test_array_field_not_list(self):
        profile = {"name": "Test", "interests": "not a list"}
        valid, errors = validate_profile(profile)
        self.assertFalse(valid)
        self.assertTrue(any("interests" in e for e in errors))

    def test_array_item_missing_item(self):
        profile = {"name": "Test", "interests": [{"confidence": 0.5}]}
        valid, errors = validate_profile(profile)
        self.assertFalse(valid)
        self.assertTrue(any("item" in e for e in errors))

    def test_invalid_version(self):
        profile = {"name": "Test", "_version": "five"}
        valid, errors = validate_profile(profile)
        self.assertFalse(valid)
        self.assertTrue(any("_version" in e for e in errors))

    def test_confidence_out_of_range(self):
        profile = {"name": "Test", "_profile_confidence": 1.5}
        valid, errors = validate_profile(profile)
        self.assertFalse(valid)
        self.assertTrue(any("_profile_confidence" in e for e in errors))

    def test_name_too_long(self):
        profile = {"name": "X" * 201}
        valid, errors = validate_profile(profile)
        self.assertFalse(valid)
        self.assertTrue(any("200" in e for e in errors))

    def test_age_null_allowed(self):
        profile = {"name": "Test", "age": None}
        valid, errors = validate_profile(profile)
        self.assertTrue(valid, f"Unexpected errors: {errors}")

    def test_age_string_allowed(self):
        profile = {"name": "Test", "age": "30s"}
        valid, errors = validate_profile(profile)
        self.assertTrue(valid, f"Unexpected errors: {errors}")

    def test_validate_profile_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"name": "Test"}, f)
            fname = f.name
        try:
            valid, errors = validate_profile_file(fname)
            self.assertTrue(valid, f"Unexpected errors: {errors}")
        finally:
            os.unlink(fname)

    def test_validate_profile_file_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json}")
            fname = f.name
        try:
            valid, errors = validate_profile_file(fname)
            self.assertFalse(valid)
            self.assertTrue(any("JSON" in e for e in errors))
        finally:
            os.unlink(fname)

    def test_validate_profile_file_not_found(self):
        valid, errors = validate_profile_file("nonexistent_file.json")
        self.assertFalse(valid)
        self.assertTrue(any("not found" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
