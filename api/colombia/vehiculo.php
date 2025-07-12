<?php
header('Content-Type: application/json; charset=utf-8');
ini_set('display_errors', 0);

require_once CORE_PATH . '/Database.php';
require_once APP_PATH . '/models/User.php';

if (!isset($_GET['id'])) {
    echo json_encode(["error" => "Falta parámetro id de usuario"], JSON_UNESCAPED_UNICODE);
    exit;
}

if (!isset($_GET['placa'])) {
    echo json_encode(["error" => "Falta parámetro placa del vehículo"], JSON_UNESCAPED_UNICODE);
    exit;
}

$userId = $_GET['id'];
$placa = trim($_GET['placa']);
$tipo = isset($_GET['tipo']) ? $_GET['tipo'] : "C";
$endpointVehiculo = "https://www.runt.gov.co/consultaCiudadana/publico/automotores/?429";
$endpointSoat = "https://www.runt.gov.co/consultaCiudadana/publico/automotores/soats?478";
$endpointRtm = "https://www.runt.gov.co/consultaCiudadana/publico/automotores/rtms?96";
$maxIntentos = 3;
$maxIntentosRunt = 3;
$captchaPoolSize = 5;

if (!ctype_digit($userId)) {
    echo json_encode(["error" => "El ID de usuario debe ser un número válido"], JSON_UNESCAPED_UNICODE);
    exit;
}

if (!preg_match('/^[A-Za-z0-9]{3,7}$/', $placa)) {
    echo json_encode(["error" => "Formato de placa inválido"], JSON_UNESCAPED_UNICODE);
    exit;
}

$db = new Database();
$conn = $db->getConnection();
$user = new User($conn);

$userData = $user->getUserById($userId);

if (!$userData) {
    echo json_encode(["error" => "Usuario no encontrado"], JSON_UNESCAPED_UNICODE);
    exit;
}

$creditosDisponibles = $userData['creditos_disponibles'];
$tipoCuenta = $userData['tipo_cuenta'];

if ($creditosDisponibles <= 0) {
    echo json_encode(["status" => "error", "message" => "Créditos insuficientes"], JSON_UNESCAPED_UNICODE);
    exit;
}

function registrarActividad($conn, $userId, $accion, $estado = "Exitoso") {
    $fecha = date('Y-m-d H:i:s');
    $query = "INSERT INTO historial_actividades (usuario_id, actividad, fecha_hora, estado) 
              VALUES (:usuario_id, :actividad, :fecha_hora, :estado)";
    try {
        $stmt = $conn->prepare($query);
        $stmt->bindParam(':usuario_id', $userId, PDO::PARAM_INT);
        $stmt->bindParam(':actividad', $accion, PDO::PARAM_STR);
        $stmt->bindParam(':fecha_hora', $fecha, PDO::PARAM_STR);
        $stmt->bindParam(':estado', $estado, PDO::PARAM_STR);
        $result = $stmt->execute();
        if (!$result) {
            error_log("Error al registrar actividad: " . implode(" ", $stmt->errorInfo()));
        }
        return $result;
    } catch (PDOException $e) {
        error_log("Excepción al registrar actividad: " . $e->getMessage());
        return false;
    }
}

function actualizarCreditos($conn, $userId, $nuevoValor) {
    $query = "UPDATE usuarios SET creditos_disponibles = :creditos WHERE id = :id";
    $stmt = $conn->prepare($query);
    $stmt->bindParam(':creditos', $nuevoValor, PDO::PARAM_INT);
    $stmt->bindParam(':id', $userId, PDO::PARAM_INT);
    return $stmt->execute();
}

function actualizarContadoresConsulta($conn, $userId) {
    $query = "UPDATE usuarios SET 
              total_consultas = total_consultas + 1, 
              consultas_mensuales = consultas_mensuales + 1
              WHERE id = :id";
    $stmt = $conn->prepare($query);
    $stmt->bindParam(':id', $userId, PDO::PARAM_INT);
    return $stmt->execute();
}

