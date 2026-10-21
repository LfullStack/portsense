from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
import io
from openpyxl import Workbook
from openpyxl.styles import Font
from config import Config
from database import (db, User, Ship, Cargo, Alert, Operation, Driver, Truck,
                       Yard, Equipment, Personnel, DocumentRecord, Accident,
                       AccidentFollowUp, CargoTrace, AccessLog, YardSlot, RouteEvent)

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_today():
    return {'today': date.today()}

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Acceso restringido: se requiere rol de administrador', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def log_access(action, details=''):
    try:
        log = AccessLog(user_id=current_user.id if current_user.is_authenticated else None,
                       action=action,
                       ip_address=request.remote_addr or 'unknown',
                       details=details)
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

def analyze_risk(ship):
    alerts = []
    cargo_count = Cargo.query.filter_by(ship_id=ship.id).count()
    if cargo_count == 0:
        alerts.append(('documents', 'medium', 'Buque sin mercancia registrada'))
    if ship.status == 'pending':
        alerts.append(('delay', 'low', 'Buque en estado pendiente - posible retraso'))
    today = date.today()
    if ship.arrival_date < today and ship.status == 'pending':
        alerts.append(('delay', 'high', 'Buque atrasado - fecha de llegada ya paso'))
    return alerts

def get_risk_level(alerts):
    severities = [a[1] for a in alerts]
    if 'high' in severities:
        return 'alto'
    elif 'medium' in severities:
        return 'medio'
    return 'bajo'

