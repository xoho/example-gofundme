import os
from pydantic import BaseModel


class Config(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "MyFundQuest")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key")
    WEEDFS_FILER_URL: str = os.getenv("WEEDFS_FILER_URL", "")
    WEEDFS_BASE_FOLDER: str = os.getenv("WEEDFS_BASE_FOLDER", "/myfundquest")
    LOCAL_BASE_FOLDER: str = os.getenv("LOCAL_BASE_FOLDER", "data")
    FILE_SYSTEM_TYPE: str = os.getenv("FILE_SYSTEM_TYPE", "localfs")
    DEFAULT_RANDOM_TEXT_LENGTH: int = int(os.getenv("DEFAULT_RANDOM_TEXT_LENGTH", 32))
    PATH_SEPERATOR: str = os.getenv("PATH_SEPERATOR", os.path.sep)

    CELERY_BROKER: str = os.getenv("CELERY_BROKER", "redis://localhost:6379/0")
    CELERY_BACKEND: str = os.getenv("CELERY_BACKEND", "redis://localhost:6379/1")

    SERVER_PORT: int = int(os.getenv("SERVER_PORT", 80))
    ADMIN_EMAILS: str = os.getenv("ADMIN_EMAILS", "")
    ENABLE_EXPLICIT_TEXT_CHECKING: bool = (
        os.getenv("ENABLE_EXPLICIT_TEXT_CHECKING", "FALSE").upper() == "TRUE"
    )
    ENABLE_EXPLICIT_IMAGE_CHECKING: bool = (
        os.getenv("ENABLE_EXPLICIT_IMAGE_CHECKING", "TRUE").upper() == "TRUE"
    )
    MAX_DESCRIPTION_LENGTH: int = int(os.getenv("MAX_DESCRIPTION_LENGTH", 4000))

    EXPLICIT_IMAGE_THRESHOLD: float = float(os.getenv("EXPLICIT_IMAGE_THRESHOLD", 0.6))
    NUDENET_CLASSIFIER_URL: str = os.getenv("NUDENET_CLASSIFIER_URL", "")
    ROOT_LOG_LEVEL: str = os.getenv("ROOT_LOG_LEVEL", "INFO")
    COUNTRY_CURRENCY_DATA: str = os.getenv(
        "COUNTRY_CURRENCY_DATA",
        os.path.join(os.path.dirname(__file__), "support", "country_currency.json"),
    )
    CATEGORIES_DATA: str = os.getenv(
        "CATEGORIES_DATA",
        os.path.join(os.path.dirname(__file__), "support", "categories.json"),
    )
    CAMPAIGN_TYPES_DATA: str = os.getenv(
        "CAMPAIGN_TYPES_DATA",
        os.path.join(os.path.dirname(__file__), "support", "campaign_types.json"),
    )
    DONATION_DISTRIBUTION_DATA: str = os.getenv(
        "DONATION_DISTRIBUTION_DATA",
        os.path.join(
            os.path.dirname(__file__), "support", "donation_distribution.json"
        ),
    )
    FIRST_NAMES_DATA: str = os.getenv(
        "FIRST_NAMES_DATA",
        os.path.join(os.path.dirname(__file__), "support", "first_names.json"),
    )
    MESSAGE_BANK_DATA: str = os.getenv(
        "MESSAGE_BANK_DATA",
        os.path.join(os.path.dirname(__file__), "support", "message_bank.json"),
    )
    ANONYMOUS_POST_PERCENT: float = float(os.getenv("ANONYMOUS_POST_PERCENT", 0.2))
    MESSAGE_POST_PERCENT: float = float(os.getenv("MESSAGE_POST_PERCENT", 0.3))
    MAX_LATEST_COUNT: int = int(os.getenv("MAX_LATEST_COUNT", 100))
    SENTIMENT_URL: str = os.getenv("SENTIMENT_URL", "")

    # algorithm: see readme
    DIVISOR_UPDATES_PER_TIME_PERIOD: int = max(
        1, int(os.getenv("NUMBER_UPDATES_PER_TIME_PERIOD", 1000))
    )  # higher means less updates
    UPDATE_TIME_PERIOD_IN_MINUTES: int = max(
        1, int(os.getenv("UPDATE_TIME_PERIOD_IN_MINUTES", 100))
    )  # higher means less updates


config = Config()

# print relevant variables
for var in ["ADMIN_EMAILS"]:
    print(f"{var}: {getattr(config, var)}")


if __name__ == "__main__":
    # create the config if called from cli
    for key in config.dict().keys():
        print(f"export {key}={getattr(config, key)}")
