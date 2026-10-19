"""Browser-audited researcher navigation, not a human usability study."""
import sqlite3
from pathlib import Path
import tempfile
import threading
from playwright.sync_api import sync_playwright
from cite_refinery.hosted_store import WorkspaceDB
from cite_refinery.store import JsonStore
from cite_refinery.web import make_server
from scripts.acceptance_free_roaming_dogs import evaluate_case, run_case

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="cr-dog-acceptance-browser-") as database_dir:
    source=str(Path(database_dir)/"dog-case.sqlite3")
    run_case(ROOT/"examples/free_roaming_dog_semantic_pilot.json",
             ROOT/"examples/acceptance_free_roaming_dog_source_review_v1.json",source)
    with sqlite3.connect(source) as raw:
        uid=raw.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        project=raw.execute("SELECT id FROM projects LIMIT 1").fetchone()[0]
    state=WorkspaceDB(source).project_state(uid,project)
    report=evaluate_case(state,project)
    assert report["outcome"]=="ACCEPTED_WITH_OPEN_GAPS"
    with tempfile.TemporaryDirectory(prefix="cr-dog-browser-") as folder:
        JsonStore(folder).save(state)
        server=make_server(folder,host="127.0.0.1",port=0)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,
                    executable_path="/home/phyrexian/.local/bin/google-chrome",
                    args=["--no-sandbox","--disable-dev-shm-usage"])
                page=browser.new_page(viewport={"width":1620,"height":980})
                errors=[]
                page.on("pageerror",lambda err:errors.append(str(err)))
                page.goto(f"http://127.0.0.1:{server.server_address[1]}/",
                          wait_until="networkidle")
                assert page.locator(".cluster-button").count()==4
                page.locator(".cluster-button").filter(has_text="Population observability").click()
                counts=[page.locator(".layer-col").nth(i).locator("[data-node]").count()
                        for i in range(3)]
                assert counts==[2,2,2],counts
                # Task 1: official source & non-significance must be findable.
                page.locator(".layer-col").nth(0).locator("[data-node]").filter(
                    has_text="not statistically significant").click()
                page.wait_for_timeout(300)
                assert page.locator(".inspector a").count()>0
                assert "animal.moa.gov.tw" in page.locator(".inspector").inner_text()
                # Task 2: Talea's documented missing individual-photo functionality.
                page.locator(".layer-col").nth(2).locator("[data-node]").filter(
                    has_text="cannot include an animal photograph").click()
                page.wait_for_timeout(300)
                assert "icam-coalition.org" in page.locator(".inspector").inner_text()
                # Task 3: Shoushan evidence is geographically limited, not national proof.
                page.locator(".cluster-button").filter(
                    has_text="Population replenishment and source control").click()
                page.locator(".layer-col").nth(1).locator("[data-node]").filter(
                    has_text="Shoushan").first.click()
                page.wait_for_timeout(300)
                assert "sciencedirect.com" in page.locator(".inspector").inner_text()
                # Task 4: government program is documented intention, not results.
                page.locator(".layer-col").nth(2).locator("[data-node]").filter(
                    has_text="Taiwan").first.click()
                page.wait_for_timeout(300)
                assert "animal.moa.gov.tw" in page.locator(".inspector").inner_text()
                assert not errors,errors
                print("CASE 02 CHROME AUDIT PASS: 4 modules; obs layers",counts,
                    "; 4 source-inspection tasks; 0 browser JS errors")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
