# PortuSense — Documento de Presentación del Sistema

**Versión:** 2.0
**Autor:** Ing. Levi J. Quintero
**Fecha:** Octubre 2026

---

## 1. ¿Qué es PortuSense?

PortuSense es un **sistema integral de gestión portuaria y logística** diseñado para operar los puertos de manera eficiente, segura y trazable. Centraliza en una sola plataforma el control de buques, mercancías, transporte terrestre, personal, equipamiento, seguridad y documentación — todo con alertas automáticas, análisis de riesgo en tiempo real, recomendaciones inteligentes y generación de reportes exportables.

### Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.14 + Flask 3.0 |
| Base de datos | SQLite (local) / MySQL (producción) via SQLAlchemy ORM |
| Frontend | Bootstrap 5.3 + Chart.js 4 + Font Awesome 5 |
| Autenticación | Flask-Login con roles y hashing de contraseñas |
| Reportes | openpyxl (exportación a Excel .xlsx) |
| Seguridad | Control de accesos, registro de actividad, roles jerárquicos |

---

## 2. Roles de Usuario y Permisos

El sistema maneja **3 niveles de acceso**:

| Rol | Permisos |
|-----|----------|
| **Administrador** | Acceso total. Ve el Control de Accesos (log de actividad). Puede crear/editar/eliminar todo. |
| **Supervisor** | Acceso operativo completo. Gestiona buques, carga, personal, accidentes. No ve control de accesos. |
| **Operador** | Acceso limitado. Registra movimientos, reporta accidentes, consulta información. |

Cada acción queda registrada con fecha, hora, usuario e IP en el módulo de **Control de Accesos**.

---

## 3. Escenario Operativo: Un Día en el Puerto

Para presentar el sistema, el siguiente escenario muestra cómo los módulos se conectan en una operación real.

---

### FASE 1 — Llegada del Buque

**Situación:** El buque **"MV Pacific Star"** está programado para llegar el 20 de octubre a las 14:00 con 500 contenedores de carga general.

**Lo que se hace en PortuSense:**

1. **Registro de Buque** (módulo *Buques*)
   - El supervisor crea el registro: nombre, fecha de llegada, ETA, tipo de carga, estado = **Pendiente**.
   - El sistema automáticamente evalúa el riesgo: si la fecha de llegada ya pasó y el buque sigue pendiente, genera una **alerta de alta severidad** ("Buque atrasado").

2. **Análisis de Riesgo** (módulo *Dashboard*)
   - El dashboard muestra al buque con su nivel de riesgo: **ALTO / MEDIO / BAJO**.
   - El cálculo considera: ¿tiene carga registrada? ¿Está atrasado? ¿Tiene alertas activas?

3. **Generación de Alertas** (módulo *Alertas*)
   - Con un clic, el sistema genera alertas automáticas para todos los buques basándose en reglas:
     - Sin mercancía registrada → alerta media
     - Atrasado → alerta alta
     - En espera → alerta baja

---

### FASE 2 — Registro de Mercancía

**Situación:** El MV Pacific Star llega al puerto. Se descargan 500 contenedores: 300 de electrónica, 150 de alimentos congelados y 50 de maquinaria.

**Lo que se hace en PortuSense:**

4. **Gestión de Mercancías** (módulo *Mercancías*)
   - Se registra cada tipo de carga: tipo, cantidad, peso, ubicación de destino, destino final.
   - Cada registro queda **vinculado al buque** que la trajo.

5. **Trazabilidad de Mercancía** (módulo *Trazabilidad*)
   - Al registrar la carga, el sistema **crea automáticamente** el primer registro de trazabilidad: "Buque → Patio A1".
   - Cada vez que la mercancía se mueve (de patio a bodega, de bodega a camión), se registra:
     - De dónde viene
     - A dónde va
     - Quién lo movió
     - Fecha y hora
     - Notas adicionales
   - **Resultado:** cualquier mercancía puede rastrearse desde que llegó en el buque hasta que salió del puerto.

