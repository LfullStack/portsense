import random
from datetime import datetime, date, timedelta
from app import app, db
from database import User, Ship, Cargo, Alert, Operation
from werkzeug.security import generate_password_hash

with app.app_context():
    db.drop_all()
    db.create_all()

    users = [
        User(username='admin', password_hash=generate_password_hash('admin123'), role='admin'),
        User(username='carlos', password_hash=generate_password_hash('carlos123'), role='operator'),
        User(username='maria', password_hash=generate_password_hash('maria123'), role='supervisor'),
        User(username='pedro', password_hash=generate_password_hash('pedro123'), role='operator'),
        User(username='laura', password_hash=generate_password_hash('laura123'), role='supervisor'),
    ]
    db.session.add_all(users)
    db.session.commit()

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
    for i, name in enumerate(ship_names):
        arrival = date.today() + timedelta(days=random.randint(-10, 15))
        eta_h = random.randint(0, 23)
        eta_m = random.choice([0, 15, 30, 45])
        status = random.choice(statuses)
        cargo = random.choice(cargo_types)
        ship = Ship(
            name=name,
            arrival_date=arrival,
            eta=datetime(2024, 1, 1, eta_h, eta_m).time(),
            cargo_type=cargo,
            status=status,
            created_by=random.choice([1, 2, 4])
        )
        ships.append(ship)
    db.session.add_all(ships)
    db.session.commit()

    for ship in ships:
        num_cargo = random.randint(1, 4)
        for _ in range(num_cargo):
            item = Cargo(
                ship_id=ship.id,
                cargo_type=random.choice(cargo_types),
                quantity=random.randint(10, 500),
                weight=round(random.uniform(5.0, 200.0), 1),
                location=random.choice(locations),
                destination=random.choice(destinations)
            )
            db.session.add(item)
    db.session.commit()

    alert_configs = [
        ('delay', 'high', 'Buque atrasado - fecha de llegada ya paso'),
        ('delay', 'medium', 'Posible retraso en operacion'),
        ('delay', 'low', 'Buque en espera - sin novedad'),
        ('space', 'high', 'Patio de almacenamiento lleno'),
        ('space', 'medium', 'Espacio disponible limitado'),
        ('space', 'low', 'Espacio disponible suficiente'),
        ('equipment', 'high', 'Grua principal fuera de servicio'),
        ('equipment', 'medium', 'Montacargas en mantenimiento'),
        ('equipment', 'low', 'Equipos operando normalmente'),
        ('documents', 'high', 'Documentos de aduana pendientes'),
        ('documents', 'medium', 'Falta certificado de carga'),
        ('documents', 'low', 'Todos los documentos en orden'),
    ]

    for ship in ships:
        num_alerts = random.randint(1, 3)
        chosen = random.sample(alert_configs, num_alerts)
        for alert_type, severity, message in chosen:
            alert = Alert(
                ship_id=ship.id,
                alert_type=alert_type,
                severity=severity,
                message=f"{ship.name}: {message}",
                is_read=random.choice([True, False]),
                created_at=datetime.now() - timedelta(hours=random.randint(0, 72))
            )
            db.session.add(alert)
    db.session.commit()

    for ship in ships:
        if ship.status in ('in_progress', 'completed'):
            op = Operation(
                ship_id=ship.id,
                start_time=datetime.now() - timedelta(hours=random.randint(1, 48)),
                end_time=datetime.now() - timedelta(hours=random.randint(0, 24)) if ship.status == 'completed' else None,
                status=ship.status,
                notes=random.choice([
                    'Operacion normal',
                    'Retraso por clima',
                    'Equipo disponible rapidamente',
                    'Carga completada sin problemas',
                    'Requiere seguimiento'
                ])
            )
            db.session.add(op)
    db.session.commit()

    print("Base de datos poblada con exito!")
    print(f"  - {len(users)} usuarios")
    print(f"  - {len(ships)} buques")
    print(f"  - {Cargo.query.count()} mercancias")
    print(f"  - {Alert.query.count()} alertas")
    print(f"  - {Operation.query.count()} operaciones")
    print("\nCredenciales de acceso:")
    print("  admin / admin123  (Administrador)")
    print("  carlos / carlos123 (Operador)")
    print("  maria / maria123  (Supervisor)")
