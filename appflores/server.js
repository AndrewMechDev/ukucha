const express = require('express');
const { WebSocketServer } = require('ws');
const dgram = require('dgram');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(express.static(path.join(__dirname, 'public')));

const archivoCSV = path.join(__dirname, 'registro_telemetria.csv');

// Inicializar cabecera del CSV si no existe
if (!fs.existsSync(archivoCSV)) {
    fs.writeFileSync(archivoCSV, 'Timestamp,Vol_L,Vol_R,MQ1,MQ2,PM25,Latitud,Longitud,Temp,Pres,Hum\n');
}

// Servidor Web para la interfaz HTML
app.listen(8080, () => {
    console.log('==================================================');
    console.log('🚀 SERVIDOR CENTRAL WI-FI / LAN ONLINE');
    console.log('🔗 Consola web lista en http://localhost:8080');
    console.log('==================================================');
});

// Servidor de WebSockets (Puerto 8081)
const wss = new WebSocketServer({ port: 8081 });
let clientesActivos = [];

let esp32S3Ip = '192.168.206.100'; // IP de destino auto-mapeada del ESP32-S3

wss.on('connection', (ws) => {
    clientesActivos.push(ws);
    console.log('🔌 Cliente Web acoplado al WebSocket (8081)');

    // Escucha comandos desde la web y los despacha al ESP32-S3 mediante UDP
    ws.on('message', (msg) => {
        try {
            const comando = JSON.parse(msg);
            if (comando.tipo === 'CONTROL') {
                const cadenaComando = `C:${comando.luces},${comando.motorA},${comando.motorB}\n`;
                const clientUDP = dgram.createSocket('udp4');
                
                // Envía comando UDP directo al puerto 4210 del S3 de Campo
                clientUDP.send(cadenaComando, 4210, esp32S3Ip, (err) => {
                    if (err) console.error(`Error al enviar comando UDP a ${esp32S3Ip}:`, err);
                    clientUDP.close();
                });
                console.log(`🎮 Comando enviado vía UDP a ${esp32S3Ip}:4210 -> ${cadenaComando.trim()}`);
            }
        } catch (e) {
            console.error("Error al procesar comando WebSocket:", e);
        }
    });

    ws.onclose = () => {
        clientesActivos = clientesActivos.filter(c => c !== ws);
        console.log('🔌 Cliente Web desconectado');
    };
});

// --- RECEPCIÓN DE TELEMETRÍA UDP (Puerto 5002) ---
const udpTelemetry = dgram.createSocket('udp4');

udpTelemetry.on('message', (msg, rinfo) => {
    // Registrar dinámicamente la IP del S3 de Campo que envía telemetría
    esp32S3Ip = rinfo.address;

    const lineaTexto = msg.toString('utf8').trim();
    if (lineaTexto.includes('|')) {
        // 1. Broadcast de telemetría al cliente web conectado
        clientesActivos.forEach(c => c.send(JSON.stringify({ telemetria: lineaTexto })));

        // 2. Persistencia asíncrona estructurada en el log CSV
        // Formato esperado de entrada: A:L,R|M:mq1,mq2|P:pm25|G:lat,lon|C:t,p,h
        try {
            const secciones = lineaTexto.split('|');
            const audio = secciones[0].substring(2).split(',');
            const mqs = secciones[1].substring(2).split(',');
            const polvo = secciones[2].substring(2);
            const gps = secciones[3].substring(2).split(',');
            const clima = secciones[4].substring(2).split(',');

            const timestamp = new Date().toISOString();
            const filaCSV = `${timestamp},${audio[0]},${audio[1]},${mqs[0]},${mqs[1]},${polvo},${gps[0]},${gps[1]},${clima[0]},${clima[1]},${clima[2]}\n`;

            fs.appendFile(archivoCSV, filaCSV, (err) => {
                if (err) console.error("❌ Error al escribir en registro CSV:", err);
            });
        } catch (csvError) {
            console.error("⚠️ Error de procesamiento CSV en línea:", lineaTexto);
        }
    }
});

udpTelemetry.bind(5002, () => {
    console.log('📊 Servidor UDP Telemetría escuchando en el puerto 5002');
});