def generate_recommendations():
    recs = []
    today = date.today()

    expiring_licenses = Driver.query.filter(
        Driver.license_expiry <= today + timedelta(days=30),
        Driver.license_expiry >= today,
        Driver.status == 'active'
    ).all()
    if expiring_licenses:
        recs.append(('warning', 'Conductores con licencia por vencer',
            f'{len(expiring_licenses)} conductor(es) tienen licencia que vence en 30 dias o menos. '
            'Programe la renovacion a la brevedad.'))

    overdue_maint = Equipment.query.filter(
        Equipment.next_maintenance < today,
        Equipment.status != 'offline'
    ).all()
    if overdue_maint:
        recs.append(('danger', 'Mantenimiento de equipos atrasado',
            f'{len(overdue_maint)} equipo(s) tienen mantenimiento vencido. '
            'Programe el mantenimiento inmediatamente.'))

    yards_full = Yard.query.filter(Yard.status == 'full').all()
    yards_high_occ = [y for y in Yard.query.filter(Yard.status == 'active').all()
                     if y.capacity_tons > 0 and y.current_occupancy_tons / y.capacity_tons > 0.85]
    if yards_full or yards_high_occ:
        total = len(yards_full) + len(yards_high_occ)
        recs.append(('warning', 'Patio/Bodega con ocupacion alta',
            f'{total} zona(s) tienen ocupacion >85%. Considere redistribuir mercancia.'))

    active_accidents = Accident.query.filter(
        Accident.status.in_(['reported', 'investigating'])
    ).count()
    if active_accidents > 0:
        recs.append(('info', 'Accidentes pendientes de seguimiento',
            f'Hay {active_accidents} accidente(s) sin resolver. Verifique el seguimiento.'))

    pending_followups = AccidentFollowUp.query.filter(
        AccidentFollowUp.status == 'pending',
        AccidentFollowUp.followup_date <= today
    ).count()
    if pending_followups > 0:
        recs.append(('danger', 'Seguimientos de accidentes vencidos',
            f'{pending_followups} seguimiento(s) tienen fecha vencida. Atienda a la brevedad.'))

    expiring_docs = DocumentRecord.query.filter(
        DocumentRecord.expires_at <= today + timedelta(days=30),
        DocumentRecord.expires_at >= today,
        DocumentRecord.is_valid == True
    ).count()
    if expiring_docs > 0:
        recs.append(('warning', 'Documentos por vencer',
            f'{expiring_docs} documento(s) vencen en 30 dias o menos.'))

    inactive_trucks = Truck.query.filter(Truck.status == 'maintenance').count()
    if inactive_trucks > 0:
        recs.append(('info', 'Camiones en mantenimiento',
            f'{inactive_trucks} camion(es) estan en estado de mantenimiento.'))

    today_ships = Ship.query.filter(
        Ship.arrival_date == today,
        Ship.status == 'pending'
    ).count()
    if today_ships > 0:
        recs.append(('info', 'Llegadas de buques hoy',
            f'{today_ships} buque(s) tienen fecha de llegada hoy.'))

    if not recs:
        recs.append(('success', 'Todo en orden',
            'No se detectaron problemas ni recomendaciones pendientes en este momento.'))

    return recs

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            log_access('login', f'Login exitoso: {username}')
            flash('Bienvenido a PortuSense', 'success')
            return redirect(url_for('dashboard'))
        log_access('failed_login', f'Login fallido: {username}')
        flash('Usuario o contrasena incorrectos', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'operator')
        full_name = request.form.get('full_name', '')
        email = request.form.get('email', '')
        if User.query.filter_by(username=username).first():
            flash('El usuario ya existe', 'danger')
            return render_template('register.html')
        user = User(username=username, role=role, full_name=full_name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Cuenta creada exitosamente. Inicia sesion.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    log_access('logout', 'Sesion cerrada')
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    ships = Ship.query.all()
    total_ships = len(ships)
    pending_ships = Ship.query.filter_by(status='pending').count()
    in_progress_ships = Ship.query.filter_by(status='in_progress').count()
    completed_ships = Ship.query.filter_by(status='completed').count()
    recent_alerts = Alert.query.filter_by(is_read=False).order_by(Alert.created_at.desc()).limit(5).all()

    risk_data = []
    for ship in ships:
        alerts = analyze_risk(ship)
        risk_data.append({'ship': ship, 'risk': get_risk_level(alerts), 'alert_count': len(alerts)})
    risk_counts = {'alto': 0, 'medio': 0, 'bajo': 0}
    for item in risk_data:
        risk_counts[item['risk']] = risk_counts.get(item['risk'], 0) + 1

    total_trucks = Truck.query.count()
    available_trucks = Truck.query.filter_by(status='available').count()
    transit_trucks = Truck.query.filter_by(status='in_transit').count()
    total_drivers = Driver.query.count()
    active_drivers = Driver.query.filter_by(status='active').count()
    total_yards = Yard.query.count()
    total_equipment = Equipment.query.count()
    active_equipment = Equipment.query.filter_by(status='active').count()
    total_personnel = Personnel.query.count()
    active_personnel = Personnel.query.filter_by(status='active').count()
    open_accidents = Accident.query.filter(Accident.status.in_(['reported', 'investigating'])).count()
    critical_accidents = Accident.query.filter_by(severity='critical', status='reported').count()
    pending_docs = DocumentRecord.query.filter_by(is_valid=True).filter(
        DocumentRecord.expires_at <= date.today() + timedelta(days=30)
    ).count()
    total_cargo = Cargo.query.count()
    total_weight = db.session.query(db.func.sum(Cargo.weight)).scalar() or 0

    recommendations = generate_recommendations()

    return render_template('dashboard.html',
        total_ships=total_ships, pending_ships=pending_ships,
        in_progress_ships=in_progress_ships, completed_ships=completed_ships,
        recent_alerts=recent_alerts, risk_data=risk_data,
        risk_alto=risk_counts['alto'], risk_medio=risk_counts['medio'], risk_bajo=risk_counts['bajo'],
        total_trucks=total_trucks, available_trucks=available_trucks, transit_trucks=transit_trucks,
        total_drivers=total_drivers, active_drivers=active_drivers,
        total_yards=total_yards, total_equipment=total_equipment, active_equipment=active_equipment,
        total_personnel=total_personnel, active_personnel=active_personnel,
        open_accidents=open_accidents, critical_accidents=critical_accidents,
        pending_docs=pending_docs, total_cargo=total_cargo, total_weight=total_weight,
        recommendations=recommendations)

@app.route('/ships', methods=['GET', 'POST'])
@login_required
def ships():
    if request.method == 'POST':
        name = request.form['name']
        arrival_date = datetime.strptime(request.form['arrival_date'], '%Y-%m-%d').date()
        eta = datetime.strptime(request.form['eta'], '%H:%M').time()
        cargo_type = request.form.get('cargo_type', '')
        status = request.form.get('status', 'pending')
        ship = Ship(name=name, arrival_date=arrival_date, eta=eta,
                    cargo_type=cargo_type, status=status, created_by=current_user.id)
        db.session.add(ship)
        db.session.commit()
        flash('Buque registrado exitosamente', 'success')
        return redirect(url_for('ships'))
    all_ships = Ship.query.order_by(Ship.created_at.desc()).all()
    return render_template('ships.html', ships=all_ships)

@app.route('/ships/edit/<int:ship_id>', methods=['GET', 'POST'])
@login_required
def edit_ship(ship_id):
    ship = Ship.query.get_or_404(ship_id)
    if request.method == 'POST':
        ship.name = request.form['name']
        ship.arrival_date = datetime.strptime(request.form['arrival_date'], '%Y-%m-%d').date()
        ship.eta = datetime.strptime(request.form['eta'], '%H:%M').time()
        ship.cargo_type = request.form.get('cargo_type', '')
        ship.status = request.form.get('status', 'pending')
        db.session.commit()
        flash('Buque actualizado', 'success')
        return redirect(url_for('ships'))
    return render_template('ships.html', ships=Ship.query.order_by(Ship.created_at.desc()).all(), edit_ship=ship)

@app.route('/ships/delete/<int:ship_id>')
@login_required
def delete_ship(ship_id):
    ship = Ship.query.get_or_404(ship_id)
    db.session.delete(ship)
    db.session.commit()
    flash('Buque eliminado', 'success')
    return redirect(url_for('ships'))

@app.route('/cargo', methods=['GET', 'POST'])
@login_required
def cargo():
    if request.method == 'POST':
        ship_id = int(request.form['ship_id'])
        cargo_type = request.form['cargo_type']
        quantity = int(request.form['quantity'])
        weight = float(request.form['weight'])
        location = request.form.get('location', '')
        destination = request.form.get('destination', '')
        item = Cargo(ship_id=ship_id, cargo_type=cargo_type, quantity=quantity,
                     weight=weight, location=location, destination=destination)
        db.session.add(item)
        db.session.commit()
        trace = CargoTrace(cargo_id=item.id, from_location='Buque', to_location=location or 'Patio general',
                          moved_by=current_user.username, notes='Carga inicial registrada')
        db.session.add(trace)
        db.session.commit()
        flash('Mercancia registrada', 'success')
        return redirect(url_for('cargo'))
    all_cargo = Cargo.query.order_by(Cargo.created_at.desc()).all()
    ships = Ship.query.all()
    return render_template('cargo.html', cargo_items=all_cargo, ships=ships)

@app.route('/cargo/delete/<int:cargo_id>')
@login_required
def delete_cargo(cargo_id):
    item = Cargo.query.get_or_404(cargo_id)
    db.session.delete(item)
    db.session.commit()
    flash('Mercancia eliminada', 'success')
    return redirect(url_for('cargo'))

@app.route('/alerts')
@login_required
def alerts():
    all_alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    ships = Ship.query.all()
    return render_template('alerts.html', alerts_list=all_alerts, ships=ships)

@app.route('/alerts/generate', methods=['POST'])
@login_required
def generate_alerts():
    ships = Ship.query.all()
    new_alerts = 0
    for ship in ships:
        existing = Alert.query.filter_by(ship_id=ship.id).filter(
            Alert.created_at >= datetime.combine(date.today(), datetime.min.time())
        ).count()
        if existing > 0:
            continue
        risk_alerts = analyze_risk(ship)
        for alert_type, severity, message in risk_alerts:
            alert = Alert(ship_id=ship.id, alert_type=alert_type,
                         severity=severity, message=message)
            db.session.add(alert)
            new_alerts += 1
    db.session.commit()
    flash(f'Se generaron {new_alerts} nuevas alertas', 'info')
    return redirect(url_for('alerts'))

@app.route('/alerts/read/<int:alert_id>')
@login_required
def mark_alert_read(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_read = True
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/trucks', methods=['GET', 'POST'])
@login_required
def trucks():
    if request.method == 'POST':
        plate = request.form['plate_number']
        if Truck.query.filter_by(plate_number=plate).first():
            flash('Ya existe un camion con esa placa', 'danger')
            return redirect(url_for('trucks'))
        truck = Truck(
            plate_number=plate,
            truck_type=request.form['truck_type'],
            capacity_tons=float(request.form['capacity_tons']),
            status=request.form.get('status', 'available'),
            driver_id=int(request.form['driver_id']) if request.form.get('driver_id') else None
        )
        db.session.add(truck)
        db.session.commit()
        flash('Camion registrado', 'success')
        return redirect(url_for('trucks'))
    all_trucks = Truck.query.order_by(Truck.created_at.desc()).all()
    drivers = Driver.query.filter_by(status='active').all()
    return render_template('trucks.html', trucks=all_trucks, drivers=drivers)

@app.route('/trucks/edit/<int:truck_id>', methods=['GET', 'POST'])
@login_required
def edit_truck(truck_id):
    truck = Truck.query.get_or_404(truck_id)
    if request.method == 'POST':
        truck.plate_number = request.form['plate_number']
        truck.truck_type = request.form['truck_type']
        truck.capacity_tons = float(request.form['capacity_tons'])
        truck.status = request.form.get('status', 'available')
        truck.driver_id = int(request.form['driver_id']) if request.form.get('driver_id') else None
        db.session.commit()
        flash('Camion actualizado', 'success')
        return redirect(url_for('trucks'))
    drivers = Driver.query.filter_by(status='active').all()
    all_trucks = Truck.query.order_by(Truck.created_at.desc()).all()
    return render_template('trucks.html', trucks=all_trucks, drivers=drivers, edit_truck=truck)

@app.route('/trucks/delete/<int:truck_id>')
@login_required
def delete_truck(truck_id):
    truck = Truck.query.get_or_404(truck_id)
    db.session.delete(truck)
    db.session.commit()
    flash('Camion eliminado', 'success')
    return redirect(url_for('trucks'))

@app.route('/drivers', methods=['GET', 'POST'])
@login_required
def drivers():
    if request.method == 'POST':
        lic = request.form['license_number']
        if Driver.query.filter_by(license_number=lic).first():
            flash('Ya existe un conductor con esa licencia', 'danger')
            return redirect(url_for('drivers'))
        driver = Driver(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            license_number=lic,
            license_expiry=datetime.strptime(request.form['license_expiry'], '%Y-%m-%d').date() if request.form.get('license_expiry') else None,
            phone=request.form.get('phone', ''),
            status=request.form.get('status', 'active')
        )
        db.session.add(driver)
        db.session.commit()
        flash('Conductor registrado', 'success')
        return redirect(url_for('drivers'))
    all_drivers = Driver.query.order_by(Driver.created_at.desc()).all()
    return render_template('drivers.html', drivers=all_drivers)

@app.route('/drivers/edit/<int:driver_id>', methods=['GET', 'POST'])
@login_required
def edit_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    if request.method == 'POST':
        driver.first_name = request.form['first_name']
        driver.last_name = request.form['last_name']
        driver.license_number = request.form['license_number']
        driver.license_expiry = datetime.strptime(request.form['license_expiry'], '%Y-%m-%d').date() if request.form.get('license_expiry') else None
        driver.phone = request.form.get('phone', '')
        driver.status = request.form.get('status', 'active')
        db.session.commit()
        flash('Conductor actualizado', 'success')
        return redirect(url_for('drivers'))
    all_drivers = Driver.query.order_by(Driver.created_at.desc()).all()
    return render_template('drivers.html', drivers=all_drivers, edit_driver=driver)

@app.route('/drivers/delete/<int:driver_id>')
@login_required
def delete_driver(driver_id):
    driver = Driver.query.get_or_404(driver_id)
    db.session.delete(driver)
    db.session.commit()
    flash('Conductor eliminado', 'success')
    return redirect(url_for('drivers'))

@app.route('/yards', methods=['GET', 'POST'])
@login_required
def yards():
    if request.method == 'POST':
        yard = Yard(
            name=request.form['name'],
            yard_type=request.form.get('yard_type', 'yard'),
            capacity_tons=float(request.form['capacity_tons']),
            status=request.form.get('status', 'active'),
            location=request.form.get('location', '')
        )
        db.session.add(yard)
        db.session.flush()
        prefix = 'P' if yard.yard_type == 'yard' else 'B'
        for i in range(30):
            db.session.add(YardSlot(yard_id=yard.id, code=f'{prefix}{yard.id}-{i+1:02d}', status='empty'))
        db.session.commit()
        flash('Patio/Bodega registrado con 30 puestos', 'success')
        return redirect(url_for('yards'))
    all_yards = Yard.query.order_by(Yard.created_at.desc()).all()
    active_id = request.args.get('yard', type=int)
    if not active_id and all_yards:
        active_id = all_yards[0].id
    active_yard = Yard.query.get(active_id) if active_id else None
    tab = request.args.get('tab', 'grid')
    return render_template('yards.html', yards=all_yards, active_yard=active_yard, tab=tab)

@app.route('/yards/edit/<int:yard_id>', methods=['GET', 'POST'])
@login_required
def edit_yard(yard_id):
    yard = Yard.query.get_or_404(yard_id)
    if request.method == 'POST':
        yard.name = request.form['name']
        yard.yard_type = request.form.get('yard_type', 'yard')
        yard.capacity_tons = float(request.form['capacity_tons'])
        yard.current_occupancy_tons = float(request.form.get('current_occupancy_tons', 0))
        yard.status = request.form.get('status', 'active')
        yard.location = request.form.get('location', '')
        if yard.capacity_tons > 0 and yard.current_occupancy_tons >= yard.capacity_tons:
            yard.status = 'full'
        elif yard.status == 'full' and yard.current_occupancy_tons < yard.capacity_tons:
            yard.status = 'active'
        db.session.commit()
        flash('Patio/Bodega actualizado', 'success')
        return redirect(url_for('yards'))
    all_yards = Yard.query.order_by(Yard.created_at.desc()).all()
    return render_template('yards.html', yards=all_yards, edit_yard=yard)

@app.route('/yards/delete/<int:yard_id>')
@login_required
def delete_yard(yard_id):
    yard = Yard.query.get_or_404(yard_id)
    db.session.delete(yard)
    db.session.commit()
    flash('Patio/Bodega eliminado', 'success')
    return redirect(url_for('yards', tab='gestion'))

@app.route('/yards/<int:yard_id>/slots/init', methods=['POST'])
@login_required
def init_yard_slots(yard_id):
    yard = Yard.query.get_or_404(yard_id)
    if yard.slots:
        flash('Este patio ya tiene puestos generados', 'info')
        return redirect(url_for('yards', yard=yard.id))
    prefix = 'P' if yard.yard_type == 'yard' else 'B'
    for i in range(30):
        db.session.add(YardSlot(yard_id=yard.id, code=f'{prefix}{yard.id}-{i+1:02d}', status='empty'))
    db.session.commit()
    flash(f'30 puestos generados para {yard.name}', 'success')
    return redirect(url_for('yards', yard=yard.id))

@app.route('/api/yards/slots/<int:slot_id>/assign', methods=['POST'])
@login_required
def assign_slot(slot_id):
    slot = YardSlot.query.get_or_404(slot_id)
    if slot.status != 'empty':
        return jsonify({'ok': False, 'msg': 'El puesto no esta disponible'}), 400
    data = request.get_json(silent=True) or {}
    slot.cargo_name = (data.get('cargo_name') or request.form.get('cargo_name') or 'Materia prima sin nombre').strip()
    slot.internal_code = (data.get('internal_code') or request.form.get('internal_code') or 'MP-0000').strip()
    slot.onu_number = (data.get('onu_number') or request.form.get('onu_number') or '').strip()
    slot.weight = (data.get('weight') or request.form.get('weight') or '').strip()
    slot.quantity = (data.get('quantity') or request.form.get('quantity') or '').strip()
    slot.status = 'full'
    yard = slot.yard
    yard.current_occupancy_tons = round(yard.current_occupancy_tons + 1.0, 1)
    if yard.capacity_tons > 0 and yard.current_occupancy_tons >= yard.capacity_tons:
        yard.status = 'full'
    db.session.commit()
    log_access('assign_slot', f'{slot.code} <- {slot.internal_code}')
    return jsonify({'ok': True, 'slot': slot.code})

@app.route('/api/yards/slots/<int:slot_id>/release', methods=['POST'])
@login_required
def release_slot(slot_id):
    slot = YardSlot.query.get_or_404(slot_id)
    slot.status = 'empty'
    slot.cargo_name = None
    slot.internal_code = None
    slot.onu_number = None
    slot.weight = None
    slot.quantity = None
    yard = slot.yard
    if yard.current_occupancy_tons > 0:
        yard.current_occupancy_tons = round(max(0, yard.current_occupancy_tons - 1.0), 1)
    if yard.status == 'full' and yard.capacity_tons > 0 and yard.current_occupancy_tons < yard.capacity_tons:
        yard.status = 'active'
    db.session.commit()
    log_access('release_slot', slot.code)
    return jsonify({'ok': True})

@app.route('/api/yards/slots/scan')
@login_required
def scan_slot():
    code = (request.args.get('code') or '').strip()
    if not code:
        return jsonify({'ok': False, 'msg': 'Codigo vacio'}), 400
    slot = YardSlot.query.filter(db.func.lower(YardSlot.internal_code) == code.lower()).first()
    if not slot:
        slot = YardSlot.query.filter(db.func.lower(YardSlot.code) == code.lower()).first()
    if not slot:
        return jsonify({'ok': False, 'msg': f'No se encontro ningun puesto con el codigo "{code}"'}), 404
    return jsonify({'ok': True, 'yard_id': slot.yard_id, 'slot_id': slot.id, 'slot_code': slot.code})

@app.route('/equipment', methods=['GET', 'POST'])
@login_required
def equipment():
    if request.method == 'POST':
        equip = Equipment(
            name=request.form['name'],
            equipment_type=request.form['equipment_type'],
            status=request.form.get('status', 'active'),
            location=request.form.get('location', ''),
            last_maintenance=datetime.strptime(request.form['last_maintenance'], '%Y-%m-%d').date() if request.form.get('last_maintenance') else None,
            next_maintenance=datetime.strptime(request.form['next_maintenance'], '%Y-%m-%d').date() if request.form.get('next_maintenance') else None
        )
        db.session.add(equip)
        db.session.commit()
        flash('Equipo registrado', 'success')
        return redirect(url_for('equipment'))
    all_equipment = Equipment.query.order_by(Equipment.created_at.desc()).all()
    return render_template('equipment.html', equipment=all_equipment)

@app.route('/equipment/edit/<int:equip_id>', methods=['GET', 'POST'])
@login_required
def edit_equipment(equip_id):
    equip = Equipment.query.get_or_404(equip_id)
    if request.method == 'POST':
        equip.name = request.form['name']
        equip.equipment_type = request.form['equipment_type']
        equip.status = request.form.get('status', 'active')
        equip.location = request.form.get('location', '')
        equip.last_maintenance = datetime.strptime(request.form['last_maintenance'], '%Y-%m-%d').date() if request.form.get('last_maintenance') else None
        equip.next_maintenance = datetime.strptime(request.form['next_maintenance'], '%Y-%m-%d').date() if request.form.get('next_maintenance') else None
        db.session.commit()
        flash('Equipo actualizado', 'success')
        return redirect(url_for('equipment'))
    all_equipment = Equipment.query.order_by(Equipment.created_at.desc()).all()
    return render_template('equipment.html', equipment=all_equipment, edit_equipment=equip)

@app.route('/equipment/delete/<int:equip_id>')
@login_required
def delete_equipment(equip_id):
    equip = Equipment.query.get_or_404(equip_id)
    db.session.delete(equip)
    db.session.commit()
    flash('Equipo eliminado', 'success')
    return redirect(url_for('equipment'))

@app.route('/personnel', methods=['GET', 'POST'])
@login_required
def personnel():
    if request.method == 'POST':
        p = Personnel(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            position=request.form['position'],
            department=request.form.get('department', ''),
            phone=request.form.get('phone', ''),
            email=request.form.get('email', ''),
            status=request.form.get('status', 'active'),
            hire_date=datetime.strptime(request.form['hire_date'], '%Y-%m-%d').date() if request.form.get('hire_date') else None
        )
        db.session.add(p)
        db.session.commit()
        flash('Personal registrado', 'success')
        return redirect(url_for('personnel'))
    all_personnel = Personnel.query.order_by(Personnel.created_at.desc()).all()
    return render_template('personnel.html', personnel=all_personnel)

@app.route('/personnel/edit/<int:person_id>', methods=['GET', 'POST'])
@login_required
def edit_personnel(person_id):
    p = Personnel.query.get_or_404(person_id)
    if request.method == 'POST':
        p.first_name = request.form['first_name']
        p.last_name = request.form['last_name']
        p.position = request.form['position']
        p.department = request.form.get('department', '')
        p.phone = request.form.get('phone', '')
        p.email = request.form.get('email', '')
        p.status = request.form.get('status', 'active')
        db.session.commit()
        flash('Personal actualizado', 'success')
        return redirect(url_for('personnel'))
    all_personnel = Personnel.query.order_by(Personnel.created_at.desc()).all()
    return render_template('personnel.html', personnel=all_personnel, edit_person=p)

@app.route('/personnel/delete/<int:person_id>')
@login_required
def delete_personnel(person_id):
    p = Personnel.query.get_or_404(person_id)
    db.session.delete(p)
    db.session.commit()
    flash('Personal eliminado', 'success')
    return redirect(url_for('personnel'))

@app.route('/documents', methods=['GET', 'POST'])
@login_required
def documents():
    if request.method == 'POST':
        doc = DocumentRecord(
            doc_type=request.form['doc_type'],
            title=request.form['title'],
            ship_id=int(request.form['ship_id']) if request.form.get('ship_id') else None,
            personnel_id=int(request.form['personnel_id']) if request.form.get('personnel_id') else None,
            truck_id=int(request.form['truck_id']) if request.form.get('truck_id') else None,
            expires_at=datetime.strptime(request.form['expires_at'], '%Y-%m-%d').date() if request.form.get('expires_at') else None,
            is_valid=request.form.get('is_valid') == 'on',
            file_reference=request.form.get('file_reference', ''),
            notes=request.form.get('notes', '')
        )
        db.session.add(doc)
        db.session.commit()
        flash('Documento registrado', 'success')
        return redirect(url_for('documents'))
    all_docs = DocumentRecord.query.order_by(DocumentRecord.created_at.desc()).all()
    ships = Ship.query.all()
    personnel_list = Personnel.query.all()
    truck_list = Truck.query.all()
    return render_template('documents.html', documents=all_docs, ships=ships,
                          personnel_list=personnel_list, truck_list=truck_list)

@app.route('/documents/delete/<int:doc_id>')
@login_required
def delete_document(doc_id):
    doc = DocumentRecord.query.get_or_404(doc_id)
    db.session.delete(doc)
    db.session.commit()
    flash('Documento eliminado', 'success')
    return redirect(url_for('documents'))

@app.route('/documents/toggle/<int:doc_id>')
@login_required
def toggle_document(doc_id):
    doc = DocumentRecord.query.get_or_404(doc_id)
    doc.is_valid = not doc.is_valid
    db.session.commit()
    return jsonify({'status': 'ok', 'is_valid': doc.is_valid})

@app.route('/accidents', methods=['GET', 'POST'])
@login_required
def accidents():
    if request.method == 'POST':
        accident = Accident(
            title=request.form['title'],
            description=request.form['description'],
            severity=request.form.get('severity', 'minor'),
            location=request.form.get('location', ''),
            ship_id=int(request.form['ship_id']) if request.form.get('ship_id') else None,
            truck_id=int(request.form['truck_id']) if request.form.get('truck_id') else None,
            personnel_id=int(request.form['personnel_id']) if request.form.get('personnel_id') else None,
            accident_date=datetime.strptime(request.form['accident_date'], '%Y-%m-%dT%H:%M'),
            status=request.form.get('status', 'reported'),
            injuries_count=int(request.form.get('injuries_count', 0)),
            created_by=current_user.id
        )
        db.session.add(accident)
        db.session.commit()

        if accident.severity in ('severe', 'critical'):
            emergency = Alert(ship_id=accident.ship_id,
                            alert_type='emergency',
                            severity='high',
                            message=f'EMERGENCIA: {accident.title} - Severidad: {accident.severity}')
            db.session.add(emergency)
            db.session.commit()

        flash('Accidente registrado', 'success')
        return redirect(url_for('accidents'))
    all_accidents = Accident.query.order_by(Accident.accident_date.desc()).all()
    ships = Ship.query.all()
    trucks_list = Truck.query.all()
    personnel_list = Personnel.query.all()
    return render_template('accidents.html', accidents=all_accidents, ships=ships,
                          trucks_list=trucks_list, personnel_list=personnel_list)

@app.route('/accidents/edit/<int:accident_id>', methods=['GET', 'POST'])
@login_required
def edit_accident(accident_id):
    accident = Accident.query.get_or_404(accident_id)
    if request.method == 'POST':
        accident.title = request.form['title']
        accident.description = request.form['description']
        accident.severity = request.form.get('severity', 'minor')
        accident.location = request.form.get('location', '')
        accident.status = request.form.get('status', 'reported')
        accident.injuries_count = int(request.form.get('injuries_count', 0))
        db.session.commit()
        flash('Accidente actualizado', 'success')
        return redirect(url_for('accidents'))
    ships = Ship.query.all()
    trucks_list = Truck.query.all()
    personnel_list = Personnel.query.all()
    all_accidents = Accident.query.order_by(Accident.accident_date.desc()).all()
    return render_template('accidents.html', accidents=all_accidents, ships=ships,
                          trucks_list=trucks_list, personnel_list=personnel_list, edit_accident=accident)

@app.route('/accidents/<int:accident_id>')
@login_required
def view_accident(accident_id):
    accident = Accident.query.get_or_404(accident_id)
    return render_template('accident_detail.html', accident=accident)

@app.route('/accidents/followup/<int:accident_id>', methods=['POST'])
@login_required
def add_followup(accident_id):
    accident = Accident.query.get_or_404(accident_id)
    followup = AccidentFollowUp(
        accident_id=accident_id,
        description=request.form['description'],
        action_taken=request.form.get('action_taken', ''),
        followup_date=datetime.strptime(request.form['followup_date'], '%Y-%m-%d').date(),
        status=request.form.get('status', 'pending'),
        created_by=current_user.id
    )
    db.session.add(followup)
    db.session.commit()
    flash('Seguimiento agregado', 'success')
    return redirect(url_for('view_accident', accident_id=accident_id))

@app.route('/accidents/followup/update/<int:followup_id>', methods=['POST'])
@login_required
def update_followup(followup_id):
    followup = AccidentFollowUp.query.get_or_404(followup_id)
    followup.status = request.form.get('status', followup.status)
    followup.action_taken = request.form.get('action_taken', followup.action_taken)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/trace', methods=['GET', 'POST'])
@login_required
def trace():
    if request.method == 'POST':
        cargo_id = int(request.form['cargo_id'])
        to_location = request.form['to_location']
        moved_by = request.form.get('moved_by', current_user.username)
        notes = request.form.get('notes', '')
        cargo = Cargo.query.get_or_404(cargo_id)
        old_location = cargo.location or 'Buque'
        trace_entry = CargoTrace(cargo_id=cargo_id, from_location=old_location,
                                to_location=to_location, moved_by=moved_by, notes=notes)
        db.session.add(trace_entry)
        cargo.location = to_location
        db.session.commit()
        flash('Mercancia movida - trazabilidad registrada', 'success')
        return redirect(url_for('trace', q=cargo_id))
    q = (request.args.get('q') or '').strip()
    all_cargo = Cargo.query.order_by(Cargo.created_at.desc()).all()
    tracked = None
    tracked_traces = []
    tracked_docs = []
    search_results = []
    if q:
        if q.isdigit():
            tracked = Cargo.query.get(int(q))
        if not tracked:
            search_results = Cargo.query.join(Ship).filter(
                db.or_(
                    db.func.lower(Cargo.cargo_type).contains(q.lower()),
                    db.func.lower(Ship.name).contains(q.lower()),
                    db.func.lower(db.cast(Cargo.id, db.String)).contains(q),
                    db.func.lower(Cargo.destination).contains(q.lower())
                )
            ).limit(8).all()
            if len(search_results) == 1:
                tracked = search_results[0]
        if tracked:
            tracked_traces = CargoTrace.query.filter_by(cargo_id=tracked.id).order_by(CargoTrace.moved_at.desc()).all()
            tracked_docs = DocumentRecord.query.filter(
                db.or_(DocumentRecord.ship_id == tracked.ship_id,
                       DocumentRecord.truck_id == Truck.current_cargo_id)
            ).limit(6).all()
            search_results = []
    hazmat_types = ('granel liquido', 'petroleo', 'quimicos', 'inflamable')
    is_hazmat = tracked and any(h in (tracked.cargo_type or '').lower() for h in hazmat_types)
    return render_template('trace.html', cargo_items=all_cargo, traces=CargoTrace.query.order_by(CargoTrace.moved_at.desc()).all(),
                           q=q, tracked=tracked, tracked_traces=tracked_traces,
                           tracked_docs=tracked_docs, search_results=search_results,
                           is_hazmat=is_hazmat)

@app.route('/rastreo', methods=['GET', 'POST'])
@login_required
def rastreo():
    if request.method == 'POST':
        return submit_route_event()
    trucks_on_route = Truck.query.filter(Truck.status == 'in_transit').all()
    events = RouteEvent.query.order_by(RouteEvent.created_at.desc()).limit(20).all()
    deliveries = []
    for t in trucks_on_route:
        cargo = Cargo.query.get(t.current_cargo_id) if t.current_cargo_id else None
        last_ev = RouteEvent.query.filter_by(truck_id=t.id).order_by(RouteEvent.created_at.desc()).first()
        state = 'ok'
        if last_ev and last_ev.severity == 'bad':
            state = 'incident'
        elif last_ev and last_ev.severity == 'warn':
            state = 'delay'
        deliveries.append({'truck': t, 'cargo': cargo, 'state': state, 'last_event': last_ev})
    my_events = RouteEvent.query.order_by(RouteEvent.created_at.desc()).limit(10).all()
    return render_template('rastreo.html', deliveries=deliveries, events=events,
                           my_events=my_events, trucks=Truck.query.order_by(Truck.plate_number).all())

def submit_route_event():
    truck_id = request.form.get('truck_id', type=int)
    tipo = request.form.get('event_type', 'ubicacion')
    truck = Truck.query.get(truck_id) if truck_id else None
    driver_name = request.form.get('driver_name', '')
    if truck and truck.driver and not driver_name:
        driver_name = f'{truck.driver.first_name} {truck.driver.last_name}'
    titulo, detalle, severidad, lat, lng = '', '', 'ok', None, None

    if tipo == 'ubicacion':
        loc = request.form.get('location_text', '').strip() or 'Sin especificar'
        titulo = 'Actualizacion de ubicacion'
        detalle = loc
        lat = request.form.get('lat', type=float)
        lng = request.form.get('lng', type=float)
        if truck:
            if lat is not None: truck.lat = lat
            if lng is not None: truck.lng = lng
            truck.last_location = loc
            truck.last_report_at = datetime.utcnow()
    elif tipo == 'peaje':
        peaje = request.form.get('peaje_name', '').strip() or 'Peaje sin nombre'
        hora = request.form.get('peaje_time', '').strip()
        titulo = 'Paso por peaje'
        detalle = peaje + (f' · {hora}' if hora else '')
    elif tipo == 'control':
        motivo = request.form.get('control_reason', 'Control rutinario')
        autoridad = request.form.get('authority', '').strip() or 'No especificada'
        resultado = request.form.get('result', 'curso')
        notas = request.form.get('notes', '').strip()
        res_txt = {'curso': 'en curso', 'ok': 'liberado sin novedad',
                   'multa': 'con comparendo/multa', 'apoyo': 'requiere apoyo'}.get(resultado, resultado)
        titulo = f'Control policial · {motivo}'
        detalle = f'Autoridad: {autoridad} · Resultado: {res_txt}' + (f' · {notas}' if notas else '')
        severidad = 'bad' if resultado == 'apoyo' else 'warn' if resultado == 'multa' else 'ok'
    elif tipo == 'incidente':
        inc_tipo = request.form.get('incident_type', 'Retraso general')
        desc = request.form.get('incident_desc', '').strip()
        asistencia = request.form.get('assistance') in ('on', '1', 'true', 'True')
        titulo = f'Incidente · {inc_tipo}'
        detalle = desc + (' · Requiere asistencia inmediata' if asistencia else '')
        severidad = 'bad' if (asistencia or inc_tipo == 'Accidente') else 'warn'

    ev = RouteEvent(truck_id=truck_id, driver_name=driver_name, event_type=tipo,
                    title=titulo, detail=detalle, severity=severidad,
                    lat=lat, lng=lng, reported_by=current_user.id)
    db.session.add(ev)
    if severidad == 'bad':
        db.session.add(Alert(alert_type='emergency', severity='high',
                             message=f"Emergencia en ruta: {titulo} — {detalle}" +
                                     (f" ({truck.plate_number})" if truck else '')))
    db.session.commit()
    log_access('route_report', f'{titulo} [{tipo}]')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True, 'title': titulo, 'severity': severidad})
    flash(f'Reporte registrado: {titulo}', 'success')
    return redirect(url_for('rastreo'))

