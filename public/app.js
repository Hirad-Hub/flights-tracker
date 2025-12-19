// State
let allFlights = [];
let lastChecked = '';
let currentSort = { key: 'price', order: 'asc' };

// DOM Elements
const searchInput = document.getElementById('departure-search');
const autocompleteList = document.getElementById('autocomplete-list');
const searchStatus = document.getElementById('search-status');
const resultsPanel = document.getElementById('results-panel');
const emptyState = document.getElementById('empty-state');
const tableBody = document.getElementById('flights-table-body');
const selectedDepartureSpan = document.getElementById('selected-departure');
const resultCountSpan = document.getElementById('result-count');
const lastCheckedSpan = document.getElementById('last-checked-time');
const quickLinks = document.querySelectorAll('.quick-link');

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    fetchData();
    setupEventListeners();
});

async function fetchData() {
    try {
        // Try requesting from local 'data' folder (relative to index.html) - Production
        let response = await fetch('data/flights.json');

        // If that fails, try moving up (Local dev serving project root)
        if (!response.ok) {
            response = await fetch('../data/flights.json');
        }

        if (!response.ok) throw new Error('Failed to load data');

        const data = await response.json();
        allFlights = data.flights;
        lastChecked = new Date(data.last_checked).toLocaleString();
        lastCheckedSpan.textContent = lastChecked;

        // Extract unique airports for autocomplete
        // Format: "City (Code)"
        const availableAirports = [...new Set(allFlights.map(f => f.departure_airport))];
        setupAutocomplete(availableAirports);

    } catch (error) {
        console.error('Error fetching data:', error);
        // Show mock data or error in UI?
        // For now, fail silently or show alert?
        // Let's use the error state in UI
        lastCheckedSpan.textContent = "Error loading data";
        lastCheckedSpan.classList.add("text-red-400");
    }
}

function setupEventListeners() {
    // Quick Links
    quickLinks.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const code = e.target.dataset.code;
            // Find full name from data
            const match = allFlights.find(f => f.departure_airport.includes(`(${code})`));
            if (match) {
                selectAirport(match.departure_airport);
            } else {
                // Determine name based on code map if not in data (fallback)
                const fallbackMap = {
                    'AMS': 'Amsterdam (AMS)', 'LHR': 'London (LHR)',
                    'CDG': 'Paris (CDG)', 'IST': 'Istanbul (IST)',
                    'MAD': 'Madrid (MAD)', 'RTM': 'Rotterdam (RTM)'
                };
                // Still try to filter even if exact match not found in initial find
                selectAirport(fallbackMap[code] || code);
            }
        });
    });

    // Sorting headers
    document.getElementById('sort-price').addEventListener('click', () => sortTable('price'));
    document.getElementById('sort-dest').addEventListener('click', () => sortTable('destination'));
    document.getElementById('sort-dur').addEventListener('click', () => sortTable('duration'));
    document.getElementById('sort-date').addEventListener('click', () => sortTable('dates'));
}

function setupAutocomplete(airports) {
    searchInput.addEventListener('input', (e) => {
        const val = e.target.value.toLowerCase();
        autocompleteList.innerHTML = '';
        if (!val) {
            autocompleteList.classList.add('hidden');
            searchStatus.classList.add('hidden');
            return;
        }

        const matches = airports.filter(a => a.toLowerCase().includes(val));

        if (matches.length > 0) {
            searchStatus.classList.add('hidden');
            autocompleteList.classList.remove('hidden');
            matches.forEach(airport => {
                const div = document.createElement('div');
                div.className = 'px-4 py-2 hover:bg-slate-700 cursor-pointer text-sm text-slate-200 transition-colors';
                div.textContent = airport;
                div.addEventListener('click', () => {
                    selectAirport(airport);
                });
                autocompleteList.appendChild(div);
            });
        } else {
            autocompleteList.classList.add('hidden');
            searchStatus.classList.remove('hidden');
            searchStatus.textContent = "No airport found";
        }
    });

    // Close autocomplete on outside click
    document.addEventListener('click', (e) => {
        if (e.target !== searchInput && e.target !== autocompleteList) {
            autocompleteList.classList.add('hidden');
        }
    });
}

