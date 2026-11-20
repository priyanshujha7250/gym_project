/**
 * IronCore Management Portal JavaScript
 * Handles authentication, data tables, modals, cash recording, and renewals.
 */

// Global state
let currentAdmin = null;
let currentTab = "overview";
let allMembersCache = [];
let allPlansCache = [];
let allEnquiriesCache = [];
let allPaymentsCache = [];

document.addEventListener("DOMContentLoaded", () => {
  initAuth();
  initTabNavigation();
  initFormsAndModals();
});

/* ================= AUTHENTICATION ================= */
async function initAuth() {
  const token = localStorage.getItem("gym_admin_token");
  if (!token) {
    showLoginView();
    return;
  }

  try {
    const res = await fetch("/api/admin/me", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      currentAdmin = data.admin;
      showDashboardView();
    } else {
      localStorage.removeItem("gym_admin_token");
      showLoginView();
    }
  } catch (err) {
    showLoginView();
  }
}

function showLoginView() {
  document.getElementById("loginView").style.display = "flex";
  document.getElementById("dashboardView").style.display = "none";
}

function showDashboardView() {
  document.getElementById("loginView").style.display = "none";
  document.getElementById("dashboardView").style.display = "flex";

  document.getElementById("userName").textContent = currentAdmin.name;
  document.getElementById("userRole").textContent = currentAdmin.role;
  document.getElementById("userAvatar").textContent = currentAdmin.name.charAt(0).toUpperCase();

  loadDashboardStats();
  loadAllPlans();
}

function getAuthHeader() {
  const token = localStorage.getItem("gym_admin_token");
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`
  };
}

/* ================= TAB NAVIGATION ================= */
function initTabNavigation() {
  const navItems = document.querySelectorAll(".sidebar-nav .nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabName = item.dataset.tab;
      switchTab(tabName);
    });
  });

  document.getElementById("logoutBtn").addEventListener("click", async () => {
    try {
      await fetch("/api/admin/logout", {
        method: "POST",
        headers: getAuthHeader()
      });
    } catch (e) {}
    localStorage.removeItem("gym_admin_token");
    currentAdmin = null;
    showLoginView();
  });

  document.getElementById("refreshStatsBtn").addEventListener("click", () => {
    loadDashboardStats();
    loadCurrentTabData();
  });
}

function switchTab(tabName) {
  currentTab = tabName;
  document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
    item.classList.toggle("active", item.dataset.tab === tabName);
  });

  document.querySelectorAll(".tab-pane").forEach(pane => {
    pane.classList.remove("active");
  });

  const activePane = document.getElementById(`tab-${tabName}`);
  if (activePane) activePane.classList.add("active");

  const titles = {
    overview: ["Dashboard Overview", "System statistics, revenue metrics and floor status."],
    enquiries: ["Prospect Enquiries", "Follow up with prospective members and tour bookings."],
    members: ["Members Directory", "Manage member profiles, renewals, and access status."],
    payments: ["Payments & Collections", "Audit trail of cash received at desk and Razorpay online payments."],
    plans: ["Plans & Pricing Configuration", "Manage membership packages, durations, and cardio inclusions."],
    equipment: ["Equipment & Video Tutorials", "Maintain gym machine inventory, setup guides, and video links."],
    diet: ["Dietary Consultations", "Review custom nutrition inquiries with members."],
    audit: ["Security Audit Trail", "System activity and operational change logs."]
  };

  if (titles[tabName]) {
    document.getElementById("pageTitle").textContent = titles[tabName][0];
    document.getElementById("pageSub").textContent = titles[tabName][1];
  }

  loadCurrentTabData();
}

function loadCurrentTabData() {
  if (currentTab === "overview") loadDashboardStats();
  else if (currentTab === "enquiries") loadEnquiries();
  else if (currentTab === "members") loadMembers();
  else if (currentTab === "payments") loadPayments();
  else if (currentTab === "plans") loadPlansTable();
  else if (currentTab === "equipment") loadEquipmentTable();
  else if (currentTab === "diet") loadDietRequests();
  else if (currentTab === "audit") loadAuditLogs();
}

/* ================= 1. OVERVIEW & KPIS ================= */
async function loadDashboardStats() {
  try {
    const res = await fetch("/api/admin/stats", { headers: getAuthHeader() });
    if (!res.ok) return;
    const data = await res.json();
    const s = data.stats;

    document.getElementById("statTotalRev").textContent = `₹${s.total_revenue.toLocaleString('en-IN')}`;
    document.getElementById("statOnlineRev").textContent = `₹${s.online_revenue.toLocaleString('en-IN')}`;
    document.getElementById("statCashRev").textContent = `₹${s.cash_revenue.toLocaleString('en-IN')}`;
    document.getElementById("statActiveMem").textContent = s.active_members;
    document.getElementById("statTotalMem").textContent = s.total_members;
    document.getElementById("statAwaitingPay").textContent = s.awaiting_payment;
    document.getElementById("statExpiringSoon").textContent = s.expiring_soon;
    document.getElementById("statNewEnq").textContent = s.new_enquiries;

    // Sidebar badge
    const badge = document.getElementById("enquiryBadge");
    if (badge) {
      badge.textContent = s.new_enquiries;
      badge.style.display = s.new_enquiries > 0 ? "inline-block" : "none";
    }

    // Render recent payments
    const tbody = document.getElementById("recentPaymentsTable");
    const recents = data.recent_payments || [];
    if (recents.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center">No payment records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = recents.map(p => `
      <tr>
        <td><code>${p.receipt_no || ('#' + p.id)}</code></td>
        <td><strong>${p.member_name}</strong></td>
        <td><strong>₹${p.amount.toLocaleString('en-IN')}</strong></td>
        <td>${p.payment_method}</td>
        <td><span class="badge-status ${formatStatusClass(p.payment_status)}">${p.payment_status}</span></td>
        <td>${formatDate(p.paid_at)}</td>
        <td>${p.recorded_by || 'Online System'}</td>
      </tr>
    `).join('');

  } catch (err) {
    console.error("Stats load error:", err);
  }
}

/* ================= 2. ENQUIRIES ================= */
async function loadEnquiries() {
  const tbody = document.getElementById("enquiriesTableBody");
  try {
    const res = await fetch("/api/enquiries", { headers: getAuthHeader() });
    const data = await res.json();
    allEnquiriesCache = data.enquiries || [];
    renderEnquiriesTable();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center">Failed to load enquiries.</td></tr>`;
  }
}