function obtenerDatosVehiculo($placa) {
    $baseUrl = "https://impuestovehicular.meta.gov.co/api-rest-meta/index.php/liquidarVehiculo/";
    $url = $baseUrl . $placa . "/1";
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    $response = curl_exec($ch);
    
    if (curl_errno($ch)) {
        error_log("Error CURL al consultar vehículo: " . curl_error($ch));
        curl_close($ch);
        return [
            'error' => true,
            'mensaje' => "Error al conectar con el servicio de consulta de vehículos"
        ];
    }
    
    curl_close($ch);
    $datos = json_decode($response, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        error_log("Error decodificando JSON de vehículo: " . json_last_error_msg());
        return [
            'error' => true,
            'mensaje' => "Error al procesar la respuesta del servicio"
        ];
    }
    
    if (isset($datos['status']) && $datos['status'] != 'SUCCESS') {
        return [
            'error' => true,
            'mensaje' => "El servicio respondió con un error: " . ($datos['codeStatus'] ?? 'Desconocido')
        ];
    }
    
    if (!isset($datos['vehiculo'])) {
        return [
            'error' => true,
            'mensaje' => "No se encontraron datos para este vehículo"
        ];
    }
    
    $vehiculo = $datos['vehiculo'];
    
    $datosVehiculo = [
        'Clase' => $vehiculo['clas'] ?? 'No disponible',
        'Modelo' => $vehiculo['mode'] ?? 'No disponible',
        'Importado' => $vehiculo['impo'] ?? 'No disponible',
        'Decomisado' => $vehiculo['deco'] ?? 'No disponible',
        'Marca' => $vehiculo['marc'] ?? 'No disponible',
        'Carrocería' => $vehiculo['carr'] ?? 'No disponible',
        'Blindado' => $vehiculo['blin'] ?? 'No disponible',
        'Chatarrizado' => $vehiculo['chat'] ?? 'No disponible',
        'Línea' => $vehiculo['line'] ?? 'No disponible',
        'Cilindraje' => $vehiculo['cili'] ?? 'No disponible',
        'Caja automática' => $vehiculo['caja'] ?? 'No disponible',
        'Estado' => $vehiculo['esta'] ?? 'No disponible',
        'Tonelaje' => $vehiculo['tone'] ?? 'No disponible',
        'Cartas abiertas' => $vehiculo['cart'] ?? 'No disponible',
        'Ext. de Dominio' => $vehiculo['extd'] ?? 'No disponible',
        'Tipo de servicio' => $vehiculo['serv'] ?? 'No disponible',
        'Pasajeros' => $vehiculo['pasa'] ?? 'No disponible',
        'Robado' => $vehiculo['roba'] ?? 'No disponible',
        'Antíguo' => $vehiculo['anti'] ?? 'No disponible',
        'Placa' => $vehiculo['plac'] ?? 'No disponible'
    ];
    
    $propietarios = [];
    
    if (isset($datos['pagos']) && is_array($datos['pagos'])) {
        foreach ($datos['pagos'] as $pago) {
            if (isset($pago['docu']) && !empty($pago['docu'])) {
                $propietario = [
                    'Documento' => $pago['docu'] ?? 'No disponible',
                    'Nombre' => $pago['nomb'] ?? 'No disponible',
                    'Apellido' => $pago['apel'] ?? 'No disponible',
                    'Teléfono' => $pago['tele'] ?? 'No disponible',
                    'Dirección' => $pago['dire'] ?? 'No disponible',
                    'Email' => $pago['emai'] ?? 'No disponible',
                    'Municipio' => $pago['muni'] ?? 'No disponible',
                    'ID Municipio' => $pago['idmu'] ?? 'No disponible'
                ];
                $propietarios[] = $propietario;
            }
        }
    }
    
    if (isset($datos['recaudosElectronicos']) && is_array($datos['recaudosElectronicos'])) {
        foreach ($datos['recaudosElectronicos'] as $recaudo) {
            if (
                isset($recaudo['docu']) && !empty($recaudo['docu']) &&
                $recaudo['esta'] === 'APROBADA'
            ) {
                $encontrado = false;
                foreach ($propietarios as $prop) {
                    if (isset($prop['Documento']) && $prop['Documento'] === $recaudo['docu']) {
                        $encontrado = true;
                        break;
                    }
                }
                
                if (!$encontrado) {
                    $propietario = [
                        'Documento' => $recaudo['docu'],
                        'Estado' => $recaudo['esta'] ?? 'No disponible',
                        'Banco' => $recaudo['banc'] ?? 'No disponible'
                    ];
                    $propietarios[] = $propietario;
                }
            }
        }
    }
    
    return [
        'error' => false,
        'vehiculo' => $datosVehiculo,
        'propietarios' => $propietarios
    ];
}

