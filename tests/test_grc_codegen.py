"""Regression for GNU Radio 3.10's lexical variable-prefix replacement.

Requires PyYAML. This exercises generated expressions, not the scheduler.
"""
import ast
from pathlib import Path
import re
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def prefix_variables(expression, names):
    # GRC expr_replace treats unquoted names lexically, including keyword names.
    tokens = re.findall(r"'[^']*'|\"[^\"]*\"|[A-Za-z0-9_.]+|.", expression)
    return ''.join('self.' + token if token in names else token for token in tokens)


class GrcCodegenTests(unittest.TestCase):
    def test_original_keyword_collision_is_reproduced(self):
        with self.assertRaises(SyntaxError):
            ast.parse(prefix_variables('dict(cycles=cycles)', {'cycles'}), mode='eval')

    def test_all_variable_setter_expressions_compile(self):
        graph = yaml.safe_load((ROOT / 'simulation/full_simulation.grc').read_text())
        variables = {b['name']: b['parameters']['value'] for b in graph['blocks']
                     if b['id'] == 'variable'}
        for name, expression in variables.items():
            with self.subTest(variable=name):
                rewritten = prefix_variables(expression, variables)
                ast.parse('self.set_' + name + '(' + rewritten + ')')
        original = variables['run_config']
        rewritten = prefix_variables(original, variables)
        original_keys = [k.value for k in ast.parse(original, mode='eval').body.keys]
        rewritten_keys = [k.value for k in ast.parse(rewritten, mode='eval').body.keys]
        self.assertEqual(original_keys, rewritten_keys)
        self.assertIn('cycles', rewritten_keys)
        self.assertIn("'cycles': self.cycles", rewritten)


if __name__ == '__main__':
    unittest.main()