function renderEnquiriesTable() {
  const tbody = document.getElementById("enquiriesTableBody");
  const filter = document.getElementById("enquiryFilterStatus").value;
  const filtered = filter === "All"
    ? allEnquiriesCache
    : allEnquiriesCache.filter(e => e.status === filter);

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center">No matching enquiries.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(e => `
    <tr>
      <td>#${e.id}</td>
      <td>${formatDate(e.created_at)}</td>
      <td><strong>${e.name}</strong></td>
      <td>
        <a href="tel:${e.phone}" style="color: var(--accent-blue);">📞 ${e.phone}</a><br>
        <a href="https://wa.me/91${e.phone.replace(/\D/g, '')}" target="_blank" style="color: #25d366; font-size: 0.8rem;">💬 WhatsApp</a>
      </td>
      <td>${e.interested_plan || 'General'}</td>
      <td>${e.preferred_time || 'Anytime'}</td>
      <td style="max-width: 200px;">${e.message || '—'}</td>
      <td>
        <span class="badge-status ${formatStatusClass(e.status)}">${e.status}</span>
      </td>
      <td>
        <select class="form-select-sm" onchange="updateEnquiryStatus(${e.id}, this.value)">
          <option value="New" ${e.status === 'New' ? 'selected' : ''}>New</option>
          <option value="Contacted" ${e.status === 'Contacted' ? 'selected' : ''}>Contacted</option>
          <option value="Converted" ${e.status === 'Converted' ? 'selected' : ''}>Converted</option>
          <option value="Closed" ${e.status === 'Closed' ? 'selected' : ''}>Closed</option>
        </select>
      </td>
    </tr>
  `).join('');
}

window.updateEnquiryStatus = async function(id, status) {
  try {
    const res = await fetch(`/api/enquiries/${id}/status`, {
      method: "PUT",
      headers: getAuthHeader(),
      body: JSON.stringify({ status })
    });
    if (res.ok) {
      loadEnquiries();
      loadDashboardStats();
    }
  } catch (err) {
    alert("Failed to update enquiry status");
  }
};

/* ================= 3. MEMBERS ================= */
async function loadMembers() {
  const tbody = document.getElementById("membersTableBody");
  try {
    const res = await fetch("/api/members", { headers: getAuthHeader() });
    const data = await res.json();
    allMembersCache = data.members || [];
    renderMembersTable();
    populateCashMemberDropdown();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center">Failed to load members.</td></tr>`;
  }
}