function obtenerMultiplesCaptchas($cantidad) {
    $captchas = [];
    for ($i = 0; $i < $cantidad; $i++) {
        $captchas[] = obtenerCaptchaYToken();
    }
    
    $captchasValidos = array_filter($captchas, function($captcha) {
        return !empty($captcha['text']) && strlen($captcha['text']) >= 4;
    });
    
    error_log("Obtenidos " . count($captchasValidos) . " CAPTCHAs válidos de $cantidad intentos");
    
    return $captchasValidos;
}

function obtenerCaptchaYToken() {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, "https://www.runt.gov.co/consultaCiudadana/captcha?id=" . rand(1, 1000));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36');
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    
    $response = curl_exec($ch);
    
    if (curl_errno($ch)) {
        error_log("Error al obtener CAPTCHA: " . curl_error($ch));
        curl_close($ch);
        return [
            'text' => '',
            'cookies' => [],
            'xsrfToken' => ''
        ];
    }
    
    $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $headers = substr($response, 0, $headerSize);
    $imageData = substr($response, $headerSize);
    
    curl_close($ch);
    
    if (empty($imageData)) {
        error_log("No se recibieron datos de imagen de CAPTCHA");
        return [
            'text' => '',
            'cookies' => [],
            'xsrfToken' => ''
        ];
    }
    
    $cookies = [];
    preg_match_all('/^Set-Cookie:\s*([^;]*)/mi', $headers, $matches);
    foreach ($matches[1] as $cookie) {
        $parts = explode('=', $cookie, 2);
        if (count($parts) == 2) {
            $cookies[$parts[0]] = $parts[1];
        }
    }
    
    $xsrfToken = '';
    if (preg_match('/XSRF-TOKEN=([^;]+)/', $headers, $match)) {
        $xsrfToken = urldecode($match[1]);
    }
    
    $imagePath = 'captcha_' . uniqid() . '.jpg';
    file_put_contents($imagePath, $imageData);
    
    $apiKey = 'K82240321788957';
    $imageBase64 = base64_encode($imageData);
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, 'https://api.ocr.space/parse/image');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['apikey: ' . $apiKey]);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    curl_setopt($ch, CURLOPT_POSTFIELDS, [
        'language' => 'eng',
        'base64Image' => 'data:image/jpeg;base64,' . $imageBase64,
        'OCREngine' => '2'
    ]);
    
    $response = curl_exec($ch);
    
    if (curl_errno($ch)) {
        error_log("Error en OCR API: " . curl_error($ch));
        curl_close($ch);
        unlink($imagePath);
        return [
            'text' => '',
            'cookies' => $cookies,
            'xsrfToken' => $xsrfToken
        ];
    }
    
    curl_close($ch);
    unlink($imagePath);
    
    $result = json_decode($response, true);
    $captchaText = '';
    
    if (isset($result['ParsedResults'][0]['ParsedText'])) {
        $captchaText = preg_replace('/[^a-zA-Z0-9]/', '', $result['ParsedResults'][0]['ParsedText']);
        error_log("CAPTCHA reconocido: $captchaText");
    } else {
        error_log("No se pudo reconocer el CAPTCHA");
    }
    
    return [
        'text' => $captchaText,
        'cookies' => $cookies,
        'xsrfToken' => $xsrfToken
    ];
}

