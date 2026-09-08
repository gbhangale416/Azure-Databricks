from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# pip install selenium
SERVICENOW_URL = "https://your-instance.service-now.com"


def connect_to_existing_edge():

    options = Options()

    options.add_experimental_option(
        "debuggerAddress",
        "127.0.0.1:9222"
    )

    driver = webdriver.Edge(options=options)

    return driver


def get_value_by_xpath(driver, xpath, timeout=30):

    try:

        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, xpath)
            )
        )

        tag_name = element.tag_name.lower()

        if tag_name in ["input", "textarea", "select"]:
            return element.get_attribute("value")

        return element.text

    except Exception as e:

        print(f"Failed XPath: {xpath}")
        print(f"Error: {e}")

        return None


def open_servicenow(driver):

    # Open NEW TAB
    driver.switch_to.new_window("tab")

    # Open ServiceNow
    driver.get(SERVICENOW_URL)

    print("ServiceNow opened")


def main():

    driver = connect_to_existing_edge()

    print("Connected to existing Edge")

    open_servicenow(driver)

    # Give yourself time for SSO/MFA
    input("Complete ServiceNow login/MFA, then press ENTER...")

    # Test XPath
    xpath = "//input[@name='number']"

    value = get_value_by_xpath(
        driver,
        xpath
    )

    print("Value:", value)


if __name__ == "__main__":
    main()
