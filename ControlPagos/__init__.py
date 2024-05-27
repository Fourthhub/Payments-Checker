from datetime import datetime, timezone, timedelta
import logging
from zoneinfo import ZoneInfo
import requests
import os

zona_horaria_españa = ZoneInfo("Europe/Madrid")
fecha_hoy = datetime.now(zona_horaria_españa)
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition,To

import azure.functions as func

URL_HOSTAWAY_TOKEN = "https://api.hostaway.com/v1/accessTokens"

def obtener_acceso_hostaway():
    try:
        payload = {
            "grant_type": "client_credentials",
            "client_id": "81585",
            "client_secret": "0e3c059dceb6ec1e9ec6d5c6cf4030d9c9b6e5b83d3a70d177cf66838694db5f",
            "scope": "general"
        }
        headers = {'Content-type': "application/x-www-form-urlencoded", 'Cache-control': "no-cache"}
        response = requests.post(URL_HOSTAWAY_TOKEN, data=payload, headers=headers)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.RequestException as e:
        logging.error(f"Error al obtener el token de acceso: {str(e)}")
        raise

def reservasSemana(token):
    reservasSinPagar = []
    hoy = datetime.now().strftime('%Y-%m-%d')
    catorce_dias_antes = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    url = f"https://api.hostaway.com/v1/reservations?arrivalStartDate={catorce_dias_antes}&arrivalEndDate={hoy}&includeResources=1&includePayments=1" 

    headers = {
        'Authorization': f"Bearer {token}",
        'Content-type': "application/json",
        'Cache-control': "no-cache",
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        for element in data["result"]:
            if element["paymentStatus"] != "Paid":
                nombre = element["guestName"]
                reservasSinPagar.append(f"{nombre} aún no ha pagado")

    except Exception as e:
        raise SyntaxError(f"Error al procesar la reserva: {e}")
    return data
def enviarMail(reservasSinPagar):
    cadena_unida = ' '.join(reservasSinPagar)
    message = Mail(
        from_email='reservas@apartamentoscantabria.net',
        to_emails=[
        To('diegoechaure@gmail.com'),
       # To('reservas@apartamentoscantabria.net'),
    ],
        subject='<strong>¡Reservas Sin Pagar!</strong>',
        html_content=f'Ojo las siguientes Reservas estan sin pagar: {cadena_unida}'
    )
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
         logging.error(f"Error en la función: {str(e)}")

def main(mytimer: func.TimerRequest) -> None:

    token = obtener_acceso_hostaway()
    reservasSinPagar = reservasSemana(token)
    enviarMail(reservasSinPagar)

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