function consultarVehiculo($captchaInfo, $placa, $documento, $tipo, $endpoint) {
    $authToken = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJSVU5UX0NPTlNVTFRBX0NJVUQiLCJwYXNzd29yZCI6bnVsbCwiaXAiOiJ3d3cucnVudC5nb3YuY28iLCJpc3MiOiJ7XCJ0aXBvQ29uc3VsdGFcIjpcIjFcIixcInRpcG9Eb2N1bWVudG9cIjpcIkNcIixcIm5vRG9jdW1lbnRvXCI6XCIxMTkzMDMyMzQ1XCIsXCJjYXB0Y2hhXCI6XCJwYXdhclwiLFwibm9QbGFjYVwiOlwiSkNONzBGXCIsXCJwcm9jZWRlbmNpYVwiOlwiTkFDSU9OQUxcIn0iLCJleHAiOjE3NDQ3MzA0NzAsImlhdCI6MTc0NDcyOTg3MCwianRpIjoiMjJhOWE0ZTItYmEzNi00MDM4LWJhOTMtOThiYWU0NTEzYWI4IiwidXNlcm5hbWUiOm51bGx9.68ui0Exd-pYvAFh9IhRhmD791F2osa_ASnJYnjSl512W-koSPijvD1mrsSkK2CuxwPx4lXaCbSmDkp25j2UZyA";
    
    if (empty($captchaInfo['text'])) {
        return ['body' => '{"error":true,"mensajeError":"CAPTCHA no disponible"}'];
    }
    
    $payload = [
        "tipoDocumento" => $tipo,
        "procedencia" => "NACIONAL",
        "tipoConsulta" => "1",
        "vin" => null,
        "noDocumento" => $documento,
        "noPlaca" => $placa,
        "soat" => null,
        "codigoSoat" => null,
        "rtm" => null,
        "captcha" => $captchaInfo['text']
    ];
    
    $acceptData = base64_encode(json_encode($payload));
    
    $cookieStr = '';
    foreach ($captchaInfo['cookies'] as $name => $value) {
        $cookieStr .= "$name=$value; ";
    }
    $cookieStr = rtrim($cookieStr, '; ');
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $endpoint);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
    
    $headers = [
        'Accept: application/json, text/plain, */*',
        'Accept-Data: ' . $acceptData,
        'Accept-Encoding: gzip, deflate, br, zstd',
        'Accept-Language: es-ES,es;q=0.9',
        'Authorization: Bearer ' . $authToken,
        'Content-Type: application/json;charset=UTF-8',
        'Origin: https://www.runt.gov.co',
        'Referer: https://www.runt.gov.co/consultaCiudadana/',
        'X-XSRF-TOKEN: ' . urlencode($captchaInfo['xsrfToken']),
        'sec-ch-ua: "Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile: ?0',
        'sec-ch-ua-platform: "Windows"',
        'Cookie: ' . $cookieStr
    ];
    
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    
    $response = curl_exec($ch);
    
    if (curl_errno($ch)) {
        error_log("Error al consultar vehículo: " . curl_error($ch));
        curl_close($ch);
        return ['body' => '{"error":true,"mensajeError":"Error de conexión: ' . curl_error($ch) . '"}'];
    }
    
    curl_close($ch);
    
    if (empty($response)) {
        error_log("Respuesta vacía al consultar vehículo");
        return ['body' => '{"error":true,"mensajeError":"Respuesta vacía del servidor"}'];
    }
    
    return ['body' => $response];
}

function consultarEndpoint($captchaInfo, $token, $placa, $documento, $endpoint) {
    if (empty($token)) {
        error_log("Token vacío al consultar endpoint");
        return ['body' => '{"error":true,"mensajeError":"Token no disponible"}'];
    }
    
    $dataPayload = [
        "tipoDocumento" => "C",
        "procedencia" => "NACIONAL",
        "tipoConsulta" => "1",
        "vin" => null,
        "noDocumento" => $documento,
        "noPlaca" => $placa,
        "soat" => null,
        "codigoSoat" => null,
        "rtm" => null,
        "captcha" => $captchaInfo['text']
    ];
    
    $acceptData = base64_encode(json_encode($dataPayload));
    
    $cookieStr = '';
    foreach ($captchaInfo['cookies'] as $name => $value) {
        $cookieStr .= "$name=$value; ";
    }
    $cookieStr = rtrim($cookieStr, '; ');
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $endpoint);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    
    $headers = [
        'Accept: application/json, text/plain, */*',
        'Accept-Data: ' . $acceptData,
        'Accept-Encoding: gzip, deflate, br, zstd',
        'Accept-Language: es-ES,es;q=0.9',
        'Authorization: Bearer ' . $token,
        'Referer: https://www.runt.gov.co/consultaCiudadana/',
        'X-XSRF-TOKEN: ' . urlencode($captchaInfo['xsrfToken']),
        'sec-ch-ua: "Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile: ?0',
        'sec-ch-ua-platform: "Windows"',
        'Cookie: ' . $cookieStr
    ];
    
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    
    $response = curl_exec($ch);
    
    if (curl_errno($ch)) {
        error_log("Error al consultar endpoint: " . curl_error($ch));
        curl_close($ch);
        return ['body' => '{"error":true,"mensajeError":"Error de conexión: ' . curl_error($ch) . '"}'];
    }
    
    curl_close($ch);
    
    if (empty($response)) {
        error_log("Respuesta vacía del endpoint");
        return ['body' => '{"error":true,"mensajeError":"Respuesta vacía del servidor"}'];
    }
    
    return ['body' => $response];
}

