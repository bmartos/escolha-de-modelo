"""Regression checks for the per-message model-routing override."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("router", Path(__file__).with_name("aplicar-plataforma.py"))
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class BypassTests(unittest.TestCase):
    def test_word_detection(self):
        for text in ("bypass", "BYPASS: corrigir bug", "/bypass sem cota", "use bypass hoje"):
            self.assertTrue(router.bypass_requested(text))
        for text in ("corrigir bug", "bypassing", "mybypass", "bypass_mode"):
            self.assertFalse(router.bypass_requested(text))

    def test_all_platforms_skip_recommendation_and_hold(self):
        for platform in ("codex", "antigravity", "claude", "grok"):
            for phase in ("pedido", "resposta"):
                with self.subTest(platform=platform, phase=phase), contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(router.sys, "stdin", io.StringIO(json.dumps({"prompt": "BYPASS corrigir bug"}))))
                    stack.enter_context(patch.object(router.sys, "argv", ["router", "--fase", phase]))
                    stack.enter_context(patch.object(router, "platform_of", return_value=platform))
                    keep = stack.enter_context(patch.object(router, "keep_configured_pair"))
                    forbidden = [stack.enter_context(patch.object(router, name, side_effect=AssertionError(name))) for name in
                                 ("rules_codex", "rules_antigravity", "rules_claude", "classify_grok", "apply_codex", "emit_hold", "log_resposta")]
                    stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                    self.assertEqual(router.main(), 0)
                    self.assertEqual(keep.call_count, int(phase == "pedido"))

    def test_codex_config_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            original = b'model = "gpt-6-luna"\r\nmodel_reasoning_effort = "medium"\r\n'
            config.write_bytes(original)
            with patch.object(router, "CODEX_CONFIG", config), patch.object(router, "log_pair") as log:
                router.keep_configured_pair({}, "codex", "bypass arquitetura")
                self.assertEqual(config.read_bytes(), original)
                self.assertEqual(log.call_args.args[0]["model"], "gpt-6-luna")
                self.assertEqual(log.call_args.args[0]["effort"], "medium")
                self.assertEqual(log.call_args.args[0]["fonte"], "bypass")

    def test_unreadable_selector_or_log_does_not_block(self):
        with patch.object(router, "selector_grok", return_value=None), patch.object(router, "log_pair", side_effect=PermissionError):
            router.keep_configured_pair({}, "grok", "bypass")

    def test_next_message_routes_normally(self):
        with patch.object(router.sys, "stdin", io.StringIO('{"prompt":"corrigir bug"}')), patch.object(router, "platform_of", return_value="codex"), patch.object(router.sys, "argv", ["router"]), patch.object(router, "apply_codex", return_value=("pedido", ("gpt-6-luna", "medium"))) as apply, patch.object(router, "log_pair"), patch.object(router, "emit_hold") as hold:
            self.assertEqual(router.main(), 0)
            apply.assert_called_once()
            hold.assert_called_once()


if __name__ == "__main__":
    unittest.main()
