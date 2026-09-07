import re
import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURATION
# ============================================================

# YOUR SERVICENOW URL
SERVICENOW_URL = "https://yourcompany.service-now.com"

# Existing Edge browser CDP connection
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
# SERVICE NOW LABELS
# ============================================================

FIELD_LABELS = {

    "Stry Number": [
        "Number",
        "Story Number"
    ],

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
# GET VALUE FROM ELEMENT
# ============================================================

def get_element_value(element):

    try:

        tag = element.evaluate(
            "(el) => el.tagName.toLowerCase()"
        )

        # ----------------------------------------------------
        # Input / textarea
        # ----------------------------------------------------

        if tag in [
            "input",
            "textarea"
        ]:

            value = element.input_value()

            if value:
                return normalize_text(value)


        # ----------------------------------------------------
        # Select
        # ----------------------------------------------------

        if tag == "select":

            value = element.input_value()

            if value:
                return normalize_text(value)


    except Exception:
        pass


    # --------------------------------------------------------
    # Try text content
    # --------------------------------------------------------

    try:

        value = element.text_content()

        if value:
            return normalize_text(value)

    except Exception:
        pass


    return ""


# ============================================================
# FIND FIELD USING SERVICENOW DOM
# ============================================================

def get_field_value(page, labels):

    """
    ServiceNow example:

        <div
            data-type="label"
            id="label.rm_story.number">
            Number
        </div>

        <input
            id="rm_story.number"
            value="STRY0055879"
            aria-label="Number">
    """

    # --------------------------------------------------------
    # Find all ServiceNow field labels
    # --------------------------------------------------------

    label_elements = page.locator(
        "div[data-type='label']"
    )

    label_count = label_elements.count()

    print(
        f"    ServiceNow labels found: {label_count}"
    )

    for i in range(label_count):

        try:

            label_element = label_elements.nth(i)

            label_text = normalize_text(
                label_element.inner_text()
            )

            # ------------------------------------------------
            # Check whether this is the label we want
            # ------------------------------------------------

            matched = False

            for expected_label in labels:

                if label_text.lower() == expected_label.lower():

                    matched = True
                    break

            if not matched:
                continue


            # ------------------------------------------------
            # Get label ID
            #
            # Example:
            # label.rm_story.number
            # ------------------------------------------------

            label_id = label_element.get_attribute(
                "id"
            )

            print(
                f"    Found label: {label_text}"
            )

            print(
                f"    Label ID: {label_id}"
            )


            if not label_id:
                continue


            # ------------------------------------------------
            # Convert:
            #
            # label.rm_story.number
            #
            # to:
            #
            # rm_story.number
            # ------------------------------------------------

            if label_id.startswith("label."):

                field_id = label_id[
                    len("label.") :
                ]

            else:

                field_id = label_id


            print(
                f"    Field ID: {field_id}"
            )


            # ------------------------------------------------
            # Find exact field
            # ------------------------------------------------

            field = page.locator(
                f"#{field_id}"
            ).first


            if field.count() > 0:

                value = get_element_value(
                    field
                )

                if value:

                    print(
                        f"    Value: {value}"
                    )

                    return value


            # ------------------------------------------------
            # Try input
            # ------------------------------------------------

            field = page.locator(
                f"input#{field_id}"
            ).first

            if field.count() > 0:

                value = get_element_value(
                    field
                )

                if value:

                    print(
                        f"    Value: {value}"
                    )

                    return value


            # ------------------------------------------------
            # Try textarea
            # ------------------------------------------------

            field = page.locator(
                f"textarea#{field_id}"
            ).first

            if field.count() > 0:

                value = get_element_value(
                    field
                )

                if value:

                    print(
                        f"    Value: {value}"
                    )

                    return value


            # ------------------------------------------------
            # Try select
            # ------------------------------------------------

            field = page.locator(
                f"select#{field_id}"
            ).first

            if field.count() > 0:

                value = get_element_value(
                    field
                )

                if value:

                    print(
                        f"    Value: {value}"
                    )

                    return value


            # ------------------------------------------------
            # Search inside parent container
            # ------------------------------------------------

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

                    print(
                        f"    Value: {value}"
                    )

                    return value


        except Exception as e:

            print(
                f"    Field processing error: {e}"
            )


    print(
        "    NOT FOUND"
    )

    return ""


# ============================================================
# DEBUG - SHOW ALL SERVICENOW FIELDS
# ============================================================

def show_servicenow_fields(page):

    print()
    print("=" * 80)
    print("SERVICE NOW FIELDS FOUND")
    print("=" * 80)

    labels = page.locator(
        "div[data-type='label']"
    )

    count = labels.count()

    for i in range(count):

        try:

            label = labels.nth(i)

            text = normalize_text(
                label.inner_text()
            )

            label_id = label.get_attribute(
                "id"
            )

            print(
                f"{i:03d} | {text:40} | {label_id}"
            )

        except Exception:
            pass

    print("=" * 80)


# ============================================================
# OPEN SERVICENOW
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

    page.wait_for_timeout(5000)

    page.bring_to_front()

    print(
        f"ServiceNow URL: {page.url}"
    )

    return page


# ============================================================
# SEARCH STORY
# ============================================================

def search_story(page, story_number):

    print()
    print("=" * 80)
    print(
        f"Searching for Story: {story_number}"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # Look for ServiceNow search boxes
    # --------------------------------------------------------

    selectors = [
        "input[placeholder*='Search']",
        "input[placeholder*='search']",
        "input[aria-label*='Search']",
        "input[aria-label*='search']"
    ]

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            )

            count = elements.count()

            print(
                f"Selector {selector}: {count}"
            )

            for i in range(count):

                element = elements.nth(i)

                if not element.is_visible():
                    continue

                print(
                    f"Using search box: {selector}"
                )

                element.fill(
                    story_number
                )

                element.press(
                    "Enter"
                )

                page.wait_for_timeout(
                    5000
                )

                return True

        except Exception as e:

            print(
                f"Search error: {e}"
            )


    print()
    print(
        "Could not automatically identify the "
        "ServiceNow search box."
    )

    return False


# ============================================================
# CHECK STORY
# ============================================================

def story_is_visible(page, story_number):

    try:

        field = page.locator(
            "#rm_story\\.number"
        )

        if field.count() > 0:

            value = field.input_value()

            if value.strip() == story_number:

                return True

    except Exception:
        pass


    try:

        elements = page.locator(
            "input"
        )

        for i in range(elements.count()):

            element = elements.nth(i)

            try:

                value = element.input_value()

                if value.strip() == story_number:

                    return True

            except Exception:
                pass

    except Exception:
        pass


    return False


# ============================================================
# SCRAPE STORY
# ============================================================

def scrape_story(page, story_number):

    print()
    print("=" * 80)
    print(
        f"SCRAPING STORY: {story_number}"
    )
    print("=" * 80)

    page.wait_for_timeout(3000)

    # --------------------------------------------------------
    # First display all fields
    # --------------------------------------------------------

    show_servicenow_fields(
        page
    )

    # --------------------------------------------------------
    # Extract
    # --------------------------------------------------------

    result = {}

    for column in EXCEL_COLUMNS:

        print()
        print(
            f"Reading: {column}"
        )

        # ----------------------------------------------------
        # Story Number
        # ----------------------------------------------------

        if column == "Stry Number":

            value = story_number

        else:

            value = get_field_value(
                page,
                FIELD_LABELS[column]
            )

        result[column] = value

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

        # Freeze header
        worksheet.freeze_panes = "A2"

        # Auto width
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
    print("=" * 80)
    print("EXCEL CREATED SUCCESSFULLY")
    print("=" * 80)

    print(
        Path(OUTPUT_FILE).absolute()
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
            "Story number cannot be empty."
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Connect to Edge
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

        except Exception as e:

            print()
            print(
                "ERROR: Could not connect to Edge."
            )

            print(e)

            print()
            print(
                "Start Edge with:"
            )

            print(
                r'& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" '
                r'--remote-debugging-port=9222'
            )

            sys.exit(1)


        print(
            "Connected to Edge successfully."
        )


        # ----------------------------------------------------
        # Browser context
        # ----------------------------------------------------

        if not browser.contexts:

            print(
                "No Edge context found."
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
        # Wait
        # ----------------------------------------------------

        page.wait_for_timeout(
            5000
        )


        # ----------------------------------------------------
        # Verify Story
        # ----------------------------------------------------

        if not story_is_visible(
            page,
            story_number
        ):

            print()
            print(
                "WARNING:"
            )

            print(
                f"{story_number} was not detected "
                "on the current page."
            )

            print()
            print(
                "The ServiceNow search/navigation "
                "may need to be adjusted for your "
                "specific application."
            )

            print()
            print(
                "However, the current page fields "
                "will still be inspected."
            )


        # ----------------------------------------------------
        # Scrape
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
            "Completed."
        )

        print(
            "Edge has been left open."
        )


if __name__ == "__main__":
    main()
