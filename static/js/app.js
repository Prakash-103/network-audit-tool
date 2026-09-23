let currentState = {
    project_name: "Enterprise Network Infrastructure Audit",
    devices: [],
    topology_links: [],
    port_channels: [],
    validation_issues: [],
    device_audit_tasks: [],
    audit_results: [],
    summary: null,
    raw_configs: {},
    operational_logs: {}
};

let selectedAuditDevice = null;
let selectedAuditDeviceData = null;
let activeProtocolFilter = null;

let currentStage = 1;

let vendorCatalog = { vendors: [] };
let scenarioCatalog = { scenarios: [] };

document.addEventListener('DOMContentLoaded', () => {
    setupStageNavigation();
    loadVendorCatalog();
    loadScenarioCatalog();
    loadProjectState();
    setupVendorSelectListener();
    loadSavedFilesList();
});

function setupStageNavigation() {
    document.querySelectorAll('.step-item').forEach(item => {
        item.addEventListener('click', () => {
            const stage = parseInt(item.getAttribute('data-stage'));
            switchStage(stage);
        });
    });
}

function switchStage(stage) {
    currentStage = stage;
    document.querySelectorAll('.step-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.getAttribute('data-stage')) === stage);
    });

    document.getElementById('stage1View').style.display = stage === 1 ? 'block' : 'none';
    document.getElementById('stage2View').style.display = stage === 2 ? 'block' : 'none';
    document.getElementById('stage3View').style.display = stage === 3 ? 'block' : 'none';

    // Auto-refresh: reload project state on every stage change
    refreshStageData(stage);
}

async function refreshStageData(stage) {
    try {
        const res = await fetch('/api/state');
        if (res.ok) {
            const data = await res.json();
            currentState = data;
        }
    } catch (err) {
        console.warn('Auto-refresh: could not reload state', err);
    }
    if (stage === 1) {
        renderInventoryTable();
    }
    if (stage === 2) {
        renderTopologyStage();
        runLiveTopologyValidation();
    }
    if (stage === 3) {
        renderAuditStage();
    }
}

/* Inventory Actions Dropdown Toggle */
function toggleInvActionsDropdown() {
    const menu = document.getElementById('invActionsDropdownMenu');
    if (menu) {
        const isOpen = menu.style.display !== 'none';
        menu.style.display = isOpen ? 'none' : 'block';
    }
}

function closeInvActionsDropdown() {
    const menu = document.getElementById('invActionsDropdownMenu');
    if (menu) menu.style.display = 'none';
}

// Close dropdown when clicking outside
document.addEventListener('click', function (e) {
    const wrapper = document.querySelector('.inv-actions-dropdown-wrapper');
    if (wrapper && !wrapper.contains(e.target)) {
        closeInvActionsDropdown();
    }
});

async function loadProjectState() {
    try {
        const res = await fetch('/api/state');
        const data = await res.json();
        currentState = data;
        renderInventoryTable();
        renderTopologyStage();
    } catch (err) {
        console.error("Error loading project state:", err);
    }
}

async function loadPresetTopology() {
    try {
        const res = await fetch('/api/presets/enterprise');
        const data = await res.json();
        currentState = data;
        renderInventoryTable();
        renderTopologyStage();
        alert("Enterprise Multi-Tier Network Preset Loaded Successfully!");
    } catch (err) {
        alert("Failed to load preset: " + err);
    }
}

/* ==========================================================================
   PAGE 1: DEVICE INVENTORY & EDITING
   ========================================================================== */
function filterInventoryTable(query) {
    renderInventoryTable(query);
}

function renderInventoryTable(filterQuery = '') {
    const tbody = document.getElementById('inventoryTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const compHeader = document.getElementById('invCompanyHeader');
    const siteHeader = document.getElementById('invSiteHeader');
    if (compHeader) compHeader.innerText = currentState.company_name || 'Enterprise Org';
    if (siteHeader) siteHeader.innerText = currentState.site_location || 'HQ Primary DC';

    // Synchronize Project Manager inputs to match selected/loaded/created file
    const compInput = document.getElementById('newCompanyInput');
    const siteInput = document.getElementById('newSiteInput');
    if (compInput && currentState.company_name) compInput.value = currentState.company_name;
    if (siteInput && currentState.site_location) siteInput.value = currentState.site_location;

    document.getElementById('totalDevicesCount').innerText = currentState.devices.length;

    const query = filterQuery.toLowerCase().trim();
    const filtered = currentState.devices.filter(d => {
        if (!query) return true;
        return (d.device_id && d.device_id.toLowerCase().includes(query)) ||
            (d.hostname && d.hostname.toLowerCase().includes(query)) ||
            (d.vendor && d.vendor.toLowerCase().includes(query)) ||
            (d.device_model && d.device_model.toLowerCase().includes(query)) ||
            (d.device_role && d.device_role.toLowerCase().includes(query)) ||
            (d.management_ip && d.management_ip.toLowerCase().includes(query)) ||
            (d.site_location && d.site_location.toLowerCase().includes(query));
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 30px; color: var(--text-dim);">No devices match "${filterQuery}".</td></tr>`;
        return;
    }

    filtered.forEach((dev) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${dev.device_id}</strong></td>
            <td><strong style="color: #ffffff;">${dev.hostname}</strong></td>
            <td>${dev.vendor}</td>
            <td>${dev.device_model}</td>
            <td><code>${dev.os_version}</code></td>
            <td><span class="badge badge-func">${dev.device_function}</span></td>
            <td><span class="badge badge-role">${dev.device_role}</span></td>
            <td>${dev.num_ports} ports (${dev.port_speed})</td>
            <td><code>${dev.management_ip}</code></td>
            <td><span class="badge badge-${dev.lifecycle_status === 'Active' ? 'pass' : 'warning'}">${dev.lifecycle_status}</span></td>
            <td style="white-space: nowrap; text-align: center;">
                <div style="display: flex; gap: 6px; align-items: center; justify-content: center;">
                    <button class="btn btn-secondary btn-sm" onclick="openEditDeviceModal('${dev.device_id}')">✏️ Edit</button>
                    <button class="btn btn-secondary btn-sm" onclick="deleteDevice('${dev.device_id}')">🗑️</button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

/**
 * Generate next unique IP address (e.g. 10.254.1.11, 10.254.1.12)
 */
function getNextAvailableMgmtIp() {
    const existingIps = new Set(currentState.devices.map(d => (d.management_ip || '').trim()));
    // Try incrementing from last device IP or default 10.254.1.10
    let lastIp = "10.254.1.10";
    if (currentState.devices && currentState.devices.length > 0) {
        lastIp = currentState.devices[currentState.devices.length - 1].management_ip || "10.254.1.10";
    }

    const parts = lastIp.split('.');
    if (parts.length === 4 && !isNaN(parts[3])) {
        let prefix = `${parts[0]}.${parts[1]}.${parts[2]}`;
        let octet = parseInt(parts[3], 10) + 1;
        while (existingIps.has(`${prefix}.${octet}`)) {
            octet++;
        }
        return `${prefix}.${octet}`;
    }
    return `10.254.1.${currentState.devices.length + 10}`;
}

/**
 * Generate next unique Serial Number
 */
function getNextAvailableSerial() {
    const existingSerials = new Set(currentState.devices.map(d => (d.serial_number || '').trim().toLowerCase()));
    let sn = `SN-${Math.floor(1000000 + Math.random() * 9000000)}`;
    while (existingSerials.has(sn.toLowerCase())) {
        sn = `SN-${Math.floor(1000000 + Math.random() * 9000000)}`;
    }
    return sn;
}

/**
 * Generate next unique Device ID (DEV-{count+1})
 */
function getNextAvailableDevId() {
    const existingIds = new Set(currentState.devices.map(d => (d.device_id || '').trim().toUpperCase()));
    let count = currentState.devices.length + 1;
    let devId = `DEV-${count}`;
    while (existingIds.has(devId)) {
        count++;
        devId = `DEV-${count}`;
    }
    return devId;
}

async function loadVendorCatalog() {
    try {
        const res = await fetch('/api/catalog/vendors');
        if (res.ok) {
            vendorCatalog = await res.json();
            populateVendorDropdown();
        }
    } catch (e) {
        console.warn('Failed to load vendor catalog:', e);
    }
}

async function loadScenarioCatalog() {
    try {
        const res = await fetch('/api/catalog/scenarios');
        if (res.ok) {
            scenarioCatalog = await res.json();
        }
    } catch (e) {
        console.warn('Failed to load scenario catalog:', e);
    }
}

function populateVendorDropdown(selectedVendor) {
    const vendorSelect = document.getElementById('devVendorSelect');
    if (!vendorSelect) return;

    const vendors = (vendorCatalog && vendorCatalog.vendors && vendorCatalog.vendors.length > 0)
        ? vendorCatalog.vendors
        : [
            { name: "Cisco" }, { name: "Arista" }, { name: "Juniper" },
            { name: "Fortinet" }, { name: "Palo Alto" }, { name: "Aruba" }
        ];

    vendorSelect.innerHTML = '';
    vendors.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.name;
        opt.textContent = v.display_name || v.name;
        vendorSelect.appendChild(opt);
    });

    if (selectedVendor) {
        let hasOpt = Array.from(vendorSelect.options).some(o => o.value.toLowerCase() === selectedVendor.toLowerCase());
        if (!hasOpt) {
            const opt = document.createElement('option');
            opt.value = selectedVendor;
            opt.textContent = selectedVendor;
            vendorSelect.appendChild(opt);
        }
        vendorSelect.value = selectedVendor;
    }
}

function populateModelDropdown(vendorName, selectedModel) {
    const modelSelect = document.getElementById('devModelSelect');
    const customInput = document.getElementById('devModelCustomInput');
    if (!modelSelect) return;

    const v = (vendorCatalog && vendorCatalog.vendors || []).find(
        x => x.name.toLowerCase() === (vendorName || '').toLowerCase() ||
             (x.display_name && x.display_name.toLowerCase() === (vendorName || '').toLowerCase())
    );

    const platforms = (v && v.platforms && v.platforms.length > 0)
        ? v.platforms
        : ["Generic Model", "Edge Router", "Access Switch", "Core Switch"];

    modelSelect.innerHTML = '';
    platforms.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p;
        modelSelect.appendChild(opt);
    });

    // Add option for custom model
    const customOpt = document.createElement('option');
    customOpt.value = '__custom__';
    customOpt.textContent = '➕ Other / Custom Model...';
    modelSelect.appendChild(customOpt);

    if (selectedModel) {
        let hasOpt = Array.from(modelSelect.options).some(o => o.value.toLowerCase() === selectedModel.toLowerCase());
        if (hasOpt) {
            modelSelect.value = selectedModel;
            if (customInput) customInput.style.display = 'none';
        } else {
            // It's a custom model not in the vendor's preset platform list
            // Insert it as an option before the __custom__ option
            const opt = document.createElement('option');
            opt.value = selectedModel;
            opt.textContent = selectedModel;
            modelSelect.insertBefore(opt, customOpt);
            modelSelect.value = selectedModel;
            if (customInput) customInput.style.display = 'none';
        }
    } else {
        // Default to first platform
        modelSelect.selectedIndex = 0;
        if (customInput) customInput.style.display = 'none';
    }
}

function handleModelSelectChange() {
    const modelSelect = document.getElementById('devModelSelect');
    const customInput = document.getElementById('devModelCustomInput');
    if (!modelSelect || !customInput) return;

    if (modelSelect.value === '__custom__') {
        customInput.style.display = 'block';
        customInput.focus();
    } else {
        customInput.style.display = 'none';
        customInput.value = '';
    }
}

function populatePortSpeedDropdown(vendorName, selectedSpeed) {
    const speedSelect = document.getElementById('devSpeedSelect');
    if (!speedSelect) return;

    const v = (vendorCatalog && vendorCatalog.vendors || []).find(
        x => x.name.toLowerCase() === (vendorName || '').toLowerCase() ||
             (x.display_name && x.display_name.toLowerCase() === (vendorName || '').toLowerCase())
    );

    // List port speeds configured in catalog for this vendor
    const speeds = (v && v.supported_speeds && v.supported_speeds.length > 0)
        ? v.supported_speeds
        : ["1G", "10G", "25G", "40G", "100G"];

    speedSelect.innerHTML = '';
    speeds.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        speedSelect.appendChild(opt);
    });

    if (selectedSpeed) {
        let hasOpt = Array.from(speedSelect.options).some(o => o.value.toLowerCase() === selectedSpeed.toLowerCase());
        if (!hasOpt) {
            const opt = document.createElement('option');
            opt.value = selectedSpeed;
            opt.textContent = selectedSpeed;
            speedSelect.appendChild(opt);
        }
        speedSelect.value = selectedSpeed;
    } else {
        speedSelect.selectedIndex = 0;
    }
}

function setupVendorSelectListener() {
    const vendorSelect = document.getElementById('devVendorSelect');
    if (!vendorSelect) return;
    vendorSelect.addEventListener('change', () => {
        const vName = vendorSelect.value;
        const v = (vendorCatalog.vendors || []).find(x => x.name.toLowerCase() === vName.toLowerCase());
        const isEditing = !!document.getElementById('editDeviceOriginalId').value;

        // Dynamically update Hardware Model dropdown and Port Speed dropdown based on vendor catalog
        populateModelDropdown(vName);
        populatePortSpeedDropdown(vName);

        if (v && !isEditing) {
            if (v.default_os_version) {
                document.getElementById('devOsInput').value = v.default_os_version;
            }
        }
    });
}

function openAddDeviceModal() {
    document.getElementById('deviceModalTitle').innerText = "➕ Add Network Device (Page 1)";
    document.getElementById('editDeviceOriginalId').value = "";
    document.getElementById('devIdInput').value = getNextAvailableDevId();
    document.getElementById('devHostnameInput').value = "";

    // Prefill with last added device's exact specifications and values as preset
    const lastDev = (currentState.devices && currentState.devices.length > 0)
        ? currentState.devices[currentState.devices.length - 1]
        : null;

    const targetVendor = lastDev ? lastDev.vendor : "Cisco";
    populateVendorDropdown(targetVendor);
    populateModelDropdown(targetVendor, lastDev ? lastDev.device_model : null);
    populatePortSpeedDropdown(targetVendor, lastDev ? lastDev.port_speed : null);

    document.getElementById('devOsInput').value = lastDev ? lastDev.os_version : "IOS-XE 17.9";
    document.getElementById('devFunctionSelect').value = lastDev ? lastDev.device_function : "L2/L3";
    document.getElementById('devRoleSelect').value = lastDev ? lastDev.device_role : "Access";
    document.getElementById('devPortsInput').value = lastDev ? lastDev.num_ports : 24;
    document.getElementById('devMgmtIpInput').value = lastDev ? lastDev.management_ip : "10.254.1.10";
    document.getElementById('devSiteInput').value = lastDev ? lastDev.site_location : (currentState.site_location || "HQ Primary DC");
    document.getElementById('devSerialInput').value = lastDev ? lastDev.serial_number : "SN-9823412";
    document.getElementById('devLifecycleSelect').value = lastDev ? lastDev.lifecycle_status : "Active";

    // Fixed company name (inherited from project state, non-editable)
    document.getElementById('devCompanyInput').value = currentState.company_name || "Acme Corp";
    document.getElementById('addDeviceModal').classList.add('active');
}

function openEditDeviceModal(devId) {
    const dev = currentState.devices.find(d => d.device_id === devId || d.hostname === devId);
    if (!dev) return;

    document.getElementById('deviceModalTitle').innerText = `✏️ Edit Device: ${dev.hostname} (Page 1)`;
    document.getElementById('editDeviceOriginalId').value = dev.device_id;
    document.getElementById('devIdInput').value = dev.device_id;
    document.getElementById('devHostnameInput').value = dev.hostname;

    populateVendorDropdown(dev.vendor);
    populateModelDropdown(dev.vendor, dev.device_model);
    populatePortSpeedDropdown(dev.vendor, dev.port_speed);

    document.getElementById('devOsInput').value = dev.os_version;
    document.getElementById('devFunctionSelect').value = dev.device_function;
    document.getElementById('devRoleSelect').value = dev.device_role;
    document.getElementById('devPortsInput').value = dev.num_ports;
    document.getElementById('devMgmtIpInput').value = dev.management_ip;
    document.getElementById('devSiteInput').value = dev.site_location;
    document.getElementById('devSerialInput').value = dev.serial_number;
    document.getElementById('devLifecycleSelect').value = dev.lifecycle_status;

    document.getElementById('devCompanyInput').value = dev.company_name || currentState.company_name || "Acme Corp";
    document.getElementById('addDeviceModal').classList.add('active');
}

function closeAddDeviceModal() {
    document.getElementById('addDeviceModal').classList.remove('active');
}

async function saveNewDevice() {
    const origId = document.getElementById('editDeviceOriginalId').value;
    const devId = document.getElementById('devIdInput').value.trim() || getNextAvailableDevId();
    const hostname = document.getElementById('devHostnameInput').value.trim();
    const company = document.getElementById('devCompanyInput').value.trim() || currentState.company_name || 'Acme Corp';
    const vendor = document.getElementById('devVendorSelect').value;

    const modelSelect = document.getElementById('devModelSelect');
    const customModelInput = document.getElementById('devModelCustomInput');
    let model = "";
    if (modelSelect) {
        model = (modelSelect.value === '__custom__' && customModelInput && customModelInput.value.trim())
            ? customModelInput.value.trim()
            : modelSelect.value.trim();
    } else {
        model = (document.getElementById('devModelInput')?.value || '').trim();
    }

    const osVer = document.getElementById('devOsInput').value.trim();
    const func = document.getElementById('devFunctionSelect').value;
    const role = document.getElementById('devRoleSelect').value;
    const numPorts = parseInt(document.getElementById('devPortsInput').value) || 24;
    const portSpeed = document.getElementById('devSpeedSelect').value;
    const mgmtIp = document.getElementById('devMgmtIpInput').value.trim();
    const site = document.getElementById('devSiteInput').value.trim() || currentState.site_location || 'HQ DC';
    const serial = document.getElementById('devSerialInput').value.trim();
    const lifecycle = document.getElementById('devLifecycleSelect').value;

    if (!hostname) {
        alert("⚠️ Hostname is required!");
        return;
    }

    if (!mgmtIp) {
        alert("⚠️ Management IP Address is required!");
        return;
    }

    if (!serial) {
        alert("⚠️ Serial Number is required!");
        return;
    }

    // Client-side uniqueness validation
    const otherDevices = currentState.devices.filter(d => origId ? (d.device_id !== origId && d.hostname !== origId) : true);

    const dupHostname = otherDevices.find(d => d.hostname.toLowerCase() === hostname.toLowerCase());
    if (dupHostname) {
        alert(`❌ Validation Error: Hostname '${hostname}' already exists (${dupHostname.device_id}). Hostnames must be unique!`);
        return;
    }

    const dupIp = otherDevices.find(d => d.management_ip.trim() === mgmtIp);
    if (dupIp) {
        alert(`❌ Validation Error: Management IP '${mgmtIp}' is already assigned to '${dupIp.hostname}' (${dupIp.device_id}). Management IP addresses must be unique!`);
        return;
    }

    const dupSerial = otherDevices.find(d => d.serial_number.trim().toLowerCase() === serial.toLowerCase());
    if (dupSerial) {
        alert(`❌ Validation Error: Serial Number '${serial}' is already assigned to '${dupSerial.hostname}' (${dupSerial.device_id}). Serial numbers must be unique!`);
        return;
    }

    const dupId = otherDevices.find(d => d.device_id.trim().toLowerCase() === devId.toLowerCase());
    if (dupId) {
        alert(`❌ Validation Error: Device ID '${devId}' already exists. Please use a unique Device ID!`);
        return;
    }

    const deviceData = {
        device_id: devId,
        hostname: hostname,
        company_name: company,
        vendor: vendor,
        device_model: model,
        os_version: osVer,
        device_function: func,
        device_role: role,
        num_ports: numPorts,
        port_type: "Ethernet",
        port_speed: portSpeed,
        management_ip: mgmtIp,
        site_location: site,
        serial_number: serial,
        lifecycle_status: lifecycle,
        ports: []
    };

    try {
        const url = origId ? `/api/devices/${encodeURIComponent(origId)}` : '/api/devices';
        const method = origId ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(deviceData)
        });

        if (!res.ok) {
            const errData = await res.json();
            alert(`❌ Error: ${errData.detail || 'Failed to save device'}`);
            return;
        }

        currentState = await res.json();
        renderInventoryTable();
        renderTopologyStage();
        closeAddDeviceModal();
    } catch (err) {
        alert("Failed to save device: " + err);
    }
}

