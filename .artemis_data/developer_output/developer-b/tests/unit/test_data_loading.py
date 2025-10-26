import unittest
from data_loader import load_execution_data

class TestDataLoading(unittest.TestCase):

    def test_load_execution_data_success(self):
        """Test that data is loaded successfully when file path is correct."""
        data = load_execution_data('correct_path.json')
        self.assertIsNotNone(data)

    def test_load_execution_data_file_not_found(self):
        """Test FileNotFoundError is raised when file path is incorrect."""
        with self.assertRaises(FileNotFoundError):
            load_execution_data('incorrect_path.json')

    def test_load_execution_data_invalid_format(self):
        """Test ValueError is raised for invalid file format."""
        with self.assertRaises(ValueError):
            load_execution_data('invalid_format.txt')
