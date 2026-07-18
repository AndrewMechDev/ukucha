/*
 * FIRMWARE MULTITAREA PARA ESP32-S3 DE CAMPO (SISTEMA INTEGRADO REPETIDOR)
 * Ecosistema del Ratón Biónico S3 - Nivel Industrial
 * 
 * Implementa multitarea con FreeRTOS en ESP32-S3 distribuyendo la lógica en dos hilos:
 * - CORE 0 (Misión Crítica de Audio): Lectura DMA I2S en estéreo (BCLK=1, WS=2, DIN=41), 
 *   cálculo de la envolvente de volumen de canales L/R y dibujo de un vúmetro en tira NeoPixel (GPIO 14).
 * - CORE 1 (Diagnóstico, Sensores y Enlace): Lectura de sensores I2C (BMP280 + AHT20 en SDA=8, SCL=9),
 *   GPS por UART (Serial1 RX=18, TX=17 a 9600), transmisión de telemetría por UDP (puerto 5002) a 10Hz,
 *   y escucha de comandos del servidor en puerto 4210.
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_AHTX0.h>
#include <TinyGPS++.h>
#include <Adafruit_NeoPixel.h>
#include "driver/i2s.h"

// --- CONFIGURACIÓN DE RED LOCAL ---
const char* ssid     = "Bruno";
const char* password = "12345678";
const char* hostIp   = "192.168.206.221"; // IP del servidor central Node.js
const uint16_t telemetryPort = 5002;
const uint16_t controlPort   = 4210;

WiFiUDP udpTelemetry;
WiFiUDP udpControl;

// --- HARDWARE / SENSORES ---
#define I2C_SDA_PIN 8
#define I2C_SCL_PIN 9
Adafruit_BMP280 bmp;
Adafruit_AHTX0 aht;

TinyGPSPlus gps;

#define NEOPIXEL_PIN 14
#define NUM_LEDS 8
Adafruit_NeoPixel pixels(NUM_LEDS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

// Variables globales para sincronización de envolvente de volumen
volatile float volLeft = 0.0;
volatile float volRight = 0.0;

// Estructuras de control
int lucesVal = 0;
int motorAVal = 0;
int motorBVal = 0;

// Prototipos de Tareas FreeRTOS
void TaskAudio(void *pvParameters);
void TaskTelemetry(void *pvParameters);

void setup() {
    Serial.begin(115200);
    Serial.println("\n--- INICIALIZANDO ESP32-S3 CENTRAL DE CAMPO ---");

    // 1. Conectar a la Red Wi-Fi
    WiFi.begin(ssid, password);
    Serial.printf("[WIFI] Conectando a SSID: %s ", ssid);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n[WIFI] Conexión Wi-Fi establecida.");
    Serial.printf("[WIFI] IP asignada: %s\n", WiFi.localIP().toString().c_str());

    // Inicializar UDP de Control
    udpControl.begin(controlPort);
    Serial.printf("[UDP] Escuchando comandos en puerto local %d\n", controlPort);

    // 2. Inicializar Tira NeoPixel
    pixels.begin();
    pixels.setBrightness(30);
    pixels.show(); // Apagar todos los LEDs inicialmente

    // 3. Inicializar Bus I2C y Sensores
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
    
    if (!bmp.begin(0x76)) {
        Serial.println("[I2C] Advertencia: No se detectó el sensor BMP280.");
    } else {
        Serial.println("[I2C] Sensor BMP280 acoplado con éxito.");
    }
    
    if (!aht.begin()) {
        Serial.println("[I2C] Advertencia: No se detectó el sensor AHT20.");
    } else {
        Serial.println("[I2C] Sensor AHT20 acoplado con éxito.");
    }

    // 4. Inicializar GPS por UART1
    Serial1.begin(9600, SERIAL_8N1, 18, 17); // RX=18, TX=17
    Serial.println("[UART] Puerto Serial1 para GPS inicializado a 9600 baudios.");

    // 5. Creación de Tareas FreeRTOS en Cores Independientes
    xTaskCreatePinnedToCore(
        TaskAudio,         // Función de la tarea
        "TaskAudio",       // Nombre identificativo
        4096,              // Tamaño de pila (stack size en palabras)
        NULL,              // Parámetros de entrada
        3,                 // Prioridad de la tarea (Misión Crítica)
        NULL,              // Handle de la tarea
        0                  // CORE 0
    );

    xTaskCreatePinnedToCore(
        TaskTelemetry,
        "TaskTelemetry",
        8192,
        NULL,
        2,
        NULL,
        1                  // CORE 1
    );

    Serial.println("[SISTEMA] Multitarea FreeRTOS inicializado y corriendo en Cores 0 y 1.");
}

void loop() {
    // El bucle principal de Arduino queda libre de operaciones pesadas.
    // FreeRTOS gestiona las tareas en paralelo.
    vTaskDelay(pdMS_TO_TICKS(1000));
}

// ==========================================
// --- CORE 0: TAREA DE AUDIO Y VÚMETRO ---
// ==========================================
void TaskAudio(void *pvParameters) {
    (void) pvParameters;

    // Configuración del driver DMA I2S (Mapeo de hardware)
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT, // Ancho de ranura de 32 bits
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT, // Estéreo estándar
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 64,
        .use_apll = false
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num = 1,  // Pin BCLK
        .ws_io_num = 2,   // Pin WS (LRCK)
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = 41 // Pin DIN
    };

    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pin_config);
    Serial.println("[I2S] Driver I2S DMA inicializado en Core 0.");

    const int bufferSize = 128;
    int32_t i2sBuffer[bufferSize]; // Buffer de lectura de 32-bits
    size_t bytesRead = 0;

    while (true) {
        // Lectura de datos desde el bus I2S
        esp_err_t err = i2s_read(I2S_NUM_0, i2sBuffer, sizeof(i2sBuffer), &bytesRead, portMAX_DELAY);
        if (err == ESP_OK && bytesRead > 0) {
            long sumL = 0, sumR = 0;
            int count = bytesRead / 4; // Cada muestra son 4 bytes (32-bit)

            // Procesar muestras estéreo entrelazadas (L, R, L, R...)
            for (int i = 0; i < count; i += 2) {
                sumL += abs(i2sBuffer[i] >> 16);      // Escalar la muestra a 16 bits para evitar overflows
                sumR += abs(i2sBuffer[i + 1] >> 16);
            }

            float avgL = (float)sumL / (count / 2);
            float avgR = (float)sumR / (count / 2);

            // Convertir a escala de porcentaje relativo (0 a 100%)
            volLeft = constrain((avgL / 12000.0) * 100.0, 0.0, 100.0);
            volRight = constrain((avgR / 12000.0) * 100.0, 0.0, 100.0);

            // Representar volumen promedio en la tira local de 8 NeoPixels
            float avgVol = (volLeft + volRight) / 2.0;
            int ledsToLight = (int)((avgVol / 100.0) * NUM_LEDS);

            for (int i = 0; i < NUM_LEDS; i++) {
                if (i < ledsToLight) {
                    // Gradiente de color: Verde a Amarillo a Rojo
                    if (i < 5) pixels.setPixelColor(i, pixels.Color(0, 255, 0)); // Verde
                    else if (i < 7) pixels.setPixelColor(i, pixels.Color(255, 180, 0)); // Amarillo
                    else pixels.setPixelColor(i, pixels.Color(255, 0, 0)); // Rojo
                } else {
                    pixels.setPixelColor(i, pixels.Color(0, 0, 0)); // Apagar
                }
            }
            pixels.show();
        }
        
        // Pausa breve para liberar procesamiento
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

// ==========================================
// --- CORE 1: SENSORES, GPS, UDP Y CONTROL ---
// ==========================================
void TaskTelemetry(void *pvParameters) {
    (void) pvParameters;

    char telemetryBuffer[160];
    char udpPacket[64];

    while (true) {
        // 1. Lectura del flujo GPS desde el puerto serie UART1
        while (Serial1.available() > 0) {
            gps.encode(Serial1.read());
        }

        // 2. Extracción de datos del sensor climatológico I2C
        float tempVal = 0.0;
        float pressVal = 0.0;
        float humVal = 0.0;

        // Leer AHT20
        sensors_event_t humidityEvent, tempEvent;
        aht.getEvent(&humidityEvent, &tempEvent);
        tempVal = tempEvent.temperature;
        humVal = humidityEvent.relative_humidity;

        // Leer BMP280 para complementar presión de alta precisión
        pressVal = bmp.readPressure() / 100.0; // En hPa

        // Si falla lectura de AHT, BMP280 sirve como respaldo de temperatura
        if (isnan(tempVal) || tempVal == 0.0) {
            tempVal = bmp.readTemperature();
        }

        // 3. Extracción de coordenadas GPS
        double latVal = 0.0;
        double lonVal = 0.0;
        if (gps.location.isValid()) {
            latVal = gps.location.lat();
            lonVal = gps.location.lng();
        }

        // 4. Empaquetar y enviar telemetría a 10Hz (Puerto 5002)
        // Formato: A:L,R|M:0.0,0.0|P:0|G:lat,lon|C:t,p,h
        snprintf(telemetryBuffer, sizeof(telemetryBuffer), 
            "A:%.1f,%.1f|M:0.0,0.0|P:0|G:%.6f,%.6f|C:%.2f,%.2f,%.2f",
            volLeft, volRight, latVal, lonVal, tempVal, pressVal, humVal
        );

        udpTelemetry.beginPacket(hostIp, telemetryPort);
        udpTelemetry.write((const uint8_t*)telemetryBuffer, strlen(telemetryBuffer));
        udpTelemetry.endPacket();

        // 5. Escucha de comandos entrantes UDP en paralelo (Puerto 4210)
        int packetSize = udpControl.parsePacket();
        if (packetSize > 0) {
            int len = udpControl.read(udpPacket, sizeof(udpPacket) - 1);
            if (len > 0) {
                udpPacket[len] = '\0';
                String msgComando = String(udpPacket);

                if (msgComando.startsWith("C:")) {
                    // Parsea estructura C:luces,motorA,motorB\n
                    int scanCount = sscanf(msgComando.c_str(), "C:%d,%d,%d", &lucesVal, &motorAVal, &motorBVal);
                    if (scanCount == 3) {
                        Serial.printf("[EJECUCIÓN] Luces: %d | Motor A: %d | Motor B: %d\n", lucesVal, motorAVal, motorBVal);
                    }
                }
            }
        }

        // Frecuencia constante de 10Hz (100ms de período de refresco de telemetría)
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
