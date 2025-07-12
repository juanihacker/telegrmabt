from flask import Flask, request, jsonify
import asyncio
import requests
from playwright.async_api import async_playwright
import base64
from io import BytesIO

# ---------------- CONFIGURACIONES ---------------- #

PROXY_URL = "http://9KSjzc5XYm2fKdKF:0UYdEff1TeRrIaaF_country-ar@geo.iproyal.com:12321"
CAPMONSTER_API_KEY = 'a6ce897be16ec1f77472ca6bc08361ac'

PROXY_HOST = "geo.iproyal.com:12321"
PROXY_USER = "9KSjzc5XYm2fKdKF"
PROXY_PASS = "0UYdEff1TeRrIaaF_country-ar"

# ---------------- FLASK APP ---------------- #

app = Flask(__name__)

# ----------- CAPTCHA CapMonster ----------- #

async def solve_captcha_with_capmonster(api_key, sitekey, url):
    create_task_payload = {
        'clientKey': api_key,
        'task': {
            'type': 'RecaptchaV2TaskProxyless',
            'websiteURL': url,
            'websiteKey': sitekey
        }
    }
    response = requests.post('https://api.capmonster.cloud/createTask', json=create_task_payload)
    result = response.json()
    if result['errorId'] != 0:
        raise Exception(f"Error creando tarea: {result['errorDescription']}")
    task_id = result['taskId']

    while True:
        await asyncio.sleep(5)
        res = requests.post('https://api.capmonster.cloud/getTaskResult', json={
            'clientKey': api_key,
            'taskId': task_id
        })
        res_json = res.json()
        if res_json['errorId'] != 0:
            raise Exception(f"Error en obtener resultado: {res_json['errorDescription']}")
        if res_json['status'] == 'ready':
            return res_json['solution']['gRecaptchaResponse']

# ----------- Consulta IPAV ----------- #

async def consulta_ipav(dni, sexo):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": f"http://{PROXY_HOST}",
                "username": PROXY_USER,
                "password": PROXY_PASS
            }
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        await page.goto('https://oficinaipav.lapampa.gob.ar/oauth/gam/redirect')

        await page.fill('#vUSERNAME', '20217696780')
        await page.fill('#vUSERPASSWORD', 'Nico2Ceci$')
        await page.click('#INGRESAR')
        await page.wait_for_timeout(2000)

        cookies = await context.cookies()
        await browser.close()

        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        # Proxy también para requests
        session.proxies = {
            "http": PROXY_URL,
            "https": PROXY_URL
        }

        sitekey = "6Lf1njUqAAAAAPtTIWj4jG-pk3n1GtTLisLI4bt2"
        url = "https://oficinaipav.lapampa.gob.ar/"
        captcha_response = await solve_captcha_with_capmonster(CAPMONSTER_API_KEY, sitekey, url)

        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': url,
            'Origin': url
        }

        response = session.get(
            f'https://oficinaipav.lapampa.gob.ar/json/datospersona?cuil={dni}&sexo={sexo}&parentescoId=&g-recaptcha-response={captcha_response}',
            headers=headers,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception("Error al obtener datos del IPAV")

        return response.json()

# ----------- Endpoint Flask ----------- #

@app.route("/rn/<dni>/<sexo>")
def rn(dni, sexo):
    try:
        resultado = asyncio.run(consulta_ipav(dni, sexo))
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------- Inicio del servidor ----------- #

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5025)