function renderMembersTable() {
  const tbody = document.getElementById("membersTableBody");
  const search = document.getElementById("memberSearchInput").value.toLowerCase();
  const filter = document.getElementById("memberFilterStatus").value;

  const filtered = allMembersCache.filter(m => {
    const matchesSearch = m.name.toLowerCase().includes(search) || m.phone.includes(search);
    const matchesStatus = filter === "All" || m.status === filter;
    return matchesSearch && matchesStatus;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center">No members found matching criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(m => {
    const isAwaiting = m.status === "Awaiting payment";
    const isActive = m.status === "Active";

    return `
      <tr>
        <td>#${m.id}</td>
        <td>
          <strong>${m.name}</strong><br>
          <small style="color: var(--text-dim);">${m.email || ''}</small>
        </td>
        <td><a href="tel:${m.phone}" style="color: var(--accent-blue);">📞 ${m.phone}</a></td>
        <td>${m.plan_name || 'Custom'} (${m.duration_months || 1}m)</td>
        <td>${m.cardio_addon || m.includes_cardio ? '<span style="color: var(--accent-green); font-weight: 700;">✔ Added</span>' : '<span style="color: var(--text-dim);">✖ No</span>'}</td>
        <td>${m.membership_start || '—'}</td>
        <td>${m.membership_end || '—'}</td>
        <td><span class="badge-status ${formatStatusClass(m.status)}">${m.status}</span></td>
        <td>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            ${isAwaiting ? `
              <button class="btn btn-primary btn-sm" onclick="openCashForMember(${m.id})">💵 Record Cash</button>
            ` : ''}
            ${isActive ? `
              <button class="btn btn-secondary btn-sm" onclick="renewMember(${m.id})">🔄 Renew</button>
            ` : ''}
            <button class="btn btn-outline btn-sm" onclick="openEditMember(${m.id})">✏️ Edit</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

window.renewMember = async function(id) {
  if (!confirm("Renew this member for another term? This will extend their expiry date.")) return;
  try {
    const res = await fetch(`/api/members/${id}/renew`, {
      method: "PUT",
      headers: getAuthHeader()
    });
    const data = await res.json();
    if (res.ok) {
      alert(`Membership renewed until: ${data.membership_end}`);
      loadMembers();
      loadDashboardStats();
    } else {
      alert(data.error || "Renewal failed");
    }
  } catch (err) {
    alert("Network error while renewing");
  }
};

window.openEditMember = function(id) {
  const member = allMembersCache.find(m => m.id === id);
  if (!member) return;

  document.getElementById("editMemberId").value = member.id;
  document.getElementById("editMemberName").value = `${member.name} (${member.phone})`;
  document.getElementById("editMemberStatus").value = member.status;
  document.getElementById("editStartDate").value = member.membership_start || "";
  document.getElementById("editEndDate").value = member.membership_end || "";
  document.getElementById("editNotes").value = member.notes || "";
  document.getElementById("editMemberStatusMsg").textContent = "";

  document.getElementById("editMemberModal").classList.add("open");
};

/* ================= 4. PAYMENTS & CASH RECORDING ================= */
async function loadPayments() {
  const tbody = document.getElementById("allPaymentsTableBody");
  try {
    const res = await fetch("/api/payments", { headers: getAuthHeader() });
    const data = await res.json();
    allPaymentsCache = data.payments || [];
    renderPaymentsTable();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center">Failed to load payments.</td></tr>`;
  }
}

function renderPaymentsTable() {
  const tbody = document.getElementById("allPaymentsTableBody");
  const filterMethod = document.getElementById("paymentFilterMethod").value;

  const filtered = filterMethod === "All"
    ? allPaymentsCache
    : allPaymentsCache.filter(p => p.payment_method === filterMethod);

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center">No payment records.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(p => `
    <tr>
      <td><code>${p.receipt_no || ('#' + p.id)}</code></td>
      <td>
        <strong>${p.member_name}</strong><br>
        <small style="color: var(--text-dim);">${p.member_phone}</small>
      </td>
      <td>${p.plan_name || 'Standard'}</td>
      <td><strong style="color: var(--accent-primary);">₹${p.amount.toLocaleString('en-IN')}</strong></td>
      <td>${p.payment_method === 'Cash' ? '💵 Cash at Desk' : '💳 Razorpay Online'}</td>
      <td><small>${p.gateway_payment_id || p.gateway_order_id || 'Cash Desk Voucher'}</small></td>
      <td><span class="badge-status ${formatStatusClass(p.payment_status)}">${p.payment_status}</span></td>
      <td>${formatDate(p.paid_at)}</td>
      <td>${p.recorded_by || 'Online Checkout'}</td>
    </tr>
  `).join('');
}

function populateCashMemberDropdown() {
  const select = document.getElementById("cashMemberSelect");
  if (!select) return;

  select.innerHTML = '<option value="">-- Choose Member --</option>' +
    allMembersCache.map(m => `
      <option value="${m.id}" data-price="${m.base_price || 1000}" data-cardio="${m.cardio_addon}">
        ${m.name} (${m.phone}) - ${m.plan_name || 'Basic'} [${m.status}]
      </option>
    `).join('');
}

window.openCashForMember = function(memberId) {
  const member = allMembersCache.find(m => m.id === memberId);
  const select = document.getElementById("cashMemberSelect");
  const amountInput = document.getElementById("cashAmount");

  select.value = memberId;

  // Calculate default price
  const base = member.base_price || 1000;
  const extra = (member.cardio_addon && !member.includes_cardio) ? (300 * (member.duration_months || 1)) : 0;
  amountInput.value = base + extra;

  document.getElementById("cashModal").classList.add("open");
};

/* ================= 5. PLANS ================= */
async function loadAllPlans() {
  try {
    const res = await fetch("/api/plans");
    const data = await res.json();
    allPlansCache = data.plans || [];

    // Populate new member plan select
    const planSelect = document.getElementById("newMemPlan");
    if (planSelect) {
      planSelect.innerHTML = allPlansCache.map(p => `
        <option value="${p.id}">
          ${p.name} - ₹${p.base_price} (${p.duration_months}m) ${p.includes_cardio ? '[Includes Cardio]' : ''}
        </option>
      `).join('');
    }
  } catch (err) {
    console.error("Failed to load plans:", err);
  }
}

async function loadPlansTable() {
  const tbody = document.getElementById("plansTableBody");
  await loadAllPlans();

  if (allPlansCache.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center">No plans defined.</td></tr>`;
    return;
  }

  tbody.innerHTML = allPlansCache.map(p => `
    <tr>
      <td>#${p.id}</td>
      <td><strong>${p.name}</strong></td>
      <td>${p.duration_months} ${p.duration_months === 1 ? 'Month' : 'Months'}</td>
      <td><strong>₹${p.base_price.toLocaleString('en-IN')}</strong></td>
      <td>${p.includes_cardio ? '<span style="color: var(--accent-green);">✔ Included</span>' : '<span style="color: #fbbf24;">✖ Excluded (+₹300/mo)</span>'}</td>
      <td>${p.savings_text ? `<span style="color: var(--accent-green);">${p.savings_text}</span>` : '—'}</td>
      <td><small>${(p.features || []).slice(0, 2).join(' • ')}...</small></td>
      <td><span class="badge-status active">Active</span></td>
    </tr>
  `).join('');
}