@app.route('/rastreo/import-csv', methods=['POST'])
@login_required
def import_route_csv():
    f = request.files.get('csv_file')
    if not f or not f.filename.lower().endswith('.csv'):
        flash('Selecciona un archivo CSV valido', 'danger')
        return redirect(url_for('rastreo'))
    raw = f.read().decode('utf-8-sig', errors='replace')
    lines = [l for l in raw.splitlines() if l.strip()]
    if len(lines) < 2:
        flash('El archivo no tiene filas de datos', 'danger')
        return redirect(url_for('rastreo'))
    def parse_line(line):
        out, cur, q = [], '', False
        i = 0
        while i < len(line):
            ch = line[i]
            if q:
                if ch == '"':
                    if i + 1 < len(line) and line[i+1] == '"':
                        cur += '"'; i += 1
                    else:
                        q = False
                else:
                    cur += ch
            else:
                if ch == '"':
                    q = True
                elif ch == ',':
                    out.append(cur); cur = ''
                else:
                    cur += ch
            i += 1
        out.append(cur)
        return [s.strip() for s in out]
    headers = [h.lower() for h in parse_line(lines[0])]
    def col(*frags):
        for i, h in enumerate(headers):
            if any(fr in h for fr in frags):
                return i
        return -1
    i_veh, i_tipo = col('vehículo', 'vehiculo'), col('tipo de evento')
    i_ubic, i_peaje, i_hpeaje = col('ubicación', 'ubicacion'), col('peaje'), col('hora de paso')
    i_motivo, i_aut, i_res = col('motivo'), col('autoridad'), col('resultado')
    i_notas, i_tinc, i_desc, i_asist = col('nota'), col('tipo de incidente'), col('descripción', 'descripcion'), col('asistencia')
    nuevos, criticos = 0, 0
    for row in lines[1:]:
        cols = parse_line(row)
        tipo_raw = cols[i_tipo] if i_tipo >= 0 and i_tipo < len(cols) else ''
        veh = cols[i_veh] if i_veh >= 0 and i_veh < len(cols) else ''
        truck = Truck.query.filter_by(plate_number=veh).first() if veh else None
        titulo, detalle, sev = '', '', 'ok'
        if 'ubicaci' in tipo_raw.lower():
            titulo = 'Actualizacion de ubicacion'
            detalle = cols[i_ubic] if i_ubic >= 0 and i_ubic < len(cols) else '—'
            if truck:
                truck.last_location = detalle
                truck.last_report_at = datetime.utcnow()
        elif 'peaje' in tipo_raw.lower():
            titulo = 'Paso por peaje'
            p = cols[i_peaje] if i_peaje >= 0 and i_peaje < len(cols) else '—'
            h = cols[i_hpeaje] if i_hpeaje >= 0 and i_hpeaje < len(cols) else ''
            detalle = p + (f' · {h}' if h else '')
        elif 'control' in tipo_raw.lower():
            res = cols[i_res] if i_res >= 0 and i_res < len(cols) else ''
            motivo = cols[i_motivo] if i_motivo >= 0 and i_motivo < len(cols) else '—'
            aut = cols[i_aut] if i_aut >= 0 and i_aut < len(cols) else '—'
            notas = cols[i_notas] if i_notas >= 0 and i_notas < len(cols) else ''
            titulo = f'Control policial · {motivo}'
            detalle = f'Autoridad: {aut} · Resultado: {res or "—"}' + (f' · {notas}' if notas else '')
            sev = 'bad' if 'apoyo' in res.lower() else 'warn' if ('multa' in res.lower() or 'comparendo' in res.lower()) else 'ok'
        elif 'incidente' in tipo_raw.lower():
            tinc = cols[i_tinc] if i_tinc >= 0 and i_tinc < len(cols) else '—'
            desc = cols[i_desc] if i_desc >= 0 and i_desc < len(cols) else ''
            asist = cols[i_asist] if i_asist >= 0 and i_asist < len(cols) else ''
            titulo = f'Incidente · {tinc}'
            detalle = desc + (' · Requiere asistencia inmediata' if asist[:1].lower() == 's' else '')
            sev = 'bad' if (asist[:1].lower() == 's' or 'accidente' in tinc.lower()) else 'warn'
        else:
            continue
        hora_txt = cols[0] if cols else ''
        if ' ' in hora_txt:
            hora_txt = hora_txt.split(' ')[1][:5]
        if detalle and hora_txt:
            detalle = f'{detalle} · {hora_txt}'
        db.session.add(RouteEvent(truck_id=truck.id if truck else None,
                                  driver_name=veh, event_type='importado',
                                  title=titulo, detail=detalle, severity=sev,
                                  reported_by=current_user.id))
        nuevos += 1
        if sev == 'bad':
            criticos += 1
    db.session.commit()
    log_access('import_csv', f'{nuevos} reportes importados')
    flash(f'Se importaron {nuevos} reporte(s)' + (f', {criticos} critico(s)' if criticos else '') + '.', 'success')
    return redirect(url_for('rastreo'))

