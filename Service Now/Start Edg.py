import pandas as pd
from playwright.sync_api import sync_playwright

#pip install playwright pandas openpyxl

# ============================================================
# CONFIGURATION
# ============================================================

EDGE_CDP_URL = "http://127.0.0.1:9222"

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
# FIND EXISTING SERVICENOW TAB
# ============================================================

def find_servicenow_page(context):

    for page in context.pages:

        url = page.url.lower()

        if "service-now" in url or "servicenow" in url:

            print("Found ServiceNow tab:")
            print(page.url)

            return page

    return None


# ============================================================
# GET FIELD VALUE
# ============================================================

def get_field_value(page, label):

    # --------------------------------------------------------
    # Method 1 - label + input
    # --------------------------------------------------------

    try:

        locator = page.locator(
            f"label:has-text('{label}')"
        ).first

        if locator.count() > 0:

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


    # --------------------------------------------------------
    # Method 2 - textarea
    # --------------------------------------------------------

    try:

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


    # --------------------------------------------------------
    # Method 3 - aria-label
    # --------------------------------------------------------

    try:

        element = page.locator(
            f"[aria-label='{label}']"
        ).first

        if element.count() > 0:

            value = element.input_value(
                timeout=2000
            )

            if value:
                return value.strip()

    except Exception:
        pass


    # --------------------------------------------------------
    # Method 4 - generic text
    # --------------------------------------------------------

    try:

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

            if len(lines) > 1:
                return lines[-1]

    except Exception:
        pass


    return ""


# ============================================================
# SCRAPE STORY
# ============================================================

def scrape_story(page, story_number):

    print()
    print("=" * 70)
    print(f"Processing: {story_number}")
    print("=" * 70)

    # --------------------------------------------------------
    # Search ServiceNow using current browser session
    # --------------------------------------------------------

    # IMPORTANT:
    # Replace this URL with the actual URL pattern
    # used by your ServiceNow Story application.

    url = (
        f"https://YOUR-COMPANY.service-now.com/"
        f"rm_story_list.do"
        f"?sysparm_query=number={story_number}"
    )

    print("Opening:")
    print(url)

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(3000)

    # --------------------------------------------------------
    # Extract fields
    # --------------------------------------------------------

    data = {}

    data["Stry Number"] = story_number

    data["SC Task/Incident"] = get_field_value(
        page,
        "SC Task/Incident"
    )

    data["Stry Description"] = get_field_value(
        page,
        "Story Description"
    )

    data["State"] = get_field_value(
        page,
        "State"
    )

    data["Sub State"] = get_field_value(
        page,
        "Sub State"
    )

    data["Work Notes"] = get_field_value(
        page,
        "Work Notes"
    )

    data["Dev Document"] = get_field_value(
        page,
        "Dev Document"
    )

    data["QA Document"] = get_field_value(
        page,
        "QA Document"
    )

    data["Assigned To"] = get_field_value(
        page,
        "Assigned To"
    )

    data["Owner"] = get_field_value(
        page,
        "Owner"
    )

    data["Original Task"] = get_field_value(
        page,
        "Original Task"
    )

    data["Project"] = get_field_value(
        page,
        "Project"
    )

    data["Release"] = get_field_value(
        page,
        "Release"
    )

    return data


# ============================================================
# CREATE EXCEL
# ============================================================

def create_excel(data):

    df = pd.DataFrame(
        [data],
        columns=EXCEL_COLUMNS
    )

    df.to_excel(
        OUTPUT_FILE,
        index=False,
        engine="openpyxl"
    )

    print()
    print("=" * 70)
    print("Excel created:")
    print(OUTPUT_FILE)
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    story_number = input(
        "Enter ServiceNow Story Number: "
    ).strip()

    if not story_number:

        raise ValueError(
            "Story number cannot be empty."
        )


    with sync_playwright() as p:

        print("Connecting to existing Microsoft Edge...")

        browser = p.chromium.connect_over_cdp(
            EDGE_CDP_URL
        )

        print("Connected to Edge.")

        context = browser.contexts[0]

        # ----------------------------------------------------
        # Find ServiceNow tab
        # ----------------------------------------------------

        page = find_servicenow_page(
            context
        )

        if page is None:

            print()
            print(
                "No ServiceNow tab was found."
            )

            print(
                "Please open ServiceNow in Edge "
                "and run the script again."
            )

            browser.close()

            return

        # ----------------------------------------------------
        # Scrape
        # ----------------------------------------------------

        data = scrape_story(
            page,
            story_number
        )

        # ----------------------------------------------------
        # Create Excel
        # ----------------------------------------------------

        create_excel(
            data
        )

        # ----------------------------------------------------
        # Do NOT close Edge
        # ----------------------------------------------------

        print()
        print(
            "Done. Existing Edge browser remains open."
        )


if __name__ == "__main__":
    main()
