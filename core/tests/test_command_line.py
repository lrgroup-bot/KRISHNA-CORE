import unittest

from krishna_core.command_line import split_command


class CommandLineTests(unittest.TestCase):
    def test_quoted_paths_and_arguments_are_preserved(self):
        parsed=split_command('"C:\\Program Files\\KRISHNA\\python.exe" -m worker --label "hello world"')
        self.assertEqual(parsed[0],r"C:\Program Files\KRISHNA\python.exe")
        self.assertEqual(parsed[1:4],["-m","worker","--label"])
        self.assertEqual(parsed[4],"hello world")

    def test_list_commands_remain_argument_lists(self):
        self.assertEqual(split_command(["python","-m","worker"]),["python","-m","worker"])

    def test_empty_command_is_rejected(self):
        with self.assertRaises(ValueError):
            split_command("   ",empty_message="empty")


if __name__=="__main__":
    unittest.main()