/* ================= 6. EQUIPMENT ================= */
async function loadEquipmentTable() {
  const tbody = document.getElementById("equipmentTableBody");
  try {
    const res = await fetch("/api/equipment");
    const data = await res.json();
    const items = data.equipment || [];

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center">No equipment found.</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map(eq => `
      <tr>
        <td>#${eq.id}</td>
        <td><strong>${eq.name}</strong></td>
        <td><span class="badge-status contacted">${eq.category}</span></td>
        <td><small>${eq.description}</small></td>
        <td><small style="color: var(--text-muted);">${eq.beginner_notes}</small></td>
        <td>${eq.tutorial_url ? `<a href="${eq.tutorial_url}" target="_blank" style="color: var(--accent-primary);">🎥 Video</a>` : '—'}</td>
        <td>
          <button class="btn btn-danger btn-sm" onclick="deleteEquipment(${eq.id})">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center">Failed to load equipment.</td></tr>`;
  }
}

window.deleteEquipment = async function(id) {
  if (!confirm("Are you sure you want to deactivate this equipment?")) return;
  try {
    const res = await fetch(`/api/equipment/${id}`, {
      method: "DELETE",
      headers: getAuthHeader()
    });
    if (res.ok) {
      loadEquipmentTable();
    }
  } catch (err) {
    alert("Delete failed");
  }
};

