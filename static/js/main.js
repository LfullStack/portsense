console.log('PortuSense - Sistema de Gestion Portuaria');

function refreshDashboard() {
    fetch('/api/dashboard-data')
        .then(response => response.json())
        .then(data => {
            document.getElementById('stat-pending').textContent = data.pending;
            document.getElementById('stat-progress').textContent = data.in_progress;
            document.getElementById('stat-completed').textContent = data.completed;
        })
        .catch(err => console.log('Error actualizando dashboard:', err));
}

setInterval(refreshDashboard, 30000);
