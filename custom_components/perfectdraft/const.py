DOMAIN = "perfectdraft"

API_BASE_URL = "https://api.perfectdraft.com"
API_KEY = "cAyzERqthCJXYVExjNAhr9CzE8ncLN2cQK3WGK10"

RECAPTCHA_SITE_KEY = "6LcZQiUoAAAAAAO3JUjLiT470c-pNXbWyepuvMtV"
RECAPTCHA_ACTION = "Magento/login"
# PerfectDraft's Cognito PreAuthentication Lambda rejects sign-in without it.
RECAPTCHA_DOMAIN = "https://www.perfectdraft.com"

COGNITO_REGION = "eu-west-1"
COGNITO_CLIENT_ID = "57ddq2ppqg2jcpup06r2g1deur"

DEFAULT_SCAN_INTERVAL = 900  # 15 minutes
MIN_SCAN_INTERVAL = 60  # 1 minute

CONF_REFRESH_TOKEN = "refresh_token"
CONF_ACCESS_TOKEN = "access_token"
CONF_ID_TOKEN = "id_token"
CONF_USER_ID = "user_id"
CONF_MACHINE_ID = "machine_id"
CONF_SCAN_INTERVAL = "scan_interval"

PLATFORMS = ["sensor", "button"]


def keg_changed_signal(machine_id: str) -> str:
    """Dispatcher signal fired when the keg is manually marked as changed."""
    return f"{DOMAIN}_keg_changed_{machine_id}"
