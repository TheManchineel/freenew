# URLs
REMOTE_EXECUTOR_URL = "http://127.0.0.1:4444/wd/hub"
RENEWALS_URL = "https://my.freenom.com/domains.php?a=renewals"
RENEW_DOMAIN_URL = "https://my.freenom.com/domains.php?a=renewdomain&domain="
LOGOUT_URL = "https://my.freenom.com/logout.php"

# Configuration
DRIVER_START_COMMAND = ("chromedriver", ["--port=4444", "--url-base=/wd/hub", "--whitelisted-ips=127.0.0.1"])
STARTUP_SUCESS_MESSAGE = "ChromeDriver was started successfully."
CONFIG_FILE = "config.json"
RENEWAL_PERIOD = "12M"
TIMEOUT = 30  # seconds
RETRY_SECONDS = 60
