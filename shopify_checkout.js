/**
 * Bath Haus — Sacred Lunar Calendar
 * Shopify Product Page: Birth Data + Calendar Selection Form
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * HOW TO INSTALL:
 *   1. Shopify Admin → Online Store → Themes → Edit Code
 *   2. assets/ → Add new file: "bath-haus-birth-data.js" → paste this file
 *   3. In product.liquid or product-form.liquid, before </body>:
 *        {{ 'bath-haus-birth-data.js' | asset_url | script_tag }}
 *
 * WHAT THIS DOES:
 *   - Injects a birth data form above the Add to Cart button
 *   - Detects the customer's timezone automatically (for UTC offset)
 *   - Lets customer choose: 1 month or 12-month subscription
 *   - Lets customer pick their starting month
 *   - Optional: "What are you calling in?" intentions field
 *   - Submits all data as Shopify line_item.properties
 *
 * WHAT THE SERVER RECEIVES (line_item.properties):
 *   birth_name        — string
 *   birth_date        — YYYY-MM-DD
 *   birth_time        — HH:MM (24h)
 *   birth_city        — "Los Angeles, USA"
 *   utc_offset        — float, e.g. "-7.0" (auto-detected from browser)
 *   timezone          — string, e.g. "America/Los_Angeles" (for server fallback)
 *   calendar_plan     — "1" or "12"
 *   calendar_year     — YYYY
 *   calendar_month    — 1–12 (starting month)
 *   intention         — string, optional (empty string if not filled)
 * ─────────────────────────────────────────────────────────────────────────────
 */

