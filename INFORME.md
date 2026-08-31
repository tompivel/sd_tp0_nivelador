# Detalle de Solución

## Protocolo de Comunicación

Se implementó un protocolo binario basado en la arquitectura **TLV (Type-Length-Value)** sobre TCP, priorizando la eficiencia, robustez y separación de responsabilidades entre la capa de red y el dominio (lógica de negocio).

### Estructura del Mensaje
Todos los mensajes intercambiados poseen una cabecera fija de 5 bytes:
1. **Opcode (1 byte):** Define el tipo de operación. 
   - `0x01`: Envío de lote (Batch) de apuestas.
   - `0x02`: Acuse de recibo (ACK) de lote procesado.
   - `0x03`: Fin de transmisión (EOF) por parte del cliente.
   - `0x04`: Respuesta con la lista de apuestas ganadoras.
2. **Longitud (4 bytes - Big Endian):** Indica el tamaño exacto del Payload (puede ser 0).
3. **Payload (N bytes):** Contenido del mensaje, procesado secuencialmente según el Opcode.

### Decisiones de Diseño y Alternativas Consideradas

* **Serialización Binaria vs. Texto (CSV):** 
  * *Alternativa:* Enviar las líneas CSV directamente como texto dentro del payload y usar delimitadores (`,`).
  * *Decisión:* Se optó por serialización binaria empacada. Los tipos numéricos viajan como enteros de 4 bytes (`uint32`) y los strings poseen un prefijo de 1 byte con su longitud.
  * *Razón:* Evita problemas de colisión de delimitadores (ej. una coma dentro de un nombre), reduce drásticamente la transferencia de red y minimiza el uso de CPU al evitar algoritmos de parseo de texto puro.
* **Procesamiento de Lotes (Batching) Síncrono vs. Asíncrono:**
  * *Alternativa:* Que el cliente envíe todos los lotes de forma asíncrona de corrido.
  * *Decisión:* El cliente envía un batch (`0x01`) y bloquea su ejecución a la espera de un `ACK` (`0x02`) del servidor.
  * *Razón:* Aunque TCP garantiza la entrega de los paquetes a nivel de transporte, un `ACK` a nivel de aplicación era fundamental para garantizar que el servidor persistió exitosamente el lote en disco (cumpliendo el requerimiento del ejercicio 6). Previene la saturación de buffers y simplifica el manejo de errores.
* **Señalización explícita de fin de transmisión:**
  * En lugar de depender de *timeouts* o cierres abruptos de socket, el protocolo usa un Opcode específico (`0x03`) con payload vacío para indicar el fin de lectura de apuestas. Esto es vital para que el servidor sepa el momento exacto en el cual debe proceder a calcular los ganadores para dicha agencia.

## Mecanismos para sincronizar la ejecución concurrente

*(Completar con el detalle de los mecanismos utilizados en el Ejercicio 7)*
