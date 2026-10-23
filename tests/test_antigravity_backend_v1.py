"""Authenticated Antigravity explicit catalog route contracts."""
from __future__ import annotations
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from cite_refinery.external_llm_runtime import invoke_semantic_llm, LLMUnavailable

PROMPT="Review a claim against literal publisher evidence. Preserve original scope, distinguish source wording from causal attribution, and return a JSON decision only. "*2

class AntigravityBackendTests(unittest.TestCase):
    def setUp(self):
        # Each contract test exercises a mocked subprocess, never a live CLI.
        # An explicit inert binary path is required by the runtime's safe
        # fail-closed CLI-presence guard; no installation or network needed.
        env = patch.dict("os.environ", {"CITE_REFINERY_ANTIGRAVITY_BIN": "/opt/fake-agy-cli"})
        env.start()
        self.addCleanup(env.stop)

    def test_model_invocation_is_sandboxed_and_bounded(self):
        commands=[]
        def completed(command,**kwargs):
            commands.append((command,kwargs))
            body={"status":"SUCCESS","response":json.dumps({"decision":"inconclusive","reason":"No original raw observations were provided."}),
                  "num_turns":1}
            return subprocess.CompletedProcess(command,0,stdout=json.dumps(body),stderr="")
        with patch.dict("os.environ",{"CITE_REFINERY_ANTIGRAVITY_BIN":"/opt/agy"}):
            with patch("cite_refinery.external_llm_runtime.subprocess.run",side_effect=completed):
                result=invoke_semantic_llm(PROMPT,provider="antigravity",model="gemini-3.8-flash-high",timeout_seconds=90)
        argv,kw=commands[0]
        self.assertEqual(argv[0],"/opt/agy")
        self.assertEqual(argv[argv.index("--model")+1],"gemini-3.8-flash-high")
        self.assertEqual(argv[argv.index("--mode")+1],"plan")
        self.assertIn("--sandbox",argv)
        self.assertIn("--disable-slash-commands",argv)
        self.assertNotIn("--dangerously-skip-permissions",argv)
        self.assertIn("--print-timeout",argv)
        self.assertEqual(argv[argv.index("--print-timeout")+1],"85s")
        self.assertIn("Do not use tools.",argv[-1])
        self.assertTrue(kw["cwd"].startswith(tempfile.gettempdir()))
        self.assertIn("cite-refinery-readonly-llm-",kw["cwd"])
        self.assertEqual(kw["input"],"")
        self.assertEqual(result["raw"]["decision"],"inconclusive")

    def test_failed_model_status_is_rejected(self):
        data=json.dumps({"status":"ERROR","response":'{"decision":"supported"}'})
        with patch("cite_refinery.external_llm_runtime.subprocess.run",
                   return_value=subprocess.CompletedProcess([],0,stdout=data,stderr="")):
            with self.assertRaises(LLMUnavailable):
                invoke_semantic_llm(PROMPT,provider="antigravity",timeout_seconds=60)

    def test_model_id_is_catalog_scoped_no_guessing(self):
        with self.assertRaises(ValueError):
            invoke_semantic_llm(PROMPT,provider="antigravity",model="gemini-3.8-flash-unknown")
        with self.assertRaises(ValueError):
            invoke_semantic_llm(PROMPT,provider="antigravity",model="gemini-4-argon")
    def test_explicit_argon_opus_sonnet_55_catalog_ids(self):
        for model in ("gemini-4-argon-medium", "claude-opus-5-5-medium",
                      "claude-sonnet-5-5-medium"):
            calls=[]
            def mock_run(command,**kwargs):
                calls.append(command)
                return subprocess.CompletedProcess(command,0,stdout=json.dumps({
                    "status":"SUCCESS","response":'{"verdict":"candidate_only"}'}),
                    stderr="")
            with self.subTest(model=model):
                with patch("cite_refinery.external_llm_runtime.subprocess.run",side_effect=mock_run):
                    r=invoke_semantic_llm(PROMPT,provider="antigravity",model=model)
                self.assertEqual(r["model"],model)
                self.assertEqual(calls[0][calls[0].index("--model")+1],model)
                self.assertIn("--sandbox",calls[0])
                self.assertIn("Do not use tools.",calls[0][-1])
                self.assertEqual(r["raw"]["verdict"],"candidate_only")
        for malformed in ("claude-opus-5.5", "gemini-4-argon-ultra",
                          "claude-sonnet-5-5", "claude-opus-5-5-unknown"):
            with self.assertRaises(ValueError):
                invoke_semantic_llm(PROMPT,provider="antigravity",model=malformed)

    def test_default_selects_gemini_medium(self):
        def mock_run(command,**kwargs):
            self.assertEqual(command[command.index("--model")+1],"gemini-3.8-flash-medium")
            return subprocess.CompletedProcess(command,0,stdout=json.dumps({
                "status":"SUCCESS","response":'{"ok":true}'}),stderr="")
        with patch("cite_refinery.external_llm_runtime.subprocess.run",side_effect=mock_run):
            r=invoke_semantic_llm(PROMPT,provider="antigravity")
        self.assertTrue(r["raw"]["ok"])
        self.assertEqual(r["model"],"gemini-3.8-flash-medium")

if __name__=="__main__":
    unittest.main()
