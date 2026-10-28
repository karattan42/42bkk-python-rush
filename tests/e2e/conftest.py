"""Start server.py with an empty temporary database and open a real Chrome for the tests."""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid

import pytest
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def base_url():
    port = free_port()
    folder = tempfile.mkdtemp(prefix="streakr-e2e-")
    env = dict(os.environ)
    env.update({"PORT": str(port), "HOST": "127.0.0.1", "ALLOWED_HOSTS": f"127.0.0.1:{port}",
                "STREAKR_DB": os.path.join(folder, "e2e.db")})
    process = subprocess.Popen([sys.executable, "server.py"], cwd=ROOT, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    deadline = time.time() + 15
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            break
        except OSError:
            if time.time() > deadline or process.poll() is not None:
                process.kill()
                raise RuntimeError("server.py did not start: " + process.stderr.read().decode())
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    process.terminate()
    process.wait(timeout=5)
    shutil.rmtree(folder, ignore_errors=True)


@pytest.fixture(scope="session")
def browser():
    # Uses the Chrome already installed on this computer, so no browser download is needed.
    # PLAYWRIGHT_CHANNEL=chromium uses Playwright's own browser instead.
    channel = os.environ.get("PLAYWRIGHT_CHANNEL", "chrome")
    with sync_playwright() as playwright:
        if channel == "chromium":
            launched = playwright.chromium.launch()
        else:
            launched = playwright.chromium.launch(channel=channel)
        yield launched
        launched.close()


@pytest.fixture
def new_page(browser, base_url):
    """Make pages in fresh browser sessions (no shared cookies). Console errors fail the test."""
    contexts = []
    errors = []

    def make(**options):
        context = browser.new_context(base_url=base_url, **options)
        contexts.append(context)
        page = context.new_page()
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(str(error)))
        return page

    yield make
    for context in contexts:
        context.close()
    assert errors == [], errors


@pytest.fixture
def page(new_page):
    return new_page()


def unique_name(prefix="user"):
    return prefix + uuid.uuid4().hex[:8]