@app.route('/api/trucks-geo')
@login_required
def trucks_geo():
    trucks = Truck.query.filter(Truck.lat.isnot(None), Truck.lng.isnot(None)).all()
    data = []
    for t in trucks:
        cargo = Cargo.query.get(t.current_cargo_id) if t.current_cargo_id else None
        last_ev = RouteEvent.query.filter_by(truck_id=t.id).order_by(RouteEvent.created_at.desc()).first()
        data.append({
            'id': t.id,
            'plate': t.plate_number,
            'type': t.truck_type,
            'status': t.status,
            'driver': f'{t.driver.first_name} {t.driver.last_name}' if t.driver else 'Sin asignar',
            'lat': t.lat, 'lng': t.lng,
            'last_location': t.last_location or '—',
            'destination': cargo.destination if cargo else '—',
            'cargo': cargo.cargo_type if cargo else None,
            'last_event': last_ev.title if last_ev else None,
            'severity': last_ev.severity if last_ev else 'ok',
            'updated': t.last_report_at.strftime('%H:%M') if t.last_report_at else None,
        })
    yards = Yard.query.filter(Yard.lat.isnot(None), Yard.lng.isnot(None)).all()
    yards_data = [{'id': y.id, 'name': y.name, 'type': y.yard_type,
                   'lat': y.lat, 'lng': y.lng, 'location': y.location or '',
                   'occupancy': y.current_occupancy_tons, 'capacity': y.capacity_tons}
                  for y in yards]
    ships = Ship.query.filter(Ship.status.in_(['pending', 'in_progress'])).all()
    ships_data = [{'id': s.id, 'name': s.name, 'status': s.status,
                   'lat': 19.0558 + (s.id % 5) * 0.004, 'lng': -104.3184 - (s.id % 4) * 0.005,
                   'eta': s.eta.strftime('%H:%M')} for s in ships[:8]]
    return jsonify({'trucks': data, 'yards': yards_data, 'ships': ships_data,
                    'port': {'lat': 19.0558, 'lng': -104.3184}})

