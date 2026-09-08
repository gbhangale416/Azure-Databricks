from playwright.sync_api import sync_playwright


SERVICENOW_URL = "https://your-instance.service-now.com"

SEARCH_BOX_XPATH = "//input[@placeholder='Search']"
SEARCH_BUTTON_XPATH = "//button[@type='submit']"


def search_servicenow_story(page, story_number):
    """
    Search for a ServiceNow Story.

    Args:
        page: Playwright page object
        story_number: Story number, e.g. STRY0055879

    Returns:
        Playwright page object
    """

    # Open ServiceNow
    page.goto(
        SERVICENOW_URL,
        wait_until="domcontentloaded"
    )

    print("ServiceNow opened")

    # Give time for SSO/MFA
    page.wait_for_timeout(10000)

    # Enter Story number
    search_box = page.locator(SEARCH_BOX_XPATH)

    search_box.fill(story_number)

    print(f"Searching for: {story_number}")

    # Click Search
    page.locator(SEARCH_BUTTON_XPATH).click()

    # Wait for results
    page.wait_for_timeout(5000)

    print("Search completed")

    return page


def main():

    with sync_playwright() as p:

        # Connect to existing Edge
        browser = p.chromium.connect_over_cdp(
            "http://127.0.0.1:9222"
        )

        context = browser.contexts[0]

        # Open new tab
        page = context.new_page()

        # Search Story
        search_servicenow_story(
            page,
            "STRY0055879"
        )

        input("Press Enter to finish...")

        # Don't close browser because it is the existing Edge

if __name__ == "__main__":
    main()
