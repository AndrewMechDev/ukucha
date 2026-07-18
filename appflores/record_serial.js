const { SerialPort } = require('serialport');
const fs = require('fs');
const path = require('path');

const logFile = path.join(__dirname, 'serial_capture.log');
const rawFile = path.join(__dirname, 'serial_capture.bin');

fs.writeFileSync(logFile, `--- INICIO DE GRABACIÓN DE 10 SEGUNDOS: ${new Date().toISOString()} ---\n`);
const rawStream = fs.createWriteStream(rawFile);

async function startRecording() {
    try {
        const puertos = await SerialPort.list();
        if (puertos.length === 0) {
            console.log('❌ No hay puertos serie disponibles para grabar.');
            process.exit(1);
        }

        let target = puertos.find(p => {
            const mfg = (p.manufacturer || '').toLowerCase();
            return mfg.includes('silicon') || mfg.includes('ch340') || mfg.includes('wch') || mfg.includes('espressif') || mfg.includes('usb');
        }) || puertos[0];

        console.log(`🔌 Conectando a ${target.path} para grabar por 10 segundos...`);
        const port = new SerialPort({ path: target.path, baudRate: 921600 });

        let bytesCount = 0;
        let lineCount = 0;
        let bufferAcc = '';

        port.on('data', (chunk) => {
            bytesCount += chunk.length;
            rawStream.write(chunk);

            bufferAcc += chunk.toString('utf8');
            let lines = bufferAcc.split('\n');
            bufferAcc = lines.pop();

            lines.forEach(line => {
                const cleanLine = line.trim();
                if (cleanLine.includes('|')) {
                    lineCount++;
                    fs.appendFileSync(logFile, `[TEXTO] ${cleanLine}\n`);
                }
            });
        });

        port.on('error', (err) => {
            console.error('Error de puerto serie:', err.message);
        });

        setTimeout(() => {
            port.close(() => {
                rawStream.end();
                console.log('\n⏱️ Grabación de 10 segundos completada.');
                console.log(`📊 Total de Bytes Recibidos: ${bytesCount}`);
                console.log(`📝 Total de Líneas de Telemetría Registradas: ${lineCount}`);
                console.log(`💾 Datos binarios crudos guardados en: ${rawFile}`);
                console.log(`💾 Líneas de telemetría filtradas guardadas en: ${logFile}`);
                process.exit(0);
            });
        }, 10000);

    } catch (e) {
        console.error('Error en grabación:', e);
        process.exit(1);
    }
}

startRecording();
