/**
 * IronCore Fitness Website Frontend Scripts
 * Handles dynamic content fetching, filters, pricing toggles, modals, and forms.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Global state
  let allPlans = [];
  let allEquipment = [];
  let currentDuration = 1;
  let selectedPlanForCheckout = null;

  // Initialize UI components
  initMobileMenu();
  fetchPlans();
  fetchEquipment();
  fetchTrainers();
  fetchNutrition();
  initDurationSwitcher();
  initModals();
  initEnquiryForm();
  initDietForm();
  initCheckoutForm();

  /* ================= NAVIGATION ================= */
  function initMobileMenu() {
    const menuBtn = document.getElementById("mobileMenuBtn");
    const navMenu = document.getElementById("navMenu");

    if (menuBtn && navMenu) {
      menuBtn.addEventListener("click", () => {
        navMenu.classList.toggle("open");
      });

      // Close menu on link click
      navMenu.querySelectorAll(".nav-link").forEach(link => {
        link.addEventListener("click", () => {
          navMenu.classList.remove("open");
        });
      });
    }
  }

  /* ================= PLANS & PRICING ================= */
  async function fetchPlans() {
    const container = document.getElementById("pricingCardsGrid");
    try {
      const res = await fetch("/api/plans");
      const data = await res.json();
      allPlans = data.plans || [];
      renderPricingCards(currentDuration);
    } catch (err) {
      container.innerHTML = `<div class="loading-spinner">Unable to load plans. Please refresh.</div>`;
    }
  }

  function initDurationSwitcher() {
    const buttons = document.querySelectorAll(".duration-btn");
    buttons.forEach(btn => {
      btn.addEventListener("click", () => {
        buttons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentDuration = parseInt(btn.dataset.duration);
        renderPricingCards(currentDuration);
      });
    });
  }

  function renderPricingCards(duration) {
    const container = document.getElementById("pricingCardsGrid");
    const plansForDuration = allPlans.filter(p => p.duration_months === duration);

    if (plansForDuration.length === 0) {
      container.innerHTML = `<div class="loading-spinner">No specific plans for this duration.</div>`;
      return;
    }

    container.innerHTML = plansForDuration.map(plan => {
      const isCardio = Boolean(plan.includes_cardio);
      const isFeatured = isCardio;

      return `
        <div class="pricing-card ${isFeatured ? 'featured' : ''}">
          ${isFeatured ? '<span class="pricing-badge">Most Popular</span>' : ''}
          <div class="plan-header">
            <h3 class="plan-name">${plan.name}</h3>
            ${plan.savings_text ? `<span class="plan-savings-pill">🎉 ${plan.savings_text}</span>` : ''}
            <div class="plan-price-wrap">
              <span class="currency">₹</span>
              <span class="price-val">${plan.base_price.toLocaleString('en-IN')}</span>
              <span class="price-period">/ ${plan.duration_months === 1 ? 'month' : `${plan.duration_months} months`}</span>
            </div>
            <div class="plan-cardio-status ${isCardio ? 'included' : 'excluded'}">
              ${isCardio ? '✔ Cardio Access Included' : '✖ Cardio Not Included (Optional +₹300/mo)'}
            </div>
          </div>

          <ul class="plan-features-list">
            ${(plan.features || []).map(feat => {
              const isEx = feat.includes("NOT INCLUDED");
              return `
                <li class="plan-feature-item ${isEx ? 'excluded-item' : ''}">
                  <span class="feature-tick">${isEx ? '—' : '✔'}</span>
                  <span>${feat}</span>
                </li>
              `;
            }).join('')}
          </ul>

          <button class="btn ${isFeatured ? 'btn-primary' : 'btn-secondary'} btn-block select-plan-btn" data-plan-id="${plan.id}">
            Choose ${plan.name}
          </button>
        </div>
      `;
    }).join('');

    // Attach click handlers to plan buttons
    container.querySelectorAll(".select-plan-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const planId = parseInt(btn.dataset.planId);
        const plan = allPlans.find(p => p.id === planId);
        openCheckoutModal(plan);
      });
    });
  }

  /* ================= EQUIPMENT & INVENTORY ================= */
  async function fetchEquipment() {
    const grid = document.getElementById("equipmentGrid");
    try {
      const res = await fetch("/api/equipment");
      const data = await res.json();
      allEquipment = data.equipment || [];
      renderEquipment("All");
      initEquipmentFilters();
    } catch (err) {
      grid.innerHTML = `<div class="loading-spinner">Unable to load equipment inventory.</div>`;
    }
  }

  function initEquipmentFilters() {
    const filterBtns = document.querySelectorAll("#equipmentFilters .filter-btn");
    filterBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        filterBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const cat = btn.dataset.category;
        renderEquipment(cat);
      });
    });
  }

  function renderEquipment(category) {
    const grid = document.getElementById("equipmentGrid");
    const filtered = category === "All"
      ? allEquipment
      : allEquipment.filter(e => e.category === category);

    if (filtered.length === 0) {
      grid.innerHTML = `<div class="loading-spinner">No equipment found in this category.</div>`;
      return;
    }

    grid.innerHTML = filtered.map(item => `
      <div class="equipment-card">
        <div class="card-img-wrap">
          <img src="${item.image_url}" alt="${item.name}" loading="lazy">
          <span class="card-category-tag">${item.category}</span>
        </div>
        <div class="card-body">
          <h3 class="equipment-title">${item.name}</h3>
          <p class="equipment-desc">${item.description}</p>
          <div class="beginner-tip-box">
            <strong>Beginner Note:</strong> ${item.beginner_notes}
          </div>
          <div class="card-footer">
            <button class="btn btn-secondary btn-block view-tutorial-btn" data-eq-id="${item.id}">
              🎥 Setup & Tutorial Video
            </button>
          </div>
        </div>
      </div>
    `).join('');

    grid.querySelectorAll(".view-tutorial-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const eqId = parseInt(btn.dataset.eqId);
        const item = allEquipment.find(e => e.id === eqId);
        openTutorialModal(item);
      });
    });
  }

  /* ================= TRAINERS ================= */
  async function fetchTrainers() {
    const grid = document.getElementById("trainersGrid");
    try {
      const res = await fetch("/api/trainers");
      const data = await res.json();
      const trainers = data.trainers || [];

      grid.innerHTML = trainers.map(t => `
        <div class="trainer-card">
          <div class="trainer-img-wrap">
            <img src="${t.image_url}" alt="${t.name}" loading="lazy">
          </div>
          <div class="trainer-info">
            <h3 class="trainer-name">${t.name}</h3>
            <div class="trainer-role">${t.role_title}</div>
            <div class="trainer-qual">🎓 ${t.qualifications}</div>
            <p class="trainer-bio">${t.bio}</p>
            <div class="trainer-reach-box">
              <strong>🕒 When to find on floor:</strong><br>${t.how_to_reach}
            </div>
          </div>
        </div>
      `).join('');
    } catch (err) {
      grid.innerHTML = `<div class="loading-spinner">Unable to load coaches.</div>`;
    }
  }

  /* ================= NUTRITION ================= */
  async function fetchNutrition() {
    const grid = document.getElementById("nutritionGrid");
    try {
      const res = await fetch("/api/nutrition");
      const data = await res.json();
      const resources = data.nutrition || [];

      grid.innerHTML = resources.map(n => `
        <div class="nutrition-card">
          <div class="nutrition-cat">${n.category}</div>
          <h3 class="nutrition-title">${n.title}</h3>
          <p class="nutrition-desc">${n.description}</p>
          <ul class="nutrition-points">
            ${(n.key_points || []).map(pt => `<li>${pt}</li>`).join('')}
          </ul>
          <div class="nutrition-reviewer">
            Reviewed by: <strong>${n.reviewed_by}</strong>
          </div>
        </div>
      `).join('');
    } catch (err) {
      grid.innerHTML = `<div class="loading-spinner">Unable to load nutrition resources.</div>`;
    }
  }

  /* ================= MODAL HANDLERS ================= */
  function initModals() {
    // Tutorial Modal Close
    const closeTutBtn = document.getElementById("closeTutorialModal");
    const tutModal = document.getElementById("tutorialModal");
    if (closeTutBtn && tutModal) {
      closeTutBtn.addEventListener("click", () => tutModal.classList.remove("open"));
      tutModal.addEventListener("click", (e) => {
        if (e.target === tutModal) tutModal.classList.remove("open");
      });
    }

    // Checkout Modal Close
    const closeCheckBtn = document.getElementById("closeCheckoutModal");
    const checkModal = document.getElementById("checkoutModal");
    if (closeCheckBtn && checkModal) {
      closeCheckBtn.addEventListener("click", () => checkModal.classList.remove("open"));
      checkModal.addEventListener("click", (e) => {
        if (e.target === checkModal) checkModal.classList.remove("open");
      });
    }

    // Diet Modal Open/Close
    const openDietBtn = document.getElementById("openDietModalBtn");
    const closeDietBtn = document.getElementById("closeDietModal");
    const dietModal = document.getElementById("dietModal");
    if (openDietBtn && dietModal) {
      openDietBtn.addEventListener("click", () => dietModal.classList.add("open"));
    }
    if (closeDietBtn && dietModal) {
      closeDietBtn.addEventListener("click", () => dietModal.classList.remove("open"));
      dietModal.addEventListener("click", (e) => {
        if (e.target === dietModal) dietModal.classList.remove("open");
      });
    }
  }

  function openTutorialModal(item) {
    const modal = document.getElementById("tutorialModal");
    const content = document.getElementById("tutorialModalContent");

    const setupStepsFormatted = (item.setup_steps || '').split('\n').filter(s => s.trim());
    const commonMistakesFormatted = (item.common_mistakes || '').split(';').filter(s => s.trim());

    content.innerHTML = `
      <div class="modal-header">
        <span class="card-category-tag">${item.category}</span>
        <h2 style="font-family: var(--font-heading); font-size: 2rem; color: #fff; margin-top: 8px;">
          ${item.name} Tutorial & Setup
        </h2>
        <p style="color: var(--text-muted); font-size: 0.95rem;">${item.description}</p>
      </div>

      ${item.tutorial_url ? `
        <div class="tutorial-video-wrapper">
          <iframe src="${item.tutorial_url}" title="${item.name} Video Tutorial" allowfullscreen></iframe>
        </div>
      ` : ''}

      <div class="tutorial-meta-grid">
        <div class="tutorial-step-box">
          <h4>🛠️ Step-by-Step Machine Setup</h4>
          <ol style="padding-left: 20px; font-size: 0.88rem; color: #d1d5db; display: flex; flex-direction: column; gap: 8px;">
            ${setupStepsFormatted.map(step => `<li>${step.replace(/^\d+\.\s*/, '')}</li>`).join('')}
          </ol>
        </div>

        <div class="tutorial-step-box">
          <h4>⚠️ Common Mistakes to Avoid</h4>
          <ul style="padding-left: 20px; font-size: 0.88rem; color: #fca5a5; display: flex; flex-direction: column; gap: 8px;">
            ${commonMistakesFormatted.map(m => `<li>${m}</li>`).join('')}
          </ul>
        </div>
      </div>

      <div class="beginner-tip-box" style="margin-bottom: 20px;">
        <strong>💡 Beginner Tip:</strong> ${item.beginner_notes}
      </div>

      <div class="help-guide-box" style="padding: 16px 20px;">
        <span class="help-icon">👨‍🏫</span>
        <div class="help-text">
          <h4 style="color: #fff; font-size: 1rem;">Unsure about your seat height or weight pin?</h4>
          <p style="font-size: 0.85rem; color: var(--text-muted);">
            Never force a stuck pin or guess your posture. Wave to our floor trainer on duty to double-check your position in 30 seconds!
          </p>
        </div>
      </div>
    `;

    modal.classList.add("open");
  }

  /* ================= CHECKOUT / JOIN WIZARD ================= */
  function openCheckoutModal(plan) {
    selectedPlanForCheckout = plan;
    const modal = document.getElementById("checkoutModal");
    const sumPlanName = document.getElementById("sumPlanName");
    const sumPlanDuration = document.getElementById("sumPlanDuration");
    const sumBasePrice = document.getElementById("sumBasePrice");
    const cardioRow = document.getElementById("cardioAddonRow");
    const cardioCheckbox = document.getElementById("checkoutCardioAddon");
    const cardioFeeText = document.getElementById("cardioAddonFeeText");
    const receiptBox = document.getElementById("receiptContainer");
    const checkoutForm = document.getElementById("checkoutForm");
    const statusBox = document.getElementById("checkoutStatus");

    // Reset status & forms
    receiptBox.style.display = "none";
    checkoutForm.style.display = "block";
    statusBox.textContent = "";

    sumPlanName.textContent = plan.name;
    sumPlanDuration.textContent = `${plan.duration_months} ${plan.duration_months === 1 ? 'Month' : 'Months'}`;
    sumBasePrice.textContent = `₹${plan.base_price.toLocaleString('en-IN')}`;

    const alreadyIncludesCardio = Boolean(plan.includes_cardio);

    if (alreadyIncludesCardio) {
      cardioRow.style.display = "none";
      cardioCheckbox.checked = true;
    } else {
      cardioRow.style.display = "flex";
      cardioCheckbox.checked = false;
      const totalCardioFee = 300 * plan.duration_months;
      cardioFeeText.textContent = `+₹${totalCardioFee.toLocaleString('en-IN')} (+₹300/mo for ${plan.duration_months}m)`;
    }

    updateCheckoutTotal();
    modal.classList.add("open");
  }

  function updateCheckoutTotal() {
    if (!selectedPlanForCheckout) return;
    const cardioCheckbox = document.getElementById("checkoutCardioAddon");
    const sumTotalPrice = document.getElementById("sumTotalPrice");
    const duration = selectedPlanForCheckout.duration_months;
    const base = selectedPlanForCheckout.base_price;
    const alreadyCardio = Boolean(selectedPlanForCheckout.includes_cardio);

    let extra = 0;
    if (cardioCheckbox.checked && !alreadyCardio) {
      extra = 300 * duration;
    }

    const total = base + extra;
    sumTotalPrice.textContent = `₹${total.toLocaleString('en-IN')}`;
  }

  function initCheckoutForm() {
    const cardioCheckbox = document.getElementById("checkoutCardioAddon");
    const modeCards = document.querySelectorAll(".pay-mode-card");
    const proceedBtn = document.getElementById("proceedPaymentBtn");
    const checkoutForm = document.getElementById("checkoutForm");

    if (cardioCheckbox) {
      cardioCheckbox.addEventListener("change", updateCheckoutTotal);
    }

    // Payment mode selection (Razorpay vs Cash)
    modeCards.forEach(card => {
      card.addEventListener("click", () => {
        modeCards.forEach(c => c.classList.remove("selected"));
        card.classList.add("selected");
        const radio = card.querySelector('input[name="paymentMethod"]');
        if (radio) radio.checked = true;

        if (radio.value === "cash") {
          proceedBtn.textContent = "Reserve & Pay Cash at Gym";
        } else {
          proceedBtn.textContent = "Proceed with Online Payment";
        }
      });
    });

    checkoutForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!selectedPlanForCheckout) return;

      const name = document.getElementById("regName").value.trim();
      const phone = document.getElementById("regPhone").value.trim();
      const email = document.getElementById("regEmail").value.trim();
      const cardioAddon = cardioCheckbox.checked;
      const paymentChoice = document.querySelector('input[name="paymentMethod"]:checked').value;
      const statusBox = document.getElementById("checkoutStatus");

      const payload = {
        name,
        phone,
        email,
        plan_id: selectedPlanForCheckout.id,
        cardio_addon: cardioAddon,
        payment_choice: paymentChoice
      };

      PaymentHandler.processRegistration(
        payload,
        (msg, type) => {
          statusBox.textContent = msg;
          statusBox.className = `form-status ${type}`;
        },
        (result) => {
          showReceipt(result, payload);
        }
      );
    });
  }

  function showReceipt(result, payload) {
    const form = document.getElementById("checkoutForm");
    const receiptBox = document.getElementById("receiptContainer");
    form.style.display = "none";

    const isOnline = result.mode === "online";

    receiptBox.innerHTML = `
      <div class="receipt-icon">${isOnline ? '✅' : '🎫'}</div>
      <h3 class="receipt-title">${isOnline ? 'Membership Activated!' : 'Registration Reserved!'}</h3>
      <span class="receipt-num">${result.receipt_no ? `Receipt #: ${result.receipt_no}` : `Member ID: #${result.member_id}`}</span>

      <div class="receipt-details">
        <div><strong>Member Name:</strong> ${payload.name}</div>
        <div><strong>Mobile:</strong> ${payload.phone}</div>
        <div><strong>Plan:</strong> ${selectedPlanForCheckout.name}</div>
        <div><strong>Cardio Access:</strong> ${payload.cardio_addon || selectedPlanForCheckout.includes_cardio ? 'Included ✔' : 'Not Included'}</div>
        <div><strong>Payment Mode:</strong> ${isOnline ? 'Paid Online via Razorpay' : 'Pay Cash at Front Desk'}</div>
        <div><strong>Status:</strong> <span style="color: ${isOnline ? 'var(--accent-green)' : '#fbbf24'}; font-weight: 700;">${isOnline ? 'Active' : 'Awaiting Cash at Desk'}</span></div>
        ${isOnline ? `
          <div><strong>Active Validity:</strong> ${result.membership_start} to ${result.membership_end}</div>
          <div><strong>Payment ID:</strong> ${result.payment_id}</div>
        ` : `
          <div style="background: rgba(226, 241, 11, 0.1); padding: 8px; border-radius: 4px; margin-top: 8px;">
            👉 <strong>Instructions:</strong> Please show this receipt or share your mobile number at the gym reception desk to complete your cash payment and collect your access key fob.
          </div>
        `}
      </div>

      <div style="display: flex; gap: 12px; justify-content: center;">
        <button class="btn btn-secondary btn-sm" onclick="window.print()">🖨️ Print Receipt</button>
        <button class="btn btn-primary btn-sm" onclick="document.getElementById('checkoutModal').classList.remove('open')">Done</button>
      </div>
    `;

    receiptBox.style.display = "block";
  }

  /* ================= ENQUIRY FORM ================= */
  function initEnquiryForm() {
    const form = document.getElementById("enquiryForm");
    const status = document.getElementById("enqStatusMessage");
    const submitBtn = document.getElementById("enqSubmitBtn");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting...";
      status.textContent = "";

      const body = {
        name: document.getElementById("enqName").value.trim(),
        phone: document.getElementById("enqPhone").value.trim(),
        email: document.getElementById("enqEmail").value.trim(),
        interested_plan: document.getElementById("enqPlan").value,
        preferred_time: document.getElementById("enqTime").value,
        message: document.getElementById("enqMessage").value.trim()
      };

      try {
        const res = await fetch("/api/enquiries", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });

        const data = await res.json();
        if (res.ok) {
          status.className = "form-status success";
          status.textContent = "✔ " + data.message;
          form.reset();
        } else {
          status.className = "form-status error";
          status.textContent = "✖ " + (data.error || "Submission failed");
        }
      } catch (err) {
        status.className = "form-status error";
        status.textContent = "✖ Connection error. Please try again.";
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Enquiry";
      }
    });
  }

  /* ================= DIET CONSULTATION FORM ================= */
  function initDietForm() {
    const form = document.getElementById("dietForm");
    const status = document.getElementById("dietStatus");
    const submitBtn = document.getElementById("dietSubmitBtn");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting...";

      const body = {
        name: document.getElementById("dietName").value.trim(),
        phone: document.getElementById("dietPhone").value.trim(),
        dietary_preference: document.getElementById("dietPreference").value,
        primary_goal: document.getElementById("dietGoal").value,
        allergies: document.getElementById("dietAllergies").value.trim(),
        budget_range: document.getElementById("dietBudget").value.trim(),
        notes: document.getElementById("dietNotes").value.trim()
      };

      try {
        const res = await fetch("/api/diet-requests", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });

        const data = await res.json();
        if (res.ok) {
          status.className = "form-status success";
          status.textContent = "✔ " + data.message;
          form.reset();
          setTimeout(() => {
            document.getElementById("dietModal").classList.remove("open");
            status.textContent = "";
          }, 3000);
        } else {
          status.className = "form-status error";
          status.textContent = "✖ " + (data.error || "Submission failed");
        }
      } catch (err) {
        status.className = "form-status error";
        status.textContent = "✖ Network error. Please try again.";
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Request";
      }
    });
  }
});
