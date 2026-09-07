import sys
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# ============================================================
# CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# YOUR SERVICENOW URL
# ------------------------------------------------------------
#
# Example:
# https://abc.service-now.com
#
# This URL will be opened in a NEW Edge tab.
#
# ------------------------------------------------------------

SERVICENOW_URL = "https://YOUR-COMPANY.service-now.com"


# ------------------------------------------------------------
# EXISTING MICROSOFT EDGE
# ------------------------------------------------------------
#
# Python connects to the already-running Edge browser through
# this local debugging endpoint.
#
# DO NOT change this unless you use another port.
#
# ------------------------------------------------------------

EDGE_CDP_URL = "http://127.0.0.1:9222"


# ------------------------------------------------------------
# OUTPUT FILE
# ------------------------------------------------------------

OUTPUT_FILE = "servicenow_story_details.xlsx"


# ============================================================
# XPATH CONFIGURATION
# ============================================================
#
# PUT YOUR ACTUAL XPATHS HERE.
#
# Example:
#
# "Stry Number":
#     '//*[@id="number"]'
#
# ------------------------------------------------------------


# ============================================================
# STORY SEARCH
# ============================================================
#
# XPath of the search box where you enter:
#
# STRY0056319
#
# Example:
#
# STORY_SEARCH_XPATH = '//*[@id="sysparm_query"]'
#
# ------------------------------------------------------------

STORY_SEARCH_XPATH = ""


# ============================================================
# SEARCH BUTTON
# ============================================================
#
# If pressing ENTER on the search box works, leave this empty.
#
# If you need to click a Search button, provide its XPath.
#
# Example:
#
# SEARCH_BUTTON_XPATH = '//button[@id="search"]'
#
# ------------------------------------------------------------

SEARCH_BUTTON_XPATH = ""


# ============================================================
# STORY READY XPATH
# ============================================================
#
# This is VERY IMPORTANT.
#
# Put the XPath of one element that exists on the Story page.
#
# Best option:
#
# Story Number field.
#
# Example:
#
# STORY_READY_XPATH = '//*[@id="number"]'
#
# The script waits for this element instead of waiting for the
# whole ServiceNow page to finish loading.
#
# ------------------------------------------------------------

STORY_READY_XPATH = ""


# ============================================================
# FIELD XPATHS
# ============================================================
#
# Put the exact XPath for every field.
#
# ------------------------------------------------------------

XPATHS = {

    "Stry Number":
        "",

    "SC Task/Incident":
        "",

    "Stry Description":
        "",

    "State":
        "",

    "Sub State":
        "",

    "Work Notes":
        "",

    "Dev Document":
        "",

    "QA Document":
        "",

    "Assigned To":
        "",

    "Owner":
        "",

    "Original Task":
        "",

    "Project":
        "",

    "Release":
        ""
}


# ============================================================
# EXCEL COLUMNS
# ============================================================

EXCEL_COLUMNS = [

    "Stry Number",

    "SC Task/Incident",

    "Stry Description",

    "State",

    "Sub State",

    "Work Notes",

    "Dev Document",

    "QA Document",

    "Assigned To",

    "Owner",

    "Original Task",

    "Project",

    "Release"
]


# ============================================================
# SETTINGS
# ============================================================

# Maximum time to wait for an element
ELEMENT_TIMEOUT = 60000

# Time to allow ServiceNow JavaScript to render
RENDER_WAIT = 3000


# ============================================================
# CONNECT TO EDGE
# ============================================================

def connect_to_edge(playwright):

    print()
    print("=" * 80)
    print("CONNECTING TO EXISTING MICROSOFT EDGE")
    print("=" * 80)

    try:

        browser = playwright.chromium.connect_over_cdp(
            EDGE_CDP_URL
        )

        print("Connected to existing Edge successfully.")

        return browser

    except Exception as error:

        print()
        print("ERROR: Could not connect to Microsoft Edge.")
        print()
        print(error)

        print()
        print("Make sure Edge was started with:")
        print()

        print(
            r'& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222'
        )

        print()
        print("Or:")
        print()

        print(
            r'& "C:\Program Files\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222'
        )

        sys.exit(1)


# ============================================================
# GET EDGE CONTEXT
# ============================================================

def get_edge_context(browser):

    if not browser.contexts:

        print(
            "ERROR: No browser context found."
        )

        sys.exit(1)

    context = browser.contexts[0]

    print()
    print(
        f"Existing tabs: {len(context.pages)}"
    )

    for index, page in enumerate(context.pages):

        try:

            print(
                f"  Tab {index + 1}: "
                f"{page.url}"
            )

        except Exception:
            pass

    return context