@app.route('/api/route-events')
@login_required
def route_events_api():
    evs = RouteEvent.query.order_by(RouteEvent.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': e.id, 'truck': e.truck.plate_number if e.truck else (e.driver_name or '—'),
        'title': e.title, 'detail': e.detail, 'severity': e.severity,
        'type': e.event_type,
        'time': e.created_at.strftime('%H:%M'), 'date': e.created_at.strftime('%d/%m')
    } for e in evs])

@app.route('/recommendations')
@login_required
def recommendations():
    recs = generate_recommendations()
    return render_template('recommendations.html', recommendations=recs)

@app.route('/access-logs')
@admin_required
def access_logs():
    page = request.args.get('page', 1, type=int)
    logs = AccessLog.query.order_by(AccessLog.created_at.desc()).paginate(page=page, per_page=50)
    return render_template('access_logs.html', logs=logs)

@app.route('/reports')
@login_required
def reports():
    ships = Ship.query.all()
    total_ships = len(ships)
    pending = Ship.query.filter_by(status='pending').count()
    in_progress = Ship.query.filter_by(status='in_progress').count()
    completed = Ship.query.filter_by(status='completed').count()
    total_cargo = Cargo.query.count()
    total_weight = db.session.query(db.func.sum(Cargo.weight)).scalar() or 0
    high_alerts = Alert.query.filter_by(severity='high', is_read=False).count()
    medium_alerts = Alert.query.filter_by(severity='medium', is_read=False).count()
    low_alerts = Alert.query.filter_by(severity='low', is_read=False).count()
    total_trucks = Truck.query.count()
    total_drivers = Driver.query.count()
    total_personnel = Personnel.query.count()
    total_accidents = Accident.query.count()
    total_equipment = Equipment.query.count()
    total_yards = Yard.query.count()
    return render_template('reports.html',
        total_ships=total_ships, pending=pending,
        in_progress=in_progress, completed=completed,
        total_cargo=total_cargo, total_weight=total_weight,
        high_alerts=high_alerts, medium_alerts=medium_alerts,
        low_alerts=low_alerts, ships=ships,
        total_trucks=total_trucks, total_drivers=total_drivers,
        total_personnel=total_personnel, total_accidents=total_accidents,
        total_equipment=total_equipment, total_yards=total_yards)