---

### FASE 3 — Almacenamiento

**Situación:** La mercancía necesita almacenarse temporalmente antes de ser distribuida por tierra.

**Lo que se hace en PortuSense:**

6. **Control de Patios y Bodegas** (módulo *Patios y Bodegas*)
   - El puerto tiene 6 patios y 4 bodegas registrados, cada uno con su capacidad en toneladas.
   - El dashboard muestra una **barra de ocupación** con código de color:
     - 🟢 Verde: ocupación < 60%
     - 🟡 Amarillo: 60% - 85%
     - 🔴 Rojo: > 85%
   - Si un patio supera el 85%, el sistema genera una **recomendación inteligente** para redistribuir carga.

---

### FASE 4 — Transporte Terrestre

**Situación:** La mercancía necesita salir del puerto en camiones hacia distintas ciudades del interior.

**Lo que se hace en PortuSense:**

7. **Registro de Conductores** (módulo *Conductores*)
   - Se registran los 10 conductores de la empresa con: nombre, licencia, fecha de vencimiento, teléfono, estado.
   - **Control automático de licencias:** el sistema marca las licencias que vencen en 30 días o menos con badge "Por vencer", y las ya vencidas con badge "Vencida".
   - Recomendación automática si hay conductores con licencia por vencer.

8. **Control de Camiones** (módulo *Camiones*)
   - Se registran los 15 camiones de la flota: placa, tipo (granelero, container, frigorífico, etc.), capacidad en toneladas, estado.
   - Cada camión se **asocia a un conductor**.
   - Estados: **Disponible** 🟢, **En Tránsito** 🟡, **Mantenimiento** 🔴.
   - El dashboard muestra un gráfico de dona con la distribución de la flota.

---

### FASE 5 — Equipamiento y Mantenimiento

**Situación:** Las grúas portuarias, montacargas y otra maquinaria necesitan mantenimiento preventivo.

**Lo que se hace en PortuSense:**

9. **Control de Equipos** (módulo *Equipos*)
   - Se registran los 15 equipos: nombre, tipo (grúa, montacargas, excavadora, etc.), estado, ubicación.
   - Se registra la **fecha de último mantenimiento** y la **fecha del próximo**.
   - Si el próximo mantenimiento ya pasó, el sistema muestra badge "Vencido" en rojo.
   - Recomendación automática: "X equipos tienen mantenimiento vencido".

---

### FASE 6 — Personal y Documentación

**Situación:** El puerto tiene 12 empleados en operaciones, mantenimiento, calidad, logística y seguridad. Todos necesitan documentos vigentes.

**Lo que se hace en PortuSense:**

10. **Gestión de Personal** (módulo *Personal*)
    - Registro completo: nombre, cargo, departamento, teléfono, email, fecha de ingreso, estado.
    - Estados: **Activo** 🟢, **Vacaciones** 🔵, **Enfermo** 🟡, **Terminado** ⚪.

11. **Control Documental** (módulo *Documentos*)
    - Cada documento se registra con: tipo (pasaporte, licencia, certificación, permiso, seguro, contrato), título, y se **asocia** a un buque, una persona o un camión.
    - El sistema controla:
      - ¿Está **válido** o **inválido**? (toggle con un clic)
      - ¿Cuándo **vence**? (badge "Por vencer" si vence en 30 días, "Vencido" si ya pasó)
    - Recomendación automática: "X documentos vencen en 30 días".

---

### FASE 7 — Seguridad y Emergencias

**Situación:** Ocurre un incidente: un contenedor cae durante una operación de izaje, resultando 2 heridos.

**Lo que se hace en PortuSense:**

12. **Registro y Gestión de Accidentes** (módulo *Accidentes*)
    - Se reporta el accidente: título, descripción detallada, severidad (menor / moderado / grave / crítico), ubicación, fecha/hora, número de heridos.
    - Se **vincula** al buque, camión y/o personal involucrado.
    - **Alerta de emergencia automática:** si la severidad es "grave" o "crítica", el sistema genera inmediatamente una alerta de tipo **EMERGENCIA** con severidad alta, visible en el dashboard.

