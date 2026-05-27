from playwright.sync_api import sync_playwright

url = "https://www.chase.com/personal/mortgage/refinance-rates"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    # 用 placeholder 找 ZIP 输入框
    zip_box = page.get_by_placeholder("Please enter 5 digit zip code")
    zip_box.click()
    page.keyboard.type("98033")

    page.wait_for_timeout(1000)

    page.get_by_role("button", name="See rates").click()

    page.wait_for_timeout(10000)

    text = page.locator("body").inner_text()
    print(text[:15000])

    # input("Press Enter to close browser...")
    browser.close()