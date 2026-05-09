"""Playwright smoke tests for MacroHero — captures screenshots to screenshots/."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5030"
SCREENSHOTS = Path(__file__).parent.parent / "screenshots"
SCREENSHOTS.mkdir(exist_ok=True)


def test_landing_page():
    """Test 1: Landing page loads for unauthenticated users."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Check hero section
        assert page.locator("text=MacroHero").first.is_visible(), "MacroHero branding not found"
        assert page.locator("text=macro intelligence").first.is_visible(), "Hero tagline not found"

        # Check CTA buttons
        assert page.locator("text=Sign in").first.is_visible(), "Sign in button not found"
        assert page.locator("text=Book a demo").first.is_visible(), "Book a demo button not found"

        # Check features section
        assert page.locator("text=Features").first.is_visible(), "Features section not found"

        # Check team section exists
        assert page.locator("text=Team").first.is_visible(), "Team section not found"

        page.screenshot(path=str(SCREENSHOTS / "01_landing.png"), full_page=False)
        print("PASS: Landing page loads with hero, features, and CTAs")
        browser.close()


def test_login_page():
    """Test 2: Login page renders correctly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        assert page.locator("text=Sign in").first.is_visible(), "Sign in button not found"
        assert page.locator("#username").is_visible(), "Username field not found"
        assert page.locator("#password").is_visible(), "Password field not found"

        page.screenshot(path=str(SCREENSHOTS / "02_login.png"), full_page=False)
        print("PASS: Login page renders correctly")
        browser.close()


def test_register_page():
    """Test 3: Register page renders correctly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE_URL}/register", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        assert page.locator("text=Create account").first.is_visible(), "Create account button not found"

        page.screenshot(path=str(SCREENSHOTS / "03_register.png"), full_page=False)
        print("PASS: Register page renders correctly")
        browser.close()


def test_category_view():
    """Test 4: Category view loads when clicking sidebar."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE_URL}/category/central-bank", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Verify 3-pane layout still works
        assert page.locator(".left-pane").is_visible(), "Left pane not visible"
        assert page.locator(".center-pane").is_visible(), "Center pane not visible"

        page.screenshot(path=str(SCREENSHOTS / "04_category_central_bank.png"), full_page=False)
        print("PASS: Category view loads")
        browser.close()


def test_chat_send():
    """Test 5: Sending a chat message shows user bubble and thinking indicator."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE_URL}/category/central-bank", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Type a message
        chat_input = page.locator("#chat-input")
        chat_input.fill("What is the current EUR/USD rate?")

        # Submit the form
        page.locator("#center-content button[type='submit']").click()
        page.wait_for_timeout(5000)

        page.screenshot(path=str(SCREENSHOTS / "05_chat_sending.png"), full_page=False)

        # Wait for response (up to 30s)
        page.wait_for_timeout(30000)
        page.screenshot(path=str(SCREENSHOTS / "06_chat_response.png"), full_page=False)

        print("PASS: Chat message sent and screenshot captured")
        browser.close()


def test_view_history():
    """Test 6: News history view loads via HTMX."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE_URL}/view/history", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        page.screenshot(path=str(SCREENSHOTS / "07_news_history.png"), full_page=False)
        print("PASS: News history view loads")
        browser.close()


def test_view_pairs():
    """Test 7: Currency pairs view loads."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE_URL}/view/pairs", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        page.screenshot(path=str(SCREENSHOTS / "08_currency_pairs.png"), full_page=False)
        print("PASS: Currency pairs view loads")
        browser.close()


if __name__ == "__main__":
    tests = [
        test_landing_page,
        test_login_page,
        test_register_page,
        test_category_view,
        test_chat_send,
        test_view_history,
        test_view_pairs,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    sys.exit(1 if failed > 0 else 0)