13. **Seguimiento Posterior** (módulo *Accidentes* → detalle)
    - Para cada accidente se crean **seguimientos** con:
      - Descripción de la acción realizada
      - Acción tomada (correctivo, preventivo, formativo, documental)
      - Fecha programada de seguimiento
      - Estado: **Pendiente** → **En Progreso** → **Completado**
    - El sistema genera recomendación si hay seguimientos vencidos.

14. **Sistema de Alertas** (módulo *Alertas*)
    - Todas las alertas (de buques, accidentes, emergencias) se centralizan en una vista.
    - Se pueden marcar como leídas.
    - El dashboard muestra las 5 más recientes no leídas.

---

### FASE 8 — Análisis y Decisión

**Situación:** El gerente del puerto necesita tomar decisiones informadas.

**Lo que se hace en PortuSense:**

15. **Panel Principal — Dashboard**
    - **16 tarjetas de métrica** en tiempo real:
      - Buques: total, pendientes, en proceso, completados
      - Camiones: total, disponibles, en tránsito
      - Conductores: total, activos
      - Personal: total, activos
      - Patios/Bodegas: total
      - Equipos: total, activos
      - Accidentes abiertos (con contador de críticos)
      - Documentos por vencer
      - Mercancía: items y peso total
    - **3 gráficos interactivos:**
      - Dona: estado de operaciones de buques
      - Barras: nivel de riesgo por buque
      - Dona: estado de la flota de camiones
    - **Tabla de riesgo** por buque con badges de color
    - **Alertas recientes** y **recomendaciones inteligentes**

16. **Recomendaciones Inteligentes** (módulo *Recomendaciones*)
    - El sistema analiza **8 reglas automáticamente** y genera sugerencias priorizadas:
      | Regla | Severidad |
      |-------|-----------|
      | Conductores con licencia por vencer (30 días) | ⚠️ Warning |
      | Equipos con mantenimiento atrasado | 🔴 Danger |
      | Patios/bodegas con ocupación > 85% | ⚠️ Warning |
      | Accidentes pendientes de seguimiento | ℹ️ Info |
      | Seguimientos de accidentes vencidos | 🔴 Danger |
      | Documentos por vencer (30 días) | ⚠️ Warning |
      | Camiones en mantenimiento | ℹ️ Info |
      | Llegadas de buques hoy | ℹ️ Info |

17. **Reportes y Exportación** (módulo *Reportes*)
    - Resumen visual con gráficos de pie y barras.
    - **10 exportaciones a Excel (.xlsx):**
      1. Buques
      2. Mercancías
      3. Alertas
      4. Operaciones
      5. Camiones
      6. Conductores
      7. Personal
      8. Accidentes
      9. Equipos
      10. Patios y Bodegas

---

### FASE 9 — Control de Accesos

**Situación:** El administrador necesita auditar quién hizo qué y cuándo.

**Lo que se hace en PortuSense:**

18. **Control de Accesos** (solo administradores)
    - Cada login, logout y login fallido queda registrado con:
      - Fecha y hora exacta
      - Usuario
      - Tipo de acción (Login / Logout / Login Fallido)
      - Dirección IP
      - Detalles adicionales
    - Paginación para manejar grandes volúmenes de registros.

---

## 4. Diagrama de Conexiones entre Módulos

