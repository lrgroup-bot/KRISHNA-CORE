"""Guard explicit-language exact-output behavior in the canonical persona."""
import unittest

from krishna_core.character_persona import KrishnaCharacterPersona


class TestPersonaExactOutput(unittest.TestCase):
    def test_odia_default_preserved_with_literal_override(self):
        contract = KrishnaCharacterPersona.prompt_contract()
        self.assertIn("defaults to natural Odia", contract)
        self.assertIn("exact literal output", contract)
        self.assertIn("do not prepend Odia greetings", contract)
        self.assertIn("This exception does not authorize unsafe actions", contract)


if __name__ == "__main__":
    unittest.main()