async function deleteDevice(devId) {
    if (!confirm("Are you sure you want to delete this device and all its connections?")) return;
    try {
        const res = await fetch(`/api/devices/${devId}`, { method: 'DELETE' });
        currentState = await res.json();
        renderInventoryTable();
        renderTopologyStage();
    } catch (err) {
        alert("Failed to delete device: " + err);
    }
}

/* ==========================================================================
   PAGE 2: NETWORK CONNECTION TOPOLOGY & PORT-CHANNEL MULTI-SELECT BUILDER
   ========================================================================== */
let selectedSrcMultiPorts = [];
let selectedTgtMultiPorts = [];

function renderTopologyStage() {
    populateTopologyDeviceDropdowns();
    renderLinksTable();
    renderPortChannelsTable();
}

function populateTopologyDeviceDropdowns() {
    const srcSelect = document.getElementById('topoSrcDevice');
    const tgtSelect = document.getElementById('topoTgtDevice');
    if (!srcSelect || !tgtSelect) return;

    const currSrc = srcSelect.value;
    const currTgt = tgtSelect.value;

    srcSelect.innerHTML = '<option value="">Select Source Device...</option>';
    currentState.devices.forEach(d => {
        srcSelect.innerHTML += `<option value="${d.hostname}">${d.hostname} (${d.device_role})</option>`;
    });

    if (currSrc) srcSelect.value = currSrc;

    updateTargetDeviceOptions();

    if (currTgt && currTgt !== srcSelect.value) {
        tgtSelect.value = currTgt;
    }

    refreshPortSelectors('src');
    refreshPortSelectors('tgt');
    updateMappingPreview();
}

function onSourceDeviceChanged() {
    updateTargetDeviceOptions();
    selectedSrcMultiPorts = [];
    refreshPortSelectors('src');
    updateMappingPreview();
}

function onTargetDeviceChanged() {
    selectedTgtMultiPorts = [];
    refreshPortSelectors('tgt');
    updateMappingPreview();
}

function updateTargetDeviceOptions() {
    const srcSelect = document.getElementById('topoSrcDevice');
    const tgtSelect = document.getElementById('topoTgtDevice');
    if (!srcSelect || !tgtSelect) return;

    const selectedSrc = srcSelect.value;
    const currTgt = tgtSelect.value;

    tgtSelect.innerHTML = '<option value="">Select Target Device...</option>';

    currentState.devices.forEach(d => {
        if (d.hostname !== selectedSrc) {
            tgtSelect.innerHTML += `<option value="${d.hostname}">${d.hostname} (${d.device_role})</option>`;
        }
    });

    if (currTgt && currTgt !== selectedSrc) {
        tgtSelect.value = currTgt;
    } else {
        tgtSelect.value = "";
    }
}

function onPortChannelToggleChanged() {
    const isPo = document.getElementById('topoPoCheckbox').checked;
    const poNumberInput = document.getElementById('topoPoNumberInput');
    const srcModeBadge = document.getElementById('srcPortModeBadge');
    const tgtModeBadge = document.getElementById('tgtPortModeBadge');
    const srcSingleSelect = document.getElementById('topoSrcPort');
    const tgtSingleSelect = document.getElementById('topoTgtPort');
    const srcMultiContainer = document.getElementById('topoSrcMultiContainer');
    const tgtMultiContainer = document.getElementById('topoTgtMultiContainer');
    const banner = document.getElementById('topoIndexMappingBanner');

    if (isPo) {
        poNumberInput.disabled = false;
        if (!poNumberInput.value) poNumberInput.focus();

        srcModeBadge.textContent = 'Multi-Select';
        srcModeBadge.classList.add('multi-active');
        tgtModeBadge.textContent = 'Multi-Select';
        tgtModeBadge.classList.add('multi-active');

        srcSingleSelect.style.display = 'none';
        tgtSingleSelect.style.display = 'none';
        srcMultiContainer.style.display = 'block';
        tgtMultiContainer.style.display = 'block';
        banner.style.display = 'flex';
    } else {
        poNumberInput.disabled = true;

        srcModeBadge.textContent = 'Single';
        srcModeBadge.classList.remove('multi-active');
        tgtModeBadge.textContent = 'Single';
        tgtModeBadge.classList.remove('multi-active');

        srcSingleSelect.style.display = 'block';
        tgtSingleSelect.style.display = 'block';
        srcMultiContainer.style.display = 'none';
        tgtMultiContainer.style.display = 'none';
        banner.style.display = 'none';

        // Close any open dropdowns
        closeAllMultiDropdowns();
    }

    refreshPortSelectors('src');
    refreshPortSelectors('tgt');
    updateMappingPreview();
}

/**
 * Returns available unused ports for a device
 */
function getFreePortsForDevice(devName) {
    if (!devName) return [];
    const dev = currentState.devices.find(d => d.hostname === devName);
    if (!dev || !dev.ports) return [];

    const usedPorts = new Set();
    currentState.topology_links.forEach(l => {
        if (l.source_device === devName) usedPorts.add(l.source_port);
        if (l.target_device === devName) usedPorts.add(l.target_port);
    });

    currentState.port_channels.forEach(po => {
        if (po.source_device === devName) po.source_member_ports.forEach(p => usedPorts.add(p));
        if (po.target_device === devName) po.target_member_ports.forEach(p => usedPorts.add(p));
    });

    return dev.ports.filter(p => !usedPorts.has(p));
}

/**
 * Updates single select or multi-select dropdown for source or target
 */
