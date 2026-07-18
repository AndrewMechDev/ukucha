/*
 * FIRMWARE PARA ESP32-CAM (SERVIDOR DE STREAMING DE VIDEO EN TIEMPO REAL)
 * Ecosistema del Ratón Biónico S3 - Nivel Industrial
 * 
 * Este código configura la cámara AI-Thinker en formato RGB565 (sin compresión por hardware)
 * y resolución QQVGA (160x120) a 10MHz para evitar ruidos de acoplamiento.
 * Levanta un servidor HTTP local en el puerto 80 que comprime cada cuadro a JPEG al vuelo
 * y lo transmite por sockets web nativos mediante un stream multiparte multipart/x-mixed-replace.
 */

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

// --- CONFIGURACIÓN DE RED ---
const char* ssid     = "Bruno";
const char* password = "12345678";

// --- DEFINICIÓN DE PINES ESP32-CAM (MÓDULO AI-THINKER) ---
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t stream_httpd = NULL;

// --- CONTROLADOR DEL STREAMING MJPEG ---
static esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t * _jpg_buf = NULL;
    char * part_buf[64];

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) {
        return res;
    }

    // Permitir CORS para que la consola web del servidor principal no tenga bloqueos
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    Serial.println("[STREAM] Cliente conectado. Iniciando flujo de video...");

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("[STREAM] Error: No se pudo capturar el frame de la cámara.");
            res = ESP_FAIL;
            break;
        }

        // Compresión RGB565 -> JPEG al vuelo (por software debido a incompatibilidad de hardware en el chip)
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb); // Devolver el framebuffer de inmediato para liberar memoria
        fb = NULL;

        if (!jpeg_converted) {
            Serial.println("[STREAM] Error: Falló la conversión a JPEG.");
            res = ESP_FAIL;
            break;
        }

        // Transmisión del delimitador multiparte
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }

        // Transmisión de cabeceras de la imagen actual
        if (res == ESP_OK) {
            size_t hlen = snprintf((char *)part_buf, 64, _STREAM_PART, _jpg_buf_len);
            res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
        }

        // Transmisión de los bytes del buffer de JPEG
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
        }

        free(_jpg_buf); // Liberar memoria del buffer temporal de JPEG
        _jpg_buf = NULL;

        if (res != ESP_OK) {
            Serial.println("[STREAM] Error al enviar chunk. Enlace finalizado.");
            break;
        }
    }
    return res;
}

// --- CONFIGURACIÓN DEL SERVIDOR WEB ---
void startCameraServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;

    httpd_uri_t index_uri = {
        .uri       = "/",
        .method    = HTTP_GET,
        .handler   = stream_handler,
        .user_ctx  = NULL
    };

    Serial.printf("[WEB] Levantando servidor HTTP en puerto: %d\n", config.server_port);
    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &index_uri);
        Serial.println("[WEB] Servidor registrado en ruta '/'");
    } else {
        Serial.println("[WEB] Error crítico al arrancar el servidor HTTP.");
    }
}

void setup() {
    Serial.begin(115200);
    Serial.setDebugOutput(true);
    Serial.println("\n--- INICIALIZANDO ESP32-CAM ---");

    // 1. Conexión a la Red Wi-Fi (Diagnóstico serie al principio)
    WiFi.begin(ssid, password);
    Serial.printf("[WIFI] Conectando a SSID: %s ", ssid);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n[WIFI] ¡Conexión establecida con éxito!");
    Serial.printf("[WIFI] IP asignada de forma fija: %s\n", WiFi.localIP().toString().c_str());

    // 2. Configuración e inicialización del Sensor de Cámara
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    
    // Frecuencia XCLK a 10MHz (Mitiga ruidos electromagnéticos en pistas de PCB)
    config.xclk_freq_hz = 10000000;
    config.ledc_timer = LEDC_TIMER_0;
    config.ledc_channel = LEDC_CHANNEL_0;

    // Configuración para el chip sensor RGB565 sin JPEG de hardware (Error 0x106)
    config.pixel_format = PIXFORMAT_RGB565;
    config.frame_size = FRAMESIZE_QQVGA; // 160x120 píxeles
    config.jpeg_quality = 12;
    config.fb_count = 2; // Doble buffer para streaming fluido

    // Inicializar Cámara
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[CAM] Error crítico inicializando sensor óptico (0x%x)\n", err);
        return;
    }
    Serial.println("[CAM] Sensor óptico acoplado e inicializado.");

    // 3. Levantar Servidor HTTP
    startCameraServer();
}

void loop() {
    delay(1000); // El trabajo principal lo procesa el controlador de eventos de esp_http_server
}