# ============================================================
# OPEN SERVICENOW IN NEW TAB
# ============================================================

def open_servicenow(context):

    print()
    print("=" * 80)
    print("OPENING SERVICENOW IN NEW TAB")
    print("=" * 80)

    # IMPORTANT:
    # This creates a NEW TAB in the existing Edge browser.

    page = context.new_page()

    print(
        "New tab created."
    )

    print(
        f"Navigating to: {SERVICENOW_URL}"
    )

    try:

        page.goto(
            SERVICENOW_URL,
            wait_until="domcontentloaded",
            timeout=30000
        )

    except PlaywrightTimeoutError:

        # ServiceNow can continue loading after DOMContentLoaded.
        # We don't treat this as fatal.

        print(
            "Navigation timeout reached."
        )

        print(
            "Continuing because ServiceNow may still be rendering."
        )

    print(
        f"Current URL: {page.url}"
    )

    # Allow JavaScript application to render
    page.wait_for_timeout(
        RENDER_WAIT
    )

    return page


# ============================================================
# FIND ELEMENT
# ============================================================

def find_xpath(page, xpath):

    if not xpath:

        return None

    try:

        element = page.locator(
            f"xpath={xpath}"
        ).first

        if element.count() == 0:

            return None

        return element

    except Exception:

        return None


# ============================================================
# SEARCH STORY
# ============================================================

