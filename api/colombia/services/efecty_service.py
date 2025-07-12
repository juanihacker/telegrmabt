import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import base64
from config import Config

def consultar_persona(cedula):
    url = Config.EFECTY_SOAP_URL
    username = Config.EFECTY_USERNAME
    password = Config.EFECTY_PASSWORD

    created = datetime.utcnow().isoformat() + "Z"
    nonce = base64.b64encode(b"12345678").decode()

    headers = {
        "Content-Type": "text/xml",
        "SOAPAction": "http://tempuri.org/IServicioConsultas/ConsultarPersona",
        "User-Agent": "Efecty-V2/4 CFNetwork/1335.0.3 Darwin/21.6.0"
    }

    xml_payload = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                      xmlns:tem="http://tempuri.org/"
                      xmlns:efec="http://schemas.datacontract.org/2004/07/Efecty.ServiciosSOA.Consultas.DataContracts"
                      xmlns:efec1="http://schemas.datacontract.org/2004/07/Efecty.ServiciosSOA.Comun.DataContracts">
       <soapenv:Header>
          <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
                         xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
             <wsse:UsernameToken wsu:Id="UsernameToken-Test">
                <wsse:Username>{username}</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{password}</wsse:Password>
                <wsse:Nonce>{nonce}</wsse:Nonce>
                <wsu:Created>{created}</wsu:Created>
             </wsse:UsernameToken>
          </wsse:Security>
       </soapenv:Header>
       <soapenv:Body>
          <tem:ConsultarPersona>
             <tem:request>
                <efec:identificacion>
                   <efec1:Documento>{cedula}</efec1:Documento>
                   <efec1:TipoDocumento>CC</efec1:TipoDocumento>
                </efec:identificacion>
             </tem:request>
          </tem:ConsultarPersona>
       </soapenv:Body>
    </soapenv:Envelope>"""

    response = requests.post(url, headers=headers, data=xml_payload)

    if response.status_code != 200:
        raise Exception(f"Error al consultar Efecty: {response.status_code}")

    root = ET.fromstring(response.content)
    ns = {
        's': 'http://schemas.xmlsoap.org/soap/envelope/',
        'a': 'http://schemas.datacontract.org/2004/07/Efecty.ServiciosSOA.Consultas.DataContracts',
        'b': 'http://schemas.datacontract.org/2004/07/Efecty.ServiciosSOA.Comun.DataContracts'
    }

    usuario = root.find('.//b:ClienteID/..', ns)
    if usuario is None:
        raise Exception("No se encontró información de usuario.")

    def get(tag):
        el = usuario.find(f'b:{tag}', ns)
        return el.text if el is not None and el.text is not None else ""

    def get_bool(tag):
        val = get(tag)
        return val.lower() == "true"

    return {
        "cedula": get("ClienteID/b:Documento"),
        "nombre": get("Nombre"),
        "apellido_1": get("Apellido1"),
        "apellido_2": get("Apellido2"),
        "tipo_documento": get("ClienteID/b:TipoDocumento"),
        "fecha_expedicion": get("FechaExpedicion")[:10],
        "municipio_expedicion": get("MunicipioExpedicion"),
        "municipio_residencia": get("MunicipioResidencia"),
        "direccion": get("Direccion"),
        "codigo_postal": get("CodigoPostal"),
        "telefono": get("Telefono"),
        "celular": get("Celular"),
        "correo": get("CorreoElectronico"),
        "ocupacion": get("Ocupacion"),
        "origen_fondos": get("OrigenFondos"),
        "pep": get("ClientePEP"),
        "autorizo_consulta": get_bool("AutorizoConsulta"),
        "consultado_cifin": get_bool("ConsultadoCifin"),
        "tratamiento_datos": get_bool("TratamientoDatos"),
        "biometria_web": get_bool("BiometriaWeb")
    }
