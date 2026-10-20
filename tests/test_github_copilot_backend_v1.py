"""GitHub Copilot CLI backend: explicit account, isolated tool-free inference."""
from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from cite_refinery.external_llm_runtime import (
    invoke_semantic_llm,LLMUnavailable,_copilot_json_from_stdout,
)
from cite_refinery.investigation_controller import InvestigationController
from test_investigation_controller_v1 import MODULES
from tempfile import TemporaryDirectory, gettempdir

PROMPT="Find distinct scholarly and institutional evidence for the dog population census and give an evidence-bounded JSON research planning response. "*3


class GithubCopilotBackendTests(unittest.TestCase):
    def test_copilot_uses_explicit_launcher_with_empty_tool_catalog(self):
        commands=[]
        def simulate(command,**kwargs):
            commands.append((command,kwargs))
            return subprocess.CompletedProcess(command,0,
                stdout='{"focus":"Canine abundance measurement differs from sterilization counts","queries":[{"lane":"academic","query":"dog detectability population survey"},{"lane":"official","query":"WHO dog population monitoring"}]}',
                stderr='')
        with patch.dict('os.environ',{'CITE_REFINERY_COPILOT_BIN':'/machine/copilot-student'}):
            with patch('cite_refinery.external_llm_runtime.subprocess.run',side_effect=simulate):
                result=invoke_semantic_llm(PROMPT,provider="copilot",timeout_seconds=45)
        argv,options=commands[0]
        self.assertEqual(argv[0],'/machine/copilot-student')
        self.assertIn('--disable-builtin-mcps',argv)
        self.assertIn('--available-tools',argv)
        self.assertEqual(argv[argv.index('--available-tools')+1],"")
        self.assertIn('--allow-all-tools',argv)
        self.assertEqual(argv[argv.index('--model')+1],'auto')
        self.assertIn('--disable-client-telemetry',argv)
        self.assertNotIn('--allow-all-paths',argv)
        self.assertNotIn('--allow-all-urls',argv)
        self.assertNotIn('--share-gist',argv)
        self.assertNotIn('--share',argv)
        self.assertNotIn('--add-dir',argv)
        self.assertNotIn('--enable-memory',argv)
        self.assertEqual(options['input'],"")
        self.assertTrue(options['cwd'].startswith(gettempdir()))
        self.assertIn("cite-refinery-readonly-llm-",options['cwd'])
        self.assertEqual(result['raw']['queries'][0]['lane'],'academic')
        self.assertEqual(result['provider'],'copilot')
        self.assertEqual(result['model'],'auto')

    def test_copilot_wrapper_banner_before_valid_json(self):
        banner='● Disabled tools: edit, glob, grep, sql, view\n● Unknown tool in excludedlist: report_intent\n'
        answer=_copilot_json_from_stdout(banner+'{"valid":true,"result":"source observations"}\n')
        self.assertTrue(answer['valid'])
        with self.assertRaises(LLMUnavailable):
            _copilot_json_from_stdout(banner+'not a model answer')
        with self.assertRaises(LLMUnavailable):
            _copilot_json_from_stdout('{"result": true}\nnot a valid reply')

    def test_copilot_quota_surfaces_even_when_wrapper_swallow_exit_code(self):
        with patch.dict('os.environ',{'CITE_REFINERY_COPILOT_BIN':'/machine/copilot-ly2'}):
            with patch('cite_refinery.external_llm_runtime.subprocess.run',
                       return_value=subprocess.CompletedProcess([],
                           0,stdout='● Disabled tools: edit, glob',
                           stderr='You have exceeded your monthly quota (Request ID: confidential)')):
                with self.assertRaisesRegex(LLMUnavailable,"Copilot quota"):
                    invoke_semantic_llm(PROMPT,provider='copilot',timeout_seconds=45)

    def test_provider_auth_failure_does_not_dump_stderr_token(self):
        with patch.dict('os.environ',{'CITE_REFINERY_COPILOT_BIN':'/machine/copilot'}):
            with patch('cite_refinery.external_llm_runtime.subprocess.run',
                       return_value=subprocess.CompletedProcess([],1,stdout='',
                           stderr='auth failed account x with token ghp_SECRET_IN_LOG')):
                with self.assertRaises(LLMUnavailable) as ctx:
                    invoke_semantic_llm(PROMPT,provider='copilot',timeout_seconds=45)
        self.assertNotIn('ghp_SECRET',str(ctx.exception))
        self.assertIn('check authentication',str(ctx.exception))

    def test_real_controller_checkpoint_advances_through_copilot_provider_contract(self):
        plan={"focus":"Why independent dog abundance monitoring differs from sterilization catch rates",
              "reason":"Test availability of consistent field surveys versus institutional dog rabies reporting.",
              "hypotheses":["Regional population trends may differ from intervention intake counts."],
              "queries":[{"lane":"academic","query":"independent population resighting dog rabies"},
                         {"lane":"official","query":"WHO WOAH surveillance dog population sampling"}]}
        with TemporaryDirectory() as root:
            ctrl=InvestigationController(root,reasoner=lambda prompt:
                invoke_semantic_llm(prompt,provider="copilot",model="auto",timeout_seconds=90)["raw"])
            s=ctrl.start('Which independent field surveys can validate canine rabies intervention impact?',MODULES)
            with patch.dict('os.environ',{'CITE_REFINERY_COPILOT_BIN':'/machine/copilot-spectator'}):
                with patch('cite_refinery.external_llm_runtime.subprocess.run',
                           return_value=subprocess.CompletedProcess([],0,
                               stdout='● Disabled tools: edit, glob, grep\n'+__import__('json').dumps(plan),stderr='')):
                    advanced=ctrl.step(s['id'])
            self.assertEqual(advanced['stage'],'collect')
            self.assertEqual(advanced['rounds'][0]['plan']['focus'],plan['focus'])
            self.assertEqual(ctrl.load(s['id'])['stage'],'collect')
            self.assertEqual(len(advanced['rounds'][0]['plan']['queries']),2)

    def test_invalid_json_is_rejected_without_fabricated_result(self):
        with patch.dict('os.environ',{'CITE_REFINERY_COPILOT_BIN':'/machine/copilot'}):
            with patch('cite_refinery.external_llm_runtime.subprocess.run',
                       return_value=subprocess.CompletedProcess([],0,stdout='Your research is done.',stderr='')):
                with self.assertRaisesRegex(LLMUnavailable,'valid JSON research object'):
                    invoke_semantic_llm(PROMPT,provider='copilot',timeout_seconds=30)

if __name__=="__main__":unittest.main()
