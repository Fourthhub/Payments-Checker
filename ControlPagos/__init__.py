from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo
import requests
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To
import azure.functions as func

# Definir zona horaria de España
zona_horaria_españa = ZoneInfo("Europe/Madrid")
fecha_hoy = datetime.now(zona_horaria_españa)

# URL para obtener el token de acceso de Hostaway
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
        response.raise_for_status()
        data = response.json()
        for element in data.get("result", []):
            if element["status"] != "modified" and element["status"] != "new":
                continue
            if element.get("paymentStatus") != "Paid":
                nombre = element.get("guestName", "Nombre no disponible")
                reserva_id = element.get("id")
                link_reserva = f"https://dashboard.hostaway.com/reservations/{reserva_id}"
                reservasSinPagar.append(f'<li>{nombre} aún no ha pagado. <a href="{link_reserva}">Ver reserva</a></li>')
    except Exception as e:
        logging.error(f"Error al procesar la reserva: {e}")
        raise
    return reservasSinPagar

def enviarMail(reservasSinPagar):
    if reservasSinPagar:
        contenido = '<ul>' + ''.join(f'<li>{reserva}</li>' for reserva in reservasSinPagar) + '</ul>'
        mensaje_html = f'''
        <html>
        <body>
            <p><strong>Ojo, las siguientes reservas están sin pagar:</strong></p>
            {contenido}
        </body>
        </html>
        '''
    else:
        mensaje_html = '''
        <html>
        <body>
            <p><strong>No hay reservas sin pagar.</strong></p>
        </body>
        </html>
        '''

    message = Mail(
        from_email='reservas@apartamentoscantabria.net',
        to_emails=[
            To('diegoechaure@gmail.com'),
            To('rocio@apartamentoscantabria.net'),
        ],
        subject='¡Reservas Sin Pagar!',
        html_content=mensaje_html
    )
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        logging.info(f"Correo enviado, estado: {response.status_code}")
    except Exception as e:
        logging.error(f"Error al enviar el correo: {str(e)}")

def main(mytimer: func.TimerRequest) -> None:
    if mytimer.past_due:
        logging.info('The timer is past due!')

    token = obtener_acceso_hostaway()
    reservasSinPagar = reservasSemana(token)
    enviarMail(reservasSinPagar)