/* ================= 7. DIET REQUESTS ================= */
async function loadDietRequests() {
  const tbody = document.getElementById("dietTableBody");
  try {
    const res = await fetch("/api/diet-requests", { headers: getAuthHeader() });
    const data = await res.json();
    const reqs = data.diet_requests || [];

    if (reqs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center">No diet consultation requests.</td></tr>`;
      return;
    }

    tbody.innerHTML = reqs.map(d => `
      <tr>
        <td>#${d.id}</td>
        <td>${formatDate(d.created_at)}</td>
        <td><strong>${d.name}</strong></td>
        <td><a href="tel:${d.phone}" style="color: var(--accent-blue);">📞 ${d.phone}</a></td>
        <td>${d.dietary_preference}</td>
        <td><strong style="color: var(--accent-primary);">${d.primary_goal}</strong></td>
        <td>${d.allergies || 'None'}</td>
        <td>${d.budget_range || '—'}</td>
        <td><span class="badge-status ${formatStatusClass(d.status)}">${d.status}</span></td>
        <td>
          <select class="form-select-sm" onchange="updateDietStatus(${d.id}, this.value)">
            <option value="Pending Review" ${d.status === 'Pending Review' ? 'selected' : ''}>Pending</option>
            <option value="Reviewed" ${d.status === 'Reviewed' ? 'selected' : ''}>Reviewed</option>
            <option value="Consulted" ${d.status === 'Consulted' ? 'selected' : ''}>Consulted</option>
          </select>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center">Failed to load diet requests.</td></tr>`;
  }
}

window.updateDietStatus = async function(id, status) {
  try {
    const res = await fetch(`/api/diet-requests/${id}/status`, {
      method: "PUT",
      headers: getAuthHeader(),
      body: JSON.stringify({ status })
    });
    if (res.ok) loadDietRequests();
  } catch (err) {
    alert("Status update failed");
  }
};

/* ================= 8. AUDIT LOGS ================= */
async function loadAuditLogs() {
  const tbody = document.getElementById("auditTableBody");
  try {
    const res = await fetch("/api/admin/audit-logs", { headers: getAuthHeader() });
    const data = await res.json();
    const logs = data.audit_logs || [];

    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center">No audit logs found.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map(l => `
      <tr>
        <td><small style="color: var(--text-dim);">${formatDate(l.created_at)}</small></td>
        <td><code>${l.action}</code></td>
        <td>${l.details}</td>
        <td><strong>${l.admin_name}</strong></td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center">Failed to load audit log.</td></tr>`;
  }
}

/* ================= FORMS & MODAL HANDLERS ================= */
function initFormsAndModals() {
  // Login Form
  const loginForm = document.getElementById("adminLoginForm");
  const loginError = document.getElementById("loginError");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      loginError.textContent = "";

      const email = document.getElementById("adminEmail").value.trim();
      const password = document.getElementById("adminPassword").value;

      try {
        const res = await fetch("/api/admin/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) {
          localStorage.setItem("gym_admin_token", data.token);
          currentAdmin = data.admin;
          showDashboardView();
        } else {
          loginError.textContent = data.error || "Login failed";
        }
      } catch (err) {
        loginError.textContent = "Network error";
      }
    });
  }

  // Quick Action Buttons
  document.getElementById("quickRecordCashBtn").addEventListener("click", () => {
    document.getElementById("cashModal").classList.add("open");
  });
  document.getElementById("openRecordCashModalBtn").addEventListener("click", () => {
    document.getElementById("cashModal").classList.add("open");
  });
  document.getElementById("closeCashModal").addEventListener("click", () => {
    document.getElementById("cashModal").classList.remove("open");
  });

  // Cash Member Select Change
  document.getElementById("cashMemberSelect").addEventListener("change", (e) => {
    const selected = e.target.selectedOptions[0];
    if (selected && selected.dataset.price) {
      const base = parseInt(selected.dataset.price);
      const isCardio = selected.dataset.cardio === "1";
      document.getElementById("cashAmount").value = base + (isCardio ? 300 : 0);
    }
  });

  // Cash Form Submission
  document.getElementById("cashPaymentForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const statusBox = document.getElementById("cashStatus");
    statusBox.textContent = "Recording payment...";
    statusBox.className = "form-status";

    const memberId = document.getElementById("cashMemberSelect").value;
    const amount = document.getElementById("cashAmount").value;
    const startDate = document.getElementById("cashStartDate").value;
    const notes = document.getElementById("cashNotes").value.trim();

    try {
      const res = await fetch("/api/payments/cash", {
        method: "POST",
        headers: getAuthHeader(),
        body: JSON.stringify({
          member_id: memberId,
          amount,
          start_date: startDate || null,
          notes
        })
      });
      const data = await res.json();
      if (res.ok) {
        statusBox.className = "form-status success";
        statusBox.textContent = `✔ Payment recorded! Receipt: ${data.receipt_no}. Active until ${data.membership_end}`;
        setTimeout(() => {
          document.getElementById("cashModal").classList.remove("open");
          statusBox.textContent = "";
          loadDashboardStats();
          loadMembers();
          loadPayments();
        }, 1800);
      } else {
        statusBox.className = "form-status error";
        statusBox.textContent = data.error || "Failed to record cash";
      }
    } catch (err) {
      statusBox.className = "form-status error";
      statusBox.textContent = "Network error";
    }
  });

  // Edit Member Modal Close & Submit
  document.getElementById("closeEditMemberModal").addEventListener("click", () => {
    document.getElementById("editMemberModal").classList.remove("open");
  });

  document.getElementById("editMemberForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("editMemberId").value;
    const status = document.getElementById("editMemberStatus").value;
    const start_date = document.getElementById("editStartDate").value;
    const end_date = document.getElementById("editEndDate").value;
    const notes = document.getElementById("editNotes").value;
    const statusMsg = document.getElementById("editMemberStatusMsg");

    try {
      const res = await fetch(`/api/members/${id}`, {
        method: "PUT",
        headers: getAuthHeader(),
        body: JSON.stringify({
          status,
          membership_start: start_date || null,
          membership_end: end_date || null,
          notes
        })
      });
      if (res.ok) {
        statusMsg.className = "form-status success";
        statusMsg.textContent = "✔ Member updated successfully";
        setTimeout(() => {
          document.getElementById("editMemberModal").classList.remove("open");
          loadMembers();
          loadDashboardStats();
        }, 1200);
      } else {
        statusMsg.className = "form-status error";
        statusMsg.textContent = "Update failed";
      }
    } catch (err) {
      statusMsg.className = "form-status error";
      statusMsg.textContent = "Network error";
    }
  });

  // Add Walk-in Member Modal
  document.getElementById("addNewMemberBtn").addEventListener("click", () => {
    document.getElementById("addMemberModal").classList.add("open");
  });
  document.getElementById("closeAddMemberModal").addEventListener("click", () => {
    document.getElementById("addMemberModal").classList.remove("open");
  });

  document.getElementById("addMemberForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("newMemName").value.trim();
    const phone = document.getElementById("newMemPhone").value.trim();
    const email = document.getElementById("newMemEmail").value.trim();
    const plan_id = document.getElementById("newMemPlan").value;
    const cardio_addon = document.getElementById("newMemCardio").checked;
    const statusMsg = document.getElementById("addMemberStatusMsg");

    try {
      const res = await fetch("/api/members/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name, phone, email, plan_id, cardio_addon,
          payment_choice: "cash"
        })
      });
      const data = await res.json();
      if (res.ok) {
        statusMsg.className = "form-status success";
        statusMsg.textContent = `✔ Member created! ID: #${data.member_id}. You can now record cash payment.`;
        setTimeout(() => {
          document.getElementById("addMemberModal").classList.remove("open");
          document.getElementById("addMemberForm").reset();
          loadMembers();
          loadDashboardStats();
        }, 1500);
      } else {
        statusMsg.className = "form-status error";
        statusMsg.textContent = data.error || "Failed to create member";
      }
    } catch (err) {
      statusMsg.className = "form-status error";
      statusMsg.textContent = "Network error";
    }
  });

  // Add Equipment Modal
  document.getElementById("addNewEquipmentBtn").addEventListener("click", () => {
    document.getElementById("addEquipmentModal").classList.add("open");
  });
  document.getElementById("closeAddEquipmentModal").addEventListener("click", () => {
    document.getElementById("addEquipmentModal").classList.remove("open");
  });

  document.getElementById("addEquipmentForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("eqName").value.trim();
    const category = document.getElementById("eqCategory").value;
    const description = document.getElementById("eqDescription").value.trim();
    const beginner_notes = document.getElementById("eqBeginnerNotes").value.trim();
    const setup_steps = document.getElementById("eqSetupSteps").value.trim();
    const common_mistakes = document.getElementById("eqCommonMistakes").value.trim();
    const tutorial_url = document.getElementById("eqTutorialUrl").value.trim();
    const statusMsg = document.getElementById("eqStatusMsg");

    try {
      const res = await fetch("/api/equipment", {
        method: "POST",
        headers: getAuthHeader(),
        body: JSON.stringify({
          name, category, description, beginner_notes,
          setup_steps, common_mistakes, tutorial_url
        })
      });
      if (res.ok) {
        statusMsg.className = "form-status success";
        statusMsg.textContent = "✔ Equipment saved successfully!";
        setTimeout(() => {
          document.getElementById("addEquipmentModal").classList.remove("open");
          document.getElementById("addEquipmentForm").reset();
          loadEquipmentTable();
        }, 1200);
      } else {
        statusMsg.className = "form-status error";
        statusMsg.textContent = "Failed to save equipment";
      }
    } catch (err) {
      statusMsg.className = "form-status error";
      statusMsg.textContent = "Network error";
    }
  });

  // Filter Listeners
  document.getElementById("enquiryFilterStatus").addEventListener("change", renderEnquiriesTable);
  document.getElementById("memberSearchInput").addEventListener("input", renderMembersTable);
  document.getElementById("memberFilterStatus").addEventListener("change", renderMembersTable);
  document.getElementById("paymentFilterMethod").addEventListener("change", renderPaymentsTable);
}

/* ================= HELPERS ================= */
function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  } catch (e) {
    return dateStr;
  }
}

function formatStatusClass(status) {
  if (!status) return "";
  return status.toLowerCase().replace(/\s+/g, '-');
}