function obtenerDatosCompletos($placa, $documento, $tipo, $endpointVehiculo, $endpointSoat, $endpointRtm, $maxIntentos, $maxIntentosRunt, $captchaPoolSize) {
    error_log("Iniciando consulta RUNT placa: $placa documento: $documento");
    
    for ($intentoRunt = 1; $intentoRunt <= $maxIntentosRunt; $intentoRunt++) {
        error_log("Intento RUNT #$intentoRunt de $maxIntentosRunt");
        
        $captchaPool = obtenerMultiplesCaptchas($captchaPoolSize);
        
        if (empty($captchaPool)) {
            error_log("No se pudo obtener ningún CAPTCHA válido, reintentando...");
            continue;
        }
        
        foreach ($captchaPool as $captchaInfo) {
            error_log("Probando CAPTCHA: " . $captchaInfo['text']);
            
            $resultadoVehiculo = consultarVehiculo($captchaInfo, $placa, $documento, $tipo, $endpointVehiculo);
            
            if (strpos($resultadoVehiculo['body'], 'La imagen no coincide con el valor ingresado') !== false) {
                error_log("CAPTCHA incorrecto: " . $captchaInfo['text'] . ", probando siguiente");
                continue;
            }
            
            $jsonVehiculo = preg_replace('/^\)\]\}\'/', '', $resultadoVehiculo['body']);
            $datosVehiculo = json_decode($jsonVehiculo, true);
            
            if (isset($datosVehiculo['mensajeError']) && $datosVehiculo['mensajeError'] === "Parametros invalidos.") {
                error_log("Error: Parámetros inválidos detectado, probando siguiente CAPTCHA");
                continue;
            }
            
            if (!isset($datosVehiculo['token']) || empty($datosVehiculo['token'])) {
                error_log("Token no encontrado o vacío, probando siguiente CAPTCHA");
                continue;
            }
            
            $tokenRunt = $datosVehiculo['token'];
            
            if (isset($datosVehiculo['error']) && $datosVehiculo['error'] === true) {
                error_log("Error en datos de vehículo: " . ($datosVehiculo['mensajeError'] ?? 'Sin mensaje'));
                continue;
            }
            
            $resultadoSoat = consultarEndpoint($captchaInfo, $tokenRunt, $placa, $documento, $endpointSoat);
            $jsonSoat = preg_replace('/^\)\]\}\'/', '', $resultadoSoat['body']);
            $datosSoat = json_decode($jsonSoat, true);
            
            $resultadoRtm = consultarEndpoint($captchaInfo, $tokenRunt, $placa, $documento, $endpointRtm);
            $jsonRtm = preg_replace('/^\)\]\}\'/', '', $resultadoRtm['body']);
            $datosRtm = json_decode($jsonRtm, true);
            
            if (
                (isset($datosSoat['mensajeError']) && $datosSoat['mensajeError'] === "Parametros invalidos.") || 
                (isset($datosRtm['mensajeError']) && $datosRtm['mensajeError'] === "Parametros invalidos.")
            ) {
                error_log("Error de parámetros inválidos en SOAT o RTM, probando siguiente CAPTCHA");
                continue;
            }
            
            error_log("Consulta RUNT exitosa con CAPTCHA: " . $captchaInfo['text']);
            return [
                'vehiculo' => $datosVehiculo,
                'soat' => $datosSoat,
                'rtm' => $datosRtm,
                'placa' => $placa,
                'documento' => $documento,
                'tipo_documento' => $tipo
            ];
        }
        
        error_log("Ningún CAPTCHA del pool funcionó, reintentando con nuevos CAPTCHAs");
    }
    
    error_log("Se agotaron los intentos para obtener información válida del RUNT");
    return [
        'error' => 'Se agotaron los intentos para obtener información válida del RUNT.'
    ];
}