;(function () {
  'use strict';

  // ── Month names for the picker ─────────────────────────────────────────────

  const MONTHS = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December'
  ];

  // ── Detect UTC offset and IANA timezone from browser ──────────────────────

  function getBrowserTimezone() {
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const offset = -(new Date().getTimezoneOffset() / 60); // convert to hours
      return { timezone: tz, utc_offset: offset };
    } catch (e) {
      return { timezone: 'UTC', utc_offset: 0 };
    }
  }

  // ── Build the starting month options (current month → 12 months out) ───────

  function buildMonthOptions() {
    const now    = new Date();
    let year     = now.getFullYear();
    let month    = now.getMonth(); // 0-indexed
    let options  = '';

    for (let i = 0; i < 13; i++) {
      const m    = ((month + i) % 12);
      const y    = year + Math.floor((month + i) / 12);
      const val  = `${y}-${m + 1}`; // "2026-3"
      const label = `${MONTHS[m]} ${y}`;
      const sel  = i === 1 ? ' selected' : ''; // default: next month
      options   += `<option value="${val}"${sel}>${label}</option>`;
    }
    return options;
  }

  // ── Form HTML ──────────────────────────────────────────────────────────────

  function buildFormHTML() {
    const tz   = getBrowserTimezone();
    const now  = new Date();
    const nextMonth = now.getMonth() === 11 ? 1 : now.getMonth() + 2; // 1-indexed

    return `
<div class="bath-haus-birth-data" id="bh-birth-form" style="
  background: #faf9f6;
  border: 1px solid #e8e4dc;
  border-radius: 8px;
  padding: 32px 28px;
  margin: 28px 0;
  font-family: 'Jost', sans-serif;
">

  <!-- Header -->
  <p style="font-size:11px; letter-spacing:0.18em; text-transform:uppercase;
            color:#7a8c6e; margin:0 0 4px;">Sacred Lunar Calendar</p>
  <h3 style="font-family:'Cormorant Garamond',Georgia,serif; font-weight:400;
             font-size:22px; color:#3a3a2e; margin:0 0 8px;">
    Your Birth Information
  </h3>
  <p style="font-size:14px; color:#7a8c6e; line-height:1.65; margin:0 0 28px;">
    Your calendar is woven from the exact positions of the sky at the moment of
    your birth. Every transmission, ritual, and date is specific to you.
  </p>

  <!-- ── Plan selection ── -->
  <div style="margin-bottom:24px;">
    <label style="display:block; font-size:12px; letter-spacing:0.12em;
                  text-transform:uppercase; color:#5a5a4a; margin-bottom:10px;">
      Calendar Plan
    </label>
    <div style="display:flex; gap:12px; flex-wrap:wrap;">
      <label id="bh-plan-1-label" style="
        flex:1; min-width:140px; display:flex; align-items:flex-start;
        gap:10px; padding:14px 16px; border:2px solid #7a8c6e; border-radius:6px;
        cursor:pointer; background:#f0ede8;
      ">
        <input type="radio" name="properties[calendar_plan]" value="1"
               id="bh-plan-1" style="margin-top:3px; accent-color:#7a8c6e;"
               onchange="bhPlanChange()" />
        <div>
          <div style="font-size:14px; font-weight:500; color:#3a3a2e;">
            Single Month
          </div>
          <div style="font-size:12px; color:#7a8c6e; margin-top:2px;">
            One personalized calendar
          </div>
        </div>
      </label>
      <label id="bh-plan-12-label" style="
        flex:1; min-width:140px; display:flex; align-items:flex-start;
        gap:10px; padding:14px 16px; border:2px solid #e8e4dc; border-radius:6px;
        cursor:pointer;
      ">
        <input type="radio" name="properties[calendar_plan]" value="12"
               id="bh-plan-12" style="margin-top:3px; accent-color:#7a8c6e;"
               onchange="bhPlanChange()" />
        <div>
          <div style="font-size:14px; font-weight:500; color:#3a3a2e;">
            12-Month Subscription
          </div>
          <div style="font-size:12px; color:#7a8c6e; margin-top:2px;">
            Full year, starting when you choose
          </div>
        </div>
      </label>
    </div>
  </div>

  <!-- ── Starting month ── -->
  <div style="margin-bottom:20px;">
    <label style="display:block; font-size:12px; letter-spacing:0.12em;
                  text-transform:uppercase; color:#5a5a4a; margin-bottom:6px;"
           id="bh-month-label">
      Calendar Month
    </label>
    <select name="properties[calendar_month_raw]" id="bh-month-select"
            style="width:100%; padding:10px 14px; border:1px solid #d8d4cc;
                   border-radius:4px; font-size:15px; color:#3a3a2e;
                   background:#fff; box-sizing:border-box;">
      ${buildMonthOptions()}
    </select>
    <!-- Hidden fields set by JS from the select value -->
    <input type="hidden" name="properties[calendar_year]"  id="bh-cal-year" />
    <input type="hidden" name="properties[calendar_month]" id="bh-cal-month" />
  </div>

  <!-- ── Full Name ── -->
  <div style="margin-bottom:18px;">
    <label style="display:block; font-size:12px; letter-spacing:0.12em;
                  text-transform:uppercase; color:#5a5a4a; margin-bottom:6px;">
      Full Name for Calendar
    </label>
    <input type="text" name="properties[birth_name]"
           placeholder="As you'd like it to appear"
           required
           style="width:100%; padding:10px 14px; border:1px solid #d8d4cc;
                  border-radius:4px; font-size:15px; color:#3a3a2e;
                  background:#fff; box-sizing:border-box;" />
  </div>

  <!-- ── Date of Birth ── -->
  <div style="margin-bottom:18px;">
    <label style="display:block; font-size:12px; letter-spacing:0.12em;
                  text-transform:uppercase; color:#5a5a4a; margin-bottom:6px;">
      Date of Birth
    </label>
    <input type="date" name="properties[birth_date]"
           required
           style="width:100%; padding:10px 14px; border:1px solid #d8d4cc;
                  border-radius:4px; font-size:15px; color:#3a3a2e;
                  background:#fff; box-sizing:border-box;" />
  </div>

  <!-- ── Time of Birth ── -->
  <div style="margin-bottom:18px;">
    <label style="display:block; font-size:12px; letter-spacing:0.12em;
                  text-transform:uppercase; color:#5a5a4a; margin-bottom:6px;">
      Time of Birth
      <span style="font-weight:400; text-transform:none; letter-spacing:0;
                   color:#9a9a8a; margin-left:6px;">(as accurate as possible)</span>
    </label>
    <input type="time" name="properties[birth_time]"
           required
           style="width:100%; padding:10px 14px; border:1px solid #d8d4cc;
                  border-radius:4px; font-size:15px; color:#3a3a2e;
                  background:#fff; box-sizing:border-box;" />
    <p style="font-size:12px; color:#9a9a8a; margin:5px 0 0; line-height:1.5;">
      Check your birth certificate for the most accurate time.
      If unknown, enter 12:00 noon.
    </p>
  </div>

  <!-- ── City of Birth ── -->
  <div style="margin-bottom:18px;">
    <label style="display:block; font-size:12px; letter-spacing:0.12em;
                  text-transform:uppercase; color:#5a5a4a; margin-bottom:6px;">
      City &amp; Country of Birth
    </label>
    <input type="text" name="properties[birth_city]"
           placeholder="e.g. Los Angeles, USA"
           required
           style="width:100%; padding:10px 14px; border:1px solid #d8d4cc;
                  border-radius:4px; font-size:15px; color:#3a3a2e;
                  background:#fff; box-sizing:border-box;" />
    <p style="font-size:12px; color:#9a9a8a; margin:5px 0 0; line-height:1.5;">
      Used to determine your exact timezone at birth — affects your Rising sign.
    </p>
  </div>

  <!-- ── Hidden: timezone fields (auto-detected) ── -->
  <input type="hidden" name="properties[utc_offset]"
         id="bh-utc-offset" value="${tz.utc_offset}" />
  <input type="hidden" name="properties[timezone]"
         id="bh-timezone"   value="${tz.timezone}" />

  <!-- ── Intention (optional) ── -->
  <div style="margin-bottom:8px; padding-top:8px;
              border-top:1px solid #e8e4dc; margin-top:8px;">
    <label style="display:block; font-size:12px; letter-spacing:0.12em;
                  text-transform:uppercase; color:#5a5a4a; margin-bottom:6px;">
      What Are You Calling In?
      <span style="font-weight:400; text-transform:none; letter-spacing:0;
                   color:#9a9a8a; margin-left:6px;">optional</span>
    </label>
    <textarea name="properties[intention]"
              placeholder="A word, a feeling, a question, a prayer — whatever feels true right now."
              rows="3"
              style="width:100%; padding:10px 14px; border:1px solid #d8d4cc;
                     border-radius:4px; font-size:14px; color:#3a3a2e;
                     background:#fff; box-sizing:border-box;
                     resize:vertical; line-height:1.6;"></textarea>
    <p style="font-size:12px; color:#9a9a8a; margin:5px 0 0; line-height:1.5;">
      Claude will weave your intention into the monthly transmission and rituals.
    </p>
  </div>

</div>`;
  }

  // ── Plan toggle visual feedback ────────────────────────────────────────────

  window.bhPlanChange = function () {
    const is12 = document.getElementById('bh-plan-12').checked;
    const label = document.getElementById('bh-month-label');

    document.getElementById('bh-plan-1-label').style.border =
      is12 ? '2px solid #e8e4dc' : '2px solid #7a8c6e';
    document.getElementById('bh-plan-1-label').style.background =
      is12 ? 'transparent' : '#f0ede8';
    document.getElementById('bh-plan-12-label').style.border =
      is12 ? '2px solid #7a8c6e' : '2px solid #e8e4dc';
    document.getElementById('bh-plan-12-label').style.background =
      is12 ? '#f0ede8' : 'transparent';

    label.textContent = is12 ? 'Starting Month' : 'Calendar Month';
  };

  // ── Sync hidden year/month fields when select changes ─────────────────────

  function syncMonthFields() {
    const sel = document.getElementById('bh-month-select');
    if (!sel) return;
    const [year, month] = sel.value.split('-');
    document.getElementById('bh-cal-year').value  = year;
    document.getElementById('bh-cal-month').value = month;
  }

  // ── Validate before Add to Cart ───────────────────────────────────────────

  function validateForm(e) {
    const form = document.getElementById('bh-birth-form');
    if (!form) return;

    const name   = form.querySelector('[name="properties[birth_name]"]');
    const date   = form.querySelector('[name="properties[birth_date]"]');
    const time   = form.querySelector('[name="properties[birth_time]"]');
    const city   = form.querySelector('[name="properties[birth_city]"]');
    const plan   = form.querySelector('[name="properties[calendar_plan]"]:checked');

    const missing = [];
    if (!name  || !name.value.trim())  missing.push('Full Name');
    if (!date  || !date.value)         missing.push('Date of Birth');
    if (!time  || !time.value)         missing.push('Time of Birth');
    if (!city  || !city.value.trim())  missing.push('City of Birth');
    if (!plan)                          missing.push('Calendar Plan');

    if (missing.length > 0) {
      e.preventDefault();
      e.stopPropagation();
      alert(`Please fill in the following fields before adding to cart:\n\n• ${missing.join('\n• ')}`);
      return false;
    }

    // Sync the hidden year/month fields one more time before submit
    syncMonthFields();
  }

  // ── Inject and wire up ─────────────────────────────────────────────────────

  function init() {
    // Find the Add to Cart button
    const addToCartBtn = document.querySelector(
      '[name="add"], .add-to-cart, #AddToCart, [data-add-to-cart]'
    );
    if (!addToCartBtn) {
      console.warn('[Bath Haus] Could not find Add to Cart button — form not injected.');
      return;
    }

    // Inject form above the button
    const wrapper = document.createElement('div');
    wrapper.innerHTML = buildFormHTML();
    addToCartBtn.parentNode.insertBefore(wrapper, addToCartBtn);

    // Wire up month select → hidden fields
    const monthSel = document.getElementById('bh-month-select');
    if (monthSel) {
      monthSel.addEventListener('change', syncMonthFields);
      syncMonthFields(); // set initial values
    }

    // Default plan to single month selected
    const plan1 = document.getElementById('bh-plan-1');
    if (plan1) plan1.checked = true;

    // Validate on form submit / add to cart click
    const productForm = addToCartBtn.closest('form');
    if (productForm) {
      productForm.addEventListener('submit', validateForm);
    } else {
      addToCartBtn.addEventListener('click', validateForm);
    }
  }

  // ── Run ────────────────────────────────────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();


