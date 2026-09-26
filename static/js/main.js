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

const ROWS_PER_PAGE = 8;

document.querySelectorAll('table[data-paginate="true"]').forEach(table => {
    const tableId = table.id;
    const container = document.getElementById(tableId + '-pagination');
    const searchInput = document.querySelector(`.table-search[data-target="${tableId}"]`);
    let currentPage = 1;

    function visibleRows() {
        const q = searchInput ? searchInput.value.trim().toLowerCase() : '';
        return Array.from(table.querySelectorAll('tbody tr')).filter(row => {
            if (row.classList.contains('empty-row')) return false;
            return !q || row.textContent.toLowerCase().includes(q);
        });
    }

    function applyPagination() {
        const rows = visibleRows();
        const totalPages = Math.max(1, Math.ceil(rows.length / ROWS_PER_PAGE));
        if (currentPage > totalPages) {
            currentPage = totalPages;
        }
        const start = (currentPage - 1) * ROWS_PER_PAGE;
        rows.forEach((row, i) => {
            row.style.display = (i >= start && i < start + ROWS_PER_PAGE) ? '' : 'none';
        });
        const emptyRow = table.querySelector('tbody tr.empty-row');
        if (emptyRow) {
            emptyRow.style.display = rows.length ? 'none' : '';
        }
        renderControls(totalPages, rows.length);
    }

    function renderControls(totalPages, rowCount) {
        if (!container) return;
        container.innerHTML = '';
        const div = document.createElement('div');
        div.className = 'd-flex justify-content-between align-items-center mt-2 flex-wrap';
        div.innerHTML = `
            <small class="text-muted">${rowCount} registro(s) · pagina ${currentPage} de ${totalPages}</small>
            <div>
                <button class="btn btn-sm btn-outline-primary ${currentPage === 1 ? 'disabled' : ''}" data-page="prev">
                    <i class="bi bi-chevron-left"></i> Anterior
                </button>
                <button class="btn btn-sm btn-outline-primary ${currentPage === totalPages ? 'disabled' : ''}" data-page="next">
                    Siguiente <i class="bi bi-chevron-right"></i>
                </button>
            </div>`;
        div.querySelector('[data-page="prev"]').addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                applyPagination();
            }
        });
        div.querySelector('[data-page="next"]').addEventListener('click', () => {
            if (currentPage < totalPages) {
                currentPage++;
                applyPagination();
            }
        });
        container.appendChild(div);
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            currentPage = 1;
            applyPagination();
        });
    }

    applyPagination();
});