$transactionId = uniqid();
$tiempoInicio = microtime(true);
error_log("[$transactionId] Inicio consulta de vehículo - Placa: $placa - Usuario: $userId");

registrarActividad($conn, $userId, "Intento de consulta vehículo Placa: $placa");

$intentosImpuesto = 0;
$maxIntentosImpuesto = 3;
$resultadoImpuestos = ['error' => true, 'mensaje' => 'No iniciado'];

while ($intentosImpuesto < $maxIntentosImpuesto) {
    $intentosImpuesto++;
    error_log("[$transactionId] Intento #$intentosImpuesto para obtener datos de impuesto");
    
    $resultadoImpuestos = obtenerDatosVehiculo($placa);
    
    if ($resultadoImpuestos['error'] === false && 
        isset($resultadoImpuestos['vehiculo']) &&
        (!empty($resultadoImpuestos['vehiculo']) || !empty($resultadoImpuestos['propietarios']))) {
        break;
    }
    
    if (isset($resultadoImpuestos['mensaje']) && 
        strpos($resultadoImpuestos['mensaje'], "El servicio respondió con un error: 200") !== false) {
        error_log("[$transactionId] Error 200 detectado, reintentando...");
        sleep(1);
        continue;
    }
    
    break;
}

$consultaExitosa = ($resultadoImpuestos['error'] === false &&
    isset($resultadoImpuestos['vehiculo']) &&
    (!empty($resultadoImpuestos['vehiculo']) || !empty($resultadoImpuestos['propietarios'])));

error_log("[$transactionId] Resultado consulta impuestos: " . ($consultaExitosa ? 'Exitosa' : 'Fallida'));

// Sección que va dentro de la parte final donde se procesa la respuesta (parte 6):

