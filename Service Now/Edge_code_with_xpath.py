import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# YOUR SERVICENOW URL
# ------------------------------------------------------------

SERVICENOW_URL = "https://yourcompany.service-now.com"


# ------------------------------------------------------------
# EXISTING MICROSOFT EDGE CDP CONNECTION
# ------------------------------------------------------------

EDGE_CDP_URL = "http://127.0.0.1:9222"


# ------------------------------------------------------------
# OUTPUT EXCEL
# ------------------------------------------------------------

OUTPUT_FILE = "servicenow_story_details.xlsx"


# ============================================================
# SERVICE NOW XPATHS
# ============================================================
#
# PUT YOUR ACTUAL XPATHS HERE
#
# Example:
#
# "Stry Number":
#     "//input[@id='...']"
#
# If a field is a textarea:
#
# "Work Notes":
#     "//textarea[@id='...']"
#
# ============================================================

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
# OPTIONAL SEARCH XPATH
# ============================================================
#
# If ServiceNow has a search box where you enter the Story
# number, put its XPath here.
#
# Example:
#
# STORY_SEARCH_XPATH = "//input[@id='...']"
#
# If you prefer to open the Story manually after the new
# ServiceNow tab opens, leave this as "".
#
# ============================================================

STORY_SEARCH_XPATH = ""


# ============================================================
# NORMALIZE VALUE
# ============================================================

def normalize_value(value):

    if value is None:
        return ""

    value = str(value)

    return value.replace(
        "\xa0",
        " "
    ).strip()


# ============================================================
# GET VALUE USING XPATH
# ============================================================

def get_xpath_value(page, xpath):

    if not xpath:

        return ""

    try:

        element = page.locator(
            f"xpath={xpath}"
        ).first

        if element.count() == 0:

            print(
                f"    XPath not found: {xpath}"
            )

            return ""

        # ----------------------------------------------------
        # Check tag
        # ----------------------------------------------------

        tag_name = element.evaluate(
            "(element) => element.tagName.toLowerCase()"
        )

        # ----------------------------------------------------
        # INPUT / TEXTAREA / SELECT
        # ----------------------------------------------------

        if tag_name in [
            "input",
            "textarea",
            "select"
        ]:

            try:

                value = element.input_value(
                    timeout=5000
                )

                return normalize_value(
                    value
                )

            except Exception:
                pass

        # ----------------------------------------------------
        # Other elements
        # ----------------------------------------------------

        try:

            value = element.text_content(
                timeout=5000
            )

            return normalize_value(
                value
            )

        except Exception:
            pass

    except Exception as error:

        print(
            f"    Error reading XPath: {xpath}"
        )

        print(
            f"    {error}"
        )

    return ""


# ============================================================
# OPEN SERVICENOW NEW TAB
# ============================================================