/**
 * ─────────────────────────────────────────────────────────────────────────────
 * WEBHOOK SETUP (Shopify Admin)
 *
 *   Settings → Notifications → Webhooks → Create webhook:
 *     Event:  Orders / Payment
 *     URL:    https://YOUR-RAILWAY-APP.up.railway.app/shopify/order
 *     Format: JSON
 *
 *   Copy the signing secret → Railway env var: SHOPIFY_WEBHOOK_SECRET
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * TEST CURL (direct API — bypasses Shopify):
 *
 *   # Single month
 *   curl -X POST https://YOUR-APP.railway.app/generate \
 *     -H "Content-Type: application/json" \
 *     -d '{
 *       "name": "Mandana",
 *       "birth_date": "1986-09-18",
 *       "birth_time": "12:01",
 *       "birth_city": "Los Angeles, USA",
 *       "utc_offset": -7.0,
 *       "year": 2026, "month": 3,
 *       "plan": "1",
 *       "intention": "Finding my footing in a new cycle",
 *       "format": "pdf"
 *     }' --output mandana_march_2026.pdf
 *
 *   # 12-month subscription
 *   curl -X POST https://YOUR-APP.railway.app/generate \
 *     -H "Content-Type: application/json" \
 *     -d '{
 *       "name": "Mandana",
 *       "birth_date": "1986-09-18",
 *       "birth_time": "12:01",
 *       "birth_city": "Los Angeles, USA",
 *       "utc_offset": -7.0,
 *       "start_year": 2026, "start_month": 3,
 *       "plan": "12",
 *       "format": "pdf"
 *     }' --output mandana_annual_2026.zip
 * ─────────────────────────────────────────────────────────────────────────────
 */