```
                         ┌──────────────┐
                         │   DASHBOARD  │
                         │  (Panel      │
                         │  Principal)  │
                         └──────┬───────┘
                                │
        ┌───────────┬───────────┼───────────┬──────────────┐
        ▼           ▼           ▼           ▼              ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────────┐
   │ BUQUES  │ │ CAMIONES│ │PERSONAL │ │EQUIPOS  │ │RECOMENDACIONES│
   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └──────────────┘
        │           │           │           │
        ▼           ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │CARGA    │ │CONDUCT. │ │DOCUMENTOS│ │MANTENIM.│
   │(Mercan.)│ │         │ │         │ │         │
   └────┬────┘ └─────────┘ └─────────┘ └─────────┘
        │
        ▼
   ┌──────────┐     ┌──────────┐     ┌───────────────┐
   │TRAZABILIDAD│◄───│PATIOS/   │◄────│CAMIONES       │
   │          │     │BODEGAS   │     │(salida carga) │
   └──────────┘     └──────────┘     └───────────────┘
        
   ┌──────────┐     ┌──────────────┐     ┌──────────┐
   │ACCIDENTES│────►│SEGUIMIENTO   │────►│ALERTAS   │
   │          │     │(follow-up)   │     │EMERGENCIA│
   └──────────┘     └──────────────┘     └──────────┘
        
   ┌──────────────┐
   │CONTROL       │
   │ACCESOS       │  (log de todas las acciones)
   └──────────────┘
```

---

## 5. Flujo Completo de una Operación

```
1. Buque llega          → Se registra en BUQUES
2. Se descarga carga    → Se registra en MERCANCÍAS (vinculada al buque)
3. Trazabilidad         → Se crea registro automático de movimiento
4. Almacenamiento       → Se asigna a PATIO/BODEGA con control de ocupación
5. Preparación salida   → Se asigna CAMIÓN + CONDUCTOR
6. Documentación        → Se verifica en DOCUMENTOS que todo esté vigente
7. Carga sale del puerto→ Nueva entrada en TRAZABILIDAD
8. Si hay incidente     → Se reporta en ACCIDENTES + alerta automática
9. Seguimiento           → Se crean FOLLOW-UPS en ACCIDENTES
10. Reporte final       → Se exporta TODO a Excel desde REPORTES
```

---

## 6. Resumen de Datos del Sistema Demo

| Módulo | Registros de ejemplo |
|--------|---------------------|
| Usuarios | 5 (1 admin, 2 supervisores, 2 operadores) |
| Buques | 20 con estados variados |
| Mercancías | 53 items vinculados a buques |
| Conductores | 10 (1 con licencia vencida, 1 por vencer) |
| Camiones | 15 (10 disponibles, 3 en tránsito, 2 en mantenimiento) |
| Patios/Bodegas | 10 (algunos al 90%+ de ocupación) |
| Equipos | 15 (13 activos, 2 en mantenimiento) |
| Personal | 12 (departamentos: operaciones, mantenimiento, seguridad, etc.) |
| Documentos | 12 (algunos por vencer, algunos inválidos) |
| Accidentes | 8 (de menor a crítico, con seguimientos) |
| Seguimientos | 15 (pendientes, en progreso, completados) |
| Trazabilidad | 41 movimientos registrados |
| Alertas | 39 generadas automáticamente |
| Operaciones | 11 registradas |

**Credenciales:** `admin / admin123`

---

## 7. Características Destacadas para la Presentación

1. **Todo en un solo sistema** — No se necesitan hojas de cálculo, correos ni llamadas. Todo está centralizado.

2. **Trazabilidad total** — Cada mercancía puede rastrearse desde que llega en el buque hasta que sale del puerto.

3. **Alertas automáticas** — El sistema detecta problemas sin que nadie los busque: buques atrasados, licencias por vencer, mantenimiento vencido, ocupación alta.

4. **Recomendaciones inteligentes** — 8 reglas de negocio analizan el estado del puerto y sugieren acciones concretas.

5. **Seguridad con auditoría** — Control de roles (admin/supervisor/operador) y log completo de accesos.

6. **Emergencias integradas** — Un accidente severo genera automáticamente una alerta de emergencia visible en el dashboard.

7. **Reportes profesionales** — 10 exportaciones a Excel con formato, listas para presentar a dirección o auditorías.

8. **Dashboard en tiempo real** — 16 métricas y 3 gráficos que se actualizan con cada carga de página.

---

*PortuSense v2.0 — © 2026 Ing. Levi J. Quintero*