if ($consultaExitosa) {
    $nuevosCreditos = $creditosDisponibles - 3;
    $creditoActualizado = actualizarCreditos($conn, $userId, $nuevosCreditos);
    $contadorActualizado = actualizarContadoresConsulta($conn, $userId);
    
    registrarActividad($conn, $userId, "Consulta exitosa vehículo Placa: $placa - Crédito consumido");
    error_log("[$transactionId] Consulta exitosa - Crédito actualizado: " . ($creditoActualizado ? 'Sí' : 'No') .
        " - Contador actualizado: " . ($contadorActualizado ? 'Sí' : 'No'));
    
    $documento = "";
    if (!empty($resultadoImpuestos['propietarios'])) {
        $ultimoPropietario = end($resultadoImpuestos['propietarios']);
        if (isset($ultimoPropietario['Documento'])) {
            $documento = $ultimoPropietario['Documento'];
        }
    }
    
    $resultadoRunt = [];
    $maxIntentosGlobalesRunt = 5;
    $intentosGlobalesRunt = 0;
    $runtExitoso = false;
    
    if (!empty($documento)) {
        error_log("[$transactionId] Consultando RUNT con documento: $documento");
        
        while ($intentosGlobalesRunt < $maxIntentosGlobalesRunt) {
            $intentosGlobalesRunt++;
            error_log("[$transactionId] Intento global RUNT #$intentosGlobalesRunt de $maxIntentosGlobalesRunt");
            
            $resultadoRunt = obtenerDatosCompletos($placa, $documento, $tipo, $endpointVehiculo, $endpointSoat, $endpointRtm, $maxIntentos, $maxIntentosRunt, $captchaPoolSize);
            
            if (isset($resultadoRunt['vehiculo']['mensajeError']) && 
                $resultadoRunt['vehiculo']['mensajeError'] === "Parametros invalidos.") {
                error_log("[$transactionId] Error 'Parametros invalidos' detectado, reintentando consulta completa");
                sleep(1);
                continue;
            }
            
            if (isset($resultadoRunt['vehiculo']) && 
                isset($resultadoRunt['vehiculo']['token']) && 
                !empty($resultadoRunt['vehiculo']['token'])) {
                error_log("[$transactionId] Token RUNT válido obtenido");
            }
            
            if (isset($resultadoRunt['error'])) {
                error_log("[$transactionId] Error general en RUNT: " . $resultadoRunt['error']);
                sleep(1);
                continue;
            }
            
            $runtExitoso = true;
            break;
        }
        
        error_log("[$transactionId] Consulta RUNT " . ($runtExitoso ? "exitosa" : "fallida") . " después de $intentosGlobalesRunt intentos");
    } else {
        error_log("[$transactionId] No se encontró documento para consultar RUNT");
    }
    
   // Sección para censurar absolutamente todos los datos para usuarios Free

if ($tipoCuenta === 'Free') {
    // 1. Censurar información de vehículo en impuestos
    if (isset($resultadoImpuestos['vehiculo'])) {
        // Ocultar información detallada del vehículo
        if (isset($resultadoImpuestos['vehiculo']['Línea'])) {
            $resultadoImpuestos['vehiculo']['Línea'] = substr($resultadoImpuestos['vehiculo']['Línea'], 0, 3) . ' *****';
        }
        if (isset($resultadoImpuestos['vehiculo']['Cilindraje'])) {
            $resultadoImpuestos['vehiculo']['Cilindraje'] = '****';
        }
        if (isset($resultadoImpuestos['vehiculo']['Modelo'])) {
            $resultadoImpuestos['vehiculo']['Modelo'] = '****';
        }
        if (isset($resultadoImpuestos['vehiculo']['Tonelaje'])) {
            $resultadoImpuestos['vehiculo']['Tonelaje'] = '*';
        }
    }
    
    // 2. Censurar información de propietarios
    if (!empty($resultadoImpuestos['propietarios'])) {
        foreach ($resultadoImpuestos['propietarios'] as &$propietario) {
            // Conservar solo primeros y últimos dos dígitos del documento
            if (isset($propietario['Documento']) && strlen($propietario['Documento']) > 4) {
                $propietario['Documento'] = substr($propietario['Documento'], 0, 2) . str_repeat('*', strlen($propietario['Documento']) - 4) . substr($propietario['Documento'], -2);
            }
            
            // Nombres y apellidos - mostrar solo primera letra
            if (isset($propietario['Nombre']) && $propietario['Nombre'] !== 'No disponible') {
                $propietario['Nombre'] = substr($propietario['Nombre'], 0, 1) . str_repeat('*', strlen($propietario['Nombre']) - 1);
            }
            if (isset($propietario['Apellido']) && $propietario['Apellido'] !== 'No disponible') {
                $propietario['Apellido'] = substr($propietario['Apellido'], 0, 1) . str_repeat('*', strlen($propietario['Apellido']) - 1);
            }
            
            // Ocultar teléfonos y direcciones
            if (isset($propietario['Teléfono']) && $propietario['Teléfono'] !== 'No disponible' && strlen($propietario['Teléfono']) > 4) {
                $propietario['Teléfono'] = substr($propietario['Teléfono'], 0, 2) . str_repeat('*', strlen($propietario['Teléfono']) - 4) . substr($propietario['Teléfono'], -2);
            }
            
            if (isset($propietario['Dirección']) && $propietario['Dirección'] !== 'No disponible') {
                $palabras = explode(' ', $propietario['Dirección']);
                if (count($palabras) > 1) {
                    $propietario['Dirección'] = $palabras[0] . ' *****';
                } else {
                    $propietario['Dirección'] = substr($propietario['Dirección'], 0, 2) . '****';
                }
            }
            
            // Ocultar correo electrónico
            if (isset($propietario['Email']) && $propietario['Email'] !== 'No disponible' && strpos($propietario['Email'], '@') !== false) {
                $partes = explode('@', $propietario['Email']);
                $propietario['Email'] = substr($partes[0], 0, 1) . '****@' . $partes[1];
            }
        }
    }
    
    // 3. Censurar información RUNT del vehículo
    if (isset($resultadoRunt['vehiculo']) && isset($resultadoRunt['vehiculo']['informacionGeneralVehiculo'])) {
        $infoVehiculo = &$resultadoRunt['vehiculo']['informacionGeneralVehiculo'];
        
        // Ocultar números de serie, motor, chasis
        if (isset($infoVehiculo['noSerie'])) {
            $infoVehiculo['noSerie'] = substr($infoVehiculo['noSerie'], 0, 3) . '*****';
        }
        if (isset($infoVehiculo['noMotor'])) {
            $infoVehiculo['noMotor'] = substr($infoVehiculo['noMotor'], 0, 2) . '*****';
        }
        if (isset($infoVehiculo['noChasis'])) {
            $infoVehiculo['noChasis'] = substr($infoVehiculo['noChasis'], 0, 3) . '*****';
        }
        
        // Ocultar licencia de tránsito
        if (isset($infoVehiculo['noLicenciaTransito'])) {
            $infoVehiculo['noLicenciaTransito'] = '*************';
        }
        
        // Ocultar fechas
        if (isset($infoVehiculo['fechaMatricula'])) {
            $infoVehiculo['fechaMatricula'] = '**/**/****';
        }
        
        // Ocultar color
        if (isset($infoVehiculo['color'])) {
            $infoVehiculo['color'] = '*****';
        }
        
        // Ocultar información del organismo de tránsito
        if (isset($infoVehiculo['organismoTransito'])) {
            $palabras = explode('/', $infoVehiculo['organismoTransito']);
            if (count($palabras) > 1) {
                $infoVehiculo['organismoTransito'] = $palabras[0] . '/****';
            } else {
                $infoVehiculo['organismoTransito'] = substr($infoVehiculo['organismoTransito'], 0, 5) . '*****';
            }
        }
        
        // Ocultar modelo
        if (isset($infoVehiculo['modelo'])) {
            $infoVehiculo['modelo'] = '****';
        }
        
        // Ocultar cilindraje
        if (isset($infoVehiculo['cilidraje'])) {
            $infoVehiculo['cilidraje'] = '****';
        }
    }
    
    // 4. Censurar SOAT
    if (isset($resultadoRunt['soat']) && isset($resultadoRunt['soat']['data'])) {
        foreach ($resultadoRunt['soat']['data'] as &$soatItem) {
            // Mensaje sin emoji
            $soatItem['estado'] = 'Requiere membresía Premium para ver esta información';
            $soatItem['fechaVencimiento'] = '**/**/****';
            $soatItem['fechaVigencia'] = '**/**/****';
            $soatItem['fechaExpedicion'] = '**/**/****';
            $soatItem['noPoliza'] = '*******';
        }
    }
    
    // 5. Censurar RTM
    if (isset($resultadoRunt['rtm']) && isset($resultadoRunt['rtm']['data'])) {
        foreach ($resultadoRunt['rtm']['data'] as &$rtmItem) {
            // Mensaje sin emoji
            $rtmItem['vigente'] = 'Requiere membresía Premium';
            $rtmItem['fechaVigente'] = '**/**/****';
            $rtmItem['fechaExpedicion'] = '**/**/****';
            $rtmItem['nroCertificado'] = '*******';
            if (isset($rtmItem['url'])) {
                $rtmItem['url'] = 'Requiere membresía Premium';
            }
        }
    }
}
    
    $resultadoCombinado = [
        "status" => "success",
        "impuestos" => [
            "vehiculo" => $resultadoImpuestos['vehiculo'],
            "propietarios" => $resultadoImpuestos['propietarios']
        ],
        "runt" => $resultadoRunt,
        "creditosDisponibles" => $nuevosCreditos,
        "transactionId" => $transactionId,
        "documentoConsultaRunt" => $documento,
        "placa" => $placa,
        "tiempoConsulta" => round(microtime(true) - $tiempoInicio, 2) . " segundos"
    ];
    
    if ($tipoCuenta === 'Free') {
        $resultadoCombinado['mensaje_premium'] = "Datos limitados. Actualiza a Premium para ver información completa.";
        $resultadoCombinado['plan'] = "Free";
    }
    
    echo json_encode($resultadoCombinado, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
} else {
    $mensaje = $resultadoImpuestos['mensaje'] ?? "No se encontraron datos para esta placa";
    $registroFallido = registrarActividad($conn, $userId, "Consulta sin resultados para Placa: $placa - $mensaje", "Fallido");
    error_log("[$transactionId] Consulta fallida - Mensaje: $mensaje - Registro: " . ($registroFallido ? 'OK' : 'FALLÓ'));
    
    echo json_encode([
        "status" => "warning",
        "message" => $mensaje,
        "creditosDisponibles" => $creditosDisponibles,
        "transactionId" => $transactionId,
        "tiempoConsulta" => round(microtime(true) - $tiempoInicio, 2) . " segundos"
    ], JSON_UNESCAPED_UNICODE);
}   