function selectAirport(airportName) {
    searchInput.value = airportName;
    autocompleteList.classList.add('hidden');
    selectedDepartureSpan.textContent = airportName;

    // Filter flights
    // We match loosly or exact? Exact preferred.
    // Normalized check
    const filtered = allFlights.filter(f => f.departure_airport === airportName);

    // Show results
    if (filtered.length > 0) {
        emptyState.classList.add('hidden');
        resultsPanel.classList.remove('hidden');
        renderTable(filtered);
    } else {
        emptyState.classList.remove('hidden');
        emptyState.querySelector('p').textContent = `No flights found departing from ${airportName}.`;
        resultsPanel.classList.add('hidden');
    }
}

function renderTable(flights) {
    // Sort
    flights.sort((a, b) => {
        let valA = a[currentSort.key];
        let valB = b[currentSort.key];

        // Custom extraction for parsing
        if (currentSort.key === 'price') {
            valA = parsePrice(valA);
            valB = parsePrice(valB);
        } else if (currentSort.key === 'duration') {
            // Heuristic sort for duration string
            valA = parseDuration(valA);
            valB = parseDuration(valB);
        }

        if (valA < valB) return currentSort.order === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.order === 'asc' ? 1 : -1;
        return 0;
    });

    tableBody.innerHTML = '';

    flights.forEach(f => {
        const nights = calculateNights(f.dates);
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-700/30 transition-colors group border-b border-slate-700/30 last:border-0';
        tr.innerHTML = `
            <td class="px-6 py-4 font-medium text-white">${f.destination}</td>
            <td class="px-6 py-4 text-slate-400">${f.dates}</td>
            <td class="px-6 py-4 text-slate-400">
                <div class="flex flex-col">
                    <span>${f.duration}</span>
                    <span class="text-xs text-slate-500">${nights}</span>
                </div>
            </td>
            <td class="px-6 py-4 font-bold text-emerald-400 text-lg">${f.price}</td>
        `;
        tableBody.appendChild(tr);
    });

    resultCountSpan.textContent = `${flights.length} flights found`;
    updateSortIcons();
}

function sortTable(key) {
    if (currentSort.key === key) {
        currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.key = key;
        currentSort.order = 'asc'; // Reset to asc for new key
    }
    // Re-render current selection logic
    const currentAirport = selectedDepartureSpan.textContent;
    if (currentAirport && currentAirport !== '...') {
        const filtered = allFlights.filter(f => f.departure_airport === currentAirport);
        renderTable(filtered);
    }
}

function updateSortIcons() {
    ['price', 'dest', 'dur', 'date'].forEach(id => {
        const el = document.getElementById(`sort-${id}`);
        if (!el) return;
        el.textContent = el.textContent.replace(' ▴', '').replace(' ▾', '');
        el.classList.remove('text-emerald-400');
    });

    const activeMap = { 'price': 'sort-price', 'destination': 'sort-dest', 'duration': 'sort-dur', 'dates': 'sort-date' };
    const activeId = activeMap[currentSort.key];
    const activeEl = document.getElementById(activeId);
    if (activeEl) {
        activeEl.classList.add('text-emerald-400');
        activeEl.textContent += currentSort.order === 'asc' ? ' ▴' : ' ▾';
    }
}

// Helpers
function parsePrice(priceStr) {
    // Remove symbols and parse
    return parseFloat(priceStr.replace(/[^0-9.]/g, '')) || 0;
}

function parseDuration(durStr) {
    // Convert "1 hr 15 min" to minutes
    let minutes = 0;
    const hrs = durStr.match(/(\d+)\s*hr/);
    const mins = durStr.match(/(\d+)\s*min/);
    if (hrs) minutes += parseInt(hrs[1]) * 60;
    if (mins) minutes += parseInt(mins[1]);
    return minutes;
}

function calculateNights(dateRangeStr) {
    // Expected format: "Aug 20 - Aug 25" or similar
    // Simple parsing assumption: current year
    try {
        const parts = dateRangeStr.split('-');
        if (parts.length < 2) return '';

        const startStr = parts[0].trim();
        const endStr = parts[1].trim();

        // Add current year to parse
        const year = new Date().getFullYear();
        const start = new Date(`${startStr} ${year}`);
        const end = new Date(`${endStr} ${year}`);

        // Handle year rollover (Dec - Jan) - simplified
        if (end < start) {
            end.setFullYear(year + 1);
        }

        const diffTime = Math.abs(end - start);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (isNaN(diffDays)) return '';
        return `${diffDays} night${diffDays !== 1 ? 's' : ''}`;
    } catch {
        return '';
    }
}
