"""Codex backend must be explicitly read-only, bounded, isolated, no tool use."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from cite_refinery.external_llm_runtime import invoke_semantic_llm,LLMUnavailable

class CodexBackendTests(unittest.TestCase):
    def test_isolated_read_only_codex_response(self):
        commands=[]
        def fake_run(command, **kwargs):
            commands.append(command)
            self.assertEqual(kwargs['input'], '')
            self.assertTrue(kwargs['cwd'].startswith(tempfile.gettempdir()))
            self.assertIn('cite-refinery-readonly-llm-', kwargs['cwd'])
            destination=Path(command[command.index('--output-last-message')+1])
            destination.write_text(json.dumps({'focus':'An exact bounded investigation of dog population observability',
                'queries':[{'lane':'academic','query':'dog population census'},
                           {'lane':'official','query':'WHO dog rabies vaccination'}]}))
            return subprocess.CompletedProcess(command,0,stdout='',stderr='')
        with patch.dict('os.environ', {'CITE_REFINERY_CODEX_BIN':'/some/opt-in/codex'}):
            with patch('cite_refinery.external_llm_runtime.subprocess.run',side_effect=fake_run):
                result=invoke_semantic_llm('Read source statements and produce a strict JSON investigation plan. '*3,
                                           provider='codex',model='gpt-6.1-sol',timeout_seconds=50)
        self.assertEqual(result['provider'],'codex')
        self.assertEqual(result['raw']['queries'][0]['lane'],'academic')
        self.assertIn('read-only',commands[0]); self.assertIn('--ephemeral',commands[0])
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',commands[0])
        self.assertIn('Do not use any tools.',commands[0][-1])

    def test_nonzero_codex_failure_is_explicit(self):
        with patch.dict('os.environ', {'CITE_REFINERY_CODEX_BIN':'/some/opt-in/codex'}):
            with patch('cite_refinery.external_llm_runtime.subprocess.run',return_value=subprocess.CompletedProcess([],12,'','expired OAuth token')):
                with self.assertRaises(LLMUnavailable):
                    invoke_semantic_llm('Test source information and return JSON. '*4,
                                        provider='codex',timeout_seconds=30)

if __name__=='__main__':unittest.main()
