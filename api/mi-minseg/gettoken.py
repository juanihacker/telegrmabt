import requests

def main():
    print("🔑 Ingresá el JWT (solo el valor, sin 'JWT ' adelante):")
    token = input(">> ").strip()

    url = "http://localhost:5011/set_token/"
    headers = {"Content-Type": "application/json"}
    payload = {"token": token}

    try:
        response = requests.post(url, json=payload, headers=headers)
        try:
            response_data = response.json()
        except:
            print("❌ Error: El servidor respondió con algo que no es JSON.")
            print("Respuesta:", response.text)
            return

        if response.status_code == 200:
            print("✅ Token actualizado correctamente en la API.")
        else:
            print(f"❌ Error al actualizar el token: {response.status_code}")
            print(response_data)
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    main()
