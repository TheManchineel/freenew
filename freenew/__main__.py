import logging
from signal import signal, SIGINT, SIGTERM
from datetime import datetime, timedelta
from pycron import is_now, has_been
from time import sleep
from json import load as json_load
from pydantic import parse_obj_as
from pexpect import spawn
from contextlib import contextmanager
from selenium.webdriver import Remote
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from .models import Domain, Account, RenewError, Status
from . import constants


@contextmanager
def get_webdriver() -> WebDriver:
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox") # required when running as root user; TODO: create a separate user
        options.add_argument("--disable-dev-shm-usage")

        session = spawn(*constants.DRIVER_START_COMMAND)
        session.expect(constants.STARTUP_SUCESS_MESSAGE)

        driver = Remote(command_executor=constants.REMOTE_EXECUTOR_URL, options=options)
        
        yield driver
    except Exception as e:
        raise RenewError(f"Error getting webdriver: {e}")
    finally:
        driver.quit()
        session.terminate()


def renew_domain(driver: WebDriver, domain: Domain) -> int:
    logging.info(f"Renewing {domain.domain_name} (expires in {domain.days_until_expiry} days)...")

    driver.get(constants.RENEW_DOMAIN_URL + domain.domain_id)

    renew_table = driver.find_element(by=By.CLASS_NAME, value="table-striped").find_element(
        by=By.TAG_NAME, value="tbody"
    )

    renew_row = renew_table.find_element(by=By.TAG_NAME, value="tr")

    renew_columns = renew_row.find_elements(by=By.TAG_NAME, value="td")

    renew_dropdown = renew_columns[3].find_element(by=By.CSS_SELECTOR, value="select")

    renew_dropdown.find_element(by=By.CSS_SELECTOR, value=f'option[value="{constants.RENEWAL_PERIOD}"]').click()

    driver.find_element(by=By.CSS_SELECTOR, value="input[type=submit]").click()

    # wait until strong element appears with order number
    WebDriverWait(driver, constants.TIMEOUT).until(lambda driver: driver.find_element(by=By.TAG_NAME, value="strong"))

    order_number = driver.find_element(by=By.TAG_NAME, value="strong").text.split(": ")[-1]
    return order_number


def get_accounts() -> list[Account]:
    with open(constants.CONFIG_FILE, "r") as f:
        return parse_obj_as(list[Account], json_load(f)["accounts"])


def login_to_freenom(driver: WebDriver, username: str, password: str) -> None:
    driver.get(constants.RENEWALS_URL)
    driver.find_element(by=By.ID, value="username").send_keys(username)
    driver.find_element(by=By.ID, value="password").send_keys(password)
    driver.find_element(by=By.CSS_SELECTOR, value="input[type=submit]").click()

    # wait until the table appears
    try:
        WebDriverWait(driver, constants.TIMEOUT).until(
            lambda driver: driver.find_element(by=By.CLASS_NAME, value="table-striped")
        )
    except TimeoutException as e:
        raise RenewError(f"Error logging in to account {username}: {e}")


def logout_from_freenom(driver: WebDriver) -> None:
    driver.get(constants.LOGOUT_URL)


def renew_account(driver: WebDriver, account: Account) -> int:
    try:
        login_to_freenom(driver, account.username, account.password)

        domains: list[Domain] = get_domains_of_current_account(driver)
        renewed_count = 0

        for domain in domains:
            if (
                domain.renewable
                and domain.status == Status.ACTIVE
                and domain.domain_name not in account.excluded_domains
            ):
                try:
                    order_number = renew_domain(driver, domain)
                    logging.info(f"Renewed {domain.domain_name} (order number {order_number})")
                    renewed_count += 1
                except Exception as e:
                    logging.error(f"Error renewing {domain.domain_name}: {e}")

        return renewed_count

    except Exception as e:
        raise RenewError(f"Error renewing account {account.username}: {e}")

    finally:
        logout_from_freenom(driver)


def get_domains_of_current_account(driver: WebDriver) -> list[Domain]:
    domain_table: WebElement = driver.find_element(by=By.CLASS_NAME, value="table-striped").find_element(
        by=By.TAG_NAME, value="tbody"
    )
    domain_rows: list[WebElement] = domain_table.find_elements(by=By.TAG_NAME, value="tr")

    domains: list[Domain] = []
    for row in domain_rows:
        columns: list[WebElement] = row.find_elements(by=By.TAG_NAME, value="td")

        domains.append(
            Domain(
                domain_name=columns[0].text,
                status=columns[1].text,
                days_until_expiry=int(columns[2].text.split(" ")[0]),
                renewable=(columns[3].text == "Renewable"),
                domain_id=columns[4].find_element(by=By.TAG_NAME, value="a").get_attribute("href").split("=")[-1],
            )
        )

    return domains


def routine() -> None:
    with get_webdriver() as driver:
        accounts: list[Account] = get_accounts()
        total_renewed_count = 0

        with open(constants.CONFIG_FILE, "r") as f:
            config = json_load(f)
            account_interval_seconds = config["account_interval_seconds"]

        for account in accounts:
            try:
                logging.info(f"Renewing account {account.username}...")
                total_renewed_count += renew_account(driver, account)
            except RenewError as e:
                logging.error(e)
            finally:
                logout_from_freenom(driver)
                if account != accounts[-1]:
                    logging.info(f"Waiting {account_interval_seconds} seconds before renewing next account...")
                    sleep(account_interval_seconds)

        logging.info(f"Renewed {total_renewed_count} domain{'s' if total_renewed_count != 1 else ''} in total.")


if __name__ == "__main__":
    crontab: str
    exit_signal: bool = False
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    def signal_handler(signal, frame):
        logging.info("Received exit signal. Finishing any current renewal routine and exiting...")
        global exit_signal
        exit_signal = True

    signal(SIGINT, signal_handler)
    signal(SIGTERM, signal_handler)

    with open(constants.CONFIG_FILE, "r") as f:
        try:
            crontab = json_load(f)["crontab"]
        except KeyError:
            crontab = "0 16 * * *"

    last_renewal = datetime.min

    while True:
        if exit_signal:
            logging.info("Exiting...")
            exit(0)

        if last_renewal.replace(microsecond=0, second=0) != datetime.now().replace(microsecond=0, second=0) and (
            is_now(crontab) or has_been(crontab, last_renewal.replace(microsecond=0, second=0) + timedelta(minutes=1))
        ):
            logging.info("Starting automated renewal routine...")
            try:
                routine()
                last_renewal = datetime.now()
            except Exception as e:
                logging.error(f"Error running routine: {e}. Will try again in {constants.RETRY_SECONDS} seconds...")
                sleep(constants.RETRY_SECONDS)
        else:
            sleep(5)
