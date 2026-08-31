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

Para manejar el procesamiento concurrente de las conexiones y el cálculo del sorteo condicionado al quórum de agencias, se optó por un enfoque de **estado compartido mediante cerrojos (Locks) y barreras**.

### Decisiones de Diseño y Alternativas Consideradas

* **Arquitectura de Concurrencia (Estado Compartido vs. Message Passing):**
  * *Alternativa Considerada:* Utilizar un patrón de "Message Passing" con un hilo coordinador central. En este modelo, los hilos de los clientes (productores) colocarían las apuestas en una cola segura (ej. `queue.Queue` en Python), y un único hilo consumidor se encargaría de la escritura en el archivo y de contar si se alcanzó el quórum, respondiendo luego a cada cliente por colas privadas.
  * *Decisión:* Se utilizó un modelo clásico de **Multithreading con estado compartido**, lanzando un hilo por conexión (`threading.Thread`).
  * *Razón:* Si bien el modelo de colas y coordinador es excelente y libre de locks explícitos en los archivos, introducía una gran complejidad arquitectónica y requería reescribir buena parte del flujo de datos del servidor. El modelo clásico resultó mucho más simple de implementar y encajaba mejor con la estructura secuencial base, requiriendo agregar únicamente dos primitivas de sincronización.

* **Protección del Almacenamiento (Race Conditions):**
  * Puesto que la clase de dominio `Lottery` (la cual no podíamos modificar) lee y escribe sobre un mismo archivo CSV, se instanció un único `threading.Lock` global. Este Lock **envuelve las llamadas** a `store_bets` y `load_bets` por parte de los hilos clientes, garantizando acceso mutuamente exclusivo a la E/S y previniendo archivos corruptos o lecturas sucias por condiciones de carrera.

* **Sincronización del Quórum (threading.Barrier):**
  * Para satisfacer el requerimiento de esperar a que un mínimo de agencias notifiquen su fin de transmisión (`OP_END`), se utilizó la primitiva `threading.Barrier(AGENCY_QUORUM_MIN)`.
  * *Razón:* Fue elegida sobre otras opciones (como contadores protegidos con `Condition` o `Event`) porque resuelve el caso base bloqueando a los hilos pasivamente (sin consumir CPU), y posee una enorme ventaja: **se reinicia automáticamente** tras alcanzar el quórum. Esto permitió soportar naturalmente la ejecución de múltiples rondas de sorteos continuas sin agregar lógica manual para reiniciar estados.
