import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "public" / "app.js"
INDEX_HTML = ROOT / "public" / "index.html"


def extract_translation_body(source: str, language: str) -> str:
    marker = f"  {language}: {{"
    start = source.index(marker) + len(marker)
    depth = 1
    index = start
    in_string = False
    escaped = False
    while index < len(source):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return source[start:index]
        index += 1
    raise AssertionError(f"Could not parse {language} translations")


def translation_keys(source: str, language: str) -> set[str]:
    body = extract_translation_body(source, language)
    return set(re.findall(r'"([^"]+)":', body))


class FrontendI18nTests(unittest.TestCase):
    def setUp(self):
        self.app_js = APP_JS.read_text(encoding="utf-8")
        self.index_html = INDEX_HTML.read_text(encoding="utf-8")
        self.en_keys = translation_keys(self.app_js, "en")
        self.de_keys = translation_keys(self.app_js, "de")

    def test_english_and_german_dictionaries_have_same_keys(self):
        self.assertEqual(self.en_keys, self.de_keys)

    def test_html_i18n_attributes_reference_existing_keys(self):
        keys = set()
        keys.update(re.findall(r'data-i18n="([^"]+)"', self.index_html))
        keys.update(re.findall(r'data-i18n-title="([^"]+)"', self.index_html))
        keys.update(re.findall(r'data-i18n-aria-label="([^"]+)"', self.index_html))

        self.assertTrue(keys)
        self.assertLessEqual(keys, self.en_keys)

    def test_static_translation_calls_reference_existing_keys(self):
        keys = set(re.findall(r'(?<![A-Za-z0-9_$])t\("([^"`{]+)"', self.app_js))
        self.assertTrue(keys)
        self.assertLessEqual(keys, self.en_keys)

    def test_language_switch_exposes_en_and_de(self):
        self.assertIn('data-lang="en"', self.index_html)
        self.assertIn('data-lang="de"', self.index_html)


if __name__ == "__main__":
    unittest.main()
