import re
import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURATION
# ============================================================

# YOUR ACTUAL SERVICENOW URL
SERVICENOW_URL = "https://yourcompany.service-now.com"

# Connection to EXISTING Microsoft Edge
EDGE_CDP_URL = "http://127.0.0.1:9222"

# Excel output
OUTPUT_FILE = "servicenow_story_details.xlsx"


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

FIELD_LABELS = {

    "SC Task/Incident": [
        "SC Task/Incident",
        "SC Task / Incident",
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
        "Substate",
        "Sub-State"
    ],

    "Work Notes": [
        "Work Notes"
    ],

    "Dev Document": [
        "Dev Document",
        "Development Document",
        "Dev Documentation"
    ],

    "QA Document": [
        "QA Document",
        "QA Documentation"
    ],

    "Assigned To": [
        "Assigned To",
        "Assigned to"
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
# NORMALIZE TEXT
# ============================================================

def normalize_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace("\xa0", " ")

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# GET INPUT VALUE
# ============================================================

def get_element_value(element):

    try:

        tag = element.evaluate(
            "(el) => el.tagName.toLowerCase()"
        )

        if tag in ["input", "textarea", "select"]:

            return normalize_text(
                element.input_value()
            )

    except Exception:
        pass

    try:

        value = element.text_content()

        return normalize_text(value)

    except Exception:
        pass

    return ""


# ============================================================
# GET FIELD VALUE
# ============================================================

def get_field_value(page, labels):

    for label in labels:

        # ----------------------------------------------------
        # 1. Find label
        # ----------------------------------------------------

        try:

            elements = page.locator(
                "label"
            ).filter(
                has_text=label
            )

            for i in range(elements.count()):

                label_element = elements.nth(i)

                # Same parent
                parent = label_element.locator(
                    "xpath=.."
                )

                fields = parent.locator(
                    "input, textarea, select"
                )

                for j in range(fields.count()):

                    value = get_element_value(
                        fields.nth(j)
                    )

                    if value:
                        return value

        except Exception:
            pass


        # ----------------------------------------------------
        # 2. aria-label
        # ----------------------------------------------------

        try:

            elements = page.locator(
                f"[aria-label='{label}']"
            )

            for i in range(elements.count()):

                value = get_element_value(
                    elements.nth(i)
                )

                if value:
                    return value

        except Exception:
            pass


        # ----------------------------------------------------
        # 3. title
        # ----------------------------------------------------

        try:

            elements = page.locator(
                f"[title='{label}']"
            )

            for i in range(elements.count()):

                value = get_element_value(
                    elements.nth(i)
                )

                if value:
                    return value

        except Exception:
            pass


        # ----------------------------------------------------
        # 4. Exact text + parent
        # ----------------------------------------------------

        try:

            element = page.get_by_text(
                label,
                exact=True
            ).first

            if element.count() > 0:

                parent = element.locator(
                    "xpath=.."
                )

                fields = parent.locator(
                    "input, textarea, select"
                )

                for i in range(fields.count()):

                    value = get_element_value(
                        fields.nth(i)
                    )

                    if value:
                        return value

        except Exception:
            pass


        # ----------------------------------------------------
        # 5. Parent text
        # ----------------------------------------------------

        try:

            element = page.get_by_text(
                label,
                exact=True
            ).first

            if element.count() > 0:

                parent = element.locator(
                    "xpath=.."
                )

                text = normalize_text(
                    parent.inner_text()
                )

                text = text.replace(
                    label,
                    "",
                    1
                ).strip()

                if text:
                    return text

        except Exception:
            pass

    return ""


# ============================================================
# OPEN SERVICENOW IN NEW TAB
# ============================================================

def open_servicenow(context):

    print()
    print("Opening new ServiceNow tab...")

    page = context.new_page()

    page.goto(
        SERVICENOW_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(3000)

    print(
        f"ServiceNow opened: {page.url}"
    )

    return page


# ============================================================
# SEARCH STORY
# ============================================================

def search_story(page, story_number):

    print()
    print(
        f"Searching ServiceNow for: {story_number}"
    )

    # --------------------------------------------------------
    # IMPORTANT
    #
    # This searches the currently loaded ServiceNow page.
    #
    # The exact search mechanism depends on your ServiceNow
    # application/table.
    # --------------------------------------------------------

    # Try global ServiceNow search fields
    search_selectors = [
        "input[placeholder*='Search']",
        "input[aria-label*='Search']",
        "input[placeholder*='search']",
        "input[aria-label*='search']"
    ]

    for selector in search_selectors:

        try:

            search_boxes = page.locator(
                selector
            )

            if search_boxes.count() > 0:

                search_box = search_boxes.first

                awaitable = False

                search_box.fill(
                    story_number
                )

                search_box.press(
                    "Enter"
                )

                page.wait_for_timeout(4000)

                print(
                    "Search submitted."
                )

                return True

        except Exception:
            pass

    print(
        "Could not automatically find the ServiceNow search box."
    )

    return False


# ============================================================
# SCRAPE STORY
# ============================================================

def scrape_story(page, story_number):

    print()
    print("=" * 70)
    print(
        f"Extracting Story: {story_number}"
    )
    print("=" * 70)

    page.wait_for_timeout(3000)

    result = {}

    # Story Number
    result["Stry Number"] = story_number

    # Other fields
    for column, labels in FIELD_LABELS.items():

        print(
            f"Reading {column}..."
        )

        value = get_field_value(
            page,
            labels
        )

        result[column] = value

        if value:

            print(
                f"  -> {value}"
            )

        else:

            print(
                "  -> NOT FOUND"
            )

    return result


# ============================================================
# CREATE EXCEL
# ============================================================

def create_excel(result):

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

        # Freeze first row
        worksheet.freeze_panes = "A2"

        # Auto-size columns
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

                    max_length = max(
                        max_length,
                        length
                    )

                except Exception:
                    pass

            worksheet.column_dimensions[
                column_letter
            ].width = min(
                max_length + 2,
                60
            )

    print()
    print("=" * 70)
    print("EXCEL CREATED")
    print("=" * 70)

    print(
        Path(OUTPUT_FILE).absolute()
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("SERVICENOW STORY SCRAPER")
    print("=" * 70)

    # --------------------------------------------------------
    # Story Number
    # --------------------------------------------------------

    story_number = input(
        "\nEnter ServiceNow Story Number: "
    ).strip()

    if not story_number:

        print(
            "Story number cannot be empty."
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Connect to existing Edge
    # --------------------------------------------------------

    with sync_playwright() as p:

        print()
        print(
            "Connecting to existing Microsoft Edge..."
        )

        try:

            browser = p.chromium.connect_over_cdp(
                EDGE_CDP_URL
            )

        except Exception as e:

            print()
            print(
                "ERROR: Could not connect to Edge."
            )

            print(e)

            print()
            print(
                "Start Edge using:"
            )

            print(
                r'& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" '
                r'--remote-debugging-port=9222'
            )

            sys.exit(1)


        print(
            "Connected to existing Edge."
        )


        # ----------------------------------------------------
        # Existing browser context
        # ----------------------------------------------------

        if not browser.contexts:

            print(
                "No Edge browser context found."
            )

            sys.exit(1)

        context = browser.contexts[0]


        # ----------------------------------------------------
        # OPEN NEW TAB
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
            "Waiting for ServiceNow page..."
        )

        page.wait_for_timeout(5000)


        # ----------------------------------------------------
        # Scrape
        # ----------------------------------------------------

        result = scrape_story(
            page,
            story_number
        )


        # ----------------------------------------------------
        # Excel
        # ----------------------------------------------------

        create_excel(
            result
        )


        print()
        print(
            "Process completed."
        )

        print(
            "Existing Edge browser remains open."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