@app.route('/api/dashboard-data')
@login_required
def dashboard_data():
    return jsonify({
        'pending': Ship.query.filter_by(status='pending').count(),
        'in_progress': Ship.query.filter_by(status='in_progress').count(),
        'completed': Ship.query.filter_by(status='completed').count(),
        'high_alerts': Alert.query.filter_by(severity='high', is_read=False).count(),
        'medium_alerts': Alert.query.filter_by(severity='medium', is_read=False).count(),
        'low_alerts': Alert.query.filter_by(severity='low', is_read=False).count(),
        'trucks_available': Truck.query.filter_by(status='available').count(),
        'trucks_transit': Truck.query.filter_by(status='in_transit').count(),
        'accidents_open': Accident.query.filter(Accident.status.in_(['reported', 'investigating'])).count(),
        'personnel_active': Personnel.query.filter_by(status='active').count(),
        'equipment_active': Equipment.query.filter_by(status='active').count()
    })

def excel_response(filename, sheet_name, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    for col in ws.columns:
        max_length = max((len(str(cell.value or '')) for cell in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = max_length + 2
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/reports/exportar/buques')
@login_required
def export_buques_excel():
    rows = []
    for ship in Ship.query.all():
        rows.append([
            ship.id, ship.name,
            ship.arrival_date.strftime('%d/%m/%Y'),
            ship.eta.strftime('%H:%M'),
            ship.cargo_type or '',
            ship.status,
            Cargo.query.filter_by(ship_id=ship.id).count()
        ])
    return excel_response('reporte_buques.xlsx', 'Buques',
        ['ID', 'Nombre', 'Fecha Llegada', 'ETA', 'Tipo de Carga', 'Estado', 'Cant. Mercancias'],
        rows)

@app.route('/reports/exportar/mercancias')
@login_required
def export_mercancias_excel():
    rows = []
    for cargo_item in Cargo.query.all():
        rows.append([
            cargo_item.id, cargo_item.ship.name, cargo_item.cargo_type,
            cargo_item.quantity, cargo_item.weight,
            cargo_item.location or '', cargo_item.destination or '', cargo_item.status
        ])
    return excel_response('reporte_mercancias.xlsx', 'Mercancias',
        ['ID', 'Buque', 'Tipo', 'Cantidad', 'Peso (t)', 'Ubicacion', 'Destino', 'Estado'],
        rows)

@app.route('/reports/exportar/alertas')
@login_required
def export_alertas_excel():
    rows = []
    for alert in Alert.query.order_by(Alert.created_at.desc()).all():
        rows.append([
            alert.id, alert.ship.name if alert.ship else 'N/A', alert.alert_type, alert.severity,
            alert.message, alert.created_at.strftime('%d/%m/%Y %H:%M'),
            'Si' if alert.is_read else 'No'
        ])
    return excel_response('reporte_alertas.xlsx', 'Alertas',
        ['ID', 'Buque', 'Tipo', 'Severidad', 'Mensaje', 'Fecha', 'Leida'],
        rows)

@app.route('/reports/exportar/operaciones')
@login_required
def export_operaciones_excel():
    rows = []
    for ship in Ship.query.all():
        ops = Operation.query.filter_by(ship_id=ship.id).all()
        if ops:
            for op in ops:
                start = op.start_time.strftime('%d/%m/%Y %H:%M') if op.start_time else ''
                end = op.end_time.strftime('%d/%m/%Y %H:%M') if op.end_time else ''
                rows.append([ship.name, ship.id, op.status, start, end, op.notes or ''])
        else:
            rows.append([ship.name, ship.id, ship.status, '', '', 'Sin operacion registrada'])
    return excel_response('reporte_operaciones.xlsx', 'Operaciones',
        ['Buque', 'ID Buque', 'Estado', 'Inicio', 'Fin', 'Notas'],
        rows)

@app.route('/reports/exportar/camiones')
@login_required
def export_camiones_excel():
    rows = []
    for t in Truck.query.all():
        rows.append([
            t.id, t.plate_number, t.truck_type, t.capacity_tons, t.status,
            t.driver.first_name + ' ' + t.driver.last_name if t.driver else 'Sin conductor'
        ])
    return excel_response('reporte_camiones.xlsx', 'Camiones',
        ['ID', 'Placa', 'Tipo', 'Capacidad (t)', 'Estado', 'Conductor'],
        rows)

@app.route('/reports/exportar/conductores')
@login_required
def export_conductores_excel():
    rows = []
    for d in Driver.query.all():
        rows.append([
            d.id, d.first_name + ' ' + d.last_name, d.license_number,
            d.license_expiry.strftime('%d/%m/%Y') if d.license_expiry else '',
            d.phone or '', d.status
        ])
    return excel_response('reporte_conductores.xlsx', 'Conductores',
        ['ID', 'Nombre', 'Licencia', 'Vence', 'Telefono', 'Estado'],
        rows)

@app.route('/reports/exportar/personal')
@login_required
def export_personal_excel():
    rows = []
    for p in Personnel.query.all():
        rows.append([
            p.id, p.first_name + ' ' + p.last_name, p.position, p.department or '',
            p.phone or '', p.email or '', p.status,
            p.hire_date.strftime('%d/%m/%Y') if p.hire_date else ''
        ])
    return excel_response('reporte_personal.xlsx', 'Personal',
        ['ID', 'Nombre', 'Cargo', 'Departamento', 'Telefono', 'Email', 'Estado', 'Fecha Ingreso'],
        rows)

@app.route('/reports/exportar/accidentes')
@login_required
def export_accidentes_excel():
    rows = []
    for a in Accident.query.all():
        rows.append([
            a.id, a.title, a.severity, a.status, a.location or '',
            a.accident_date.strftime('%d/%m/%Y %H:%M'),
            a.injuries_count,
            a.ship.name if a.ship else 'N/A',
            a.personnel.first_name + ' ' + a.personnel.last_name if a.personnel else 'N/A'
        ])
    return excel_response('reporte_accidentes.xlsx', 'Accidentes',
        ['ID', 'Titulo', 'Severidad', 'Estado', 'Ubicacion', 'Fecha', 'Heridos', 'Buque', 'Personal'],
        rows)

@app.route('/reports/exportar/equipos')
@login_required
def export_equipos_excel():
    rows = []
    for e in Equipment.query.all():
        rows.append([
            e.id, e.name, e.equipment_type, e.status, e.location or '',
            e.last_maintenance.strftime('%d/%m/%Y') if e.last_maintenance else '',
            e.next_maintenance.strftime('%d/%m/%Y') if e.next_maintenance else ''
        ])
    return excel_response('reporte_equipos.xlsx', 'Equipos',
        ['ID', 'Nombre', 'Tipo', 'Estado', 'Ubicacion', 'Ult. Mant.', 'Prox. Mant.'],
        rows)

@app.route('/reports/exportar/patios')
@login_required
def export_patios_excel():
    rows = []
    for y in Yard.query.all():
        occ_pct = (y.current_occupancy_tons / y.capacity_tons * 100) if y.capacity_tons > 0 else 0
        rows.append([
            y.id, y.name, y.yard_type, y.capacity_tons, y.current_occupancy_tons,
            f'{occ_pct:.1f}%', y.status, y.location or ''
        ])
    return excel_response('reporte_patios.xlsx', 'Patios y Bodegas',
        ['ID', 'Nombre', 'Tipo', 'Capacidad (t)', 'Ocupacion (t)', '% Ocupacion', 'Estado', 'Ubicacion'],
        rows)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
