# freenew: renew your Freenom domains automatically

![image](https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=Selenium&logoColor=white) ![image](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![image](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)

`freenew` will regularly check your Freenom domain names to see if they are eligible for renewal. If so, it will renew them for you.

As of 2023 Freenom no longer allows domain registrations, so this tool is only useful for renewing existing domains even if they are across multiple accounts.

## Installation (Docker)

The recommended way to run `freenew` is using Docker. This will ensure that all dependencies are installed and configured correctly, including the web driver for Selenium.

First, create a valid `config.json` file on your host system. See the [Configuration](#configuration) section for details.

Then, run the following command:

```bash
docker run -d --name freenew -v /path/to/config.json:/app/config.json --restart unless-stopped manchineel/freenew
```

`freenew` will handle renewing your domains automatically.

## Configuration

Configuration is done using a `config.json` file. An example:

```json
{
    "accounts": [
        {
            "username": "me@example.com",
            "password": "1234",
            "excluded_domains": ["domain_i_dont_want_to_renew.gq"]
        },
        {
            "username": "renew_all_my_domains@example.com",
            "password": "abcd",
            "excluded_domains": []
        }
    ],
    "account_interval_seconds": 300
}
```

Domain names in the `excluded_domains` array will not be renewed, even if they are eligible for renewal.

The `account_interval_seconds` value is the number of seconds to wait between each separate account sign-in. This is to avoid Freenom blocking your IP address for too many login attempts (although this has not been an issue for me, and I have made ***lots*** of logins).