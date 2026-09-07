import os
import time
import pandas as pd

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv


load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

SERVICENOW_URL = os.getenv(
    "SERVICENOW_URL",
    "https://yourcompany.service-now.com"
)

# Change this to your actual Story table
# Example:
# /rm_story.do
# /rm_story_list.do
# /u_story.do
STORY_TABLE = os.getenv(
    "STORY_TABLE",
    "rm_story"
)

OUTPUT_FILE = "servicenow_story_details.xlsx"

# Persistent browser profile
BROWSER_PROFILE = "./servicenow_browser_profile"


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
# SERVICE NOW FIELD LABELS
# ============================================================

# These are the labels visible on the ServiceNow screen.
#
# If your ServiceNow labels are slightly different,
# update them here.

FIELD_LABELS = {

    "Stry Number": [
        "Story Number",
        "Number"
    ],

    "SC Task/Incident": [
        "SC Task/Incident",
        "SC Task",
        "Incident"
    ],

    "Stry Description": [
        "Story Description",
        "Description"
    ],

    "State": [
        "State"
    ],

    "Sub State": [
        "Sub State",
        "Substate"
    ],

    "Work Notes": [
        "Work Notes"
    ],

    "Dev Document": [
        "Dev Document",
        "Development Document"
    ],

    "QA Document": [
        "QA Document",
        "QA Documentation"
    ],

    "Assigned To": [
        "Assigned To"
    ],

    "Owner": [
        "Owner"
    ],

    "Original Task": [
        "Original Task"
    ],

    "Project": [
        "Project"
    ],

    "Release": [
        "Release"
    ]
}


# ============================================================
# FIND FIELD VALUE
# ============================================================

def get_field_value(page, labels):

    for label in labels:

        try:

            # ------------------------------------------------
            # Try standard ServiceNow input
            # ------------------------------------------------

            locator = page.locator(
                f"label:has-text('{label}')"
            ).first

            if locator.count() > 0:

                # Find associated input
                input_element = locator.locator(
                    "xpath=following::input[1]"
                )

                if input_element.count() > 0:

                    value = input_element.input_value(
                        timeout=2000
                    )

                    if value:
                        return value.strip()

        except Exception:
            pass


        try:

            # ------------------------------------------------
            # Try textarea
            # ------------------------------------------------

            locator = page.locator(
                f"label:has-text('{label}')"
            ).first

            if locator.count() > 0:

                textarea = locator.locator(
                    "xpath=following::textarea[1]"
                )

                if textarea.count() > 0:

                    value = textarea.input_value(
                        timeout=2000
                    )

                    if value:
                        return value.strip()

        except Exception:
            pass


        try:

            # ------------------------------------------------
            # Try ServiceNow reference field
            # ------------------------------------------------

            field = page.locator(
                f"[aria-label='{label}']"
            ).first

            if field.count() > 0:

                value = field.input_value(
                    timeout=2000
                )

                if value:
                    return value.strip()

        except Exception:
            pass


        try:

            # ------------------------------------------------
            # Try generic text following label
            # ------------------------------------------------

            label_element = page.get_by_text(
                label,
                exact=True
            ).first

            if label_element.count() > 0:

                parent = label_element.locator(
                    "xpath=.."
                )

                text = parent.inner_text(
                    timeout=2000
                )

                lines = [
                    x.strip()
                    for x in text.split("\n")
                    if x.strip()
                ]

                if len(lines) >= 2:

                    return lines[-1]

        except Exception:
            pass


    return ""


# ============================================================
# SCRAPE STORY
# ============================================================

def scrape_story(page, story_number):

    print(f"Opening Story: {story_number}")

    story_url = (
        f"{SERVICENOW_URL}/"
        f"{STORY_TABLE}.do"
        f"?sysparm_query=number={story_number}"
    )

    page.goto(
        story_url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    # Give ServiceNow time to render
    page.wait_for_timeout(5000)

    print("Current URL:")
    print(page.url)

    # --------------------------------------------------------
    # Check if login is required
    # --------------------------------------------------------

    if "login" in page.url.lower():

        print()
        print("ServiceNow login is required.")
        print(
            "Please login manually in the browser window "
            "the first time."
        )

        input(
            "After login is completed, press ENTER here..."
        )

        # Reload Story
        page.goto(
            story_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(5000)

    # --------------------------------------------------------
    # Verify story
    # --------------------------------------------------------

    if not page.get_by_text(
        story_number,
        exact=False
    ).count():

        print(
            f"WARNING: {story_number} "
            "was not clearly found on the page."
        )

    # --------------------------------------------------------
    # Extract fields
    # --------------------------------------------------------

    result = {}

    for excel_column, labels in FIELD_LABELS.items():

        print(
            f"Reading field: {excel_column}"
        )

        value = get_field_value(
            page,
            labels
        )

        result[excel_column] = value

        print(
            f"  -> {value}"
        )

    # --------------------------------------------------------
    # Force Story Number
    # --------------------------------------------------------

    if not result["Stry Number"]:
        result["Stry Number"] = story_number

    return result


# ============================================================
# CREATE EXCEL
# ============================================================

def create_excel(rows):

    df = pd.DataFrame(
        rows,
        columns=EXCEL_COLUMNS
    )

    df.to_excel(
        OUTPUT_FILE,
        index=False,
        engine="openpyxl"
    )

    print()
    print("=" * 70)
    print("Excel created successfully")
    print("=" * 70)
    print(
        os.path.abspath(OUTPUT_FILE)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Ask user for Story Number
    # --------------------------------------------------------

    story_number = input(
        "Enter ServiceNow Story Number: "
    ).strip()

    if not story_number:
        raise ValueError(
            "Story number cannot be empty."
        )

    with sync_playwright() as p:

        # ----------------------------------------------------
        # Launch Chromium
        #
        # headless=False for first login
        # headless=True after login/profile is saved
        # ----------------------------------------------------

        browser = p.chromium.launch_persistent_context(

            BROWSER_PROFILE,

            headless=True,

            viewport={
                "width": 1920,
                "height": 1080
            },

            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )

        page = browser.pages[0] \
            if browser.pages \
            else browser.new_page()

        try:

            row = scrape_story(
                page,
                story_number
            )

            create_excel(
                [row]
            )

        finally:

            browser.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