def search_story(
    context,
    page,
    story_number
):

    print()
    print("=" * 80)
    print(
        f"SEARCHING STORY: {story_number}"
    )
    print("=" * 80)

    if not STORY_SEARCH_XPATH:

        print()
        print(
            "STORY_SEARCH_XPATH is empty."
        )

        print(
            "Automatic search is not configured."
        )

        print()
        print(
            "Please open the Story manually."
        )

        input(
            "Press ENTER after the Story page is open..."
        )

        return page


    # --------------------------------------------------------
    # Record existing tabs
    # --------------------------------------------------------

    existing_pages = list(
        context.pages
    )


    # --------------------------------------------------------
    # Find search box
    # --------------------------------------------------------

    search_box = find_xpath(
        page,
        STORY_SEARCH_XPATH
    )

    if search_box is None:

        print()
        print(
            "ERROR: Story search XPath was not found."
        )

        print(
            STORY_SEARCH_XPATH
        )

        sys.exit(1)


    print(
        "Search box found."
    )


    # --------------------------------------------------------
    # Wait until visible
    # --------------------------------------------------------

    try:

        search_box.wait_for(
            state="visible",
            timeout=ELEMENT_TIMEOUT
        )

    except PlaywrightTimeoutError:

        print(
            "ERROR: Search box did not become visible."
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Enter Story Number
    # --------------------------------------------------------

    print(
        f"Entering Story Number: {story_number}"
    )

    try:

        search_box.fill(
            story_number
        )

    except Exception as error:

        print(
            "ERROR entering Story Number:"
        )

        print(error)

        sys.exit(1)


    # --------------------------------------------------------
    # Submit search
    # --------------------------------------------------------

    if SEARCH_BUTTON_XPATH:

        print(
            "Clicking Search button..."
        )

        button = find_xpath(
            page,
            SEARCH_BUTTON_XPATH
        )

        if button is None:

            print(
                "ERROR: Search button XPath not found."
            )

            sys.exit(1)

        button.click()

    else:

        print(
            "Pressing ENTER..."
        )

        search_box.press(
            "Enter"
        )


    print(
        "Search submitted."
    )


    # --------------------------------------------------------
    # Wait for ServiceNow
    # --------------------------------------------------------

    page.wait_for_timeout(
        3000
    )


    # --------------------------------------------------------
    # Detect newly opened tab
    # --------------------------------------------------------

    print(
        "Checking for new Story tab..."
    )

    deadline = time.time() + 30

    while time.time() < deadline:

        current_pages = list(
            context.pages
        )

        for current_page in current_pages:

            if current_page not in existing_pages:

                print()
                print(
                    "NEW TAB DETECTED."
                )

                print(
                    f"Story page URL: "
                    f"{current_page.url}"
                )

                try:

                    current_page.bring_to_front()

                except Exception:
                    pass

                return current_page

        time.sleep(0.5)


    # --------------------------------------------------------
    # No new tab
    # --------------------------------------------------------

    print(
        "No new tab detected."
    )

    print(
        "Checking current tab."
    )

    print(
        f"Current URL: {page.url}"
    )

    return page


# ============================================================
# WAIT FOR STORY PAGE
# ============================================================

def wait_for_story_page(page):

    print()
    print("=" * 80)
    print("WAITING FOR STORY PAGE")
    print("=" * 80)

    # --------------------------------------------------------
    # DO NOT use networkidle here.
    #
    # ServiceNow can continue network activity indefinitely.
    # --------------------------------------------------------

    if not STORY_READY_XPATH:

        print(
            "WARNING: STORY_READY_XPATH is empty."
        )

        print(
            "Waiting 10 seconds instead."
        )

        page.wait_for_timeout(
            10000
        )

        return True


    print(
        "Story ready XPath:"
    )

    print(
        STORY_READY_XPATH
    )

    element = find_xpath(
        page,
        STORY_READY_XPATH
    )

    if element is None:

        print(
            "ERROR: Story ready element not found."
        )

        print(
            "Current URL:"
        )

        print(
            page.url
        )

        save_debug_screenshot(
            page
        )

        return False


    try:

        element.wait_for(
            state="visible",
            timeout=ELEMENT_TIMEOUT
        )

        print(
            "Story page is ready."
        )

        return True

    except PlaywrightTimeoutError:

        print()
        print(
            "ERROR: Story page did not become ready."
        )

        print(
            f"Current URL: {page.url}"
        )

        save_debug_screenshot(
            page
        )

        return False


# ============================================================
# READ XPATH VALUE
# ============================================================

def read_xpath_value(
    page,
    xpath,
    field_name
):

    if not xpath:

        print(
            "    XPath is empty."
        )

        return ""


    print(
        f"    XPath: {xpath}"
    )


    try:

        element = page.locator(
            f"xpath={xpath}"
        ).first


        # ----------------------------------------------------
        # Wait until attached
        # ----------------------------------------------------

        element.wait_for(
            state="attached",
            timeout=ELEMENT_TIMEOUT
        )


        # ----------------------------------------------------
        # Determine element type
        # ----------------------------------------------------

        tag = element.evaluate(
            "(el) => el.tagName.toLowerCase()"
        )


        print(
            f"    HTML tag: {tag}"
        )


        # ----------------------------------------------------
        # INPUT
        # ----------------------------------------------------

        if tag == "input":

            try:

                value = element.input_value(
                    timeout=10000
                )

                if value:
                    return value.strip()

            except Exception:
                pass


            # Sometimes ServiceNow uses value attribute

            try:

                value = element.get_attribute(
                    "value"
                )

                if value:
                    return value.strip()

            except Exception:
                pass


        # ----------------------------------------------------
        # TEXTAREA
        # ----------------------------------------------------

        if tag == "textarea":

            try:

                value = element.input_value(
                    timeout=10000
                )

                if value:
                    return value.strip()

            except Exception:
                pass


        # ----------------------------------------------------
        # SELECT
        # ----------------------------------------------------

        if tag == "select":

            try:

                value = element.locator(
                    "option:checked"
                ).text_content()

                if value:
                    return value.strip()

            except Exception:
                pass


        # ----------------------------------------------------
        # NORMAL HTML ELEMENT
        # ----------------------------------------------------

        try:

            value = element.text_content(
                timeout=10000
            )

            if value:

                return value.strip()

        except Exception:
            pass


        # ----------------------------------------------------
        # INNER TEXT FALLBACK
        # ----------------------------------------------------

        try:

            value = element.inner_text(
                timeout=10000
            )

            if value:

                return value.strip()

        except Exception:
            pass


        # ----------------------------------------------------
        # VALUE ATTRIBUTE FALLBACK
        # ----------------------------------------------------

        try:

            value = element.get_attribute(
                "value"
            )

            if value:

                return value.strip()

        except Exception:
            pass


    except PlaywrightTimeoutError:

        print(
            "    TIMEOUT: Element not found."
        )

    except Exception as error:

        print(
            f"    ERROR reading {field_name}:"
        )

        print(
            f"    {error}"
        )


    return ""


# ============================================================
# SCRAPE STORY
# ============================================================

def scrape_story(
    page,
    story_number
):

    print()
    print("=" * 80)
    print(
        f"SCRAPING STORY: {story_number}"
    )
    print("=" * 80)

    result = {}


    for column in EXCEL_COLUMNS:

        print()
        print(
            f"[{column}]"
        )


        # ----------------------------------------------------
        # Story Number
        # ----------------------------------------------------

        if column == "Stry Number":

            xpath = XPATHS.get(
                column,
                ""
            )

            if xpath:

                value = read_xpath_value(
                    page,
                    xpath,
                    column
                )

                # Fallback to entered number
                if not value:

                    value = story_number

            else:

                value = story_number


        # ----------------------------------------------------
        # Other fields
        # ----------------------------------------------------

        else:

            xpath = XPATHS.get(
                column,
                ""
            )

            value = read_xpath_value(
                page,
                xpath,
                column
            )


        result[column] = value


        print(
            f"    VALUE: {value}"
        )


    return result


# ============================================================
# DEBUG SCREENSHOT
# ============================================================

def save_debug_screenshot(page):

    try:

        file_name = "servicenow_debug.png"

        page.screenshot(
            path=file_name,
            full_page=True
        )

        print()
        print(
            f"Debug screenshot saved: {file_name}"
        )

    except Exception as error:

        print(
            f"Could not create screenshot: {error}"
        )


# ============================================================
# CREATE EXCEL
# ============================================================

def create_excel(result):

    print()
    print("=" * 80)
    print("CREATING EXCEL")
    print("=" * 80)


    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(
        [result],
        columns=EXCEL_COLUMNS
    )


    # --------------------------------------------------------
    # Excel Writer
    # --------------------------------------------------------

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="ServiceNow Stories"
        )


        worksheet = writer.sheets[
            "ServiceNow Stories"
        ]


        # ----------------------------------------------------
        # Freeze header
        # ----------------------------------------------------

        worksheet.freeze_panes = "A2"


        # ----------------------------------------------------
        # Header formatting
        # ----------------------------------------------------

        from openpyxl.styles import Font, Alignment

        for cell in worksheet[1]:

            cell.font = Font(
                bold=True
            )

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center"
            )


        # ----------------------------------------------------
        # Wrap text
        # ----------------------------------------------------

        for row in worksheet.iter_rows():

            for cell in row:

                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=True
                )


        # ----------------------------------------------------
        # Auto column width
        # ----------------------------------------------------

        for column_cells in worksheet.columns:

            max_length = 0

            column_letter = (
                column_cells[0].column_letter
            )

            for cell in column_cells:

                try:

                    length = len(
                        str(cell.value)
                    )

                    if length > max_length:

                        max_length = length

                except Exception:
                    pass


            worksheet.column_dimensions[
                column_letter
            ].width = min(
                max_length + 3,
                60
            )


    print()
    print(
        "Excel created successfully."
    )

    print(
        f"File: {Path(OUTPUT_FILE).absolute()}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("SERVICENOW STORY SCRAPER")
    print("=" * 80)


    # --------------------------------------------------------
    # Story Number
    # --------------------------------------------------------

    story_number = input(
        "\nEnter ServiceNow Story Number: "
    ).strip()


    if not story_number:

        print(
            "ERROR: Story Number cannot be empty."
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Playwright
    # --------------------------------------------------------

    with sync_playwright() as playwright:


        # ----------------------------------------------------
        # Connect to Edge
        # ----------------------------------------------------

        browser = connect_to_edge(
            playwright
        )


        # ----------------------------------------------------
        # Get context
        # ----------------------------------------------------

        context = get_edge_context(
            browser
        )


        # ----------------------------------------------------
        # Open ServiceNow NEW TAB
        # ----------------------------------------------------

        service_now_page = open_servicenow(
            context
        )


        # ----------------------------------------------------
        # Search Story
        # ----------------------------------------------------

        story_page = search_story(
            context,
            service_now_page,
            story_number
        )


        # ----------------------------------------------------
        # Bring Story page to front
        # ----------------------------------------------------

        try:

            story_page.bring_to_front()

        except Exception:
            pass


        # ----------------------------------------------------
        # Wait for Story
        # ----------------------------------------------------

        if not wait_for_story_page(
            story_page
        ):

            print()
            print(
                "Story page was not detected."
            )

            sys.exit(1)


        # ----------------------------------------------------
        # Scrape fields
        # ----------------------------------------------------

        result = scrape_story(
            story_page,
            story_number
        )


        # ----------------------------------------------------
        # Create Excel
        # ----------------------------------------------------

        create_excel(
            result
        )


        print()
        print("=" * 80)
        print("PROCESS COMPLETED")
        print("=" * 80)

        print()
        print(
            f"Story: {story_number}"
        )

        print(
            f"Excel: {Path(OUTPUT_FILE).absolute()}"
        )

        print()
        print(
            "Microsoft Edge remains open."
        )

        print(
            "The ServiceNow tab remains open."
        )


        # ----------------------------------------------------
        # IMPORTANT
        #
        # Do NOT call browser.close().
        #
        # We are attached to the user's existing Edge.
        # ----------------------------------------------------


if __name__ == "__main__":

    main()
