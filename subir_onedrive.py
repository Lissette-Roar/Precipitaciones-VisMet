
import os
import requests

def subir_a_onedrive():
    # Variables de entorno obtenidas desde GitHub Secrets
    client_id = os.environ.get("MS_CLIENT_ID")
    client_secret = os.environ.get("MS_CLIENT_SECRET")
    tenant_id = os.environ.get("MS_TENANT_ID")
    user_email = os.environ.get("MS_USER_EMAIL") # Correo institucional del dueño de la carpeta

    # 1. Obtener Token de Acceso desde Microsoft Graph API
    url_token = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    r_token = requests.post(url_token, data=token_data)
    access_token = r_token.json().get('access_token')

    if not access_token:
        print("Error al obtener token de Microsoft:", r_token.text)
        return

    # 2. Definir la ruta anidada exactas: DOCUMENTOS LISSETTE / Datos_VisMet
    file_name = "origen_vismet_2026.csv"
    remote_path = f"DOCUMENTOS LISSETTE/Datos_VisMet/{file_name}"
    
    # Endpoint para subir o reemplazar el archivo en OneDrive
    upload_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{remote_path}:/content"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'text/csv'
    }

    # Leer el archivo generado por el scraper
    with open(file_name, 'rb') as f:
        file_data = f.read()

    # Enviar archivo a OneDrive
    response = requests.put(upload_url, headers=headers, data=file_data)
    
    if response.status_code in [200, 201]:
        print(f"¡Éxito! Archivo subido a: OneDrive/{remote_path}")
    else:
        print("Error al subir archivo:", response.status_code, response.text)

if __name__ == "__main__":
    subir_a_onedrive()

    