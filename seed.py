import random
from datetime import datetime, date, timedelta
from app import app, db
from database import (User, Ship, Cargo, Alert, Operation, Driver, Truck,
                       Yard, Equipment, Personnel, DocumentRecord, Accident,
                       AccidentFollowUp, CargoTrace, AccessLog, YardSlot, RouteEvent)
from werkzeug.security import generate_password_hash

with app.app_context():
    db.drop_all()
    db.create_all()

    users = [
        User(username='admin', password_hash=generate_password_hash('admin123'), role='admin', full_name='Administrador General', email='admin@portusense.com'),
        User(username='carlos', password_hash=generate_password_hash('carlos123'), role='operator', full_name='Carlos Mendez', email='carlos@portusense.com'),
        User(username='maria', password_hash=generate_password_hash('maria123'), role='supervisor', full_name='Maria Lopez', email='maria@portusense.com'),
        User(username='pedro', password_hash=generate_password_hash('pedro123'), role='operator', full_name='Pedro Ramirez', email='pedro@portusense.com'),
        User(username='laura', password_hash=generate_password_hash('laura123'), role='supervisor', full_name='Laura Torres', email='laura@portusense.com'),
    ]
    db.session.add_all(users)
    db.session.commit()

    # --- Buques ---
    ship_names = [
        'MV Pacific Star', 'MS Atlantic Wave', 'MV Nordic Spirit', 'SS Caribbean Sun',
        'MV Blue Horizon', 'MS Golden Eagle', 'MV Silver Wave', 'SS Northern Light',
        'MV Pacific Pioneer', 'MS Ocean Dream', 'MV Coral Breeze', 'SS Desert Storm',
        'MV Star of the East', 'MS Wind Chaser', 'MV Titanium', 'SS Iron Will',
        'MV Sea Dragon', 'MS Tide Runner', 'MV Crystal Wave', 'SS Storm Rider'
    ]
    cargo_types = ['Contenedores', 'Granel Solido', 'Granel Liquido', 'Vehiculos', 'Madera', 'Minerales', 'Cereales', 'Petroleo']
    locations = ['Patio A1', 'Patio A2', 'Patio B1', 'Patio B2', 'Bodega 1', 'Bodega 2', 'Bodega 3', 'Bodega 4', 'Muelle 1', 'Muelle 2']
    destinations = ['Ciudad de Mexico', 'Guadalajara', 'Monterrey', 'Puebla', 'Queretaro', 'Toluca', 'Leon', 'Merida', 'Cancun', 'Oaxaca']
    statuses = ['pending', 'in_progress', 'completed']

    ships = []
    for name in ship_names:
        arrival = date.today() + timedelta(days=random.randint(-10, 15))
        eta_h = random.randint(0, 23)
        eta_m = random.choice([0, 15, 30, 45])
        ship = Ship(
            name=name, arrival_date=arrival,
            eta=datetime(2024, 1, 1, eta_h, eta_m).time(),
            cargo_type=random.choice(cargo_types),
            status=random.choice(statuses),
            created_by=random.choice([1, 2, 4])
        )
        ships.append(ship)
    db.session.add_all(ships)
    db.session.commit()

    # --- Mercancias ---
    for ship in ships:
        for _ in range(random.randint(1, 4)):
            db.session.add(Cargo(
                ship_id=ship.id, cargo_type=random.choice(cargo_types),
                quantity=random.randint(10, 500), weight=round(random.uniform(5.0, 200.0), 1),
                location=random.choice(locations), destination=random.choice(destinations)
            ))
    db.session.commit()

    # --- Conductores ---
    driver_data = [
        ('Juan', 'Perez', 'LIC-001', 90), ('Maria', 'Garcia', 'LIC-002', 200),
        ('Carlos', 'Lopez', 'LIC-003', 15), ('Ana', 'Martinez', 'LIC-004', 300),
        ('Pedro', 'Sanchez', 'LIC-005', -5), ('Laura', 'Rivera', 'LIC-006', 180),
        ('Miguel', 'Hernandez', 'LIC-007', 45), ('Sofia', 'Diaz', 'LIC-008', 250),
        ('Roberto', 'Fernandez', 'LIC-009', 60), ('Elena', 'Torres', 'LIC-010', 120),
    ]
    drivers = []
    for fn, ln, lic, days_until_expiry in driver_data:
        d = Driver(
            first_name=fn, last_name=ln, license_number=lic,
            license_expiry=date.today() + timedelta(days=days_until_expiry),
            phone=f'55-{random.randint(1000,9999)}-{random.randint(1000,9999)}',
            status=random.choice(['active', 'active', 'active', 'inactive'])
        )
        drivers.append(d)
    db.session.add_all(drivers)
    db.session.commit()

    # --- Camiones ---
    truck_types = ['Granelero', 'Container', 'Frigorifico', 'Plataforma', 'Cisterna', 'Todo terreno']
    # Coordenadas del area portuaria de Manzanillo, Colima (centro, patio, ruta)
    route_points = [
        (19.0705, -104.3180), (19.1680, -104.2810), (19.2510, -104.1520),
        (19.4520, -103.9310), (19.8100, -103.6500), (20.1200, -103.5100),
        (19.0480, -104.3350), (19.0920, -104.3010),
    ]
    trucks = []
    for i in range(15):
        status = random.choice(['available', 'available', 'available', 'in_transit', 'maintenance'])
        t = Truck(
            plate_number=f'ABC-{1000+i}',
            truck_type=random.choice(truck_types),
            capacity_tons=round(random.uniform(5.0, 30.0), 1),
            status=status,
            driver_id=random.choice(drivers).id if random.random() > 0.2 else None
        )
        if status == 'in_transit':
            t.lat, t.lng = route_points[i % len(route_points)]
            t.last_location = f'Via al occidente, km {random.randint(5, 90)}'
            t.last_report_at = datetime.now() - timedelta(minutes=random.randint(5, 90))
        else:
            t.lat, t.lng = 19.0558 + random.uniform(-0.01, 0.01), -104.3184 + random.uniform(-0.01, 0.01)
            t.last_location = 'Terminal portuaria'
            t.last_report_at = datetime.now() - timedelta(hours=random.randint(1, 24))
        trucks.append(t)
    db.session.add_all(trucks)
    db.session.commit()

    # --- Patios y Bodegas ---
    yard_data = [
        ('Patio A1', 'yard', 500), ('Patio A2', 'yard', 400),
        ('Patio B1', 'yard', 600), ('Patio B2', 'yard', 350),
        ('Bodega 1', 'warehouse', 200), ('Bodega 2', 'warehouse', 250),
        ('Bodega 3', 'warehouse', 300), ('Bodega 4', 'warehouse', 180),
        ('Patio C1', 'yard', 450), ('Bodega 5', 'warehouse', 220),
    ]
    yard_coords = [
        (19.0590, -104.3210), (19.0610, -104.3160), (19.0575, -104.3135),
        (19.0630, -104.3240), (19.0548, -104.3195), (19.0535, -104.3225),
        (19.0650, -104.3180), (19.0520, -104.3160), (19.0665, -104.3250),
        (19.0505, -104.3200),
    ]
    yards = []
    for idx, (name, ytype, cap) in enumerate(yard_data):
        occ = round(cap * random.uniform(0.2, 0.95), 1)
        y = Yard(
            name=name, yard_type=ytype, capacity_tons=cap,
            current_occupancy_tons=occ,
            status='full' if occ >= cap else 'active',
            location=f'Sector {random.choice("ABC")} - Zona {random.randint(1,5)}',
            lat=yard_coords[idx][0], lng=yard_coords[idx][1]
        )
        yards.append(y)
    db.session.add_all(yards)
    db.session.commit()

    # --- Puestos de cuadricula (30 por patio/bodega) ---
    for y in yards:
        prefix = 'P' if y.yard_type == 'yard' else 'B'
        occupied = int(round((y.current_occupancy_tons / y.capacity_tons) * 30)) if y.capacity_tons > 0 else 0
        statuses = ['full'] * min(occupied, 24) + ['hold'] * 2 + ['empty'] * 30
        statuses = statuses[:30]
        random.shuffle(statuses)
        for i in range(30):
            st = statuses[i]
            slot = YardSlot(yard_id=y.id, code=f'{prefix}{y.id}-{i+1:02d}', status=st)
            if st == 'full':
                slot.cargo_name = random.choice(['Carga general', 'Contenedor cargado', 'Granel empacado', 'Metanol industrial'])
                slot.internal_code = f'MP-{2200 + i + y.id}'
                if 'Metanol' in slot.cargo_name:
                    slot.onu_number = 'UN1230'
                slot.weight = f'{random.randint(50, 800)} kg'
                slot.quantity = f'{random.randint(5, 60)} unidades'
            elif st == 'hold':
                slot.cargo_name = 'Carga en retencion'
                slot.internal_code = f'RET-{300 + i}'
                slot.weight = '—'
                slot.quantity = '—'
            db.session.add(slot)
    db.session.commit()

    # --- Asignar carga actual a camiones en transito y eventos de ruta ---
    cargo_list = Cargo.query.all()
    transit_trucks = [t for t in trucks if t.status == 'in_transit']
    for i, t in enumerate(transit_trucks):
        if cargo_list:
            t.current_cargo_id = random.choice(cargo_list).id
    db.session.commit()

    event_templates = [
        ('ubicacion', 'Actualizacion de ubicacion', 'Via al occidente, km {km}', 'ok'),
        ('peaje', 'Paso por peaje', 'Peaje Armeria', 'ok'),
        ('peaje', 'Paso por peaje', 'Peaje Compostela', 'ok'),
        ('control', 'Control policial · Revision de documentos', 'Autoridad: Policia de Transito · Resultado: liberado sin novedad', 'ok'),
        ('control', 'Control policial · Control rutinario', 'Autoridad: CAPUFE · Resultado: con comparendo/multa', 'warn'),
        ('incidente', 'Incidente · Averia mecanica', 'Falla en el sistema de frenos · Requiere taller movil', 'warn'),
        ('incidente', 'Incidente · Accidente', 'Colision frontal en km 45 · Requiere asistencia inmediata', 'bad'),
        ('ubicacion', 'Actualizacion de ubicacion', 'Andador de patio, zona de carga', 'ok'),
    ]
    for t in transit_trucks[:6]:
        for tipo, titulo, detalle_tpl, sev in random.sample(event_templates, random.randint(2, 4)):
            km = random.randint(5, 120)
            ev = RouteEvent(
                truck_id=t.id,
                driver_name=f'{t.driver.first_name} {t.driver.last_name}' if t.driver else t.plate_number,
                event_type=tipo, title=titulo, detail=detalle_tpl.format(km=km),
                severity=sev, lat=t.lat, lng=t.lng, reported_by=random.choice([1, 2, 4]),
                created_at=datetime.now() - timedelta(minutes=random.randint(10, 300))
            )
            db.session.add(ev)
            if t.lat and t.lng:
                t.lat += random.uniform(-0.01, 0.01)
                t.lng += random.uniform(-0.01, 0.01)
    db.session.commit()

    # --- Equipos ---
    equip_types = ['Grua', 'Montacargas', 'Apilador', 'Excavadora', 'Bulldozer', 'Generador', 'Compresor']
    equip_names = ['Grua Portuaria 1', 'Grua Portuaria 2', 'Montacargas Toyota 1', 'Montacargas Toyota 2',
                   'Apilador Kalmar', 'Excavadora CAT', 'Buldozer Komatsu', 'Generador Principal',
                   'Compresor Industrial 1', 'Grua Movil 3', 'Montacargas Hyster', 'Apilador Linde',
                   'Generador Auxiliar', 'Plataforma Elevadora', 'Carretilla Electrica']
    equipment = []
    for name in equip_names:
        last_m = date.today() - timedelta(days=random.randint(10, 120))
        e = Equipment(
            name=name, equipment_type=random.choice(equip_types),
            status=random.choice(['active', 'active', 'active', 'maintenance', 'offline']),
            location=random.choice(locations),
            last_maintenance=last_m,
            next_maintenance=last_m + timedelta(days=random.randint(30, 90))
        )
        equipment.append(e)
    db.session.add_all(equipment)
    db.session.commit()

    # --- Personal ---
    personnel_data = [
        ('Juan Carlos', 'Ruiz', 'Operador de Grua', 'Operaciones'),
        ('Ana Maria', 'Vargas', 'Supervisora de Patio', 'Operaciones'),
        ('Luis', 'Mendoza', 'Inspector de Carga', 'Calidad'),
        ('Carmen', 'Silva', 'Coordinadora de Logistica', 'Logistica'),
        ('Francisco', 'Ortiz', 'Mecanico Senior', 'Mantenimiento'),
        ('Isabel', 'Navarro', 'Analista de Seguridad', 'Seguridad'),
        ('Ricardo', 'Campos', 'Operador de Montacargas', 'Operaciones'),
        ('Patricia', 'Dominguez', 'Jefa de Turno', 'Operaciones'),
        ('Alejandro', 'Vega', 'Seguridad Industrial', 'Seguridad'),
        ('Monica', 'Ramos', 'Administradora de Documentos', 'Administracion'),
        ('Fernando', 'Castillo', 'Electromecanico', 'Mantenimiento'),
        ('Gabriela', 'Ortiz', 'Enfermera de Puerto', 'Seguridad'),
    ]
    personnel = []
    for fn, ln, pos, dept in personnel_data:
        p = Personnel(
            first_name=fn, last_name=ln, position=pos, department=dept,
            phone=f'55-{random.randint(1000,9999)}-{random.randint(1000,9999)}',
            email=f'{fn.lower()}.{ln.lower()}@portusense.com',
            status=random.choice(['active', 'active', 'active', 'vacation']),
            hire_date=date.today() - timedelta(days=random.randint(100, 2000))
        )
        personnel.append(p)
    db.session.add_all(personnel)
    db.session.commit()

    # --- Documentos ---
    doc_types = ['Pasaporte', 'Licencia', 'Certificacion', 'Permiso', 'Seguro', 'Contrato', 'Auditoria']
    doc_titles = [
        'Permiso de Operacion Portuaria', 'Seguro de Carga Maritime',
        'Certificacion de Seguridad', 'Auditoria ISO 9001',
        'Licencia de Grua Puente', 'Permiso de Zona Restringida',
        'Seguro de Responsabilidad Civil', 'Certificacion de Personal',
        'Contrato de Terminal', 'Auditoria Ambiental',
        'Permiso de Manejo de Peligrosos', 'Certificacion de Equipos'
    ]
    for i in range(12):
        d = DocumentRecord(
            doc_type=random.choice(doc_types),
            title=doc_titles[i % len(doc_titles)],
            ship_id=random.choice(ships).id if random.random() > 0.6 else None,
            personnel_id=random.choice(personnel).id if random.random() > 0.6 else None,
            truck_id=random.choice(trucks).id if random.random() > 0.8 else None,
            expires_at=date.today() + timedelta(days=random.randint(-30, 365)) if random.random() > 0.3 else None,
            is_valid=random.choice([True, True, True, False]),
            notes=f'Documento #{i+1} del sistema'
        )
        db.session.add(d)
    db.session.commit()

    # --- Accidentes ---
    accident_data = [
        ('Caida de contenedor', 'Contenedor cayo durante operacion de izaje', 'severe', 2),
        ('Vuelco de camion', 'Camion se volco al ingresar a patio B2', 'moderate', 1),
        ('Fuga de liquido', 'Fuga menor de liquido en area de tanques', 'minor', 0),
        ('Falla de grua', 'Falla en el freno de la grua portuaria 1', 'moderate', 0),
        ('Choque de montacargas', 'Montacargas impacto estructura de bodega', 'minor', 1),
        ('Incendio menor', 'Incendio en zona de carga seca, controlado', 'severe', 3),
        ('Desparramo de carga', 'Carga se desparramo en area de transito', 'minor', 0),
        ('Lesion laboral', 'Operador sufrio esguince en turno nocturno', 'minor', 1),
    ]
    accidents = []
    for title, desc, sev, injuries in accident_data:
        a = Accident(
            title=title, description=desc, severity=sev,
            location=random.choice(locations),
            ship_id=random.choice(ships).id if random.random() > 0.5 else None,
            truck_id=random.choice(trucks).id if random.random() > 0.7 else None,
            personnel_id=random.choice(personnel).id if random.random() > 0.4 else None,
            accident_date=datetime.now() - timedelta(days=random.randint(1, 60)),
            status=random.choice(['reported', 'investigating', 'resolved', 'closed']),
            injuries_count=injuries,
            created_by=random.choice([1, 3, 5])
        )
        accidents.append(a)
    db.session.add_all(accidents)
    db.session.commit()

    # --- Seguimientos de Accidentes ---
    followup_desc = [
        'Revision del area afectada realizada', 'Se contacto al seguro',
        'Maquinaria inspeccionada y aprobada', 'Personal capacitado en nuevo procedimiento',
        'Se actualizo el protocolo de seguridad', 'Inspeccion medica completada',
        'Reparacion de equipo iniciada', 'Area barrera y señalizada'
    ]
    for acc in accidents:
        for _ in range(random.randint(1, 3)):
            f = AccidentFollowUp(
                accident_id=acc.id,
                description=random.choice(followup_desc),
                action_taken=random.choice(['Correctivo', 'Preventivo', 'Formativo', 'Documental']),
                followup_date=date.today() + timedelta(days=random.randint(-10, 30)),
                status=random.choice(['pending', 'in_progress', 'completed']),
                created_by=random.choice([1, 3, 5])
            )
            db.session.add(f)
    db.session.commit()

    # --- Trazabilidad de Mercancia ---
    all_cargo = Cargo.query.all()
    for c in all_cargo[:20]:
        for _ in range(random.randint(1, 3)):
            t = CargoTrace(
                cargo_id=c.id,
                from_location=random.choice(['Buque'] + locations),
                to_location=random.choice(locations),
                moved_by=random.choice(['admin', 'carlos', 'pedro', 'laura']),
                moved_at=datetime.now() - timedelta(hours=random.randint(1, 72)),
                notes=random.choice(['Carga inicial', 'Reubicacion', 'Inspeccion', 'Preparacion para embarque', ''])
            )
            db.session.add(t)
    db.session.commit()

    # --- Alertas ---
    alert_configs = [
        ('delay', 'high', 'Buque atrasado - fecha de llegada ya paso'),
        ('delay', 'medium', 'Posible retraso en operacion'),
        ('space', 'high', 'Patio de almacenamiento lleno'),
        ('equipment', 'high', 'Equipo principal fuera de servicio'),
        ('documents', 'medium', 'Falta certificado de carga'),
        ('safety', 'high', 'Accidente reportado en area operativa'),
        ('weather', 'medium', 'Condiciones climaticas adversas pronosticadas'),
    ]
    for ship in ships:
        for alert_type, severity, message in random.sample(alert_configs, random.randint(1, 3)):
            db.session.add(Alert(
                ship_id=ship.id, alert_type=alert_type, severity=severity,
                message=f"{ship.name}: {message}",
                is_read=random.choice([True, False]),
                created_at=datetime.now() - timedelta(hours=random.randint(0, 72))
            ))
    db.session.commit()

    # --- Operaciones ---
    for ship in ships:
        if ship.status in ('in_progress', 'completed'):
            db.session.add(Operation(
                ship_id=ship.id,
                start_time=datetime.now() - timedelta(hours=random.randint(1, 48)),
                end_time=datetime.now() - timedelta(hours=random.randint(0, 24)) if ship.status == 'completed' else None,
                status=ship.status,
                notes=random.choice(['Operacion normal', 'Retraso por clima', 'Equipo disponible', 'Sin novedad'])
            ))
    db.session.commit()

    print("=" * 50)
    print("Base de datos poblada con exito!")
    print("=" * 50)
    print(f"  Usuarios:       {User.query.count()}")
    print(f"  Buques:         {Ship.query.count()}")
    print(f"  Mercancias:     {Cargo.query.count()}")
    print(f"  Conductores:    {Driver.query.count()}")
    print(f"  Camiones:       {Truck.query.count()}")
    print(f"  Patios/Bodegas: {Yard.query.count()}")
    print(f"  Puestos patio:  {YardSlot.query.count()}")
    print(f"  Eventos ruta:   {RouteEvent.query.count()}")
    print(f"  Equipos:        {Equipment.query.count()}")
    print(f"  Personal:       {Personnel.query.count()}")
    print(f"  Documentos:     {DocumentRecord.query.count()}")
    print(f"  Accidentes:     {Accident.query.count()}")
    print(f"  Seguimientos:   {AccidentFollowUp.query.count()}")
    print(f"  Trazabilidad:   {CargoTrace.query.count()}")
    print(f"  Alertas:        {Alert.query.count()}")
    print(f"  Operaciones:    {Operation.query.count()}")
    print("\nCredenciales de acceso:")
    print("  admin / admin123    (Administrador)")
    print("  carlos / carlos123  (Operador)")
    print("  maria / maria123    (Supervisor)")