def open_servicenow(context):

    print()
    print(
        "Opening ServiceNow in a NEW Edge tab..."
    )

    page = context.new_page()

    page.goto(
        SERVICENOW_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(3000)

    print(
        "ServiceNow URL:"
    )

    print(
        page.url
    )

    return page


# ============================================================
# SEARCH STORY
# ============================================================

def search_story(page, story_number):

    # --------------------------------------------------------
    # If XPath is not provided, don't attempt automatic search.
    # --------------------------------------------------------

    if not STORY_SEARCH_XPATH:

        print()
        print(
            "STORY_SEARCH_XPATH is empty."
        )

        print(
            "Automatic Story search is disabled."
        )

        print()
        print(
            f"Please open {story_number} manually "
            "in the ServiceNow tab."
        )

        input(
            "Press ENTER after the Story page is open..."
        )

        return


    print()
    print(
        f"Searching for Story: {story_number}"
    )

    try:

        search_box = page.locator(
            f"xpath={STORY_SEARCH_XPATH}"
        ).first

        if search_box.count() == 0:

            raise Exception(
                "Story search XPath was not found."
            )

        search_box.fill(
            story_number
        )

        search_box.press(
            "Enter"
        )

        print(
            "Story search submitted."
        )

        page.wait_for_timeout(5000)

    except Exception as error:

        print()
        print(
            "ERROR while searching for Story."
        )

        print(error)

        sys.exit(1)


# ============================================================
# SCRAPE STORY
# ============================================================

def scrape_story(page, story_number):

    print()
    print("=" * 80)
    print(
        f"Extracting ServiceNow Story: {story_number}"
    )
    print("=" * 80)

    result = {}

    for column in EXCEL_COLUMNS:

        xpath = XPATHS.get(
            column,
            ""
        )

        print()
        print(
            f"Reading: {column}"
        )

        print(
            f"XPath: {xpath}"
        )

        # ----------------------------------------------------
        # Story Number
        # ----------------------------------------------------

        if column == "Stry Number":

            # If XPath is supplied, use it.
            # Otherwise use the entered Story Number.

            if xpath:

                value = get_xpath_value(
                    page,
                    xpath
                )

                if not value:

                    value = story_number

            else:

                value = story_number

        else:

            value = get_xpath_value(
                page,
                xpath
            )

        result[column] = value

        print(
            f"Value: {value}"
        )

    return result


# ============================================================
# CREATE EXCEL
# ============================================================

def create_excel(result):

    print()
    print(
        "Creating Excel..."
    )

    df = pd.DataFrame(
        [result],
        columns=EXCEL_COLUMNS
    )

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
        # Auto-size columns
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
                max_length + 2,
                60
            )

    print()
    print("=" * 80)
    print(
        "EXCEL CREATED SUCCESSFULLY"
    )
    print("=" * 80)

    print(
        f"File: {Path(OUTPUT_FILE).absolute()}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print(
        "SERVICENOW STORY SCRAPER"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # Get Story Number
    # --------------------------------------------------------

    story_number = input(
        "\nEnter ServiceNow Story Number: "
    ).strip()

    if not story_number:

        print(
            "Story Number cannot be empty."
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Connect to existing Edge
    # --------------------------------------------------------

    print()
    print(
        "Connecting to existing Microsoft Edge..."
    )

    with sync_playwright() as p:

        try:

            browser = p.chromium.connect_over_cdp(
                EDGE_CDP_URL
            )

        except Exception as error:

            print()
            print(
                "ERROR: Could not connect to Microsoft Edge."
            )

            print()
            print(
                str(error)
            )

            print()
            print(
                "Make sure Edge was started using:"
            )

            print()

            print(
                r'& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222'
            )

            print()

            sys.exit(1)


        print(
            "Connected to Edge successfully."
        )


        # ----------------------------------------------------
        # Get existing Edge context
        # ----------------------------------------------------

        if not browser.contexts:

            print(
                "No Edge browser context found."
            )

            sys.exit(1)

        context = browser.contexts[0]


        # ----------------------------------------------------
        # Open ServiceNow in NEW TAB
        # ----------------------------------------------------

        page = open_servicenow(
            context
        )


        # ----------------------------------------------------
        # Search Story
        # ----------------------------------------------------

        search_story(
            page,
            story_number
        )


        # ----------------------------------------------------
        # Wait for Story page
        # ----------------------------------------------------

        print()
        print(
            "Waiting for Story page..."
        )

        page.wait_for_timeout(3000)


        # ----------------------------------------------------
        # Extract fields
        # ----------------------------------------------------

        result = scrape_story(
            page,
            story_number
        )


        # ----------------------------------------------------
        # Create Excel
        # ----------------------------------------------------

        create_excel(
            result
        )


        print()
        print(
            "Process completed."
        )

        print(
            "Edge browser remains open."
        )


        # ----------------------------------------------------
        # Disconnect from Edge
        # ----------------------------------------------------

        try:

            browser.close()

        except Exception:
            pass


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
