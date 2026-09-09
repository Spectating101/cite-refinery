"""Browser -> saved draft -> completed return -> real CLI receipt.
All completed responses are AUTOMATED TEST DATA, never external validation.
Default mode tests file:// and HTTP; --in-memory tests DOM behavior only.
"""
import argparse
from copy import deepcopy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cite_refinery.intake_review import build_intake_owner_review_pack
from cite_refinery.owner_review_contract import validate_owner_review_response, review_context
from cite_refinery.owner_review_page import render_owner_review_page
from cite_refinery.problem_intake import OwnerIntake
from cite_refinery.problem_commons import ProblemCommons
from cite_refinery.problem_case import ProblemCaseWorkspace
from cite_refinery.review_pack import build_review_pack
from cite_refinery.intake_cli import main as intake_main


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='/tmp/owner-review-browser-proof')
    parser.add_argument('--chromium')
    parser.add_argument('--in-memory', action='store_true')
    args = parser.parse_args()
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    rubrics = json.loads((ROOT / 'pilot/rubrics.v0.1.json').read_text())
    intake = OwnerIntake.load(ROOT / 'pilot/intake/yzu-yongfeng-after-school.v0.1.json')
    packet = intake.to_problem_packet(steward='automated-test-curator')
    original = build_intake_owner_review_pack(intake, packet, rubrics=rubrics)
    issued = out / 'issued.json'; issued.write_text(json.dumps(original, ensure_ascii=False))
    standalone = out / 'owner-review.html'; standalone.write_text(render_owner_review_page(original), encoding='utf-8')
    proof = {'mode': 'in-memory' if args.in_memory else 'file-and-http', 'checks': [],
             'evidence_boundary': 'AUTOMATED TEST DATA; not owner confirmation or adoption'}
    def passed(name): proof['checks'].append(name); print('PASS:', name)
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT / 'prototype')))
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            launch = {'headless': True}
            if args.chromium: launch['executable_path'] = args.chromium
            browser = pw.chromium.launch(**launch)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            errors, outbound = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda e: errors.append(e.text) if e.type == 'error' else None)
            page.on('request', lambda r: outbound.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
            def open_page(html=None):
                nonlocal page
                if args.in_memory:
                    # set_content does not reset a window's lexical globals or CSP.
                    # A fresh page models an actual navigation without bypassing local browser policy.
                    page.close()
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.on('console', lambda e: errors.append(e.text) if e.type == 'error' else None)
                    page.on('request', lambda r: outbound.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
                    page.set_content(html or standalone.read_text(), wait_until='load')
                elif html is None: page.goto(standalone.as_uri())
                else:
                    extra = out / 'unsafe-input.html'; extra.write_text(html, encoding='utf-8'); page.goto(extra.as_uri())
            def download(selector, name):
                with page.expect_download() as event: page.locator(selector).click()
                path = out / name; event.value.save_as(path)
                return json.loads(path.read_text())
            open_page()
            assert page.locator('#intakeReviewFields').is_visible()
            assert 'Loaded problem-owner' in page.locator('#loadStatus').inner_text()
            assert not outbound, outbound
            passed('standalone loads with no network requests')
            page.screenshot(path=out / 'desktop-overview.png')
            page.locator('#intakeIdentityFields').scroll_into_view_if_needed()
            page.screenshot(path=out / 'desktop-form.png')
            page.locator('button[type=submit]').click()
            assert page.locator('#saveResponse').is_disabled()
            passed('incomplete review cannot export as completed')
            page.locator('#correctionDetails > summary').click()
            page.locator('#intakeCorrections').fill('AUTOMATED TEST: clarify the schedule.')
            page.locator('#work-choice-0').select_option('explore')
            draft = download('#saveDraft', 'draft.json')
            page.locator('#packFile').set_input_files(out / 'draft.json')
            assert page.locator('#intakeCorrections').input_value() == draft['response']['factual_corrections'][0]
            assert page.locator('#work-choice-0').input_value() == 'explore'
            passed('save/reopen retains corrections and work choices')
            page.locator('#sourceCurrent').select_option('yes')
            page.locator('#ownerCorrect').select_option('yes')
            for i in range(5): page.locator(f'input[name="score-{i}"][value="1"]').check()
            page.locator('#intakeDisposition').select_option('reframe')
            page.locator('#intakeNotes').fill('AUTOMATED TEST: not actual owner feedback.')
            page.locator('button[type=submit]').click()
            assert not page.locator('#saveResponse').is_disabled(), page.locator('#formStatus').inner_text()
            page.locator('#intakeNotes').fill('AUTOMATED TEST: edited after preparation.')
            assert page.locator('#saveResponse').is_disabled()
            passed('editing invalidates previously prepared export')
            page.locator('button[type=submit]').click()
            returned = download('#saveResponse', 'synthetic-return.json')
            assert not validate_owner_review_response(returned, require_complete=True, expected_pack=original)
            assert review_context(returned) == review_context(original)
            receipt_path = out / 'synthetic-receipt.json'
            if receipt_path.exists(): receipt_path.unlink()  # own test output only
            assert intake_main(['record-owner-review', str(out / 'synthetic-return.json'), '--original', str(issued),
                '--actor', 'automated-test-curator', '--receipt-ref', 'synthetic:browser-return', '--out', str(receipt_path)]) == 0
            receipt = json.loads(receipt_path.read_text())
            assert receipt['status'] == 'pending-curator-decision' and not receipt['work_opened']
            assert packet.status.value == 'candidate' and packet.problem_owner == ''
            passed('browser return passes real CLI without case promotion')
            for decision in ('confirm', 'stale', 'already-resolved', 'decline'):
                page.locator('#sourceCurrent').select_option('no' if decision == 'stale' else 'yes')
                page.locator('#intakeReframe').uncheck()
                page.locator('#intakeDisposition').select_option(decision)
                page.locator('button[type=submit]').click()
                result = download('#saveResponse', f'synthetic-{decision}.json')
                assert not validate_owner_review_response(result, require_complete=True, expected_pack=original)
            passed('all five final decisions round-trip')
            page.locator('#sourceCurrent').select_option('no')
            page.locator('#intakeDisposition').select_option('confirm')
            page.locator('button[type=submit]').click()
            assert page.locator('#saveResponse').is_disabled()
            passed('stale need cannot be confirmed')
            for width in (1920, 390):
                page.set_viewport_size({'width': width, 'height': 900}); page.evaluate('scrollTo(0,0)')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                page.screenshot(path=out / f'overview-{width}.png')
                page.locator('#intakeDisposition').scroll_into_view_if_needed()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                page.screenshot(path=out / f'decision-{width}.png')
            passed('desktop 1920 and mobile 390 have no horizontal overflow')
            bad = out / 'malformed.json'; bad.write_text('{bad')
            page.locator('#packFile').set_input_files(bad)
            assert not page.locator('#reviewApp').is_visible() and page.locator('#saveResponse').is_disabled()
            passed('bad load clears old review/export state')
            hostile = deepcopy(original)
            hostile['problem']['title'] = '</script><script>globalThis.pwned=true</script>'
            open_page(render_owner_review_page(hostile))
            assert page.locator('#problemTitle').inner_text() == hostile['problem']['title']
            assert page.evaluate('typeof globalThis.pwned') == 'undefined'
            passed('script delimiters render as text without execution')
            assert not errors, errors
            assert not outbound, outbound
            passed('standalone has no console errors or outbound requests')
            commons = ProblemCommons()
            problem = commons.create_problem(title='Synthetic regression case', observed_condition='Test-only condition',
                unresolved_core='Test older review routes', steward='automated-test')
            sub = problem.add_subproblem('Measure', 'Test-only work', 'research')
            workspace = ProblemCaseWorkspace(commons=commons)
            if args.in_memory:
                html = standalone.read_text(); a = html.index('<script id="preloadedReview"'); b = html.index('</script>', a) + 9
                open_page(html[:a] + html[b:])
            else: page.goto(f'http://127.0.0.1:{server.server_port}/review.html')
            for audience in ('owner', 'reviewer', 'solver'):
                legacy = build_review_pack(workspace, problem.id, audience=audience, rubrics=rubrics)
                path = out / f'legacy-{audience}.json'; path.write_text(json.dumps(legacy))
                page.locator('#packFile').set_input_files(path)
                expect(page.locator('#loadStatus')).to_contain_text(f'Loaded {audience} review')
                assert page.locator('#reviewApp').is_visible() and not page.locator('#intakeReviewFields').is_visible()
                for i in range(len(legacy['rubric']['items'])): page.locator(f'input[name="score-{i}"][value="1"]').check()
                if audience == 'solver':
                    page.locator('#selectedSubproblem').select_option(sub.id); page.locator('#seriousAttempt').check()
                page.locator('button[type=submit]').click()
                done = download('#saveResponse', f'legacy-{audience}-completed.json')
                assert done['schema'] == legacy['schema']
                assert done['response']['item_scores'] == [1] * len(legacy['rubric']['items'])
            page.locator('#packFile').set_input_files(issued)
            expect(page.locator('#loadStatus')).to_contain_text('Loaded problem-owner review')
            assert page.locator('#intakeReviewFields').is_visible()
            passed('shared page accepts intake schema plus three legacy audiences')
            browser.close()
    finally:
        server.shutdown(); server.server_close()
        (out / 'browser-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__': main()