function refreshPortSelectors(type) {
    const isSrc = type === 'src';
    const devSelectId = isSrc ? 'topoSrcDevice' : 'topoTgtDevice';
    const singleSelectId = isSrc ? 'topoSrcPort' : 'topoTgtPort';
    const multiListId = isSrc ? 'topoSrcMultiList' : 'topoTgtMultiList';
    const multiSummaryId = isSrc ? 'topoSrcMultiSummary' : 'topoTgtMultiSummary';
    const countTagId = isSrc ? 'topoSrcCountTag' : 'topoTgtCountTag';

    const devName = document.getElementById(devSelectId)?.value;
    const singleSelect = document.getElementById(singleSelectId);
    const multiList = document.getElementById(multiListId);
    const multiSummary = document.getElementById(multiSummaryId);
    const countTag = document.getElementById(countTagId);

    if (!singleSelect || !multiList) return;

    const freePorts = getFreePortsForDevice(devName);
    const selectedArray = isSrc ? selectedSrcMultiPorts : selectedTgtMultiPorts;

    // Filter out any selected ports that are no longer free
    const validSelected = selectedArray.filter(p => freePorts.includes(p));
    if (isSrc) selectedSrcMultiPorts = validSelected;
    else selectedTgtMultiPorts = validSelected;

    // 1. Single Select Options
    singleSelect.innerHTML = '<option value="">Select Unused Port...</option>';
    if (freePorts.length === 0) {
        singleSelect.innerHTML = `<option value="">${devName ? 'No Free Ports Available' : 'Select Device First'}</option>`;
    } else {
        freePorts.forEach(p => {
            singleSelect.innerHTML += `<option value="${p}">${p}</option>`;
        });
    }

    // 2. Multi Select List Items
    multiList.innerHTML = '';
    if (freePorts.length === 0) {
        multiList.innerHTML = `<div style="padding: 10px; font-size: 0.8rem; color: var(--text-dim); text-align: center;">${devName ? 'No Free Ports Available' : 'Select Device First'}</div>`;
    } else {
        freePorts.forEach(p => {
            const isChecked = validSelected.includes(p);
            const index = validSelected.indexOf(p);
            const itemDiv = document.createElement('div');
            itemDiv.className = `multi-option-item ${isChecked ? 'selected' : ''}`;
            itemDiv.onclick = (e) => {
                e.stopPropagation();
                toggleMultiPortSelection(type, p);
            };
            itemDiv.innerHTML = `
                <input type="checkbox" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation(); toggleMultiPortSelection('${type}', '${p}')">
                <span>${p}</span>
                ${isChecked ? `<span class="port-index-badge">#${index + 1}</span>` : ''}
            `;
            multiList.appendChild(itemDiv);
        });
    }

    // 3. Multi summary & counter
    if (countTag) countTag.textContent = `${validSelected.length} selected`;
    if (multiSummary) {
        if (validSelected.length === 0) {
            multiSummary.textContent = 'Select Unused Ports...';
        } else if (validSelected.length <= 2) {
            multiSummary.textContent = validSelected.join(', ');
        } else {
            multiSummary.textContent = `${validSelected.length} Ports (${validSelected[0]}, ${validSelected[1]}, +${validSelected.length - 2})`;
        }
    }
}

function toggleMultiPortSelection(type, port) {
    const isSrc = type === 'src';
    let arr = isSrc ? selectedSrcMultiPorts : selectedTgtMultiPorts;

    if (arr.includes(port)) {
        arr = arr.filter(p => p !== port);
    } else {
        arr.push(port);
    }

    if (isSrc) selectedSrcMultiPorts = arr;
    else selectedTgtMultiPorts = arr;

    refreshPortSelectors(type);
    updateMappingPreview();
}

function clearMultiSelection(type) {
    if (type === 'src') selectedSrcMultiPorts = [];
    else selectedTgtMultiPorts = [];

    refreshPortSelectors(type);
    updateMappingPreview();
}

function toggleMultiDropdown(type) {
    const isSrc = type === 'src';
    const dropdown = document.getElementById(isSrc ? 'topoSrcMultiDropdown' : 'topoTgtMultiDropdown');
    const otherDropdown = document.getElementById(isSrc ? 'topoTgtMultiDropdown' : 'topoSrcMultiDropdown');

    if (otherDropdown) otherDropdown.classList.remove('open');
    if (dropdown) dropdown.classList.toggle('open');
}

function closeAllMultiDropdowns() {
    const d1 = document.getElementById('topoSrcMultiDropdown');
    const d2 = document.getElementById('topoTgtMultiDropdown');
    if (d1) d1.classList.remove('open');
    if (d2) d2.classList.remove('open');
}

// Global click listener to close multi-select dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.multi-port-container')) {
        closeAllMultiDropdowns();
    }
});

/**
 * Real-time 1-to-1 Index Matching Preview & Validation Display
 */
function updateMappingPreview() {
    const isPo = document.getElementById('topoPoCheckbox')?.checked;
    const banner = document.getElementById('topoIndexMappingBanner');
    const statusText = document.getElementById('mappingStatusText');
    const statusIcon = document.getElementById('mappingStatusIcon');
    const pairsContainer = document.getElementById('mappingPairsContainer');

    if (!isPo || !banner) {
        if (banner) banner.style.display = 'none';
        return;
    }

    banner.style.display = 'flex';
    const poNumVal = document.getElementById('topoPoNumberInput')?.value?.trim();
    const poId = poNumVal ? (poNumVal.toLowerCase().startsWith('po') ? poNumVal : `Po${poNumVal}`) : 'Po?';

    const srcCount = selectedSrcMultiPorts.length;
    const tgtCount = selectedTgtMultiPorts.length;

    pairsContainer.innerHTML = '';

    if (srcCount === 0 && tgtCount === 0) {
        banner.className = 'index-mapping-banner';
        statusIcon.textContent = 'ℹ️';
        statusText.textContent = `Select matching Source and Target ports to bundle into ${poId}`;
        return;
    }

    const maxLen = Math.max(srcCount, tgtCount);

    if (srcCount === tgtCount && srcCount > 0) {
        banner.className = 'index-mapping-banner valid';
        statusIcon.textContent = '✓';
        statusText.innerHTML = `<strong style="color:#10b981;">Equal Index Count:</strong> ${srcCount} Source = ${tgtCount} Target Ports ready for <strong>${poId}</strong> bundle`;

        for (let i = 0; i < srcCount; i++) {
            pairsContainer.innerHTML += `
                <span class="mapping-pair-pill valid">
                    <span style="opacity:0.75;">[#${i + 1}]</span> ${selectedSrcMultiPorts[i]} ↔ ${selectedTgtMultiPorts[i]}
                </span>
            `;
        }
    } else {
        banner.className = 'index-mapping-banner invalid';
        statusIcon.textContent = '⚠️';
        statusText.innerHTML = `<strong style="color:#ef4444;">Index Mismatch:</strong> ${srcCount} Source Port(s) vs ${tgtCount} Target Port(s). Must have equal counts (1-to-1 index matching) before connecting.`;

        for (let i = 0; i < maxLen; i++) {
            const sp = selectedSrcMultiPorts[i];
            const tp = selectedTgtMultiPorts[i];
            const isPairValid = sp && tp;
            pairsContainer.innerHTML += `
                <span class="mapping-pair-pill ${isPairValid ? 'valid' : 'mismatched'}">
                    <span style="opacity:0.75;">[#${i + 1}]</span> ${sp || '<span style="color:#ef4444;">Missing Source Port</span>'} ↔ ${tp || '<span style="color:#ef4444;">Missing Target Port</span>'}
                </span>
            `;
        }
    }
}

async function addTopologyLink() {
    const srcDev = document.getElementById('topoSrcDevice').value;
    const tgtDev = document.getElementById('topoTgtDevice').value;
    const speed = document.getElementById('topoSpeedSelect').value;
    const isPo = document.getElementById('topoPoCheckbox').checked;

    if (!srcDev || !tgtDev) {
        alert("Please select both source and target devices.");
        return;
    }
    if (srcDev === tgtDev) {
        alert("Source and Target device cannot be the same.");
        return;
    }

    let payload = {};

    if (isPo) {
        // Port-Channel Mode Validation
        const poNumVal = document.getElementById('topoPoNumberInput').value.trim();
        if (!poNumVal || isNaN(poNumVal) || parseInt(poNumVal, 10) <= 0) {
            alert("Please enter a valid positive integer for Port-Channel Number (e.g. 10).");
            document.getElementById('topoPoNumberInput').focus();
            return;
        }

        const poId = poNumVal.toLowerCase().startsWith('po') ? poNumVal : `Po${parseInt(poNumVal, 10)}`;
        const srcPorts = [...selectedSrcMultiPorts];
        const tgtPorts = [...selectedTgtMultiPorts];

        if (srcPorts.length === 0 || tgtPorts.length === 0) {
            alert("Please select at least one source port and one target port for Port-Channel.");
            return;
        }

        // REQUIRED VALIDATION: source port input index is equal to destination port index values
        if (srcPorts.length !== tgtPorts.length) {
            alert(`Validation Failed:\nSource port count (${srcPorts.length}) is not equal to destination port count (${tgtPorts.length}).\n\nEach source port must map 1-to-1 to a corresponding destination port index before submitting.`);
            return;
        }

        payload = {
            source_device: srcDev,
            source_ports: srcPorts,
            target_device: tgtDev,
            target_ports: tgtPorts,
            link_speed: speed,
            port_channel_id: poId
        };
    } else {
        // Single Port Mode Validation
        const srcPort = document.getElementById('topoSrcPort').value;
        const tgtPort = document.getElementById('topoTgtPort').value;

        if (!srcPort || !tgtPort) {
            alert("Please select both source and target unused ports.");
            return;
        }

        payload = {
            source_device: srcDev,
            source_port: srcPort,
            target_device: tgtDev,
            target_port: tgtPort,
            link_speed: speed,
            port_channel_id: null
        };
    }

    try {
        const res = await fetch('/api/topology/link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Failed to create connection");
        }

        currentState = await res.json();
        renderLinksTable();
        renderPortChannelsTable();

        // Clear selections
        selectedSrcMultiPorts = [];
        selectedTgtMultiPorts = [];
        document.getElementById('topoPoNumberInput').value = '';

        refreshPortSelectors('src');
        refreshPortSelectors('tgt');
        updateMappingPreview();
        runLiveTopologyValidation();

        // If diagram is visible, refresh it
        if (document.getElementById('visualDiagramSection').style.display !== 'none') {
            generateTopologyDiagram();
        }
    } catch (err) {
        alert("Failed to add connection: " + err.message);
    }
}

async function deleteTopologyLink(linkId) {
    if (!confirm("Are you sure you want to delete this link connection?")) return;
    try {
        const res = await fetch(`/api/topology/link?link_id=${encodeURIComponent(linkId)}`, { method: 'DELETE' });
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Failed to delete link");
        }
        currentState = await res.json();
        renderLinksTable();
        renderPortChannelsTable();
        refreshPortSelectors('src');
        refreshPortSelectors('tgt');
        updateMappingPreview();
        runLiveTopologyValidation();

        if (document.getElementById('visualDiagramSection').style.display !== 'none') {
            generateTopologyDiagram();
        }
    } catch (err) {
        alert("Failed to delete link: " + err.message);
    }
}

function switchTopologyTab(tabName) {
    const isPo = tabName === 'portchannels';
    const poBtn = document.getElementById('tabBtnPortChannels');
    const linksBtn = document.getElementById('tabBtnLinks');
    const poPane = document.getElementById('panePortChannels');
    const linksPane = document.getElementById('paneLinks');

    if (poBtn) poBtn.classList.toggle('active', isPo);
    if (linksBtn) linksBtn.classList.toggle('active', !isPo);

    if (poPane) poPane.style.display = isPo ? 'block' : 'none';
    if (linksPane) linksPane.style.display = !isPo ? 'block' : 'none';
}

function renderLinksTable() {
    const tbody = document.getElementById('linksTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const total = currentState.topology_links.length;
    const countEl = document.getElementById('totalLinksCount');
    const tabCountEl = document.getElementById('linksTabCount');
    if (countEl) countEl.innerText = total;
    if (tabCountEl) tabCountEl.innerText = total;

    if (total === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-dim);">No physical links configured yet. Connect interfaces using the builder above.</td></tr>`;
        return;
    }

    currentState.topology_links.forEach(l => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${l.source_device}</strong> <span style="color:#cbd5e1;">(${l.source_port})</span></td>
            <td style="color:var(--secondary); text-align:center;">⇄</td>
            <td><strong>${l.target_device}</strong> <span style="color:#cbd5e1;">(${l.target_port})</span></td>
            <td><code>${l.link_speed}</code></td>
            <td><span class="badge badge-role">${l.port_channel_id || 'SINGLE LINK'}</span></td>
            <td><span class="badge badge-pass">${l.status}</span></td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="deleteTopologyLink('${l.id}')">🗑️</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderPortChannelsTable() {
    const tbody = document.getElementById('poTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const total = currentState.port_channels.length;
    const tabCountEl = document.getElementById('poTabCount');
    if (tabCountEl) tabCountEl.innerText = total;

    if (total === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-dim);">No Port-Channel aggregations configured yet. Assign a Port-Channel ID when connecting links.</td></tr>`;
        return;
    }

    currentState.port_channels.forEach(po => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${po.id}</strong></td>
            <td>${po.source_device} ↔ ${po.target_device}</td>
            <td><code>${po.source_member_ports.join(', ')}</code></td>
            <td><code>${po.target_member_ports.join(', ')}</code></td>
            <td><span class="badge badge-func">${po.protocol}</span></td>
            <td style="white-space: nowrap;">
                <div style="display: flex; gap: 6px; align-items: center;">
                    <button class="btn btn-secondary btn-sm" onclick="openEditPortChannelModal('${po.id}')">✏️ Edit</button>
                    <button class="btn btn-secondary btn-sm" onclick="deletePortChannel('${po.id}')">🗑️</button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

/* ==========================================================================
   PORT-CHANNEL EDITING & DELETION
   ========================================================================== */
function openEditPortChannelModal(poId) {
    const po = currentState.port_channels.find(p => p.id === poId);
    if (!po) return;

    document.getElementById('editPoOriginalId').value = po.id;
    document.getElementById('editPoIdInput').value = po.id;
    document.getElementById('editPoProtocolSelect').value = po.protocol || "LACP";
    document.getElementById('editPoSrcDevice').value = po.source_device;
    document.getElementById('editPoTgtDevice').value = po.target_device;
    document.getElementById('editPoSrcPortsInput').value = po.source_member_ports.join(', ');
    document.getElementById('editPoTgtPortsInput').value = po.target_member_ports.join(', ');

    document.getElementById('editPortChannelModal').classList.add('active');
}

function closeEditPortChannelModal() {
    document.getElementById('editPortChannelModal').classList.remove('active');
}

async function saveEditedPortChannel() {
    const poId = document.getElementById('editPoOriginalId').value;
    const protocol = document.getElementById('editPoProtocolSelect').value;
    const srcDev = document.getElementById('editPoSrcDevice').value;
    const tgtDev = document.getElementById('editPoTgtDevice').value;
    const srcPorts = document.getElementById('editPoSrcPortsInput').value.split(',').map(s => s.trim()).filter(Boolean);
    const tgtPorts = document.getElementById('editPoTgtPortsInput').value.split(',').map(s => s.trim()).filter(Boolean);

    const payload = {
        id: poId,
        source_device: srcDev,
        target_device: tgtDev,
        source_member_ports: srcPorts,
        target_member_ports: tgtPorts,
        protocol: protocol,
        status: "Operational"
    };

    try {
        const res = await fetch(`/api/topology/portchannel/${encodeURIComponent(poId)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        currentState = await res.json();
        renderPortChannelsTable();
        renderLinksTable();
        runLiveTopologyValidation();
        closeEditPortChannelModal();
    } catch (err) {
        alert("Failed to update Port-Channel: " + err);
    }
}

async function deletePortChannel(poId) {
    if (!confirm(`Are you sure you want to delete Port-Channel ${poId}?`)) return;
    try {
        const res = await fetch(`/api/topology/portchannel/${encodeURIComponent(poId)}`, { method: 'DELETE' });
        currentState = await res.json();
        renderPortChannelsTable();
        renderLinksTable();
        runLiveTopologyValidation();
    } catch (err) {
        alert("Failed to delete Port-Channel: " + err);
    }
}

/* ==========================================================================
   REAL-TIME TOPOLOGY VALIDATION
   ========================================================================== */
async function runLiveTopologyValidation() {
    try {
        const res = await fetch('/api/topology/validate');
        const data = await res.json();
        currentState.validation_issues = data.issues || [];
        renderValidationAlerts();
    } catch (err) {
        console.error("Validation error:", err);
    }
}

function renderValidationAlerts() {
    const container = document.getElementById('validationAlertsContainer');
    const countBadge = document.getElementById('validationAlertCountBadge');
    if (!container) return;
    container.innerHTML = '';

    const issueCount = currentState.validation_issues ? currentState.validation_issues.length : 0;
    if (countBadge) {
        countBadge.innerHTML = issueCount === 0
            ? '<span style="color: #6ee7b7;">● 0 Issues</span>'
            : `<span style="color: #fde047;">⚠️ ${issueCount} Issue${issueCount > 1 ? 's' : ''}</span>`;
    }

    if (issueCount === 0) {
        container.innerHTML = `
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; padding: 14px 18px; border-radius: 10px; color: #6ee7b7; font-size: 0.92rem; font-weight: 600;">
                ✅ <strong>Topology Validated:</strong> Zero link integrity conflicts or duplicate port errors detected across network nodes.
            </div>
        `;
        return;
    }

    currentState.validation_issues.forEach(issue => {
        const isCrit = issue.severity === 'Critical';
        const color = isCrit ? '#fca5a5' : '#fde047';
        const bg = isCrit ? 'rgba(239, 68, 68, 0.16)' : 'rgba(245, 158, 11, 0.16)';
        const border = isCrit ? '#ef4444' : '#f59e0b';

        const div = document.createElement('div');
        div.style.cssText = `background: ${bg}; border: 1px solid ${border}; padding: 14px 18px; border-radius: 10px; margin-bottom: 10px; font-size: 0.9rem; color: #ffffff; box-shadow: 0 4px 14px rgba(0,0,0,0.3);`;
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <strong style="color: ${color}; font-size: 0.95rem;">⚠️ ${issue.rule} (${issue.source_device})</strong>
                <span class="badge badge-${issue.severity.toLowerCase()}">${issue.severity}</span>
            </div>
            <div style="color: #f8fafc; font-weight: 500;">${issue.message}</div>
            <div style="font-size: 0.82rem; color: #cbd5e1; margin-top: 8px; background: rgba(0,0,0,0.35); padding: 8px 12px; border-radius: 6px; border-left: 3px solid ${border};">
                <strong style="color: #93c5fd;">Remediation:</strong> ${issue.remediation}
            </div>
        `;
        container.appendChild(div);
    });
}

/* ==========================================================================
   INTERACTIVE NETWORK TOPOLOGY CONNECTION DIAGRAM GENERATOR (WITH CUSTOM TIERING)
   ========================================================================== */
let topologyNodePositions = {};
let topologyEdgeOffsets = {};

// Custom Tiering Configuration & Architectural Presets
let customTierConfig = {
    roleTierMap: {
        "Core": 1,
        "Distribution": 2,
        "Access": 3,
        "Firewall": 4,
        "Edge": 5,
        "Wireless AP": 6,
        "Other": 7
    },
    tierLabels: {
        1: "CORE TIER (Backbone Switching)",
        2: "DISTRIBUTION TIER (Aggregation)",
        3: "ACCESS TIER (Endpoint Connectivity)",
        4: "SECURITY & DMZ PERIMETER",
        5: "WAN EDGE & INTERNET ROUTING",
        6: "WIRELESS ACCESS LAYER",
        7: "OTHER NETWORK NODES"
    }
};

const TIER_PRESETS = {
    "3tier": {
        name: "Standard 3-Tier",
        roleTierMap: {
            "Core": 1,
            "Distribution": 2,
            "Access": 3,
            "Firewall": 4,
            "Edge": 5,
            "Wireless AP": 6,
            "Other": 7
        },
        tierLabels: {
            1: "CORE TIER (Backbone Switching)",
            2: "DISTRIBUTION TIER (Aggregation)",
            3: "ACCESS TIER (Endpoint Connectivity)",
            4: "SECURITY & DMZ PERIMETER",
            5: "WAN EDGE & INTERNET ROUTING",
            6: "WIRELESS ACCESS LAYER",
            7: "OTHER NETWORK NODES"
        }
    },
    "collapsed": {
        name: "Collapsed Core",
        roleTierMap: {
            "Core": 1,
            "Distribution": 1,
            "Firewall": 2,
            "Edge": 2,
            "Access": 3,
            "Wireless AP": 4,
            "Other": 5
        },
        tierLabels: {
            1: "COLLAPSED CORE & AGGREGATION TIER",
            2: "SECURITY & WAN EDGE PERIMETER",
            3: "ACCESS LAYER (Endpoints)",
            4: "WIRELESS ACCESS LAYER",
            5: "OTHER NETWORK NODES"
        }
    },
    "security_first": {
        name: "Perimeter First",
        roleTierMap: {
            "Edge": 1,
            "Firewall": 2,
            "Core": 3,
            "Distribution": 4,
            "Access": 5,
            "Wireless AP": 6,
            "Other": 7
        },
        tierLabels: {
            1: "WAN EDGE & INTERNET ROUTING",
            2: "FIREWALL & PERIMETER SECURITY",
            3: "CORE SWITCHING BACKBONE",
            4: "DISTRIBUTION AGGREGATION",
            5: "ACCESS ENDPOINT TIER",
            6: "WIRELESS ACCESS LAYER",
            7: "OTHER NETWORK NODES"
        }
    },
    "spine_leaf": {
        name: "Spine-Leaf Fabric",
        roleTierMap: {
            "Core": 1,
            "Distribution": 2,
            "Access": 2,
            "Firewall": 3,
            "Edge": 3,
            "Wireless AP": 4,
            "Other": 4
        },
        tierLabels: {
            1: "SPINE SWITCHING FABRIC",
            2: "LEAF / TOP-OF-RACK (ToR) TIER",
            3: "SECURITY & WAN SERVICE NODES",
            4: "ENDPOINTS & WIRELESS ACCESS"
        }
    }
};

function toggleTopologyDiagram() {
    const section = document.getElementById('visualDiagramSection');
    const btn = document.getElementById('toggleDiagramBtn');
    if (!section) return;

    if (section.style.display === 'none' || !section.style.display) {
        generateTopologyDiagram();
        if (btn) btn.innerHTML = '✕ Close Topology Graph';
    } else {
        hideTopologyDiagram();
    }
}

function hideTopologyDiagram() {
    const section = document.getElementById('visualDiagramSection');
    const btn = document.getElementById('toggleDiagramBtn');
    if (section) section.style.display = 'none';
    if (btn) btn.innerHTML = '🎨 View Topology Graph';
}

function resetTopologyLayout() {
    topologyNodePositions = {};
    topologyEdgeOffsets = {};
    generateTopologyDiagram();
}

function autoAlignTopologyTiers() {
    topologyNodePositions = {};
    topologyEdgeOffsets = {};
    generateTopologyDiagram();
}

/* ==========================================================================
   CUSTOM TIERING MODAL CONTROLS & MANAGEMENT
   ========================================================================== */
function openCustomTierModal() {
    const modal = document.getElementById('customTierModal');
    if (!modal) return;
    renderCustomTierModal();
    modal.classList.add('active');
}

function closeCustomTierModal() {
    const modal = document.getElementById('customTierModal');
    if (modal) modal.classList.remove('active');
}

function applyTierPreset(presetKey) {
    const preset = TIER_PRESETS[presetKey];
    if (!preset) return;
    customTierConfig.roleTierMap = JSON.parse(JSON.stringify(preset.roleTierMap));
    customTierConfig.tierLabels = JSON.parse(JSON.stringify(preset.tierLabels));
    renderCustomTierModal();
}

function resetCustomTiering() {
    applyTierPreset('3tier');
}

function onRoleTierChanged(role, newTier) {
    customTierConfig.roleTierMap[role] = parseInt(newTier, 10);
    renderCustomTierHierarchyFlow();
}

function onTierLabelChanged(tierLevel, labelValue) {
    customTierConfig.tierLabels[tierLevel] = labelValue.trim() || `TIER ${tierLevel}`;
    renderCustomTierHierarchyFlow();
}

function renderCustomTierModal() {
    const tbody = document.getElementById('customTierMappingTbody');
    if (!tbody) return;

    // Define standard roles and collect any dynamic roles
    const standardRoles = ["Core", "Distribution", "Access", "Firewall", "Edge", "Wireless AP", "Other"];
    const allRoles = new Set(standardRoles);
    currentState.devices.forEach(d => {
        let r = d.device_role || "Other";
        if (d.device_function === 'Firewall') r = 'Firewall';
        else if (d.device_function === 'Edge/WAN') r = 'Edge';
        else if (d.device_function === 'Wireless AP') r = 'Wireless AP';
        allRoles.add(r);
    });

    // Count nodes per role
    const nodeCounts = {};
    allRoles.forEach(r => nodeCounts[r] = 0);
    currentState.devices.forEach(d => {
        let r = d.device_role || "Other";
        if (d.device_function === 'Firewall') r = 'Firewall';
        else if (d.device_function === 'Edge/WAN') r = 'Edge';
        else if (d.device_function === 'Wireless AP') r = 'Wireless AP';
        nodeCounts[r] = (nodeCounts[r] || 0) + 1;
    });

    tbody.innerHTML = '';

    Array.from(allRoles).forEach(role => {
        const assignedTier = customTierConfig.roleTierMap[role] !== undefined ? customTierConfig.roleTierMap[role] : 7;
        const currentLabel = customTierConfig.tierLabels[assignedTier] || `${role.toUpperCase()} TIER`;
        const count = nodeCounts[role] || 0;

        let optionsHTML = '';
        for (let t = 1; t <= 7; t++) {
            const isSelected = t === assignedTier ? 'selected' : '';
            const suffix = t === 1 ? ' (Top)' : t === 7 ? ' (Bottom)' : '';
            optionsHTML += `<option value="${t}" ${isSelected}>Tier ${t}${suffix}</option>`;
        }

        tbody.innerHTML += `
            <tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="badge badge-role">${role}</span>
                    </div>
                </td>
                <td style="text-align: center;">
                    <span style="font-weight: 700; color: ${count > 0 ? 'var(--secondary)' : 'var(--text-dim)'};">${count}</span>
                </td>
                <td>
                    <select onchange="onRoleTierChanged('${role}', this.value)" style="padding: 6px 8px; font-size: 0.82rem; height: 34px;">
                        ${optionsHTML}
                    </select>
                </td>
                <td>
                    <input type="text" value="${currentLabel}" 
                           placeholder="Tier Band Name" 
                           oninput="onTierLabelChanged(${assignedTier}, this.value)"
                           style="padding: 6px 10px; font-size: 0.82rem; height: 34px;">
                </td>
            </tr>
        `;
    });

    renderCustomTierHierarchyFlow();
}

function renderCustomTierHierarchyFlow() {
    const flowContainer = document.getElementById('customTierHierarchyFlow');
    if (!flowContainer) return;

    // Group active roles by assigned tier
    const tiersInUse = {};
    Object.keys(customTierConfig.roleTierMap).forEach(role => {
        const t = customTierConfig.roleTierMap[role];
        if (!tiersInUse[t]) tiersInUse[t] = [];
        tiersInUse[t].push(role);
    });

    const sortedTiers = Object.keys(tiersInUse).map(Number).sort((a, b) => a - b);

    if (sortedTiers.length === 0) {
        flowContainer.innerHTML = `<span style="font-size: 0.8rem; color: var(--text-dim);">No active tier assignments.</span>`;
        return;
    }

    let flowHTML = '';
    sortedTiers.forEach((tierNum, idx) => {
        const roles = tiersInUse[tierNum].join(', ');
        const label = customTierConfig.tierLabels[tierNum] || `Tier ${tierNum}`;
        flowHTML += `
            <div class="tier-flow-step">
                <span class="tier-rank-badge">T${tierNum}</span>
                <span><strong>${label}</strong> (${roles})</span>
            </div>
        `;
        if (idx < sortedTiers.length - 1) {
            flowHTML += `<span class="tier-flow-arrow">➔</span>`;
        }
    });

    flowContainer.innerHTML = flowHTML;
}

function applyCustomTiering() {
    // Reset manual drag coordinates so nodes align to new tier bands
    topologyNodePositions = {};
    topologyEdgeOffsets = {};
    generateTopologyDiagram();
    closeCustomTierModal();
}

function getRoleClass(role, func) {
    const r = (role || '').toLowerCase();
    const f = (func || '').toLowerCase();
    if (r.includes('core') || r.includes('spine')) return 'role-core';
    if (r.includes('dist') || r.includes('leaf') || r.includes('agg')) return 'role-distribution';
    if (r.includes('access') || r.includes('tor')) return 'role-access';
    if (f.includes('firewall') || r.includes('firewall') || r.includes('sec')) return 'role-firewall';
    if (f.includes('edge') || r.includes('edge') || f.includes('wan') || r.includes('wan')) return 'role-edge';
    if (f.includes('wireless') || r.includes('wireless') || r.includes('ap')) return 'role-wireless';
    return '';
}

function generateTopologyDiagram() {
    const section = document.getElementById('visualDiagramSection');
    const container = document.getElementById('visualTopologyGraphContainer');
    const btn = document.getElementById('toggleDiagramBtn');
    if (!section || !container) return;

    section.style.display = 'block';
    if (btn) btn.innerHTML = '✕ Close Topology Graph';

    if (currentState.devices.length === 0) {
        container.innerHTML = `<div style="color: #cbd5e1; text-align: center; padding: 40px; font-size: 0.95rem;">No network devices added. Add devices on Page 1 or load preset.</div>`;
        return;
    }

    // Group devices according to customTierConfig
    const devicesByTierLevel = {};
    for (let t = 1; t <= 7; t++) {
        devicesByTierLevel[t] = [];
    }

    currentState.devices.forEach(d => {
        let r = d.device_role || "Other";
        if (d.device_function === 'Firewall') r = 'Firewall';
        else if (d.device_function === 'Edge/WAN') r = 'Edge';
        else if (d.device_function === 'Wireless AP') r = 'Wireless AP';

        const tierLevel = customTierConfig.roleTierMap[r] !== undefined ? customTierConfig.roleTierMap[r] : 7;
        if (!devicesByTierLevel[tierLevel]) devicesByTierLevel[tierLevel] = [];
        devicesByTierLevel[tierLevel].push(d);
    });

    const activeTierLevels = Object.keys(devicesByTierLevel)
        .map(Number)
        .filter(t => devicesByTierLevel[t] && devicesByTierLevel[t].length > 0)
        .sort((a, b) => a - b);

    const canvasWidth = container.clientWidth || 1100;
    const layerHeight = 310; // 2x from previous 155px distance
    const startY = 110;

    // Calculate node position map (update y coordinates according to active tier layout)
    const nodeCoords = {};
    let tierBandsHTML = '';

    activeTierLevels.forEach((tierLevel, layerIdx) => {
        const devs = devicesByTierLevel[tierLevel];
        const y = startY + (layerIdx * layerHeight);
        const colSpacing = canvasWidth / (devs.length + 1);
        const tierLabel = customTierConfig.tierLabels[tierLevel] || `TIER ${tierLevel} ARCHITECTURE`;

        // Add visual tier band
        tierBandsHTML += `
            <div class="topo-tier-band" style="top: ${y - (layerHeight / 2)}px; height: ${layerHeight}px;">
                <span class="topo-tier-label"><span class="tier-rank-badge" style="margin-right: 6px;">Tier ${tierLevel}</span> ${tierLabel}</span>
            </div>
        `;

        devs.forEach((dev, colIdx) => {
            const computedX = Math.round(colSpacing * (colIdx + 1));
            // Always set or update default position to match current layer height layout
            if (!topologyNodePositions[dev.hostname]) {
                topologyNodePositions[dev.hostname] = { x: computedX, y: y };
            } else {
                // Keep X if dragged, but update Y to match current tier band
                topologyNodePositions[dev.hostname].y = y;
                if (!topologyNodePositions[dev.hostname].userDragged) {
                    topologyNodePositions[dev.hostname].x = computedX;
                }
            }
            nodeCoords[dev.hostname] = {
                x: topologyNodePositions[dev.hostname].x,
                y: topologyNodePositions[dev.hostname].y,
                dev
            };
        });
    });

    const svgHeight = Math.max(550, startY + (activeTierLevels.length * layerHeight) + 60);

    // Calculate port usage per device
    const portUsage = {};
    currentState.devices.forEach(d => portUsage[d.hostname] = 0);
    currentState.topology_links.forEach(l => {
        if (portUsage[l.source_device] !== undefined) portUsage[l.source_device]++;
        if (portUsage[l.target_device] !== undefined) portUsage[l.target_device]++;
    });

    // Build lookup of all member links per Port-Channel bundle
    const poBundleMembers = {};
    currentState.topology_links.forEach(l => {
        if (l.port_channel_id) {
            const poKey = `${l.port_channel_id}___${[l.source_device, l.target_device].sort().join('___')}`;
            if (!poBundleMembers[poKey]) poBundleMembers[poKey] = [];
            poBundleMembers[poKey].push(l);
        }
    });

    // Render SVG Path Edges & Edge Badges
    let svgPaths = '';
    let edgeBadgesHTML = '';

    currentState.topology_links.forEach((link, idx) => {
        const linkKey = link.id || `${link.source_device}-${link.source_port}---${link.target_device}-${link.target_port}`;
        const src = nodeCoords[link.source_device];
        const tgt = nodeCoords[link.target_device];

        if (src && tgt) {
            const isPo = !!link.port_channel_id;
            const strokeColor = isPo ? '#38bdf8' : '#818cf8';
            const strokeWidth = isPo ? '3.5' : '2';

            const defaultMidX = (src.x + tgt.x) / 2;
            const defaultMidY = (src.y + tgt.y) / 2;

            const isSameTier = Math.abs(src.y - tgt.y) < 20;
            const offset = topologyEdgeOffsets[linkKey] || {
                dx: 0,
                dy: isSameTier ? -28 : 0 // slight curve for horizontal same-tier links so they are clearly separated
            };
            const ctrlX = defaultMidX + offset.dx;
            const ctrlY = defaultMidY + offset.dy;

            const pathD = (offset.dx === 0 && offset.dy === 0)
                ? `M ${src.x} ${src.y} L ${tgt.x} ${tgt.y}`
                : `M ${src.x} ${src.y} Q ${ctrlX} ${ctrlY} ${tgt.x} ${tgt.y}`;

            svgPaths += `
                <path id="topo-edge-line-${linkKey}" d="${pathD}"
                      data-link-key="${linkKey}"
                      stroke="${strokeColor}" stroke-width="${strokeWidth}" 
                      stroke-dasharray="${isPo ? 'none' : '6,4'}" fill="none" opacity="0.95"
                      filter="url(#neon-glow)"/>
            `;

            let badgeInner = '';
            if (isPo) {
                const poKey = `${link.port_channel_id}___${[link.source_device, link.target_device].sort().join('___')}`;
                const memberLinks = poBundleMembers[poKey] || [link];
                const poGroup = currentState.port_channels.find(p => p.id === link.port_channel_id);
                const protocol = poGroup?.protocol || "LACP";

                let portRowsHTML = '';
                memberLinks.forEach(m => {
                    portRowsHTML += `
                        <div class="po-port-pair-row">
                            <span>${m.source_port}</span>
                            <span class="arrow">↔</span>
                            <span>${m.target_port}</span>
                        </div>
                    `;
                });

                badgeInner = `
                    <div class="po-full-details-box">
                        <div class="po-full-header">
                            <span class="po-id">📦 ${link.port_channel_id}</span>
                            <span class="po-meta">${protocol} &bull; ${link.link_speed || '10G'}</span>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 3px;">
                            ${portRowsHTML}
                        </div>
                    </div>
                `;
            } else {
                badgeInner = `🔗 ${link.source_port} ↔ ${link.target_port} <span style="margin-left: 4px; padding: 1px 5px; border-radius: 4px; background: rgba(129, 140, 248, 0.25); color: #c7d2fe; font-size: 0.7rem; font-weight: 800;">${link.link_speed || '1G'}</span>`;
            }

            edgeBadgesHTML += `
                <div class="topo-edge-badge" id="topo-edge-badge-${linkKey}"
                     data-link-key="${linkKey}"
                     style="left: ${ctrlX}px; top: ${ctrlY}px; border-color: ${strokeColor};">
                    ${badgeInner}
                </div>
            `;
        }
    });

    // Render Node Overlay Cards
    let nodesHTML = '';
    Object.keys(nodeCoords).forEach(host => {
        const { x, y, dev } = nodeCoords[host];
        const icon = dev.device_function === 'Firewall' ? '🛡️' :
            dev.device_function === 'Wireless AP' ? '📡' :
                dev.device_function === 'Edge/WAN' ? '🌐' : '🖧';

        const roleClass = getRoleClass(dev.device_role, dev.device_function);
        const usedCount = portUsage[dev.hostname] || 0;

        nodesHTML += `
            <div class="topo-diagram-node ${roleClass}" id="topo-node-${dev.hostname}" data-hostname="${dev.hostname}" style="left: ${x - 90}px; top: ${y - 45}px;">
                <div style="display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 4px; pointer-events: none;">
                    <span style="font-size: 1.2rem;">${icon}</span>
                    <span style="font-weight: 800; font-size: 0.95rem; color: #ffffff;">${dev.hostname}</span>
                </div>
                <div style="display: flex; justify-content: center; gap: 4px; margin-bottom: 4px; pointer-events: none;">
                    <span class="badge badge-role" style="font-size: 0.65rem; padding: 2px 6px;">${dev.device_role}</span>
                    <span class="badge badge-func" style="font-size: 0.65rem; padding: 2px 6px;">${dev.vendor}</span>
                </div>
                <div style="font-size: 0.72rem; color: #38bdf8; font-family: 'JetBrains Mono'; pointer-events: none;">${dev.management_ip}</div>
                <div style="font-size: 0.68rem; color: var(--text-dim); margin-top: 2px; pointer-events: none;">${usedCount}/${dev.num_ports} Ports Active</div>
            </div>
        `;
    });

    container.innerHTML = `
        <div id="topoCanvasWrapper" style="position: relative; width: 100%; height: ${svgHeight}px; background: rgba(7, 10, 19, 0.98); border-radius: 12px; overflow: hidden; border: 1px solid var(--border-accent); user-select: none;">
            ${tierBandsHTML}
            <svg id="topoSvgCanvas" width="100%" height="${svgHeight}px" style="position: absolute; top:0; left:0; width:100%; height:100%; pointer-events: auto;">
                <defs>
                    <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="0" dy="0" stdDeviation="2" flood-color="#38bdf8" flood-opacity="0.6"/>
                    </filter>
                </defs>
                ${svgPaths}
            </svg>
            ${edgeBadgesHTML}
            ${nodesHTML}
        </div>
    `;

    setupTopologyDragHandlers();
    setupEdgeHoverHandlers();
}

/**
 * Setup hover effects: Hovering on link path or badge highlights the link and shows the details
 */
function setupEdgeHoverHandlers() {
    const wrapper = document.getElementById('topoCanvasWrapper');
    if (!wrapper) return;

    wrapper.querySelectorAll('path[id^="topo-edge-line-"]').forEach(pathEl => {
        const linkKey = pathEl.getAttribute('data-link-key');
        const badgeEl = document.getElementById(`topo-edge-badge-${linkKey}`);

        pathEl.addEventListener('mouseenter', () => {
            if (badgeEl) badgeEl.classList.add('hovered');
            pathEl.setAttribute('stroke-width', '5.5');
        });

        pathEl.addEventListener('mouseleave', () => {
            if (badgeEl) badgeEl.classList.remove('hovered');
            const link = currentState.topology_links.find(l => (l.id || `${l.source_device}-${l.source_port}---${l.target_device}-${l.target_port}`) === linkKey);
            const isPo = link && !!link.port_channel_id;
            pathEl.setAttribute('stroke-width', isPo ? '3.5' : '2');
        });
    });

    wrapper.querySelectorAll('.topo-edge-badge').forEach(badgeEl => {
        const linkKey = badgeEl.getAttribute('data-link-key');
        const pathEl = document.getElementById(`topo-edge-line-${linkKey}`);

        badgeEl.addEventListener('mouseenter', () => {
            badgeEl.classList.add('hovered');
            if (pathEl) pathEl.setAttribute('stroke-width', '5.5');
        });

        badgeEl.addEventListener('mouseleave', () => {
            badgeEl.classList.remove('hovered');
            if (pathEl) {
                const link = currentState.topology_links.find(l => (l.id || `${l.source_device}-${l.source_port}---${l.target_device}-${l.target_port}`) === linkKey);
                const isPo = link && !!link.port_channel_id;
                pathEl.setAttribute('stroke-width', isPo ? '3.5' : '2');
            }
        });
    });
}

/**
 * Attach mouse listeners for interactive node dragging and edge bending
 */
function setupTopologyDragHandlers() {
    const wrapper = document.getElementById('topoCanvasWrapper');
    if (!wrapper) return;

    let activeDragType = null; // 'node' or 'edge'
    let dragTarget = null;
    let startX = 0, startY = 0;
    let initialX = 0, initialY = 0;

    // Node Dragging
    wrapper.querySelectorAll('.topo-diagram-node').forEach(nodeEl => {
        nodeEl.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            e.stopPropagation();
            activeDragType = 'node';
            dragTarget = nodeEl;
            nodeEl.classList.add('dragging');

            const host = nodeEl.getAttribute('data-hostname');
            startX = e.clientX;
            startY = e.clientY;
            initialX = topologyNodePositions[host].x;
            initialY = topologyNodePositions[host].y;

            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        });
    });

    // Edge Dragging
    wrapper.querySelectorAll('.topo-edge-badge').forEach(badgeEl => {
        badgeEl.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            e.stopPropagation();
            activeDragType = 'edge';
            dragTarget = badgeEl;
            badgeEl.classList.add('dragging');

            const linkKey = badgeEl.getAttribute('data-link-key');
            startX = e.clientX;
            startY = e.clientY;

            const link = currentState.topology_links.find(l => (l.id || `${l.source_device}-${l.source_port}---${l.target_device}-${l.target_port}`) === linkKey);
            if (link) {
                const src = topologyNodePositions[link.source_device];
                const tgt = topologyNodePositions[link.target_device];
                const defaultMidX = (src.x + tgt.x) / 2;
                const defaultMidY = (src.y + tgt.y) / 2;
                const offset = topologyEdgeOffsets[linkKey] || { dx: 0, dy: 0 };

                initialX = defaultMidX + offset.dx;
                initialY = defaultMidY + offset.dy;
            }

            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        });
    });

    function onMouseMove(e) {
        if (!activeDragType || !dragTarget) return;

        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        if (activeDragType === 'node') {
            const host = dragTarget.getAttribute('data-hostname');
            const maxW = (wrapper.clientWidth || 1100) - 90;
            const newX = Math.max(90, Math.min(maxW, initialX + dx));
            const newY = Math.max(40, initialY + dy);

            topologyNodePositions[host] = { x: newX, y: newY, userDragged: true };
            dragTarget.style.left = `${newX - 90}px`;
            dragTarget.style.top = `${newY - 45}px`;

            updateAllConnectedEdges();
        } else if (activeDragType === 'edge') {
            const linkKey = dragTarget.getAttribute('data-link-key');
            const newCtrlX = initialX + dx;
            const newCtrlY = initialY + dy;

            const link = currentState.topology_links.find(l => (l.id || `${l.source_device}-${l.source_port}---${l.target_device}-${l.target_port}`) === linkKey);
            if (link) {
                const src = topologyNodePositions[link.source_device];
                const tgt = topologyNodePositions[link.target_device];
                const defaultMidX = (src.x + tgt.x) / 2;
                const defaultMidY = (src.y + tgt.y) / 2;

                topologyEdgeOffsets[linkKey] = {
                    dx: newCtrlX - defaultMidX,
                    dy: newCtrlY - defaultMidY
                };

                dragTarget.style.left = `${newCtrlX}px`;
                dragTarget.style.top = `${newCtrlY}px`;

                const pathEl = document.getElementById(`topo-edge-line-${linkKey}`);
                if (pathEl) {
                    pathEl.setAttribute('d', `M ${src.x} ${src.y} Q ${newCtrlX} ${newCtrlY} ${tgt.x} ${tgt.y}`);
                }
            }
        }
    }

    function onMouseUp() {
        if (dragTarget) {
            dragTarget.classList.remove('dragging');
        }
        activeDragType = null;
        dragTarget = null;
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
    }

    function updateAllConnectedEdges() {
        currentState.topology_links.forEach(link => {
            const linkKey = link.id || `${link.source_device}-${link.source_port}---${link.target_device}-${link.target_port}`;
            const src = topologyNodePositions[link.source_device];
            const tgt = topologyNodePositions[link.target_device];

            if (src && tgt) {
                const defaultMidX = (src.x + tgt.x) / 2;
                const defaultMidY = (src.y + tgt.y) / 2;
                const offset = topologyEdgeOffsets[linkKey] || { dx: 0, dy: 0 };
                const ctrlX = defaultMidX + offset.dx;
                const ctrlY = defaultMidY + offset.dy;

                const pathEl = document.getElementById(`topo-edge-line-${linkKey}`);
                if (pathEl) {
                    const pathD = (offset.dx === 0 && offset.dy === 0)
                        ? `M ${src.x} ${src.y} L ${tgt.x} ${tgt.y}`
                        : `M ${src.x} ${src.y} Q ${ctrlX} ${ctrlY} ${tgt.x} ${tgt.y}`;
                    pathEl.setAttribute('d', pathD);
                }

                const badgeEl = document.getElementById(`topo-edge-badge-${linkKey}`);
                if (badgeEl) {
                    badgeEl.style.left = `${ctrlX}px`;
                    badgeEl.style.top = `${ctrlY}px`;
                }
            }
        });
    }
}

async function downloadEvidenceWorkbook() {
    try {
        let response;
        if (currentState && (currentState.devices || currentState.project_name)) {
            response = await fetch('/api/export/excel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentState)
            });
        } else {
            response = await fetch('/api/export/excel');
        }

        if (!response.ok) {
            throw new Error(`Export failed with status ${response.status}`);
        }

        const blob = await response.blob();
        const comp = (currentState && currentState.company_name) || (currentState?.devices?.[0]?.company_name) || "Enterprise";
        const site = (currentState && currentState.site_location) || (currentState?.devices?.[0]?.site_location) || "Site";
        const safeComp = comp.replace(/[^a-zA-Z0-9]/g, '_');
        const safeSite = site.replace(/[^a-zA-Z0-9]/g, '_');
        const filename = `${safeComp}_${safeSite}_Audit_Evidence.xlsx`;

        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(blobUrl);
        a.remove();
        if (typeof showToast === 'function') {
            showToast(`Workbook exported: ${filename}`, 'success');
        }
    } catch (err) {
        console.error('Download error:', err);
        window.location.href = '/api/export/excel';
    }
}

function openNewFileModal() {
    const modal = document.getElementById('newProjectModal');
    if (modal) {
        modal.classList.add('active');
        const compInput = document.getElementById('newCompanyInput');
        if (compInput) {
            compInput.focus();
            compInput.select();
        }
    }
}

function closeNewFileModal() {
    const modal = document.getElementById('newProjectModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function switchProjectManagerTab(tab) {
    const createTab = document.getElementById('projTabCreate');
    const pastTab = document.getElementById('projTabPastWork');
    const createPane = document.getElementById('projCreatePane');
    const pastPane = document.getElementById('projPastWorkPane');

    if (createTab && pastTab) {
        if (tab === 'create') {
            createTab.style.borderBottomColor = '#38bdf8';
            createTab.style.color = '#38bdf8';
            pastTab.style.borderBottomColor = 'transparent';
            pastTab.style.color = 'var(--text-dim)';
            if (createPane) createPane.style.display = 'block';
            if (pastPane) pastPane.style.display = 'none';
        } else {
            pastTab.style.borderBottomColor = '#38bdf8';
            pastTab.style.color = '#38bdf8';
            createTab.style.borderBottomColor = 'transparent';
            createTab.style.color = 'var(--text-dim)';
            if (createPane) createPane.style.display = 'none';
            if (pastPane) pastPane.style.display = 'block';
        }
    }
    loadSavedFilesList();
}

async function loadSavedFilesList() {
    const container = document.getElementById('savedFilesListContainer');
    if (!container) return;
    container.innerHTML = `<div style="text-align: center; padding: 24px; color: var(--text-dim); font-size: 0.85rem;">
        <span class="spinner-small" style="margin-right: 8px;"></span> Loading saved files...
    </div>`;

    try {
        const res = await fetch('/api/project/saved-files');
        const data = await res.json();
        const files = data.files || [];

        if (files.length === 0) {
            container.innerHTML = `<div style="text-align: center; padding: 30px; color: var(--text-dim);">
                <div style="font-size: 2rem; margin-bottom: 8px;">📭</div>
                <div style="font-size: 0.9rem; font-weight: 600;">No saved project files found</div>
                <div style="font-size: 0.78rem; margin-top: 4px;">Export a workbook to save your work here.</div>
            </div>`;
            return;
        }

        let html = '';
        files.forEach((f, idx) => {
            const isActive = currentState && (
                f.filename.includes((currentState.company_name || '').replace(/[^a-zA-Z0-9]/g, '_')) ||
                f.filename.includes('BLRCC002')
            );
            const activeBadge = isActive ? `<span style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; font-weight: 700;">CURRENT</span>` : '';
            html += `
            <div class="saved-file-row" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px;
                border-bottom: 1px solid rgba(255,255,255,0.04); transition: background 0.15s; cursor: pointer;"
                onmouseover="this.style.background='rgba(56, 189, 248, 0.06)'"
                onmouseout="this.style.background='transparent'"
                onclick="loadSavedProjectFile('${f.filename.replace(/'/g, "\\'")}')">
                <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0;">
                    <div style="font-size: 1.5rem; flex-shrink: 0;">📊</div>
                    <div style="min-width: 0;">
                        <div style="font-weight: 600; font-size: 0.88rem; color: #e2e8f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            ${f.filename} ${activeBadge}
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 2px;">
                            ${f.size_kb} KB &bull; Modified: ${f.modified}
                        </div>
                    </div>
                </div>
                <button class="btn btn-sm" style="flex-shrink: 0; font-size: 0.78rem; padding: 6px 14px;"
                    onclick="event.stopPropagation(); loadSavedProjectFile('${f.filename.replace(/'/g, "\\'")}')">
                    📂 Load
                </button>
            </div>`;
        });
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<div style="text-align: center; padding: 24px; color: #f87171; font-size: 0.85rem;">
            Failed to load saved files: ${err.message}
        </div>`;
    }
}

async function loadSavedProjectFile(filename) {
    if (!confirm(`Load project "${filename}"?\nThis will replace your current workspace data.`)) return;
    try {
        const res = await fetch('/api/project/load-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
        });
        if (!res.ok) {
            const errData = await res.json();
            alert("Failed to load file: " + (errData.detail || "Unknown error"));
            return;
        }
        currentState = await res.json();
        renderInventoryTable();
        renderTopologyStage();
        if (currentStage === 3) renderAuditStage();
        closeNewFileModal();
        alert(`Project loaded from "${filename}" successfully!`);
    } catch (err) {
        alert("Failed to load project file: " + err);
    }
}

async function submitNewProject() {
    const company = document.getElementById('newCompanyInput').value.trim() || "Acme Corp";
    const site = document.getElementById('newSiteInput').value.trim() || "HQ Primary DC";

    try {
        const res = await fetch('/api/project/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                company_name: company,
                site_location: site,
                project_name: `${company} ${site} Audit`
            })
        });
        if (!res.ok) {
            const errData = await res.json();
            alert("Validation Error: " + (errData.detail || "A project with this file name already exists."));
            return;
        }

        currentState = await res.json();
        renderInventoryTable();
        renderTopologyStage();
        if (currentStage === 3) renderAuditStage();
        closeNewFileModal();
        alert(`New Audit Project created for ${company} (${site})!`);
    } catch (err) {
        alert("Failed to create new file: " + err);
    }
}

function triggerExcelImport() {
    const fileInput = document.getElementById('excelFileInput');
    if (fileInput) {
        fileInput.value = '';
        fileInput.click();
    }
}

async function handleExcelImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx')) {
        alert("Please select a valid .xlsx Excel workbook file.");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/import/excel', {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const errData = await res.json();
            alert("Import failed: " + (errData.detail || "Unknown error"));
            return;
        }

        currentState = await res.json();

        // Close project manager panel if open
        closeNewFileModal();

        // Re-render UI views
        renderInventoryTable();
        renderTopologyStage();
        if (currentStage === 3) {
            renderAuditStage();
        } else {
            alert(`Excel Worksheet imported successfully!\nLoaded ${currentState.devices.length} devices, ${currentState.topology_links.length} links, and ${currentState.device_audit_tasks.length} audit tasks.`);
        }
    } catch (err) {
        alert("Failed to import Excel worksheet: " + err);
    }
}

/* ==========================================================================
   STAGE 3: DEVICE AUDIT & PROTOCOL VERIFICATION
   ========================================================================== */

const AUDIT_STATUS_COLORS = {
    'In-Complete': { bg: 'rgba(148,163,184,0.15)', border: '#64748b', text: '#94a3b8', icon: '⏳' },
    'Completed': { bg: 'rgba(16,185,129,0.15)', border: '#10b981', text: '#6ee7b7', icon: '✅' },
    'Warning': { bg: 'rgba(245,158,11,0.15)', border: '#f59e0b', text: '#fde047', icon: '⚠️' },
    'Failed': { bg: 'rgba(239,68,68,0.15)', border: '#ef4444', text: '#fca5a5', icon: '❌' },
    'N/A': { bg: 'rgba(100,116,139,0.12)', border: '#475569', text: '#94a3b8', icon: '➖' }
};


async function renderAuditStage() {
    renderAuditDeviceList(document.getElementById('auditDeviceSearch')?.value || '');
    renderFinalAuditMatrix();
    updateAuditMetricsBar();

    // Auto-select first device if none selected yet
    if (!selectedAuditDevice && currentState.devices && currentState.devices.length > 0) {
        selectAuditDevice(currentState.devices[0].hostname);
    }
}

function renderAuditDeviceList(filterQuery = '') {
    const container = document.getElementById('auditDeviceList');
    if (!container) return;
    container.innerHTML = '';

    const query = filterQuery.toLowerCase().trim();
    const filteredDevices = currentState.devices.filter(d => {
        if (!query) return true;
        return d.hostname.toLowerCase().includes(query) ||
            d.vendor.toLowerCase().includes(query) ||
            d.device_role.toLowerCase().includes(query) ||
            d.device_function.toLowerCase().includes(query) ||
            d.device_model.toLowerCase().includes(query);
    });

    if (filteredDevices.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 30px; color: var(--text-dim);">No devices match your search.</div>`;
        return;
    }

    filteredDevices.forEach(dev => {
        // Count tasks for this device from currentState
        const devTasks = (currentState.device_audit_tasks || []).filter(t => t.device_hostname === dev.hostname);
        const total = devTasks.length;
        const completed = devTasks.filter(t => t.status === 'Completed' || t.status === 'N/A' || t.status === 'Warning').length;
        const failed = devTasks.filter(t => t.status === 'Failed').length;
        const pct = total > 0 ? Math.round(completed / total * 100) : 0;

        const protocols = [...new Set(devTasks.map(t => t.protocol))];
        const isSelected = selectedAuditDevice === dev.hostname;

        const icon = dev.device_function === 'Firewall' ? '🛡️' :
            dev.device_function === 'Wireless AP' ? '📡' :
                dev.device_function === 'Edge/WAN' ? '🌐' : '🖧';

        const vendorClass = dev.vendor.toLowerCase().replace(/\s/g, '-');

        const card = document.createElement('div');
        card.className = `audit-device-card ${isSelected ? 'selected' : ''}`;
        card.onclick = () => selectAuditDevice(dev.hostname);
        card.innerHTML = `
            <div class="audit-dev-card-header">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.4rem;">${icon}</span>
                    <div>
                        <div class="audit-dev-hostname">${dev.hostname}</div>
                        <div class="audit-dev-meta">${dev.vendor} ${dev.device_model}</div>
                    </div>
                </div>
                <span class="badge badge-role" style="font-size: 0.7rem;">${dev.device_role}</span>
            </div>
            <div class="audit-dev-card-body">
                <div class="audit-dev-protocols">
                    ${protocols.slice(0, 6).map(p => `<span class="audit-proto-tag">${p}</span>`).join('')}
                    ${protocols.length > 6 ? `<span class="audit-proto-tag" style="background: rgba(255,255,255,0.1);">+${protocols.length - 6}</span>` : ''}
                </div>
                <div class="audit-dev-progress">
                    <div class="audit-progress-bar">
                        <div class="audit-progress-fill ${failed > 0 ? 'has-fail' : ''}" style="width: ${pct}%;"></div>
                    </div>
                    <span class="audit-progress-label">${completed}/${total} Tasks</span>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function searchAuditDevices(query) {
    renderAuditDeviceList(query);
}

async function selectAuditDevice(hostname) {
    selectedAuditDevice = hostname;
    activeProtocolFilter = null;

    // Highlight selected card
    document.querySelectorAll('.audit-device-card').forEach(c => c.classList.remove('selected'));
    const allCards = document.querySelectorAll('.audit-device-card');
    allCards.forEach(c => {
        const h = c.querySelector('.audit-dev-hostname');
        if (h && h.textContent === hostname) c.classList.add('selected');
    });

    try {
        const res = await fetch(`/api/audit/device/${encodeURIComponent(hostname)}/tasks`);
        selectedAuditDeviceData = await res.json();
        renderDeviceAuditHeader(selectedAuditDeviceData);
        renderProtocolFilterPills(selectedAuditDeviceData);
        renderDeviceAuditTasks(selectedAuditDeviceData);
    } catch (err) {
        console.error('Failed to load device audit tasks:', err);
    }
}

function renderDeviceAuditHeader(data) {
    const header = document.getElementById('auditTaskHeader');
    if (!header) return;

    const pct = data.total_tasks > 0 ? Math.round(data.completed_tasks / data.total_tasks * 100) : 0;

    header.innerHTML = `
        <div class="audit-header-info">
            <div style="display: flex; align-items: center; gap: 14px;">
                <div class="audit-header-icon">${data.device_function === 'Firewall' ? '🛡️' : data.device_function === 'Wireless AP' ? '📡' : data.device_function === 'Edge/WAN' ? '🌐' : '🖧'}</div>
                <div>
                    <div class="audit-header-hostname">${data.hostname}</div>
                    <div class="audit-header-meta">${data.vendor} ${data.device_model} &bull; <code>${data.os_version}</code> &bull; ${data.management_ip}</div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <div class="audit-header-stats">
                    <span class="badge badge-func">${data.device_classification}</span>
                    <span class="badge badge-role">${data.device_role}</span>
                </div>
                <div class="audit-header-progress">
                    <div class="audit-header-pct">${pct}%</div>
                    <div style="font-size: 0.78rem; color: var(--text-dim);">${data.completed_tasks}/${data.total_tasks} Done</div>
                </div>
            </div>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap;">
            <button class="btn btn-sm" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); font-weight: 700;" onclick="openAuditTriggerModal('device', '${data.hostname}')">⚡ Trigger Device Audit</button>
            <button class="btn btn-secondary btn-sm" onclick="downloadAuditFiles('${data.hostname}')">📥 Download .cfg Logs</button>
            <button class="btn btn-secondary btn-sm" onclick="batchUpdateDeviceTasks('${data.hostname}', 'Completed')">✅ Mark All Completed</button>
            <button class="btn btn-secondary btn-sm" onclick="batchUpdateDeviceTasks('${data.hostname}', 'In-Complete')">↩️ Reset All</button>
        </div>
    `;
}

function renderProtocolFilterPills(data) {
    const container = document.getElementById('auditProtocolFilters');
    if (!container) return;
    container.style.display = 'flex';
    container.innerHTML = '';

    const allPill = document.createElement('button');
    allPill.className = `audit-filter-pill ${!activeProtocolFilter ? 'active' : ''}`;
    allPill.textContent = `All (${data.total_tasks})`;
    allPill.onclick = () => {
        activeProtocolFilter = null;
        renderProtocolFilterPills(data);
        renderDeviceAuditTasks(data);
    };
    container.appendChild(allPill);

    data.protocols.forEach(proto => {
        const count = data.tasks.filter(t => t.protocol === proto).length;
        const pill = document.createElement('button');
        pill.className = `audit-filter-pill ${activeProtocolFilter === proto ? 'active' : ''}`;
        pill.textContent = `${proto} (${count})`;
        pill.onclick = () => {
            activeProtocolFilter = proto;
            renderProtocolFilterPills(data);
            renderDeviceAuditTasks(data);
        };
        container.appendChild(pill);
    });
}

function formatClientTimestamp(tsStr) {
    if (!tsStr) return '';
    try {
        // Handle standard YYYY-MM-DD HH:mm:ss strings
        const isoLike = tsStr.includes(' ') ? tsStr.replace(' ', 'T') : tsStr;
        const d = new Date(isoLike);
        if (!isNaN(d.getTime())) {
            return d.toLocaleString(undefined, {
                month: 'short', day: '2-digit',
                hour: '2-digit', minute: '2-digit', second: '2-digit'
            });
        }
    } catch (_) {}
    return tsStr;
}

function toggleTaskCommandEditor(taskId) {
    const el = document.getElementById(`cmdEditor_${taskId}`);
    if (el) {
        const isHidden = (el.style.display === 'none');
        el.style.display = isHidden ? 'block' : 'none';
        if (isHidden) {
            const input = document.getElementById(`retryInput_${taskId}`);
            if (input) {
                input.focus();
                input.select();
            }
        }
    }
}

function renderDeviceAuditTasks(data) {
    const container = document.getElementById('auditTaskList');
    if (!container) return;
    container.innerHTML = '';

    const tasks = activeProtocolFilter
        ? data.tasks.filter(t => t.protocol === activeProtocolFilter)
        : data.tasks;

    // Group by category
    const categories = {};
    tasks.forEach(t => {
        if (!categories[t.category]) categories[t.category] = [];
        categories[t.category].push(t);
    });

    Object.keys(categories).forEach(cat => {
        const catTasks = categories[cat];
        const catCompleted = catTasks.filter(t => t.status === 'Completed' || t.status === 'N/A' || t.status === 'Warning').length;

        const catSection = document.createElement('div');
        catSection.className = 'audit-category-section';
        catSection.innerHTML = `
            <div class="audit-category-header" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span>${cat}</span>
                    <span class="audit-category-count">${catCompleted}/${catTasks.length}</span>
                </div>
                <button class="btn btn-secondary btn-sm" style="font-size: 0.74rem; padding: 4px 10px;" onclick="openAuditTriggerModal('section', '${data.hostname}', '${escapeJsString(cat)}')">
                    ⚡ Run Section
                </button>
            </div>
        `;

        catTasks.forEach(task => {
            const sc = AUDIT_STATUS_COLORS[task.status] || AUDIT_STATUS_COLORS['In-Complete'];

            const sevColors = {
                'Critical': '#ef4444', 'High': '#f59e0b', 'Medium': '#38bdf8', 'Low': '#10b981', 'Info': '#94a3b8'
            };

            const isRunningConfig = (task.protocol === 'Running Config' || (task.title && task.title.toLowerCase().includes('running configuration')));
            const isErrorOrWarning = (task.status === 'Failed' || task.status === 'Warning');
            const editorBg = task.status === 'Failed' ? 'rgba(239, 68, 68, 0.08)' : (task.status === 'Warning' ? 'rgba(245, 158, 11, 0.08)' : 'rgba(56, 189, 248, 0.08)');
            const editorBorder = task.status === 'Failed' ? 'rgba(239, 68, 68, 0.3)' : (task.status === 'Warning' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(56, 189, 248, 0.3)');
            const editorColor = task.status === 'Failed' ? '#fca5a5' : (task.status === 'Warning' ? '#fde68a' : '#7dd3fc');
            const editorIcon = task.status === 'Failed' ? '⚠️ Command Error' : (task.status === 'Warning' ? '⚠️ Command Warning' : '✏️ Modify Command');

            const taskCard = document.createElement('div');
            taskCard.className = 'audit-task-card';
            taskCard.id = `taskCard_${task.id}`;
            taskCard.style.borderLeftColor = sc.border;
            taskCard.innerHTML = `
                <div class="audit-task-card-top">
                    <div class="audit-task-info">
                        <div class="audit-task-title" style="display: flex; align-items: center; flex-wrap: wrap; gap: 6px;">
                            <span style="color: ${sevColors[task.severity] || '#38bdf8'}; font-size: 0.7rem;">●</span>
                            <span>${task.title}</span>
                            ${isRunningConfig ? `<span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;">💾 Priority 1: Baseline Backup</span>` : ''}
                        </div>
                        <div class="audit-task-desc">${task.description}</div>
                        <div class="audit-task-condition">
                            <span class="audit-proto-tag">${task.protocol}</span>
                            <span style="color: var(--text-dim); font-size: 0.78rem;">Condition: ${task.condition}</span>
                            ${task.timestamp ? `<span style="color: var(--text-dim); font-size: 0.75rem; margin-left: 8px;">🕒 ${formatClientTimestamp(task.timestamp)}</span>` : ''}
                        </div>
                    </div>
                </div>
                <div class="audit-task-cli-row">
                    <code class="audit-cli-command" id="cmdText_${task.id}" onclick="toggleTaskCommandEditor('${task.id}')" title="Click to modify command" style="cursor: pointer;">${escapeHtml(task.verification_command)}</code>
                    <button class="btn btn-sm" style="background: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; color: #38bdf8; font-size: 0.76rem;" onclick="toggleTaskCommandEditor('${task.id}')" title="Modify CLI Command &amp; Re-run">
                        ✏️ Edit Command
                    </button>
                    <button class="btn btn-sm audit-run-btn" style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981; font-size: 0.76rem;" onclick="openAuditTriggerModal('task', '${data.hostname}', null, '${task.id}')" title="Run Command Live on Device">
                        ▶️ Run
                    </button>
                    <button class="btn btn-secondary btn-sm audit-copy-btn" onclick="copyCommandToClipboard('${escapeJsString(task.verification_command)}', this)" title="Copy CLI Command">
                        📋 Copy
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="openEvidenceModal('${task.id}')" title="View Logs &amp; Evidence Notes">
                        📝 Notes
                    </button>
                </div>
                <div class="audit-task-status-row">
                    <div class="audit-status-toggle">
                        ${['In-Complete', 'Completed', 'Warning', 'Failed', 'N/A'].map(s => `
                            <button class="audit-status-btn ${task.status === s ? 'active' : ''}" 
                                    data-status="${s}"
                                    style="${task.status === s ? `background: ${AUDIT_STATUS_COLORS[s].bg}; border-color: ${AUDIT_STATUS_COLORS[s].border}; color: ${AUDIT_STATUS_COLORS[s].text};` : ''}"
                                    onclick="updateTaskStatus('${task.id}', '${s}')">
                                ${AUDIT_STATUS_COLORS[s].icon} ${s}
                            </button>
                        `).join('')}
                    </div>
                </div>
                ${task.evidence_notes ? `<div class="audit-task-evidence" style="margin-top: 6px;"><strong>Notes/Error:</strong> ${escapeHtml(task.evidence_notes)}</div>` : ''}
                <div id="cmdEditor_${task.id}" class="audit-task-error-editor" style="margin-top: 10px; background: ${editorBg}; border: 1px solid ${editorBorder}; border-radius: var(--radius-sm); padding: 10px 12px; display: ${isErrorOrWarning ? 'block' : 'none'};">
                    <div style="font-size: 0.78rem; color: ${editorColor}; font-weight: 700; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between;">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span>${editorIcon}</span>
                            <span style="font-weight: 400; color: var(--text-dim);">Edit show command and press Enter or Test &amp; Run to execute live:</span>
                        </div>
                        <button type="button" class="btn btn-secondary btn-sm" style="padding: 1px 6px; font-size: 0.7rem; border-radius: 4px;" onclick="toggleTaskCommandEditor('${task.id}')">✕</button>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <input type="text" id="retryInput_${task.id}" value="${escapeHtml(task.verification_command)}" onkeydown="if(event.key==='Enter') retryTaskCommand('${task.id}', '${escapeJsString(task.device_hostname)}')" placeholder="Enter command e.g. show version..." style="flex: 1; font-family: monospace; font-size: 0.82rem; padding: 7px 10px; background: rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.25); border-radius: 4px; color: #f8fafc;">
                        <button class="btn btn-sm" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; white-space: nowrap; font-weight: 700; padding: 7px 14px;" onclick="retryTaskCommand('${task.id}', '${escapeJsString(task.device_hostname)}')">
                            ⚡ Test &amp; Run
                        </button>
                    </div>
                    <div id="retryErrorLabel_${task.id}" style="display: none; margin-top: 6px; font-size: 0.76rem; color: #fca5a5;"></div>
                </div>
            `;
            catSection.appendChild(taskCard);
        });

        container.appendChild(catSection);
    });
}


function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escapeJsString(str) {
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}

async function copyCommandToClipboard(cmd, btnEl) {
    try {
        await navigator.clipboard.writeText(cmd);
        const orig = btnEl.innerHTML;
        btnEl.innerHTML = '✅ Copied!';
        btnEl.style.borderColor = '#10b981';
        setTimeout(() => {
            btnEl.innerHTML = orig;
            btnEl.style.borderColor = '';
        }, 1500);
    } catch (err) {
        // Fallback
        const ta = document.createElement('textarea');
        ta.value = cmd;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        btnEl.innerHTML = '✅ Copied!';
        setTimeout(() => { btnEl.innerHTML = '📋 Copy'; }, 1500);
    }
}

async function updateTaskStatus(taskId, status) {
    try {
        const res = await fetch(`/api/audit/task/${encodeURIComponent(taskId)}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        const result = await res.json();

        // Update local state
        if (currentState.device_audit_tasks) {
            const idx = currentState.device_audit_tasks.findIndex(t => t.id === taskId);
            if (idx >= 0) currentState.device_audit_tasks[idx].status = status;
        }

        // Refresh the task view
        if (selectedAuditDevice && selectedAuditDeviceData) {
            const task = selectedAuditDeviceData.tasks.find(t => t.id === taskId);
            if (task) task.status = status;
            renderDeviceAuditTasks(selectedAuditDeviceData);
            // Update header counts
            selectedAuditDeviceData.completed_tasks = selectedAuditDeviceData.tasks.filter(t => t.status === 'Completed' || t.status === 'N/A' || t.status === 'Warning').length;
            selectedAuditDeviceData.failed_tasks = selectedAuditDeviceData.tasks.filter(t => t.status === 'Failed').length;
            renderDeviceAuditHeader(selectedAuditDeviceData);
        }

        renderAuditDeviceList(document.getElementById('auditDeviceSearch')?.value || '');
        updateAuditMetricsBar();
        renderFinalAuditMatrix();
    } catch (err) {
        console.error('Failed to update task status:', err);
    }
}

async function batchUpdateDeviceTasks(hostname, status) {
    if (!confirm(`Are you sure you want to set all tasks for ${hostname} to "${status}"?`)) return;
    try {
        await fetch('/api/audit/tasks/batch_update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hostname, status })
        });

        // Refresh
        if (selectedAuditDevice === hostname) {
            await selectAuditDevice(hostname);
        }
        // Reload full state for device list metrics
        const stateRes = await fetch('/api/state');
        currentState = await stateRes.json();
        renderAuditDeviceList(document.getElementById('auditDeviceSearch')?.value || '');
        updateAuditMetricsBar();
        renderFinalAuditMatrix();
    } catch (err) {
        console.error('Batch update failed:', err);
    }
}

async function batchMarkAllVerified() {
    if (!confirm('Mark ALL audit tasks across ALL devices as Completed?')) return;
    try {
        await fetch('/api/audit/tasks/batch_update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'Completed' })
        });
        const stateRes = await fetch('/api/state');
        currentState = await stateRes.json();
        renderAuditStage();
        if (selectedAuditDevice) await selectAuditDevice(selectedAuditDevice);
    } catch (err) {
        console.error('Batch mark all failed:', err);
    }
}

function filterAuditTasksByProtocol(protocol) {
    activeProtocolFilter = protocol;
    if (selectedAuditDeviceData) {
        renderProtocolFilterPills(selectedAuditDeviceData);
        renderDeviceAuditTasks(selectedAuditDeviceData);
    }
}

// Evidence Notes Modal
function openEvidenceModal(taskId) {
    const task = selectedAuditDeviceData?.tasks?.find(t => t.id === taskId);
    document.getElementById('evidenceTaskId').value = taskId;
    document.getElementById('evidenceOutputField').value = task?.actual_output || '';
    document.getElementById('evidenceNotesField').value = task?.evidence_notes || '';
    document.getElementById('evidenceNotesModal').classList.add('active');
}

function closeEvidenceModal() {
    document.getElementById('evidenceNotesModal').classList.remove('active');
}

async function saveEvidenceNotes() {
    const taskId = document.getElementById('evidenceTaskId').value;
    const output = document.getElementById('evidenceOutputField').value;
    const notes = document.getElementById('evidenceNotesField').value;

    try {
        await fetch(`/api/audit/task/${encodeURIComponent(taskId)}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                status: 'Completed',
                actual_output: output,
                evidence_notes: notes
            })
        });
        closeEvidenceModal();
        if (selectedAuditDevice) await selectAuditDevice(selectedAuditDevice);
        renderAuditDeviceList(document.getElementById('auditDeviceSearch')?.value || '');
        updateAuditMetricsBar();
        renderFinalAuditMatrix();
    } catch (err) {
        console.error('Failed to save evidence:', err);
    }
}

// Metrics Bar
async function updateAuditMetricsBar() {
    try {
        const res = await fetch('/api/audit/matrix_summary');
        const data = await res.json();

        const totalDevs = data.matrix.length;
        const totalTasks = data.matrix.reduce((s, d) => s + d.total_tasks, 0);
        const completedTasks = data.matrix.reduce((s, d) => s + d.completed_tasks, 0);
        const failedTasks = data.matrix.reduce((s, d) => s + d.failed_tasks, 0);
        const pct = totalTasks > 0 ? Math.round(completedTasks / totalTasks * 100) : 0;

        document.getElementById('s3TotalDevices').textContent = totalDevs;
        document.getElementById('s3TotalTasks').textContent = totalTasks;
        document.getElementById('s3CompletedTasks').textContent = completedTasks;
        document.getElementById('s3FailedTasks').textContent = failedTasks;
        document.getElementById('s3CompletionPct').textContent = pct + '%';
    } catch (err) {
        console.error('Failed to update metrics:', err);
    }
}

/* =========================================================================
   STAGE 3: LIVE AUDIT TRIGGER, STREAMING & INTERACTIVE RETRY
   ========================================================================= */

/* ── Toast Notification System ─────────────────────────────────────────────
   Usage: showToast('Message text', 'success' | 'error' | 'warning' | 'info')
   Replaces alert() for non-blocking, styled error & status messages.
   ─────────────────────────────────────────────────────────────────────────── */
function showToast(message, type = 'info', duration = 5000) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = `
            position: fixed; bottom: 24px; right: 24px; z-index: 9999;
            display: flex; flex-direction: column; gap: 10px; pointer-events: none;
            max-width: 420px;
        `;
        document.body.appendChild(container);
    }

    const colors = {
        success: { bg: 'rgba(16, 185, 129, 0.95)', border: '#10b981', icon: '✅' },
        error: { bg: 'rgba(239, 68, 68, 0.95)', border: '#ef4444', icon: '❌' },
        warning: { bg: 'rgba(245, 158, 11, 0.95)', border: '#f59e0b', icon: '⚠️' },
        info: { bg: 'rgba(56, 189, 248, 0.95)', border: '#38bdf8', icon: 'ℹ️' }
    };
    const c = colors[type] || colors.info;

    const toast = document.createElement('div');
    toast.style.cssText = `
        background: ${c.bg}; border: 1px solid ${c.border}; border-radius: 10px;
        padding: 12px 16px; color: #fff; font-size: 0.85rem; line-height: 1.45;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5); pointer-events: all;
        display: flex; align-items: flex-start; gap: 10px;
        animation: toastSlideIn 0.3s ease; max-width: 420px; word-break: break-word;
        cursor: pointer;
    `;
    toast.innerHTML = `<span style="font-size: 1.1rem; flex-shrink: 0;">${c.icon}</span><span>${message}</span>`;
    toast.title = 'Click to dismiss';
    toast.onclick = () => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    };

    container.appendChild(toast);

    // Add slide-in keyframe if not present
    if (!document.getElementById('toastKeyframe')) {
        const style = document.createElement('style');
        style.id = 'toastKeyframe';
        style.textContent = `
            @keyframes toastSlideIn { from { opacity: 0; transform: translateX(60px); } to { opacity: 1; transform: translateX(0); } }
            @keyframes toastSlideOut { from { opacity: 1; transform: translateX(0); } to { opacity: 0; transform: translateX(60px); } }
        `;
        document.head.appendChild(style);
    }

    // Auto-dismiss
    setTimeout(() => {
        toast.style.animation = 'toastSlideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 320);
    }, duration);
}

let lastTriggerCredentials = null;
let stage3EventSource = null;

function openAuditTriggerModal(scope = 'all', hostname = null, section = null, taskId = null) {
    document.getElementById('triggerScope').value = scope;
    document.getElementById('triggerTargetHostname').value = hostname || '';
    document.getElementById('triggerTargetSection').value = section || '';
    document.getElementById('triggerTargetTaskId').value = taskId || '';

    const titleEl = document.getElementById('auditTriggerModalTitle');
    const subEl = document.getElementById('auditTriggerModalSubtitle');

    if (scope === 'all') {
        titleEl.innerHTML = '⚡ Trigger All Devices Live Audit';
        subEl.textContent = 'Execute real-time verification commands across all devices in inventory.';
    } else if (scope === 'device') {
        titleEl.innerHTML = `⚡ Trigger Live Audit for ${hostname}`;
        subEl.textContent = `Execute all protocol verification commands for ${hostname}.`;
    } else if (scope === 'section') {
        titleEl.innerHTML = `⚡ Run Section: ${section}`;
        subEl.textContent = `Execute ${section} verification commands on ${hostname}.`;
    } else if (scope === 'task') {
        titleEl.innerHTML = `⚡ Run Single Verification Command`;
        subEl.textContent = `Execute task command live on ${hostname}.`;
    }

    // Editable command field for single task
    const customField = document.getElementById('triggerFieldCustomCommand');
    const customInput = document.getElementById('triggerCustomCommand');
    if (scope === 'task' && taskId) {
        if (customField && customInput) {
            customField.style.display = 'block';
            const cardInput = document.getElementById(`retryInput_${taskId}`);
            const t = (currentState?.device_audit_tasks || []).find(x => x.id === taskId);
            customInput.value = (cardInput && cardInput.value.trim()) ? cardInput.value.trim() : (t ? t.verification_command : '');
        }
    } else {
        if (customField) customField.style.display = 'none';
    }

    // Prefill username if empty
    if (!document.getElementById('triggerUsername').value) {
        document.getElementById('triggerUsername').value = 'admin';
    }

    document.getElementById('auditTriggerModal').classList.add('active');
}

function closeAuditTriggerModal() {
    document.getElementById('auditTriggerModal').classList.remove('active');
}

function toggleAuditTriggerAuthFields() {
    const authType = document.getElementById('triggerAuthType').value;
    document.getElementById('triggerFieldUsername').style.display = authType === 'api_token' ? 'none' : 'block';
    document.getElementById('triggerFieldPassword').style.display = authType === 'password' ? 'block' : 'none';
    document.getElementById('triggerFieldSecret').style.display = authType === 'password' ? 'block' : 'none';
    document.getElementById('triggerFieldKey').style.display = authType === 'key' ? 'block' : 'none';
    document.getElementById('triggerFieldToken').style.display = authType === 'api_token' ? 'block' : 'none';
}

async function executeLiveAuditTrigger() {
    const scope = document.getElementById('triggerScope').value;
    const hostname = document.getElementById('triggerTargetHostname').value;
    const section = document.getElementById('triggerTargetSection').value;
    const taskId = document.getElementById('triggerTargetTaskId').value;

    const authType = document.getElementById('triggerAuthType').value;
    const credentials = {
        auth_type: authType,
        username: document.getElementById('triggerUsername').value.trim() || null,
        password: document.getElementById('triggerPassword').value || null,
        secret: document.getElementById('triggerSecret').value || null,
        ssh_key: document.getElementById('triggerSshKey').value.trim() || null,
        api_token: document.getElementById('triggerApiToken').value || null
    };

    // ── Credential Validation ────────────────────────────────────────────────
    let validationError = null;
    if (authType === 'password' && !credentials.password) {
        validationError = 'SSH Password is required for password authentication.';
    } else if (authType === 'key' && !credentials.ssh_key) {
        validationError = 'SSH Private Key is required for key-based authentication.';
    } else if (authType === 'api_token' && !credentials.api_token) {
        validationError = 'API Token / Meraki Key is required for REST API authentication.';
    }

    if (validationError) {
        // Show inline error banner in modal instead of alert
        let errBanner = document.getElementById('triggerValidationError');
        if (!errBanner) {
            errBanner = document.createElement('div');
            errBanner.id = 'triggerValidationError';
            errBanner.style.cssText = `
                background: rgba(239,68,68,0.15); border: 1px solid #ef4444;
                border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;
                font-size: 0.82rem; color: #fca5a5; display: flex; align-items: center; gap: 8px;
            `;
            const authTypeEl = document.getElementById('triggerAuthType');
            authTypeEl.closest('.form-group').parentElement.insertBefore(
                errBanner, authTypeEl.closest('.form-group')
            );
        }
        errBanner.innerHTML = `<span>⚠️</span><span>${validationError}</span>`;
        errBanner.style.display = 'flex';
        // Shake the modal button
        const runBtn = document.querySelector('#auditTriggerModal .btn[onclick="executeLiveAuditTrigger()"]');
        if (runBtn) {
            runBtn.style.animation = 'none';
            runBtn.style.transform = 'translateX(0)';
            setTimeout(() => {
                runBtn.style.transition = 'transform 0.1s';
                ['-6px', '6px', '-4px', '4px', '0px'].forEach((x, i) => {
                    setTimeout(() => runBtn.style.transform = `translateX(${x})`, i * 60);
                });
            }, 10);
        }
        return;
    }

    // Clear any previous validation error
    const errBanner = document.getElementById('triggerValidationError');
    if (errBanner) errBanner.style.display = 'none';

    // Cache in session memory for single-click retries
    lastTriggerCredentials = { ...credentials };

    // If single task scope, delegate directly to interactive live test & update
    if (scope === 'task' && taskId) {
        const customInput = document.getElementById('triggerCustomCommand');
        if (customInput && customInput.value.trim()) {
            const cardInput = document.getElementById(`retryInput_${taskId}`);
            if (cardInput) cardInput.value = customInput.value.trim();
            closeAuditTriggerModal();
            return retryTaskCommand(taskId, hostname);
        }
    }

    closeAuditTriggerModal();

    // Open Live Drawer
    const drawer = document.getElementById('stage3LiveDrawer');
    const statusText = document.getElementById('stage3LiveStatusText');
    const progressBar = document.getElementById('stage3LiveProgressBar');
    const commandLog = document.getElementById('stage3LiveCommandLog');
    const liveStats = document.getElementById('stage3LiveStats');

    if (drawer) {
        drawer.style.display = 'block';
        statusText.textContent = 'Connecting to devices and initiating live audit...';
        progressBar.style.width = '5%';
        progressBar.style.background = 'linear-gradient(90deg, #38bdf8, #10b981)';
        commandLog.textContent = 'Initializing worker threads...';
        liveStats.textContent = '0 verified | 0 failed';
    }

    try {
        const res = await fetch('/api/audit/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scope,
                hostname: hostname || null,
                section_category: section || null,
                task_id: taskId || null,
                credentials,
                timeout_seconds: 35,
                project_state: currentState,
                client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
            })
        });

        if (!res.ok) {
            let errMsg = 'HTTP ' + res.status;
            try {
                const err = await res.json();
                errMsg = (typeof err.detail === 'string') ? err.detail : JSON.stringify(err.detail);
            } catch (_) {
                try {
                    errMsg = (await res.text()).slice(0, 200);
                } catch (_) {}
            }
            showToast('Failed to start audit trigger: ' + errMsg, 'error', 8000);
            if (statusText) statusText.textContent = 'Trigger failed to start: ' + errMsg;
            if (progressBar) { progressBar.style.width = '100%'; progressBar.style.background = '#ef4444'; }
            setTimeout(() => { if (drawer) drawer.style.display = 'none'; }, 5000);
            return;
        }

        const data = await res.json();

        if (data.status === 'completed') {
            // Synchronous execution completed (Serverless / Netlify / Vercel cloud deployment)
            if (progressBar) progressBar.style.width = '100%';
            if (statusText) statusText.innerHTML = `✅ Audit completed successfully across devices.`;
            if (commandLog) commandLog.textContent = `Files saved: ${data.total_files || 0}. ${data.tasks_succeeded || 0} verified, ${data.tasks_failed || 0} failed.`;
            if (liveStats) liveStats.textContent = `${data.tasks_succeeded || 0} verified | ${data.tasks_failed || 0} failed`;

            const summaryType = (data.tasks_failed > 0) ? 'warning' : 'success';
            showToast(
                `Audit complete: ${data.tasks_succeeded} verified, ${data.tasks_failed} failed. ${data.total_files} files saved.`,
                summaryType,
                8000
            );

            // Directly adopt returned state (avoids stateless serverless instance mismatches)
            if (data.project_state) {
                currentState = data.project_state;
            } else {
                try {
                    const sRes = await fetch('/api/state');
                    currentState = await sRes.json();
                } catch (_) {}
            }

            if (selectedAuditDevice) {
                await selectAuditDevice(selectedAuditDevice);
            }
            renderAuditDeviceList(document.getElementById('auditDeviceSearch')?.value || '');
            updateAuditMetricsBar();
            renderFinalAuditMatrix();

            setTimeout(() => {
                if (drawer && !stage3EventSource) drawer.style.display = 'none';
            }, 6000);
        } else {
            // Asynchronous background execution (SSE streaming for local server)
            startStage3EventStream(data.job_id);
        }

    } catch (err) {
        showToast('Network or server error starting audit: ' + err.message, 'error', 8000);
        if (statusText) statusText.textContent = 'Network error: ' + (err.message || 'could not reach server');
        if (progressBar) { progressBar.style.width = '100%'; progressBar.style.background = '#ef4444'; }
        setTimeout(() => { if (drawer) drawer.style.display = 'none'; }, 5000);
    }
}


function startStage3EventStream(jobId) {
    if (stage3EventSource) {
        stage3EventSource.close();
    }

    const drawer = document.getElementById('stage3LiveDrawer');
    const statusText = document.getElementById('stage3LiveStatusText');
    const progressBar = document.getElementById('stage3LiveProgressBar');
    const commandLog = document.getElementById('stage3LiveCommandLog');
    const liveStats = document.getElementById('stage3LiveStats');

    let succeeded = 0;
    let failed = 0;

    stage3EventSource = new EventSource(`/api/audit/stream/${encodeURIComponent(jobId)}`);

    stage3EventSource.onmessage = async (e) => {
        try {
            const msg = JSON.parse(e.data);
            const evt = msg.event;
            const data = msg.data;

            if (evt === 'JOB_STARTED') {
                if (statusText) statusText.textContent = data.message || 'Audit job started...';
                if (progressBar) progressBar.style.width = '10%';

            } else if (evt === 'DEVICE_STARTED') {
                if (statusText) statusText.textContent = `Auditing ${data.hostname} (${data.vendor} — ${data.total_tasks} tasks)...`;

            } else if (evt === 'DEVICE_FAILED') {
                // Connection failure for a device
                showToast(`Connection failed to ${data.hostname}: ${data.error}`, 'error', 8000);
                if (commandLog) commandLog.textContent = `[${data.hostname}] ${data.error}`;

            } else if (evt === 'TASK_RUNNING') {
                if (commandLog) commandLog.textContent = `[${data.hostname}] > ${data.command}`;
                const card = document.getElementById(`taskCard_${data.task_id}`);
                if (card) {
                    card.style.boxShadow = '0 0 12px rgba(56, 189, 248, 0.3)';
                    card.style.borderLeftColor = '#38bdf8';
                    // Remove existing error editor if re-running
                    const existingEditor = card.querySelector('.audit-task-error-editor');
                    if (existingEditor) existingEditor.remove();
                }

            } else if (evt === 'TASK_COMPLETED') {
                succeeded++;
                if (liveStats) liveStats.textContent = `${succeeded} verified | ${failed} failed`;
                const card = document.getElementById(`taskCard_${data.task_id}`);
                if (card) {
                    card.style.boxShadow = '';
                    const st = data.status || 'Completed';
                    const sc = AUDIT_STATUS_COLORS[st] || AUDIT_STATUS_COLORS['Completed'];
                    card.style.borderLeftColor = sc.border;

                    // If status is Completed or N/A, remove error editor
                    const errorEditor = card.querySelector('.audit-task-error-editor');
                    if (errorEditor && st !== 'Warning') {
                        errorEditor.style.opacity = '0';
                        errorEditor.style.transition = 'opacity 0.3s';
                        setTimeout(() => errorEditor.remove(), 300);
                    }

                    // Update active status button
                    card.querySelectorAll('.audit-status-btn').forEach(btn => {
                        const isThis = btn.getAttribute('data-status') === st;
                        btn.classList.toggle('active', isThis);
                        if (isThis) {
                            btn.style.background = sc.bg;
                            btn.style.borderColor = sc.border;
                            btn.style.color = sc.text;
                        } else {
                            btn.style.background = '';
                            btn.style.borderColor = '';
                            btn.style.color = '';
                        }
                    });

                    // Update or insert evidence notes text
                    if (data.evidence_notes) {
                        let evDiv = card.querySelector('.audit-task-evidence');
                        if (!evDiv) {
                            evDiv = document.createElement('div');
                            evDiv.className = 'audit-task-evidence';
                            evDiv.style.marginTop = '6px';
                            const statusRow = card.querySelector('.audit-task-status-row');
                            if (statusRow) statusRow.insertAdjacentElement('afterend', evDiv);
                            else card.appendChild(evDiv);
                        }
                        if (evDiv) evDiv.innerHTML = `<strong>Notes/Status:</strong> ${escapeHtml(data.evidence_notes)}`;
                    }
                }

            } else if (evt === 'TASK_FAILED') {
                failed++;
                if (liveStats) liveStats.textContent = `${succeeded} verified | ${failed} failed`;
                const card = document.getElementById(`taskCard_${data.task_id}`);
                if (card) {
                    card.style.boxShadow = '';
                    const sc = AUDIT_STATUS_COLORS['Failed'];
                    card.style.borderLeftColor = sc.border;

                    // Update active status button
                    card.querySelectorAll('.audit-status-btn').forEach(btn => {
                        const isFail = btn.getAttribute('data-status') === 'Failed';
                        btn.classList.toggle('active', isFail);
                        if (isFail) {
                            btn.style.background = sc.bg;
                            btn.style.borderColor = sc.border;
                            btn.style.color = sc.text;
                        } else {
                            btn.style.background = '';
                            btn.style.borderColor = '';
                            btn.style.color = '';
                        }
                    });

                    // Update or insert evidence notes text
                    if (data.evidence_notes) {
                        let evDiv = card.querySelector('.audit-task-evidence');
                        if (!evDiv) {
                            evDiv = document.createElement('div');
                            evDiv.className = 'audit-task-evidence';
                            evDiv.style.marginTop = '6px';
                            const statusRow = card.querySelector('.audit-task-status-row');
                            if (statusRow) statusRow.insertAdjacentElement('afterend', evDiv);
                            else card.appendChild(evDiv);
                        }
                        if (evDiv) evDiv.innerHTML = `<strong>Notes/Error:</strong> ${escapeHtml(data.evidence_notes)}`;
                    }

                    // Inject inline error editor if not already present
                    if (!card.querySelector('.audit-task-error-editor')) {
                        const errClass = data.error_class || 'EXEC_ERROR';
                        const errMsg = escapeHtml(data.error || 'Command failed validation.');
                        const failedCmd = escapeHtml(data.failed_command || '');
                        const hostname = escapeHtml(data.hostname || '');
                        const taskId = data.task_id;

                        const errEditorDiv = document.createElement('div');
                        errEditorDiv.className = 'audit-task-error-editor';
                        errEditorDiv.style.cssText = 'margin-top: 10px; background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.3); border-radius: 6px; padding: 10px 12px; animation: fadeIn 0.3s ease;';
                        errEditorDiv.innerHTML = `
                            <div style="font-size: 0.78rem; color: #fca5a5; font-weight: 700; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                                <span>⚠️ ${errClass}</span>
                                <span style="font-weight: 400; color: var(--text-dim);">: ${errMsg}</span>
                            </div>
                            <div style="display: flex; gap: 8px; align-items: center;">
                                <input type="text" id="retryInput_${taskId}" value="${failedCmd}"
                                    style="flex: 1; font-family: monospace; font-size: 0.82rem; padding: 6px 10px; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; color: #f8fafc;"
                                    placeholder="Edit command and click Retry...">
                                <button class="btn btn-sm" style="background: #ef4444; color: white; white-space: nowrap; font-weight: 600;"
                                    onclick="retryTaskCommand('${taskId}', '${hostname}')">
                                    ⚡ Retry &amp; Update
                                </button>
                            </div>
                        `;
                        card.appendChild(errEditorDiv);
                    }
                }

            } else if (evt === 'JOB_COMPLETED') {
                if (progressBar) progressBar.style.width = '100%';
                if (statusText) statusText.innerHTML = `✅ ${data.message || 'Audit completed successfully.'}`;
                if (commandLog) commandLog.textContent = `Files saved: ${data.total_files}. ${data.tasks_succeeded} verified, ${data.tasks_failed} failed.`;

                stage3EventSource.close();
                stage3EventSource = null;

                const summaryType = data.tasks_failed > 0 ? 'warning' : 'success';
                showToast(
                    `Audit complete: ${data.tasks_succeeded} verified, ${data.tasks_failed} failed. ${data.total_files} files saved.`,
                    summaryType,
                    8000
                );

                // Reload local state and views
                try {
                    const sRes = await fetch('/api/state');
                    currentState = await sRes.json();
                    if (selectedAuditDevice) {
                        await selectAuditDevice(selectedAuditDevice);
                    }
                    renderAuditDeviceList(document.getElementById('auditDeviceSearch')?.value || '');
                    updateAuditMetricsBar();
                    renderFinalAuditMatrix();
                } catch (rErr) {
                    console.error('Error refreshing state after job:', rErr);
                }

                // Hide drawer after 8 seconds
                setTimeout(() => {
                    if (drawer && !stage3EventSource) drawer.style.display = 'none';
                }, 8000);

            } else if (evt === 'JOB_FAILED') {
                // Unhandled server-side exception — stop spinning, show error
                stage3EventSource.close();
                stage3EventSource = null;

                if (progressBar) { progressBar.style.width = '100%'; progressBar.style.background = '#ef4444'; }
                if (statusText) statusText.innerHTML = `❌ Audit job failed: ${escapeHtml(data.error || 'Unknown error')}`;
                if (commandLog) commandLog.textContent = data.message || '';

                showToast(`Audit job failed unexpectedly: ${data.error || 'Unknown error'}`, 'error', 10000);

                // Reload state to reflect partial changes
                try {
                    const sRes = await fetch('/api/state');
                    currentState = await sRes.json();
                    renderAuditDeviceList(document.getElementById('auditDeviceSearch')?.value || '');
                    updateAuditMetricsBar();
                    renderFinalAuditMatrix();
                } catch (_) { /* best-effort */ }

                setTimeout(() => { if (drawer) drawer.style.display = 'none'; }, 6000);
            }
        } catch (parseErr) {
            console.error('Error handling SSE message:', parseErr);
        }
    };

    stage3EventSource.onerror = (err) => {
        console.warn('SSE stream encountered error or ended:', err);
        if (stage3EventSource && stage3EventSource.readyState === EventSource.CLOSED) {
            stage3EventSource = null;
        } else if (stage3EventSource) {
            stage3EventSource.close();
            stage3EventSource = null;
            showToast('Live audit stream connection lost. Check server logs.', 'warning', 6000);
            if (statusText) statusText.textContent = 'Stream connection lost.';
            if (progressBar) { progressBar.style.background = '#f59e0b'; }
        }
    };
}

async function retryTaskCommand(taskId, hostname) {
    const inputEl = document.getElementById(`retryInput_${taskId}`);
    if (!inputEl) return;
    const newCommand = inputEl.value.trim();
    if (!newCommand) {
        showToast('Please enter a valid show command to test.', 'warning');
        return;
    }

    // Check credentials — re-open modal if none cached
    let creds = lastTriggerCredentials;
    if (!creds || (!creds.password && !creds.ssh_key && !creds.api_token)) {
        showToast('No cached credentials found. Please provide credentials to retry.', 'warning', 6000);
        openAuditTriggerModal('task', hostname, null, taskId);
        return;
    }

    inputEl.disabled = true;
    const card = document.getElementById(`taskCard_${taskId}`);
    const retryBtn = inputEl.nextElementSibling;
    if (retryBtn) { retryBtn.disabled = true; retryBtn.textContent = '⏳ Running...'; }
    if (card) card.style.borderLeftColor = '#fbbf24';

    try {
        const errLabelEl = document.getElementById(`retryErrorLabel_${taskId}`);
        if (errLabelEl) { errLabelEl.style.display = 'none'; errLabelEl.textContent = ''; }

        const res = await fetch(`/api/audit/task/${encodeURIComponent(taskId)}/retry`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: taskId,
                new_command: newCommand,
                credentials: creds,
                project_state: currentState,
                client_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
            })
        });

        if (res.ok) {
            const result = await res.json();
            if (result.project_state) {
                currentState = result.project_state;
            }
            const resStatus = result.status || 'Completed';
            const toastType = resStatus === 'Warning' ? 'warning' : 'success';
            showToast(`Command executed! Status: ${resStatus}. ${result.evidence_notes || ''}`, toastType, 7000);

            const sc = AUDIT_STATUS_COLORS[resStatus] || AUDIT_STATUS_COLORS['Completed'];
            if (card) card.style.borderLeftColor = sc.border;

            // Update visible command text in card
            const cmdTextEl = document.getElementById(`cmdText_${taskId}`);
            if (cmdTextEl) cmdTextEl.textContent = newCommand;

            // Remove or collapse the error editor if completed or N/A
            if (resStatus === 'Completed' || resStatus === 'N/A') {
                const errEditor = document.getElementById(`cmdEditor_${taskId}`);
                if (errEditor) {
                    setTimeout(() => { errEditor.style.display = 'none'; }, 600);
                }
            }

            // Refresh view
            if (selectedAuditDevice) await selectAuditDevice(selectedAuditDevice);
            renderAuditDeviceList(document.getElementById('auditDeviceSearch')?.value || '');
            updateAuditMetricsBar();
            renderFinalAuditMatrix();
        } else {
            const errData = await res.json();
            const errDetail = errData.detail || errData;
            if (errDetail && errDetail.project_state) {
                currentState = errDetail.project_state;
            }
            const errMsg = typeof errDetail === 'string' ? errDetail :
                (errDetail.error || JSON.stringify(errDetail));
            const errClass = typeof errDetail === 'object' ? (errDetail.error_class || 'EXEC_ERROR') : 'EXEC_ERROR';

            showToast(`Command failed [${errClass}]: ${errMsg}`, 'error', 8000);
            if (card) card.style.borderLeftColor = '#ef4444';

            // Update the error message in the inline editor
            if (errLabelEl) {
                errLabelEl.style.display = 'block';
                errLabelEl.innerHTML = `⚠️ <strong>${errClass}</strong>: ${escapeHtml(errMsg)}`;
            }
        }
    } catch (err) {
        showToast('Network error while retrying command: ' + (err.message || err), 'error');
        if (card) card.style.borderLeftColor = '#ef4444';
    } finally {
        inputEl.disabled = false;
        if (retryBtn) { retryBtn.disabled = false; retryBtn.innerHTML = '⚡ Test &amp; Run'; }
    }
}

function downloadAuditFiles(target = 'all') {
    window.location.href = `/api/audit/download_files/${encodeURIComponent(target)}`;
}


// Final Protocol Verification Matrix
async function renderFinalAuditMatrix() {
    const container = document.getElementById('auditMatrixContainer');
    if (!container) return;

    try {
        const res = await fetch('/api/audit/matrix_summary');
        const data = await res.json();

        if (!data.matrix || data.matrix.length === 0) {
            container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-dim);">No devices in inventory. Add devices in Stage 1 to see the verification matrix.</div>`;
            return;
        }

        let html = `
            <div style="overflow-x: auto;">
            <table class="data-table audit-matrix-table">
                <thead>
                    <tr>
                        <th>Device</th>
                        <th>Vendor</th>
                        <th>Classification</th>
                        <th>Role</th>
                        <th>Implemented Protocols</th>
                        <th>Progress</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.matrix.forEach(dev => {
            const statusBadge = dev.device_status === 'Verified' ? 'badge-pass' :
                dev.device_status === 'Failed' ? 'badge-fail' :
                    dev.device_status === 'In Progress' ? 'badge-warning' : 'badge-na';

            // Protocol pills with per-protocol status colors
            const protoPills = Object.entries(dev.protocols).map(([name, stats]) => {
                let pillClass = 'proto-incomplete';
                if (stats.failed > 0) pillClass = 'proto-fail';
                else if (stats.warning > 0) pillClass = 'proto-warning';
                else if (stats.completed + stats.na >= stats.total) pillClass = 'proto-pass';
                return `<span class="audit-matrix-proto ${pillClass}">${name}</span>`;
            }).join('');

            html += `
                <tr class="audit-matrix-row" onclick="switchStage(3); selectAuditDevice('${dev.hostname}'); document.querySelector('.audit-workbench')?.scrollIntoView({ behavior: 'smooth' });" style="cursor: pointer;">
                    <td>
                        <strong>${dev.hostname}</strong>
                        <div style="font-size: 0.78rem; color: var(--text-dim);">${dev.management_ip}</div>
                    </td>
                    <td>${dev.vendor}</td>
                    <td><span class="badge badge-func">${dev.classification}</span></td>
                    <td><span class="badge badge-role">${dev.device_role}</span></td>
                    <td>
                        <div class="audit-matrix-protos">${protoPills}</div>
                    </td>
                    <td>
                        <div class="audit-matrix-progress">
                            <div class="audit-progress-bar" style="width: 120px;">
                                <div class="audit-progress-fill" style="width: ${dev.completion_pct}%;"></div>
                            </div>
                            <span style="font-size: 0.82rem; color: var(--text-muted);">${dev.completion_pct}%</span>
                        </div>
                    </td>
                    <td><span class="badge ${statusBadge}">${dev.device_status}</span></td>
                </tr>
            `;
        });

        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (err) {
        console.error('Failed to render audit matrix:', err);
        container.innerHTML = `<div style="color: var(--danger); padding: 20px;">Failed to load matrix data.</div>`;
    }
}

async function refreshAuditMatrix() {
    await renderFinalAuditMatrix();
    await updateAuditMetricsBar();
}

/* ==========================================================================
   ENTERPRISE REPORT GENERATOR MODAL CONTROLLER
   ========================================================================== */

const REPORT_TYPE_FORMATS = {
    executive: [
        { value: 'html', label: 'HTML / Web View' },
        { value: 'docx', label: 'Word Document (.docx)' },
        { value: 'md', label: 'Markdown (.md)' }
    ],
    technical: [
        { value: 'excel', label: 'Excel Workbook (.xlsx)' }
    ],
    compliance: [
        { value: 'html', label: 'HTML / Web View' },
        { value: 'docx', label: 'Word Document (.docx)' },
        { value: 'md', label: 'Markdown (.md)' }
    ]
};

function openExecutiveReportModal() {
    const typeSelect = document.getElementById('reportGenType');
    const scopeSelect = document.getElementById('reportGenScope');
    if (typeSelect) typeSelect.value = 'executive';
    if (scopeSelect) scopeSelect.value = 'all';

    // Populate format options strictly available for executive report
    onReportTypeChange();

    const modal = document.getElementById('executiveReportModal');
    if (modal) {
        modal.classList.add('active');
    }
}

function closeExecutiveReportModal() {
    const modal = document.getElementById('executiveReportModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function switchReportFormat(fmt) {
    const formatSelect = document.getElementById('reportGenFormat');
    if (formatSelect) {
        formatSelect.value = fmt;
        onReportConfigChange();
        generateAndLoadReport();
    }
}

function switchReportType(type) {
    const typeSelect = document.getElementById('reportGenType');
    if (typeSelect) {
        typeSelect.value = type;
        onReportTypeChange();
    }
}

function onReportTypeChange() {
    const type = document.getElementById('reportGenType')?.value || 'executive';
    const formatSelect = document.getElementById('reportGenFormat');
    const scopeSelect = document.getElementById('reportGenScope');

    if (!formatSelect) return;

    const previousFormat = formatSelect.value;
    const allowed = REPORT_TYPE_FORMATS[type] || REPORT_TYPE_FORMATS.executive;

    formatSelect.innerHTML = '';
    let matchFound = false;
    allowed.forEach(opt => {
        const el = document.createElement('option');
        el.value = opt.value;
        el.textContent = opt.label;
        if (opt.value === previousFormat) {
            el.selected = true;
            matchFound = true;
        }
        formatSelect.appendChild(el);
    });

    if (!matchFound && allowed.length > 0) {
        formatSelect.value = allowed[0].value;
    }

    if (type === 'compliance' && scopeSelect && scopeSelect.value === 'all') {
        scopeSelect.value = 'critical';
    }

    onReportConfigChange();
    generateAndLoadReport();
}

function onReportFormatChange() {
    onReportConfigChange();
    generateAndLoadReport();
}

function onReportScopeChange() {
    onReportConfigChange();
    generateAndLoadReport();
}

function onReportConfigChange() {
    const type = document.getElementById('reportGenType')?.value || 'executive';
    const formatSelect = document.getElementById('reportGenFormat');
    const format = formatSelect?.value || 'html';
    const scope = document.getElementById('reportGenScope')?.value || 'all';
    const newTabBtn = document.getElementById('btnReportNewTab');
    const downloadBtn = document.getElementById('btnReportDownload');
    const printBtn = document.getElementById('btnReportPrint');

    // Dynamic Download button label and icon
    if (downloadBtn) {
        if (format === 'docx') {
            downloadBtn.innerHTML = '📝 Download Word (.docx)';
            downloadBtn.title = 'Download 6-page Executive Report in Microsoft Word (.docx)';
        } else if (format === 'excel' || type === 'technical') {
            downloadBtn.innerHTML = '📊 Download Excel (.xlsx)';
            downloadBtn.title = 'Download Technical Evidence Workbook in Microsoft Excel (.xlsx)';
        } else if (format === 'md') {
            downloadBtn.innerHTML = '📄 Download Markdown (.md)';
            downloadBtn.title = 'Download Executive Report in Markdown (.md)';
        } else {
            downloadBtn.innerHTML = '📥 Download HTML';
            downloadBtn.title = 'Download Standalone Executive Report in HTML';
        }
    }

    // Print button: visible for HTML format, hidden for binary Excel or Word
    if (printBtn) {
        printBtn.style.display = (format === 'html') ? 'inline-flex' : 'none';
    }

    // Update Open in New Tab URL
    const scopeParam = scope !== 'all' ? `?scope=${encodeURIComponent(scope)}` : '';
    if (newTabBtn) {
        if (type === 'technical' || format === 'excel') {
            newTabBtn.href = '/api/export/excel';
        } else if (format === 'docx') {
            newTabBtn.href = `/api/export/executive/docx${scopeParam}`;
        } else if (format === 'md') {
            newTabBtn.href = `/api/export/executive/md/preview${scopeParam}`;
        } else {
            newTabBtn.href = `/api/export/executive/html${scopeParam}`;
        }
    }
}

function getDocxPreviewHtml(scope) {
    const scopeParam = scope !== 'all' ? '?scope=' + encodeURIComponent(scope) : '';
    const scopeLabel = scope === 'critical' ? 'Critical & High Only' : 'Full Infrastructure';
    return `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            margin: 0; padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f8fafc; color: #0f172a; height: 100vh;
            display: flex; align-items: center; justify-content: center; box-sizing: border-box;
        }
        .card {
            background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
            padding: 36px 32px; max-width: 540px; text-align: center;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        }
        .icon-pill {
            width: 56px; height: 56px; border-radius: 14px; background: #eff6ff;
            display: inline-flex; align-items: center; justify-content: center; font-size: 1.8rem;
            margin-bottom: 16px; border: 1px solid #bfdbfe;
        }
        h2 { margin: 0 0 8px 0; font-size: 1.25rem; color: #0f172a; font-weight: 700; }
        p { color: #64748b; font-size: 0.88rem; line-height: 1.5; margin: 0 0 20px 0; }
        .action-row { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
        .btn-dl {
            background: #1e3a8a; color: #ffffff; padding: 9px 20px; border-radius: 6px;
            text-decoration: none; font-weight: 600; font-size: 0.85rem;
            display: inline-flex; align-items: center; gap: 6px;
        }
        .btn-dl:hover { background: #1e293b; }
        .btn-preview {
            background: #ffffff; color: #334155; padding: 9px 18px; border-radius: 6px;
            border: 1px solid #cbd5e1; font-weight: 600; font-size: 0.85rem; cursor: pointer;
        }
        .btn-preview:hover { background: #f1f5f9; }
        .meta-strip {
            display: flex; justify-content: center; gap: 16px; margin-top: 20px;
            padding-top: 14px; border-top: 1px solid #f1f5f9; font-size: 0.75rem; color: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-pill">📝</div>
        <h2>Executive Decision Report (.docx)</h2>
        <p>
            Publication-grade Microsoft Word document with verified KPI metrics, domain compliance tables, findings, and evidence traceability.
        </p>
        <div class="action-row">
            <a href="/api/export/executive/docx${scopeParam}" class="btn-dl">
                📥 Download Word (.docx)
            </a>
            <button onclick="parent.switchReportFormat('html')" class="btn-preview">
                👁️ View HTML Document
            </button>
        </div>
        <div class="meta-strip">
            <span>Format: Office Open XML (.docx)</span>
            <span>Pages: 6 Structured Sheets</span>
            <span>Scope: ${scopeLabel}</span>
        </div>
    </div>
</body>
</html>`;
}

function getExcelPreviewHtml() {
    return `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            margin: 0; padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f8fafc; color: #0f172a; height: 100vh;
            display: flex; align-items: center; justify-content: center; box-sizing: border-box;
        }
        .card {
            background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
            padding: 36px 32px; max-width: 540px; text-align: center;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        }
        .icon-pill {
            width: 56px; height: 56px; border-radius: 14px; background: #ecfdf5;
            display: inline-flex; align-items: center; justify-content: center; font-size: 1.8rem;
            margin-bottom: 16px; border: 1px solid #a7f3d0;
        }
        h2 { margin: 0 0 8px 0; font-size: 1.25rem; color: #0f172a; font-weight: 700; }
        p { color: #64748b; font-size: 0.88rem; line-height: 1.5; margin: 0 0 20px 0; }
        .action-row { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
        .btn-dl {
            background: #047857; color: #ffffff; padding: 9px 20px; border-radius: 6px;
            text-decoration: none; font-weight: 600; font-size: 0.85rem;
            display: inline-flex; align-items: center; gap: 6px;
        }
        .btn-dl:hover { background: #065f46; }
        .btn-preview {
            background: #ffffff; color: #334155; padding: 9px 18px; border-radius: 6px;
            border: 1px solid #cbd5e1; font-weight: 600; font-size: 0.85rem; cursor: pointer;
        }
        .btn-preview:hover { background: #f1f5f9; }
        .meta-strip {
            display: flex; justify-content: center; gap: 16px; margin-top: 20px;
            padding-top: 14px; border-top: 1px solid #f1f5f9; font-size: 0.75rem; color: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-pill">📊</div>
        <h2>Technical Audit Evidence Workbook (.xlsx)</h2>
        <p>
            Comprehensive engineering workbook containing full inventory, CLI command execution logs, raw outputs, and evidence traceability.
        </p>
        <div class="action-row">
            <a href="/api/export/excel" class="btn-dl">
                📥 Download Excel (.xlsx)
            </a>
            <button onclick="parent.switchReportType('executive')" class="btn-preview">
                👁️ View Executive Report
            </button>
        </div>
        <div class="meta-strip">
            <span>Format: Excel Workbook (.xlsx)</span>
            <span>Sheets: Inventory, Tasks, Matrix</span>
            <span>Source: Live Engineering CLI</span>
        </div>
    </div>
</body>
</html>`;
}

function generateAndLoadReport() {
    const type = document.getElementById('reportGenType')?.value || 'executive';
    const format = document.getElementById('reportGenFormat')?.value || 'html';
    const scope = document.getElementById('reportGenScope')?.value || 'all';
    const frame = document.getElementById('executiveReportFrame');
    const newTabBtn = document.getElementById('btnReportNewTab');

    onReportConfigChange();

    if (!frame) return;

    const scopeQuery = scope !== 'all' ? `&scope=${encodeURIComponent(scope)}` : '';
    const scopeParam = scope !== 'all' ? `?scope=${encodeURIComponent(scope)}` : '';

    // Replace the iframe element with a fresh clone to completely eliminate
    // any lingering srcdoc attribute or browser navigation conflict between srcdoc and src.
    const newFrame = document.createElement('iframe');
    newFrame.id = 'executiveReportFrame';
    newFrame.style.cssText = 'width: 100%; height: 100%; border: 1px solid var(--border-accent); border-radius: var(--radius-md); background: #f8fafc;';

    if (format === 'docx') {
        newFrame.srcdoc = getDocxPreviewHtml(scope);
        if (newTabBtn) newTabBtn.href = `/api/export/executive/docx${scopeParam}`;
    } else if (format === 'excel' || type === 'technical') {
        newFrame.srcdoc = getExcelPreviewHtml();
        if (newTabBtn) newTabBtn.href = '/api/export/excel';
    } else if (format === 'md') {
        newFrame.src = `/api/export/executive/md/preview${scopeParam}${scopeParam ? '&' : '?'}_t=${Date.now()}`;
        if (newTabBtn) newTabBtn.href = `/api/export/executive/md/preview${scopeParam}`;
    } else {
        // HTML / Web View (Executive or Compliance)
        newFrame.src = `/api/export/executive/html?embedded=1${scopeQuery}&_t=${Date.now()}`;
        if (newTabBtn) newTabBtn.href = `/api/export/executive/html${scopeParam}`;
    }

    frame.parentNode.replaceChild(newFrame, frame);
}

function downloadSelectedReport() {
    const format = document.getElementById('reportGenFormat')?.value || 'html';
    const type = document.getElementById('reportGenType')?.value || 'executive';
    const scope = document.getElementById('reportGenScope')?.value || 'all';

    const scopeQuery = scope !== 'all' ? `&scope=${encodeURIComponent(scope)}` : '';

    if (format === 'excel' || type === 'technical') {
        window.location.href = '/api/export/excel';
    } else if (format === 'docx') {
        window.location.href = `/api/export/executive/docx?scope=${encodeURIComponent(scope)}`;
    } else if (format === 'md') {
        window.location.href = `/api/export/executive/md?download=1${scopeQuery}`;
    } else {
        // Direct download of standalone HTML document
        window.location.href = `/api/export/executive/html?download=1${scopeQuery}`;
    }
}

function printReportFrame() {
    const format = document.getElementById('reportGenFormat')?.value || 'html';
    const scope = document.getElementById('reportGenScope')?.value || 'all';

    if (format !== 'html') {
        // Switch to HTML preview first so print dialog prints the document sheet
        switchReportFormat('html');
        setTimeout(() => {
            const frame = document.getElementById('executiveReportFrame');
            if (frame && frame.contentWindow) {
                frame.contentWindow.focus();
                frame.contentWindow.print();
            }
        }, 600);
        return;
    }

    const frame = document.getElementById('executiveReportFrame');
    if (frame && frame.contentWindow) {
        frame.contentWindow.focus();
        frame.contentWindow.print();
    } else {
        window.open(`/api/export/executive/html${scope !== 'all' ? '?scope=' + encodeURIComponent(scope) : ''}`, '_blank');
    }
}

/* ==========================================================================
   MODULAR TEST SCENARIO & VENDOR PLATFORM STUDIO CONTROLLERS
   ========================================================================== */

let activeCatalogTab = 'vendors';

async function openCatalogStudioModal() {
    await loadVendorCatalog();
    await loadScenarioCatalog();

    document.getElementById('catalogStudioModal').classList.add('active');
    switchCatalogTab(activeCatalogTab);
}

function closeCatalogStudioModal() {
    document.getElementById('catalogStudioModal').classList.remove('active');
}

function switchCatalogTab(tab) {
    activeCatalogTab = tab;

    document.getElementById('tabBtnVendors').classList.toggle('active', tab === 'vendors');
    document.getElementById('tabBtnScenarios').classList.toggle('active', tab === 'scenarios');

    document.getElementById('catalogVendorsTabContent').style.display = tab === 'vendors' ? 'flex' : 'none';
    document.getElementById('catalogScenariosTabContent').style.display = tab === 'scenarios' ? 'flex' : 'none';

    if (tab === 'vendors') {
        renderStudioVendors();
    } else {
        renderStudioScenarios();
    }
}

/* --- TAB 1: SCENARIO MANAGEMENT --- */

function renderStudioScenarios() {
    const tbody = document.getElementById('studioScenariosTbody');
    const countEl = document.getElementById('studioScenarioCount');
    if (!tbody) return;

    const scenarios = scenarioCatalog.scenarios || [];
    if (countEl) countEl.innerText = scenarios.length;

    const query = (document.getElementById('scenarioSearchInput')?.value || '').toLowerCase().trim();
    const catFilter = document.getElementById('scenarioCategoryFilter')?.value || '';

    const filtered = scenarios.filter(s => {
        const matchesCat = !catFilter || s.category === catFilter;
        const matchesQuery = !query ||
            s.id.toLowerCase().includes(query) ||
            s.title.toLowerCase().includes(query) ||
            s.protocol.toLowerCase().includes(query) ||
            (s.description && s.description.toLowerCase().includes(query));
        return matchesCat && matchesQuery;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 30px;">No test scenarios matching criteria. Click "+ Add Test Scenario" or "Import JSON".</td></tr>`;
        return;
    }

    let html = '';
    filtered.forEach(s => {
        const sevClass = s.severity === 'Critical' ? 'badge-fail' :
            s.severity === 'High' ? 'badge-warning' : 'badge-pass';

        // Build preview pills for vendor commands
        const cmds = s.vendor_commands || {};
        let cmdPills = '';
        const vendorKeys = Object.keys(cmds);
        vendorKeys.slice(0, 3).forEach(v => {
            cmdPills += `<div class="cmd-preview-pill" title="${v}: ${cmds[v]}"><span>${v}:</span>${cmds[v]}</div>`;
        });
        if (vendorKeys.length > 3) {
            cmdPills += `<div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">+${vendorKeys.length - 3} more vendors</div>`;
        }

        html += `
            <tr>
                <td><strong style="color: #38bdf8; font-family: monospace; font-size: 0.8rem;">${s.id}</strong></td>
                <td>
                    <span class="badge badge-role" style="font-size: 0.72rem; padding: 2px 6px;">${s.protocol}</span>
                    <div style="font-size: 0.72rem; color: var(--text-dim); margin-top: 2px;">${s.category || ''}</div>
                </td>
                <td>
                    <div style="font-weight: 700; color: #ffffff; font-size: 0.85rem;">${s.title}</div>
                    <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 2px;">${s.description || ''}</div>
                </td>
                <td style="text-align: center;">
                    <span class="badge ${sevClass}" style="font-size: 0.72rem;">${s.severity || 'Medium'}</span>
                </td>
                <td>${cmdPills || '<span style="color: var(--text-dim); font-size: 0.75rem;">None configured</span>'}</td>
                <td style="text-align: center;">
                    <div style="display: flex; gap: 6px; justify-content: center;">
                        <button class="btn btn-secondary btn-sm" onclick="openEditScenarioModal('${s.id}')" style="padding: 3px 8px; font-size: 0.75rem;">✏️ Edit</button>
                        <button class="btn btn-secondary btn-sm" onclick="deleteStudioScenario('${s.id}')" style="padding: 3px 8px; font-size: 0.75rem; color: #f87171; border-color: rgba(248, 113, 113, 0.3);">🗑️</button>
                    </div>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

function filterStudioScenarios() {
    renderStudioScenarios();
}

function renderVendorCmdFields(existingCmds = {}) {
    const container = document.getElementById('modalVendorCmdsList');
    if (!container) return;

    const vendorColors = {
        "cisco": "#38bdf8",
        "arista": "#818cf8",
        "juniper": "#34d399",
        "palo alto": "#f87171",
        "fortinet": "#fb923c",
        "aruba": "#e879f9",
        "huawei": "#f43f5e",
        "mikrotik": "#22d3ee",
        "dell": "#a78bfa",
        "checkpoint": "#facc15",
        "default": "#fbbf24"
    };

    // Collect all vendor names from catalog
    const vendors = (vendorCatalog && vendorCatalog.vendors) ? vendorCatalog.vendors : [];
    const vendorNames = new Set();
    vendors.forEach(v => {
        if (v.name) vendorNames.add(v.name);
    });

    // Also include any custom vendor keys in existingCmds
    Object.keys(existingCmds).forEach(k => {
        if (k.toLowerCase() !== 'default') vendorNames.add(k);
    });

    if (vendorNames.size === 0) {
        ["Cisco", "Arista", "Juniper", "Palo Alto", "Fortinet", "Aruba"].forEach(v => vendorNames.add(v));
    }

    let html = '';
    Array.from(vendorNames).forEach(vName => {
        const color = vendorColors[vName.toLowerCase()] || "#38bdf8";
        const val = existingCmds[vName] || '';
        const vObj = vendors.find(x => x.name.toLowerCase() === vName.toLowerCase());
        const displayLabel = vObj ? (vObj.display_name || vObj.name) : vName;
        const escVal = String(val).replace(/"/g, '&quot;');
        html += `
            <div style="display: flex; gap: 8px; align-items: center;">
                <span style="width: 110px; font-size: 0.8rem; font-weight: 700; color: ${color}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${displayLabel}">${displayLabel}:</span>
                <input type="text" class="scenario-vendor-cmd-input" data-vendor="${vName}"
                    placeholder="e.g. show command for ${vName}..."
                    value="${escVal}"
                    style="flex: 1; font-family: monospace; font-size: 0.82rem;">
            </div>
        `;
    });

    // Default fallback row
    const defVal = String(existingCmds["Default"] || '').replace(/"/g, '&quot;');
    html += `
        <div style="display: flex; gap: 8px; align-items: center; border-top: 1px dashed rgba(255, 255, 255, 0.12); padding-top: 6px; margin-top: 4px;">
            <span style="width: 110px; font-size: 0.8rem; font-weight: 700; color: #fbbf24;">Default:</span>
            <input type="text" class="scenario-vendor-cmd-input" data-vendor="Default"
                placeholder="Fallback command (e.g. show ip ospf neighbor)"
                value="${defVal}"
                style="flex: 1; font-family: monospace; font-size: 0.82rem;">
        </div>
    `;

    container.innerHTML = html;
}

function openAddScenarioModal() {
    document.getElementById('editScenarioModalTitle').innerText = "➕ Add New Audit Test Scenario";
    const nextId = `TS-CUSTOM-${(scenarioCatalog.scenarios?.length || 0) + 1}`;
    document.getElementById('modalScenId').value = nextId;
    document.getElementById('modalScenId').disabled = false;
    document.getElementById('modalScenProtocol').value = "";
    document.getElementById('modalScenCategory').value = "Layer 3 Routing";
    document.getElementById('modalScenSeverity').value = "High";
    document.getElementById('modalScenTitle').value = "";
    document.getElementById('modalScenDesc').value = "";
    document.getElementById('modalScenRec').value = "";

    // Dynamically render command fields for all vendors
    renderVendorCmdFields({});

    document.getElementById('editScenarioModal').classList.add('active');
}

function openEditScenarioModal(scenarioId) {
    const s = (scenarioCatalog.scenarios || []).find(x => x.id.toLowerCase() === scenarioId.toLowerCase());
    if (!s) return;

    document.getElementById('editScenarioModalTitle').innerText = `✏️ Edit Test Scenario: ${s.id}`;
    document.getElementById('modalScenId').value = s.id;
    document.getElementById('modalScenId').disabled = true;
    document.getElementById('modalScenProtocol').value = s.protocol || "";
    document.getElementById('modalScenCategory').value = s.category || "Layer 3 Routing";
    document.getElementById('modalScenSeverity').value = s.severity || "High";
    document.getElementById('modalScenTitle').value = s.title || "";
    document.getElementById('modalScenDesc').value = s.description || "";
    document.getElementById('modalScenRec').value = s.recommendation || "";

    // Dynamically render command fields with existing vendor commands
    renderVendorCmdFields(s.vendor_commands || {});

    document.getElementById('editScenarioModal').classList.add('active');
}

function closeEditScenarioModal() {
    document.getElementById('editScenarioModal').classList.remove('active');
}

async function saveScenarioFromModal() {
    const id = document.getElementById('modalScenId').value.trim();
    const protocol = document.getElementById('modalScenProtocol').value.trim();
    const category = document.getElementById('modalScenCategory').value;
    const severity = document.getElementById('modalScenSeverity').value;
    const title = document.getElementById('modalScenTitle').value.trim();
    const description = document.getElementById('modalScenDesc').value.trim();
    const recommendation = document.getElementById('modalScenRec').value.trim();

    if (!id) {
        alert("⚠️ Scenario ID is required (e.g. TS-OSPF-02)!");
        return;
    }
    if (!title) {
        alert("⚠️ Test Checklist Title is required!");
        return;
    }

    // Harvest vendor commands dynamically from all rendered vendor inputs
    const vendor_commands = {};
    document.querySelectorAll('#modalVendorCmdsList .scenario-vendor-cmd-input').forEach(inp => {
        const vName = inp.getAttribute('data-vendor');
        const val = inp.value.trim();
        if (val) vendor_commands[vName] = val;
    });

    const payload = {
        id,
        protocol: protocol || "Custom Protocol",
        category,
        title,
        description,
        condition: "Configured / Active",
        severity,
        vendor_commands,
        recommendation: recommendation || "Review configuration against enterprise standards."
    };

    try {
        const res = await fetch('/api/catalog/scenarios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            closeEditScenarioModal();
            await loadScenarioCatalog();
            renderStudioScenarios();
            if (currentStage === 3) renderAuditStage();
        } else {
            const err = await res.json();
            alert(`❌ Error saving scenario: ${err.detail || 'Failed'}`);
        }
    } catch (e) {
        alert(`❌ Network error: ${e.message}`);
    }
}

async function deleteStudioScenario(scenarioId) {
    if (!confirm(`Are you sure you want to delete test scenario '${scenarioId}'?`)) return;

    try {
        const res = await fetch(`/api/catalog/scenarios/${encodeURIComponent(scenarioId)}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            await loadScenarioCatalog();
            renderStudioScenarios();
            if (currentStage === 3) renderAuditStage();
        } else {
            const err = await res.json();
            alert(`❌ Error deleting scenario: ${err.detail || 'Failed'}`);
        }
    } catch (e) {
        alert(`❌ Network error: ${e.message}`);
    }
}

function triggerScenarioJsonImport() {
    const input = document.getElementById('scenarioJsonInput');
    if (input) input.click();
}

async function handleScenarioJsonImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/catalog/scenarios/import', {
            method: 'POST',
            body: formData
        });

        if (res.ok) {
            alert("✅ Test scenarios imported successfully!");
            await loadScenarioCatalog();
            renderStudioScenarios();
            if (currentStage === 3) renderAuditStage();
        } else {
            const err = await res.json();
            alert(`❌ Failed to import scenarios: ${err.detail || 'Error'}`);
        }
    } catch (e) {
        alert(`❌ Network error: ${e.message}`);
    } finally {
        event.target.value = '';
    }
}

function exportScenarioJson() {
    window.location.href = '/api/catalog/scenarios/export';
}

/* --- TAB 2: VENDOR & PLATFORM MANAGEMENT --- */

function renderStudioVendors() {
    const grid = document.getElementById('studioVendorsGrid');
    const countEl = document.getElementById('studioVendorCount');
    if (!grid) return;

    const vendors = vendorCatalog.vendors || [];
    if (countEl) countEl.innerText = vendors.length;

    if (vendors.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 30px;">No vendor platform profiles defined. Click "+ Add Vendor Profile".</div>`;
        return;
    }

    let html = '';
    vendors.forEach(v => {
        const platforms = v.platforms || [];
        const platChips = platforms.map(p => `<span class="vendor-platform-chip">${p}</span>`).join('');
        const speeds = (v.supported_speeds || []).join(', ');

        html += `
            <div class="vendor-card">
                <div class="vendor-card-header">
                    <div class="vendor-card-title">
                        🏢 ${v.display_name || v.name}
                    </div>
                    <span class="vendor-card-badge">${v.name}</span>
                </div>
                <div class="vendor-card-row">
                    <span>Default OS:</span>
                    <strong>${v.default_os_version || 'N/A'}</strong>
                </div>
                <div class="vendor-card-row">
                    <span>Port Interface Prefix:</span>
                    <strong style="font-family: monospace; color: #38bdf8;">${v.port_prefix || 'Port'}</strong>
                </div>
                <div class="vendor-card-row">
                    <span>Supported Speeds:</span>
                    <span>${speeds || '1G, 10G'}</span>
                </div>
                <div style="margin-top: 4px;">
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 2px;">Supported Platforms / Hardware Models:</div>
                    <div class="vendor-platforms-list">${platChips || '<span style="font-size:0.72rem; color:var(--text-dim)">None specified</span>'}</div>
                </div>
                <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px;">
                    <button class="btn btn-secondary btn-sm" onclick="openEditVendorModal('${v.name}')" style="padding: 3px 8px; font-size: 0.75rem;">✏️ Edit</button>
                    <button class="btn btn-secondary btn-sm" onclick="deleteStudioVendor('${v.name}')" style="padding: 3px 8px; font-size: 0.75rem; color: #f87171; border-color: rgba(248, 113, 113, 0.3);">🗑️</button>
                </div>
            </div>
        `;
    });

    grid.innerHTML = html;
}

function openAddVendorModal() {
    document.getElementById('editVendorModalTitle').innerText = "➕ Add Vendor Platform Profile";
    document.getElementById('modalVenName').value = "";
    document.getElementById('modalVenName').disabled = false;
    document.getElementById('modalVenDisplayName').value = "";
    document.getElementById('modalVenOs').value = "";
    document.getElementById('modalVenPortPrefix').value = "Port";
    document.getElementById('modalVenPlatforms').value = "";
    document.getElementById('modalVenSpeeds').value = "1G, 10G, 25G, 40G, 100G";

    document.getElementById('editVendorModal').classList.add('active');
}

function openEditVendorModal(vendorName) {
    const v = (vendorCatalog.vendors || []).find(x => x.name.toLowerCase() === vendorName.toLowerCase());
    if (!v) return;

    document.getElementById('editVendorModalTitle').innerText = `✏️ Edit Vendor Profile: ${v.name}`;
    document.getElementById('modalVenName').value = v.name;
    document.getElementById('modalVenName').disabled = true;
    document.getElementById('modalVenDisplayName').value = v.display_name || v.name;
    document.getElementById('modalVenOs').value = v.default_os_version || "";
    document.getElementById('modalVenPortPrefix').value = v.port_prefix || "Port";
    document.getElementById('modalVenPlatforms').value = (v.platforms || []).join(', ');
    document.getElementById('modalVenSpeeds').value = (v.supported_speeds || []).join(', ');

    document.getElementById('editVendorModal').classList.add('active');
}

function closeEditVendorModal() {
    document.getElementById('editVendorModal').classList.remove('active');
}

async function saveVendorFromModal() {
    const name = document.getElementById('modalVenName').value.trim();
    const display_name = document.getElementById('modalVenDisplayName').value.trim() || name;
    const default_os_version = document.getElementById('modalVenOs').value.trim();
    const port_prefix = document.getElementById('modalVenPortPrefix').value.trim() || "Port";
    const platformsRaw = document.getElementById('modalVenPlatforms').value.trim();
    const speedsRaw = document.getElementById('modalVenSpeeds').value.trim();

    if (!name) {
        alert("⚠️ Vendor Short Name is required (e.g. Huawei, Mikrotik)!");
        return;
    }

    const platforms = platformsRaw ? platformsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
    const supported_speeds = speedsRaw ? speedsRaw.split(',').map(s => s.trim()).filter(Boolean) : ["1G", "10G"];

    const payload = {
        name,
        display_name,
        default_os_version,
        port_prefix,
        platforms,
        supported_speeds,
        default_port_type: "GigabitEthernet"
    };

    try {
        const res = await fetch('/api/catalog/vendors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            closeEditVendorModal();
            await loadVendorCatalog();
            await loadScenarioCatalog();
            renderStudioVendors();
            populateVendorDropdown();
        } else {
            const err = await res.json();
            alert(`❌ Error saving vendor: ${err.detail || 'Failed'}`);
        }
    } catch (e) {
        alert(`❌ Network error: ${e.message}`);
    }
}

async function deleteStudioVendor(vendorName) {
    if (!confirm(`Are you sure you want to delete vendor profile '${vendorName}'?`)) return;

    try {
        const res = await fetch(`/api/catalog/vendors/${encodeURIComponent(vendorName)}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            await loadVendorCatalog();
            await loadScenarioCatalog();
            renderStudioVendors();
            populateVendorDropdown();
        } else {
            const err = await res.json();
            alert(`❌ Error deleting vendor: ${err.detail || 'Failed'}`);
        }
    } catch (e) {
        alert(`❌ Network error: ${e.message}`);
    }
}

function triggerVendorJsonImport() {
    const input = document.getElementById('vendorJsonInput');
    if (input) input.click();
}

async function handleVendorJsonImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/catalog/vendors/import', {
            method: 'POST',
            body: formData
        });

        if (res.ok) {
            alert("✅ Vendor platform profiles imported successfully!");
            await loadVendorCatalog();
            await loadScenarioCatalog();
            renderStudioVendors();
            populateVendorDropdown();
        } else {
            const err = await res.json();
            alert(`❌ Failed to import vendor profiles: ${err.detail || 'Error'}`);
        }
    } catch (e) {
        alert(`❌ Network error: ${e.message}`);
    } finally {
        event.target.value = '';
    }
}

function exportVendorJson() {
    window.location.href = '/api/catalog/vendors/export';
}

async function resetAllCatalogsToDefaults() {
    if (!confirm("Are you sure you want to reset all test scenarios and vendor catalogs to factory presets? Any custom additions will be restored.")) return;

    try {
        const res = await fetch('/api/catalog/reset', { method: 'POST' });
        if (res.ok) {
            alert("✅ Factory presets restored successfully!");
            await loadVendorCatalog();
            await loadScenarioCatalog();
            if (activeCatalogTab === 'scenarios') renderStudioScenarios();
            else renderStudioVendors();
            if (currentStage === 3) renderAuditStage();
        }
    } catch (e) {
        alert(`❌ Error: ${e.message}`);
    }
}


