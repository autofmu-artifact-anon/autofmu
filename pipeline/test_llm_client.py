from __future__ import annotations

import unittest

from pipeline.llm_client import _chat_completions_url


class LLMClientURLTest(unittest.TestCase):
    def test_appends_chat_completions_to_plain_base_url(self) -> None:
        self.assertEqual(
            _chat_completions_url("https://api.openai.com"),
            "https://api.openai.com/v1/chat/completions",
        )

    def test_reuses_v1_base_url_without_double_suffix(self) -> None:
        self.assertEqual(
            _chat_completions_url("https://coding.dashscope.aliyuncs.com/v1"),
            "https://coding.dashscope.aliyuncs.com/v1/chat/completions",
        )

    def test_reuses_full_chat_completions_url(self) -> None:
        self.assertEqual(
            _chat_completions_url("https://example.com/openai/v1/chat/completions"),
            "https://example.com/openai/v1/chat/completions",
        )


if __name__ == "__main__":
    unittest.main()
