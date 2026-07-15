import requests
from easydict import EasyDict
from playwright.sync_api import sync_playwright
import click
import json
import time
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / ".authelia"

def submit_form(goto_url: str, username: str, password: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto(goto_url)  
        
        page.fill("input#username-textfield", username)
        page.fill("input#password-textfield", password)

        page.click("button#sign-in-button")

        with page.expect_response("**/consent/openid/decision**") as response_info:
          page.click("button#openid-consent-accept")
        
        if response_info.value.ok:
            page.get_by_text("Consent has been accepted and processed").wait_for(state="visible")
        
        browser.close()

def device_authorization(base_url: str, client_id: str, client_secret: str, scope: str) -> EasyDict:
    url = f"{base_url}/api/oidc/device-authorization"
    response = requests.post(
        url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope,
        },
    )
    response.raise_for_status()
    return EasyDict(response.json())

def token(base_url: str, client_id: str, client_secret: str, device_code: str) -> EasyDict:
    url = f"{base_url}/api/oidc/token"
    response = requests.post(
        url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    response.raise_for_status()
    return EasyDict(response.json())

def auth(url, client_id, client_secret, user, password) -> EasyDict:
    auth = device_authorization(
        base_url=url,
        client_id=client_id,
        client_secret=client_secret,
        scope="openid profile email",
    )
    submit_form(auth.verification_uri_complete, user, password)
    return token(
        base_url=url,
        client_id=client_id,
        client_secret=client_secret,
        device_code=auth.device_code
    )

def is_valid_until(unix_ts: int | float) -> bool:
    if isinstance(unix_ts, str):
        try:
            unix_ts = float(unix_ts)
            if unix_ts.is_integer():
                unix_ts = int(unix_ts)
        except ValueError:
            raise ValueError(f"Cannot convert string '{unix_ts}' to a number.")
    return time.time() < unix_ts - 60

def save_id_token(id_token: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(id_token)

def load_id_token() -> EasyDict:
    cfg = None
    try: 
        cfg = EasyDict(json.loads(CONFIG_PATH.read_text()))
    except:
        pass
    return cfg

@click.command()
@click.option('--url', default="https://authelia.apps", help='Base URL of the Authelia instance.')
@click.option('--client_id', help="Authleia's client ID.")
@click.option('--client_secret', help="Authleia's client secret.")
@click.option('--user', help="The username for the token request.")
@click.option('--password', help="The password for the token request.")
def get_authelia_token(url, client_id, client_secret, user, password):
    token = load_id_token()
    if not token or not token.exp or not is_valid_until(token.exp):
        token = auth(url, client_id, client_secret, user, password)
        token.exp = str(int(time.time()) + int(token.expires_in))
        save_id_token(json.dumps(token, indent=2))
    print(token.id_token)  

if __name__ == "__main__":
    get_authelia_token()
