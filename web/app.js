// State management for dashboard

let appState = {

    date: "",

    marketPosture: "RED",

    marketScore: 0,

    marketPostureDetails: null,

    vcpCandidates: [],

    flag_candidates: [],

    lowRiskTrades: [],

    highRiskTrades: [],

    activePortfolio: [],

    portfolioManagement: null,

    closedTrades: [],

    sectorRotation: [],

    marketBreadth: null,

    tradeJournal: [],

    screenerScope: "curated",

    allScannedCandidates: [],

    selectedSectorCategory: "ALL",

    seedCapital: localStorage.getItem("seedCapital") ? parseFloat(localStorage.getItem("seedCapital")) : 850000,

    calendarYear: new Date().getFullYear(),

    calendarMonth: new Date().getMonth(), // Current month (0-indexed)

    sortColumn: "MS_Score",

    sortDirection: "desc",

    screenerSortColumn: "Overall_Rank",

    screenerSortDirection: "asc",

    showStrongLeadersOnly: true,

    niftyClose: 0,

    niftyChange: 0,

    sensexClose: 0,

    sensexChange: 0

};

const currentSysDate = new Date();

let calendarState = {

    currentYear: currentSysDate.getFullYear(),

    currentMonth: currentSysDate.getMonth()

};

// DOM Elements (evaluated dynamically on access to prevent null references during DOM loading)

const elements = {

    get navButtons() { return document.querySelectorAll(".nav-btn"); },

    get tabContents() { return document.querySelectorAll(".tab-content"); },

    get tabTitle() { return document.getElementById("tab-title"); },

    get dateDisplay() { return document.getElementById("current-date-display"); },

    get refreshBtn() { return document.getElementById("refresh-data-btn"); },

    get filterButtons() { return document.querySelectorAll(".filter-btn"); },

    

    // Stats

    get statTotalCandidates() { return document.getElementById("stat-total-candidates"); },

    get statVcpCount() { return document.getElementById("stat-vcp-count"); },

    get statFlagCount() { return document.getElementById("stat-flag-count"); },

    

    // Market Status

    get marketPostureBadge() { return document.getElementById("market-posture-badge"); },

    get marketHealthBar() { return document.getElementById("market-health-bar"); },

    get marketHealthScore() { return document.getElementById("market-health-score"); },

    get dashboardPostureBanner() { return document.getElementById("dashboard-posture-banner"); },

    get dashboardRecommendationText() { return document.getElementById("dashboard-recommendation-text"); },

    get postureBreakdownList() { return document.getElementById("posture-breakdown-list"); },

    get postureTooltipRecommendation() { return document.getElementById("posture-tooltip-recommendation"); },

    

    // Section 1: Market Health

    get mhpStatus() { return document.getElementById("mhp-status"); },

    get mhpAgg() { return document.getElementById("mhp-agg"); },

    get mhpSizing() { return document.getElementById("mhp-sizing"); },

    

    // Section 2: Focus Industries

    get focusIndustriesListGrid() { return document.getElementById("focus-industries-list-grid"); },

    

    // Section 3: Strategic High Conviction Watchlist

    get strategicWatchlistBody() { return document.getElementById("strategic-conviction-watchlist-body"); },

    

    // Section 4: Daily Focus Watchlist

    get dailyFocusWatchlistBody() { return document.getElementById("daily-focus-watchlist-body"); },

    

    get watchlistSearch() { return document.getElementById("watchlist-search"); },

    

    // Finance Widgets

    get finSeedCapital() { return document.getElementById("fin-seed-capital"); },

    get finDeployedFunds() { return document.getElementById("fin-deployed-funds"); },

    get finRealizedPnl() { return document.getElementById("fin-realized-pnl"); },

    get finAvailableFunds() { return document.getElementById("fin-available-funds"); },

    get finRiskAtStake() { return document.getElementById("fin-risk-at-stake"); },

    get riskPctBar() { return document.getElementById("risk-pct-bar"); },

    get riskPctText() { return document.getElementById("risk-pct-text"); },

    get finConcentrationList() { return document.getElementById("fin-concentration-list"); },

    get finRiskMapGrid() { return document.getElementById("fin-risk-map-grid"); },

    get editSeedCapitalBtn() { return document.getElementById("edit-seed-capital-btn"); },

    

    get rotationCategoriesContainer() { return document.getElementById("rotation-categories-container"); },

    

    // Indices and Calendar

    get niftyValue() { return document.getElementById("nifty-value"); },

    get niftyChange() { return document.getElementById("nifty-change"); },

    get sensexValue() { return document.getElementById("sensex-value"); },

    get sensexChange() { return document.getElementById("sensex-change"); },

    get calendarDate() { return document.getElementById("calendar-date"); },

    get dashboardDatePicker() { return document.getElementById("dashboard-date-picker"); },

    

    // Redesigned AMS Modal elements

    get amsModalPriority() { return document.getElementById("ams-modal-priority"); },

    get amsModalIndustry() { return document.getElementById("ams-modal-industry"); },

    get amsModalScore() { return document.getElementById("ams-modal-score"); },

    get amsModalCompany() { return document.getElementById("ams-modal-company"); },

    get amsModalTagsContainer() { return document.getElementById("ams-modal-tags-container"); },

    get amsModalEntryVal() { return document.getElementById("ams-modal-entry-val"); },

    get amsModalSlVal() { return document.getElementById("ams-modal-sl-val"); },

    get amsModalRiskVal() { return document.getElementById("ams-modal-risk-val"); },

    get amsModalAllocationText() { return document.getElementById("ams-modal-allocation-text"); },

    get amsModalChartBtn() { return document.getElementById("ams-modal-chart-btn"); },

    get amsModalAddPositionBtn() { return document.getElementById("ams-modal-add-position-btn"); },

    get amsModalPullbackBadge() { return document.getElementById("ams-modal-pullback-badge"); },

    get amsModalPullbackDesc() { return document.getElementById("ams-modal-pullback-desc"); },

    get amsModalAvgVolBadge() { return document.getElementById("ams-modal-avgvol-badge"); },

    get amsModalAvgVolDesc() { return document.getElementById("ams-modal-avgvol-desc"); },

    get amsModalSmaDistBadge() { return document.getElementById("ams-modal-smadist-badge"); },

    get amsModalSmaDistDesc() { return document.getElementById("ams-modal-smadist-desc"); },

    get amsModalRvolBadge() { return document.getElementById("ams-modal-rvol-badge"); },

    get amsModalRvolDesc() { return document.getElementById("ams-modal-rvol-desc"); },

    get amsModalAlgoDesc() { return document.getElementById("ams-modal-algo-desc"); }

};

// Initialize the app

document.addEventListener("DOMContentLoaded", async () => {

    setupTabNavigation();

    setupDashboardSubtabNavigation();

    setupSectorFilters();

    setupEventHandlers();

    setupJournalEventHandlers();

    setupChatEventHandlers();

    await loadScanDates();

    await loadDashboardData();

    await initScanNotificationCheck();

});

// Dynamic background scan status checks & client updates

function updateScanStatusUI(data) {

    const badge = document.getElementById("scan-status-badge");

    if (!badge) return;

    

    if (data.status === "success") {

        badge.className = "scan-status-badge success";

        badge.innerHTML = `<i class="fa-solid fa-circle-check"></i> Ingestion: Success (${data.timestamp})`;

        badge.title = data.message;

    } else if (data.status === "error") {

        badge.className = "scan-status-badge error";

        badge.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> Ingestion: Failed (${data.timestamp})`;

        badge.title = data.message;

    } else {

        badge.className = "scan-status-badge";

        badge.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> No Scan Data`;

    }

}

async function initScanNotificationCheck() {

    try {

        const response = await fetch("/api/scan_status");

        if (response.ok) {

            const data = await response.json();

            if (data && data.timestamp) {

                updateScanStatusUI(data);

                

                const lastNotified = localStorage.getItem("last_notified_scan_time");

                if (!lastNotified) {

                    // Very first visit: initialize silently

                    localStorage.setItem("last_notified_scan_time", data.timestamp);

                } else if (data.timestamp !== lastNotified) {

                    // First load after a new scan session completed: show toast immediately

                    localStorage.setItem("last_notified_scan_time", data.timestamp);

                    if (data.status === "success") {

                        showToast("🚀 Ingestion & EOD Scan completed successfully! Watchlist and dashboard updated.", "success");

                    } else if (data.status === "error") {

                        showToast("⚠️ Ingestion & EOD Scan failed: " + data.message, "error");

                    }

                }

            }

        }

    } catch (e) {

        console.error("Error initializing scan status check:", e);

    }

    

    // Poll every 10 seconds for completion signals from EOD tasks

    setInterval(async () => {

        try {

            const response = await fetch("/api/scan_status");

            if (response.ok) {

                const data = await response.json();

                if (data && data.timestamp) {

                    updateScanStatusUI(data);

                    

                    const lastNotified = localStorage.getItem("last_notified_scan_time");

                    if (lastNotified && data.timestamp !== lastNotified) {

                        localStorage.setItem("last_notified_scan_time", data.timestamp);

                        

                        if (data.status === "success") {

                            showToast("🚀 Ingestion & EOD Scan completed successfully! Watchlist and dashboard updated.", "success");

                            // Reload date pickers and data

                            await loadScanDates();

                            await loadDashboardData();

                        } else if (data.status === "error") {

                            showToast("⚠️ Ingestion & EOD Scan failed: " + data.message, "error");

                        }

                    }

                }

            }

        } catch (e) {

            console.error("Error polling scan status:", e);

        }

    }, 10000);

}

// Tab Navigation logic

function setupTabNavigation() {

    elements.navButtons.forEach(btn => {

        btn.addEventListener("click", () => {

            const tabId = btn.getAttribute("data-tab");

            

            // Toggle active classes on nav

            elements.navButtons.forEach(b => b.classList.remove("active"));

            btn.classList.add("active");

            

            // Toggle active classes on content

            elements.tabContents.forEach(content => {

                content.classList.remove("active");

                if (content.id === `tab-${tabId}`) {

                    content.classList.add("active");

                }

            });

            

            // Set header title

            switch(tabId) {

                case "dashboard":

                    elements.tabTitle.textContent = "Dashboard Overview";

                    break;

                case "dashboard2":

                    elements.tabTitle.textContent = "Executive Dashboard";

                    renderDashboard2();

                    break;

                case "stocks_filter":

                    elements.tabTitle.textContent = "Strategic Stock Scanner & Filter";

                    renderFilteredWatchlist();

                    break;

                case "portfolio":

                    elements.tabTitle.textContent = "Active Portfolio Holdings";

                    break;

                case "sector_rotation":

                    elements.tabTitle.textContent = "Sector Rotation & Breadth Flow";

                    break;

                case "daily_report":

                    elements.tabTitle.textContent = "Daily Action Report";

                    renderDailyReport();

                    break;

                case "trade_journal":

                    elements.tabTitle.textContent = "Trade Journal";

                    if (typeof renderJournalCharts === "function") {

                        renderJournalCharts();

                    }

                    break;

                case "trade_management":

                    elements.tabTitle.textContent = "Post-Entry Trade Management";

                    renderPortfolioManagement();

                    break;

                case "true_paper_portfolio":

                    elements.tabTitle.textContent = "Evidence-Based Paper Trading (₹1L)";

                    loadTruePaperPortfolio();

                    break;

                case "risk":

                    elements.tabTitle.textContent = "CRO Risk Manager";

                    if (typeof renderRiskManagerTab === "function") {

                        renderRiskManagerTab();

                    }

                    break;

                case "earnings":

                    elements.tabTitle.textContent = "Corporate Earnings Calendar";

                    loadAndRenderEarningsCalendar();

                    break;

                case "chat":

                    elements.tabTitle.textContent = "AI Trading Assistant";

                    break;

            }

        });

    });

}

function setupDashboardSubtabNavigation() {

    const subtabBtns = document.querySelectorAll(".dashboard-subtab-btn");

    const subtabContents = document.querySelectorAll(".dashboard-subtab-content");

    if (subtabBtns.length === 0) return;

    

    // Load last active subtab from local storage

    const lastSubtab = localStorage.getItem("activeDashboardSubtab") || "portfolio";

    subtabBtns.forEach(btn => {

        const subtabId = btn.getAttribute("data-subtab");

        if (subtabId === lastSubtab) {

            btn.classList.add("active");

        } else {

            btn.classList.remove("active");

        }

    });

    subtabContents.forEach(content => {

        const contentId = content.id.replace("subtab-", "");

        if (contentId === lastSubtab) {

            content.classList.add("active");

        } else {

            content.classList.remove("active");

        }

    });

    subtabBtns.forEach(btn => {

        btn.addEventListener("click", () => {

            const subtabId = btn.getAttribute("data-subtab");

            

            // Toggle active classes on buttons

            subtabBtns.forEach(b => b.classList.remove("active"));

            btn.classList.add("active");

            

            // Toggle active classes on content panels

            subtabContents.forEach(content => {

                content.classList.remove("active");

                if (content.id === `subtab-${subtabId}`) {

                    content.classList.add("active");

                }

            });

            

            // Persist tab state

            localStorage.setItem("activeDashboardSubtab", subtabId);

        });

    });

    // Add click listener to posture card to scroll to market health

    const postureCard = document.getElementById("kpi-posture-card");

    if (postureCard) {

        postureCard.addEventListener("click", () => {

            const healthPanel = document.querySelector(".market-health-panel");

            if (healthPanel) {

                healthPanel.scrollIntoView({ behavior: 'smooth' });

            }

        });

    }

    // Close drawer on click of the close button

    const closeBtn = document.getElementById("drawer-close-btn");

    if (closeBtn) {

        closeBtn.addEventListener("click", () => {

            const drawer = document.getElementById("ticker-detail-drawer");

            if (drawer) drawer.classList.remove("active");

        });

    }

    

    // Close drawer on clicking outside the drawer

    document.addEventListener("click", (e) => {

        const drawer = document.getElementById("ticker-detail-drawer");

        if (drawer && drawer.classList.contains("active")) {

            const isClickInside = drawer.contains(e.target);

            const isClickOnSymbol = e.target.classList.contains("stock-symbol") || e.target.closest(".stock-symbol");

            if (!isClickInside && !isClickOnSymbol) {

                drawer.classList.remove("active");

            }

        }

    });

}

function getVcpShrinkageHtml(contractionsStr) {

    if (!contractionsStr || contractionsStr === "None" || contractionsStr === "") {

        return "";

    }

    

    // Split sequence: e.g. "12, 6, 2" or "10-5-2"

    const parts = contractionsStr.replace(/-/g, ",").split(",").map(p => parseFloat(p.trim())).filter(p => !isNaN(p));

    if (parts.length === 0) return "";

    

    // Draw circles scaling down in diameter

    let html = `<div class="vcp-shrinkage-gauge" title="Contraction sequence: ${contractionsStr}">`;

    const maxPart = Math.max(...parts);

    parts.forEach((depth, idx) => {

        const ratio = maxPart > 0 ? (depth / maxPart) : 1.0;

        const size = Math.max(5, Math.min(11, ratio * 11));

        const opacity = 0.3 + ((idx + 1) / parts.length) * 0.7; 

        html += `<span class="vcp-circle" style="width: ${size}px; height: ${size}px; background: var(--accent-purple); opacity: ${opacity}; box-shadow: 0 0 ${size/2}px rgba(139, 92, 246, ${opacity});"></span>`;

    });

    html += `</div>`;

    return html;

}

function setupSectorFilters() {

    const filterContainer = document.getElementById("sector-rotation-filters");

    if (!filterContainer) return;

    const btns = filterContainer.querySelectorAll(".sector-filter-btn");

    btns.forEach(btn => {

        btn.addEventListener("click", () => {

            btns.forEach(b => b.classList.remove("active"));

            btn.classList.add("active");

            appState.selectedSectorCategory = btn.getAttribute("data-category");

            renderSectorRotation();

        });

    });

}

// Global Event Handlers

function setupEventHandlers() {

    // Refresh button

    elements.refreshBtn.addEventListener("click", () => loadDashboardData());

    

    // Date Picker Change Handler

    if (elements.dashboardDatePicker) {

        elements.dashboardDatePicker.addEventListener("change", () => {

            loadDashboardData(elements.dashboardDatePicker.value);

        });

    }

    

    // Watchlist Table Search and Filter inputs

    if (elements.watchlistSearch) {

        elements.watchlistSearch.addEventListener("input", () => {

            filterWatchlistTable();

            renderFilteredWatchlist();

        });

    }



    

    elements.filterButtons.forEach(btn => {

        btn.addEventListener("click", () => {

            elements.filterButtons.forEach(b => b.classList.remove("active"));

            btn.classList.add("active");

            filterWatchlistTable();

        });

    });

    

    // Seed Capital Edit Click

    if (elements.editSeedCapitalBtn) {

        elements.editSeedCapitalBtn.addEventListener("click", () => {

            const val = prompt("Enter new Seed Capital (₹):", appState.seedCapital);

            if (val !== null && !isNaN(val) && parseFloat(val) > 0) {

                appState.seedCapital = parseFloat(val);

                localStorage.setItem("seedCapital", appState.seedCapital);

                updateFinanceDashboard();

            }

        });

    }

    

    // Strong constituent leaders checkbox filter

    const strongFilterChk = document.getElementById("industry-modal-filter-strong");

    if (strongFilterChk) {

        strongFilterChk.addEventListener("change", () => {

            appState.showStrongLeadersOnly = strongFilterChk.checked;

            if (window.currentDeepDiveIdx !== undefined) {

                window.openIndustryDeepDive(window.currentDeepDiveIdx);

            } else if (window.currentDeepDiveIndObj !== undefined) {

                window.openIndustryDeepDive(window.currentDeepDiveIndObj.Industry);

            }

        });

    }

    

    // AMS Modal close event handlers

    const amsModal = document.getElementById("ams-modal");

    const closeAmsBtn = document.getElementById("close-ams-modal-btn");

    if (closeAmsBtn && amsModal) {

        closeAmsBtn.addEventListener("click", () => {

            amsModal.style.display = "none";

        });

        window.addEventListener("click", (e) => {

            if (e.target === amsModal) {

                amsModal.style.display = "none";

            }

        });

    }

    // Keyboard shortcut Alt + Shift + R to refresh data

    const handleRefreshShortcut = (e) => {

        if (e.altKey && e.shiftKey && e.key.toLowerCase() === "r") {

            e.preventDefault();

            showToast("Refreshing dashboard data...", "info");

            loadDashboardData();

        }

    };

    window.addEventListener("keydown", handleRefreshShortcut);

    document.addEventListener("keydown", handleRefreshShortcut);

    

    // Watchlist Table Header Sort click handler

    document.querySelectorAll(".watchlist-table th.sortable").forEach(th => {

        th.addEventListener("click", () => {

            const column = th.getAttribute("data-sort");

            if (appState.sortColumn === column) {

                // Toggle direction

                appState.sortDirection = appState.sortDirection === "asc" ? "desc" : "asc";

            } else {

                appState.sortColumn = column;

                // Default descending for numeric/score columns, ascending for text columns

                if (["Score", "MS_Score", "Risk_Pct", "Delivery_Pct", "CMP", "Trigger", "Stop_Loss", "Target_1", "Target_2"].includes(column)) {

                    appState.sortDirection = "desc";

                } else {

                    appState.sortDirection = "asc";

                }

            }

            updateHeaderSortIcons();

            filterWatchlistTable();

        });

    });

    // Grade Checkbox Automatic Pattern Toggling
    const syncPatternCheckboxes = () => {
        const gradeA = document.getElementById("filter-grade-a")?.checked ?? false;
        const gradeB = document.getElementById("filter-grade-b")?.checked ?? false;
        const gradeC = document.getElementById("filter-grade-c")?.checked ?? false;

        const vcp = document.getElementById("filter-vcp");
        const flag = document.getElementById("filter-flag");
        const pb10 = document.getElementById("filter-pb10");
        const pb20 = document.getElementById("filter-pb20");
        const pb50 = document.getElementById("filter-pb50");
        const ib = document.getElementById("filter-ib");
        const pp = document.getElementById("filter-pp");

        if (vcp) vcp.checked = gradeA || gradeB;
        if (flag) flag.checked = gradeB;
        if (pb10) pb10.checked = gradeB;
        if (pb20) pb20.checked = gradeC;
        if (pb50) pb50.checked = gradeC;
        if (ib) ib.checked = gradeB || gradeC;
        if (pp) pp.checked = gradeA;
    };

    const gradeAEl = document.getElementById("filter-grade-a");
    const gradeBEl = document.getElementById("filter-grade-b");
    const gradeCEl = document.getElementById("filter-grade-c");

    if (gradeAEl && gradeBEl && gradeCEl) {
        [gradeAEl, gradeBEl, gradeCEl].forEach(el => {
            el.addEventListener("change", () => {
                syncPatternCheckboxes();
                if (window.renderFilteredWatchlist) {
                    window.renderFilteredWatchlist();
                }
            });
        });
    }

}

// Load available scan dates from backend

async function loadScanDates() {

    try {

        const response = await fetch("/api/scan_dates");

        const dates = await response.json();

        

        if (elements.dashboardDatePicker) {

            elements.dashboardDatePicker.innerHTML = "";

            

            if (dates.length === 0) {

                const option = document.createElement("option");

                option.value = "";

                option.textContent = "Latest Scan";

                elements.dashboardDatePicker.appendChild(option);

                return;

            }

            

            dates.forEach(date => {

                const option = document.createElement("option");

                option.value = date;

                

                // Format date to a readable form (e.g. "June 18, 2026")

                const dt = new Date(date);

                const formattedDate = dt.toLocaleDateString("en-US", { year: 'numeric', month: 'long', day: 'numeric' });

                option.textContent = formattedDate;

                

                elements.dashboardDatePicker.appendChild(option);

            });

            if (dates.length > 0) {

                elements.dashboardDatePicker.value = dates[0];

            }

        }

    } catch (error) {

        console.error("Error loading scan dates:", error);

    }

}

// Load watchlist & feedback data from standard Python API server

async function loadDashboardData(dateStr = "") {

    showLoading();

    try {

        // Fetch Watchlist API

        let url = "/api/watchlist";

        if (typeof dateStr === "string" && dateStr !== "") {

            url += `?date=${dateStr}`;

        } else if (elements.dashboardDatePicker && elements.dashboardDatePicker.value) {

            url += `?date=${elements.dashboardDatePicker.value}`;

        }

        const wlResponse = await fetch(url);

        const wlData = await wlResponse.json();

        

        appState.date = wlData.date;

        appState.marketPosture = wlData.market_health ? wlData.market_health.posture : "RED";

        appState.marketScore = wlData.market_health ? wlData.market_health.score : 0;

        appState.marketPostureDetails = wlData.market_health ? wlData.market_health.breakdown : null;

        appState.niftyClose = wlData.nifty_close || 0;

        appState.niftyChange = wlData.nifty_change_pct || 0;

        appState.sensexClose = wlData.sensex_close || 0;

        appState.sensexChange = wlData.sensex_change_pct || 0;

        

        appState.marketHealth = wlData.market_health || null;

        appState.focusIndustries = wlData.focus_industries || [];

        appState.strategicWatchlist = wlData.strategic_watchlist || [];

        appState.dailyFocusWatchlist = wlData.daily_focus_watchlist || [];

        appState.allScannedCandidates = wlData.all_scanned_candidates || [];

        

        // Project candidates for backward compatibility

        appState.vcpCandidates = appState.strategicWatchlist.filter(s => (s.Setup_Type || "").includes("VCP")).map(s => ({

            Symbol: s.Symbol,

            Company_Name: s.Company_Name,

            Industry: s.Industry,

            MS_Score: s.MS_Score,

            Risk_Pct: s.Risk_Pct,

            CMP: s.CMP || 0.0,

            Trigger: s.Entry || 0.0,

            Stop_Loss: s.Stop_Loss || 0.0,

            Grade: s.Setup_Grade || "Grade C",

            Engine_Type: s.Setup_Type || "STRICT_VCP",

            Readiness: "READY",

            Target_1: s.Target_1 || 0.0,

            Target_2: s.Target_2 || 0.0,

            Score: s.MS_Score,

            MS_Breakdown: { Trend: s.Trend_Quality, RS: s.Relative_Strength, SmartMoney: s.Smart_Money_Score },

            Distance: s.Distance || "0%",

            Delivery_Pct: s.Delivery_Pct || 0.0,

            Contractions: s.Contractions || "",

            VDU_Pct: s.VDU_Pct || "0.0%",

            Execution_Readiness_Score: s.Execution_Readiness_Score || 0,

            Pocket_Pivot: s.Pocket_Pivot || 0,

            Position_Size_Recommendation: s.Position_Size_Recommendation || "",

            Industry_Category: s.Industry_Category || "",

            Overall_Rank: s.Overall_Rank || "N/A"

        }));

        

        appState.flag_candidates = appState.strategicWatchlist.filter(s => (s.Setup_Type || "").includes("FLAG")).map(s => ({

            Symbol: s.Symbol,

            Company_Name: s.Company_Name,

            Industry: s.Industry,

            MS_Score: s.MS_Score,

            Risk_Pct: s.Risk_Pct,

            CMP: s.CMP || 0.0,

            Trigger: s.Entry || 0.0,

            Stop_Loss: s.Stop_Loss || 0.0,

            Grade: s.Setup_Grade || "Grade C",

            Engine_Type: s.Setup_Type || "FLAG_SETUP",

            Readiness: "FLAG READY",

            Target_1: s.Target_1 || 0.0,

            Target_2: s.Target_2 || 0.0,

            Score: s.MS_Score,

            MS_Breakdown: { Trend: s.Trend_Quality, RS: s.Relative_Strength, SmartMoney: s.Smart_Money_Score },

            Distance: s.Distance || "0%",

            Delivery_Pct: s.Delivery_Pct || 0.0,

            Contractions: s.Contractions || "",

            VDU_Pct: s.VDU_Pct || "0.0%",

            Execution_Readiness_Score: s.Execution_Readiness_Score || 0,

            Pocket_Pivot: s.Pocket_Pivot || 0,

            Position_Size_Recommendation: s.Position_Size_Recommendation || "",

            Industry_Category: s.Industry_Category || "",

            Overall_Rank: s.Overall_Rank || "N/A"

        }));

        

        // Fetch Portfolio API

        try {

            const portResponse = await fetch("/api/portfolio");

            appState.activePortfolio = await portResponse.json();

        } catch (portErr) {

            console.error("Failed to load portfolio:", portErr);

            appState.activePortfolio = [];

        }

        // Fetch Trade Management Engine API

        try {

            const pmResponse = await fetch("/api/portfolio_management");

            appState.portfolioManagement = await pmResponse.json();

        } catch (pmErr) {

            console.error("Failed to load portfolio management report:", pmErr);

            appState.portfolioManagement = null;

        }

        

        // Fetch Closed Trades API

        try {

            const ctResponse = await fetch("/api/closed_trades");

            appState.closedTrades = await ctResponse.json();

        } catch (ctErr) {

            console.error("Failed to load closed trades:", ctErr);

            appState.closedTrades = [];

        }

        // Fetch Sector Rotation API

        let rotUrl = "/api/sector_rotation";

        let mbUrl = "/api/market_breadth";

        const activeDate = (typeof dateStr === "string" && dateStr !== "") ? dateStr : (elements.dashboardDatePicker ? elements.dashboardDatePicker.value : "");

        if (activeDate) {

            rotUrl += `?date=${activeDate}`;

            mbUrl += `?date=${activeDate}`;

        }

        

        try {

            const rotResponse = await fetch(rotUrl);

            appState.sectorRotation = await rotResponse.json();

        } catch (rotErr) {

            console.error("Failed to load sector rotation:", rotErr);

            appState.sectorRotation = [];

        }

        

        // Fetch Market Breadth API

        try {

            const mbResponse = await fetch(mbUrl);

            appState.marketBreadth = await mbResponse.json();

        } catch (mbErr) {

            console.error("Failed to load market breadth:", mbErr);

            appState.marketBreadth = null;

        }

        // Fetch RRG Data API

        try {

            const rrgResponse = await fetch("/api/rrg_data");

            appState.rrgData = await rrgResponse.json();

        } catch (rrgErr) {

            console.error("Failed to load RRG data:", rrgErr);

            appState.rrgData = [];

        }

        // Fetch Market Breadth History API

        try {

            const mbhResponse = await fetch("/api/market_breadth_history");

            appState.marketBreadthHistory = await mbhResponse.json();

        } catch (mbhErr) {

            console.error("Failed to load market breadth history:", mbhErr);

            appState.marketBreadthHistory = [];

        }

        

        // Fetch Portfolio Management Report
        try {
            const pmResponse = await fetch("/api/portfolio_management");
            appState.portfolioManagement = await pmResponse.json();
        } catch (pmErr) {
            console.error("Failed to load portfolio management report:", pmErr);
            appState.portfolioManagement = null;
        }

        // Fetch True Paper Portfolio data on startup/refresh
        try {
            const pfRes = await fetch("/api/true_paper_portfolio");
            if (pfRes.ok) {
                const pfData = await pfRes.json();
                appState.truePaperOpenTrades = pfData.open_trades || [];
            }
        } catch (pfErr) {
            console.error("Failed to load true paper portfolio in loadDashboardData:", pfErr);
        }

        await loadTradeJournalData();

        // Update UI

        updateSidebarMarketStatus();

        updateHeaderInfo();

        updateStatsMetrics();

        renderMarketHealthPanel(appState.marketHealth);

        renderFocusIndustriesGrid(appState.focusIndustries);

        renderFilteredWatchlist();

        renderPortfolio();

        updateFinanceDashboard();

        renderDashboard2();

        renderSectorRotation();

        renderDailyReport();

        renderPortfolioManagement();

        if (typeof loadTruePaperPortfolio === "function") {
            loadTruePaperPortfolio();
        }

        renderRRGChart(appState.rrgData);

        renderMarketBreadthHistory(appState.marketBreadthHistory);

        

    } catch (error) {

        console.error("Error loading dashboard data:", error);

    }

}

// Show/Hide loader states

function showLoading() {

    if (elements.lowRiskTradesList) {

        elements.lowRiskTradesList.innerHTML = `

            <div class="loading-state">

                <i class="fa-solid fa-spinner fa-spin"></i> Loading low-risk candidates...

            </div>

        `;

    }

    if (elements.highRiskTradesList) {

        elements.highRiskTradesList.innerHTML = `

            <div class="loading-state">

                <i class="fa-solid fa-spinner fa-spin"></i> Loading high-risk candidates...

            </div>

        `;

    }

    if (elements.watchlistTableBody) {

        elements.watchlistTableBody.innerHTML = `

            <tr>

                <td colspan="15" class="loading-state" style="text-align: center;">

                    <i class="fa-solid fa-spinner fa-spin"></i> Processing daily scan...

                </td>

            </tr>

        `;

    }

    if (elements.rotationCategoriesContainer) {

        elements.rotationCategoriesContainer.innerHTML = `

            <div class="loading-state" style="text-align: center; padding: 40px; color: var(--text-secondary);">

                <i class="fa-solid fa-spinner fa-spin fa-2x" style="margin-bottom: 10px; display: block; color: var(--accent-purple);"></i>

                Analyzing multi-week sector rotation data...

            </div>

        `;

    }

}

// Sidebar Market Status Indicator

function updateSidebarMarketStatus() {

    // 1. Sidebar Badge and Bar

    elements.marketPostureBadge.textContent = appState.marketPosture;

    elements.marketPostureBadge.className = `posture-badge ${appState.marketPosture.toLowerCase()}`;

    elements.marketHealthBar.style.width = `${appState.marketScore * 10}%`;

    elements.marketHealthScore.textContent = `Score: ${appState.marketScore}/10`;

    

    // 2. Recommendation Banner & Tooltip Details

    const details = appState.marketPostureDetails;

    if (details) {

        // Banner updates

        if (elements.dashboardPostureBanner && elements.dashboardRecommendationText) {

            elements.dashboardPostureBanner.className = `posture-banner ${appState.marketPosture.toLowerCase()} glass`;

            elements.dashboardRecommendationText.textContent = details.recommendation;

        }

        

        // Tooltip updates

        if (elements.postureBreakdownList && elements.postureTooltipRecommendation) {

            elements.postureTooltipRecommendation.textContent = details.recommendation;

            

            const bd = details.breakdown;

            elements.postureBreakdownList.innerHTML = `

                <li class="${bd.above_200_sma.status ? 'pass' : 'fail'}">

                    Index > 200 SMA: <strong>${bd.above_200_sma.status ? 'Pass' : 'Fail'}</strong>

                    <span class="breakdown-details">(Index: ${bd.above_200_sma.value.toFixed(2)} vs SMA: ${bd.above_200_sma.sma.toFixed(2)})</span>

                </li>

                <li class="${bd.above_50_sma.status ? 'pass' : 'fail'}">

                    Index > 50 SMA: <strong>${bd.above_50_sma.status ? 'Pass' : 'Fail'}</strong>

                    <span class="breakdown-details">(Index: ${bd.above_50_sma.value.toFixed(2)} vs SMA: ${bd.above_50_sma.sma.toFixed(2)})</span>

                </li>

                <li class="${bd.sma_50_above_200.status ? 'pass' : 'fail'}">

                    50 SMA > 200 SMA: <strong>${bd.sma_50_above_200.status ? 'Pass' : 'Fail'}</strong>

                    <span class="breakdown-details">(50 SMA: ${bd.sma_50_above_200.sma_50.toFixed(2)} vs 200 SMA: ${bd.sma_50_above_200.sma_200.toFixed(2)})</span>

                </li>

                <li class="${bd.distribution_days.status ? 'pass' : 'fail'}">

                    Distribution Days: <strong>${bd.distribution_days.count}</strong> (Max 4)

                    <span class="breakdown-details">(Rolling 20 sessions down on higher vol)</span>

                </li>

                <li class="${bd.breakout_success.status ? 'pass' : 'fail'}">

                    Breakout Win Rate: <strong>${(bd.breakout_success.rate * 100).toFixed(1)}%</strong> (Min 70%)

                    <span class="breakdown-details">(Win rate of logged feedback journal trades)</span>

                </li>

            `;

        }

    }

}

// Header Date label and Index Ticker

function updateHeaderInfo() {

    elements.dateDisplay.textContent = `EOD Trading Session: ${appState.date}`;

    

    // Update Nifty

    elements.niftyValue.textContent = appState.niftyClose.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    const niftySign = appState.niftyChange >= 0 ? "+" : "";

    elements.niftyChange.textContent = `${niftySign}${appState.niftyChange.toFixed(2)}%`;

    elements.niftyChange.className = `index-change ${appState.niftyChange >= 0 ? "positive" : "negative"}`;

    

    // Update Sensex

    elements.sensexValue.textContent = appState.sensexClose.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    const sensexSign = appState.sensexChange >= 0 ? "+" : "";

    elements.sensexChange.textContent = `${sensexSign}${appState.sensexChange.toFixed(2)}%`;

    elements.sensexChange.className = `index-change ${appState.sensexChange >= 0 ? "positive" : "negative"}`;

    

    // Update Calendar Date (Today's Date)

    const options = { year: 'numeric', month: 'long', day: 'numeric' };

    elements.calendarDate.textContent = new Date().toLocaleDateString("en-US", options);

}

// Stats metrics calculators

// Stats metrics calculators

function updateStatsMetrics() {

    const total = appState.vcpCandidates.length + appState.flag_candidates.length;

    if (elements.statTotalCandidates) elements.statTotalCandidates.textContent = total;

    if (elements.statVcpCount) elements.statVcpCount.textContent = appState.vcpCandidates.length;

    if (elements.statFlagCount) elements.statFlagCount.textContent = appState.flag_candidates.length;

    

    // 1. KPI Portfolio Value & Daily P&L

    const openJournalTrades = appState.tradeJournal ? appState.tradeJournal.filter(t => t.status === "OPEN") : [];

    let deployed = 0.0;

    openJournalTrades.forEach(t => {

        deployed += t.entry_price * (t.open_qty || 0);

    });

    let realized = 0.0;

    if (appState.tradeJournal) {

        appState.tradeJournal.forEach(t => {

            if (t.exits) {

                t.exits.forEach(e => {

                    realized += e.pnl || 0;

                });

            }

        });

    }

    let unrealized = 0.0;

    if (appState.activePortfolio) {

        appState.activePortfolio.forEach(p => {

            unrealized += p.PnL_Net || 0.0;

        });

    }

    const totalValue = appState.seedCapital + realized + unrealized;

    const netPnl = realized + unrealized;

    const netPnlPct = appState.seedCapital > 0 ? (netPnl / appState.seedCapital) * 100 : 0.0;

    const sign = netPnl >= 0 ? "+" : "";

    const color = netPnl >= 0 ? "var(--accent-green)" : "var(--accent-red)";

    

    const kpiValEl = document.getElementById("kpi-portfolio-value");

    const kpiPnlEl = document.getElementById("kpi-portfolio-pnl");

    if (kpiValEl) kpiValEl.textContent = `₹${totalValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

    if (kpiPnlEl) kpiPnlEl.innerHTML = `Net P&L: <span style="color: ${color}; font-weight: bold;">${sign}₹${netPnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })} (${sign}${netPnlPct.toFixed(1)}%)</span>`;

    // 2. KPI Market Posture

    const posture = appState.marketHealth ? appState.marketHealth.posture : "RED";

    const score = appState.marketHealth ? appState.marketHealth.score : 0;

    const mhpStatusColor = posture === "GREEN" ? "var(--accent-green)" : "var(--accent-red)";

    const kpiPostureEl = document.getElementById("kpi-market-posture");

    const kpiHealthEl = document.getElementById("kpi-market-health");

    if (kpiPostureEl) {

        kpiPostureEl.textContent = posture;

        kpiPostureEl.style.color = mhpStatusColor;

    }

    if (kpiHealthEl) kpiHealthEl.textContent = `Score: ${score}/10`;

    const postureIcon = document.getElementById("kpi-posture-icon");

    if (postureIcon) {

        postureIcon.className = `kpi-icon ${posture === "GREEN" ? "green" : "orange"}`;

    }

    // 3. KPI Active Setup Counts

    const vcpCount = appState.vcpCandidates ? appState.vcpCandidates.length : 0;

    const flagCount = appState.flag_candidates ? appState.flag_candidates.length : 0;

    const pullbackCount = appState.strategicWatchlist ? appState.strategicWatchlist.filter(s => s.Setup_Type === "PULLBACK").length : 0;

    const ibCount = appState.strategicWatchlist ? appState.strategicWatchlist.filter(s => s.Setup_Type === "INSIDE_BAR_FLAG").length : 0;

    const setupsCountEl = document.getElementById("kpi-setups-count");

    const setupsBreakdownEl = document.getElementById("kpi-setups-breakdown");

    if (setupsCountEl) setupsCountEl.textContent = vcpCount + flagCount + pullbackCount;

    if (setupsBreakdownEl) setupsBreakdownEl.textContent = `VCP: ${vcpCount} | Pullback: ${pullbackCount} | Flag: ${flagCount} | IB: ${ibCount}`;

    // 4. KPI Top Sector Theme

    const topInd = appState.focusIndustries && appState.focusIndustries.length > 0 ? appState.focusIndustries[0] : null;

    const topSectorEl = document.getElementById("kpi-top-sector");

    const topSectorScoreEl = document.getElementById("kpi-top-sector-score");

    if (topSectorEl && topSectorScoreEl) {

        if (topInd) {

            topSectorEl.textContent = topInd.Industry;

            topSectorScoreEl.textContent = `${topInd.Zone} (Part: ${topInd.Part_EMA20_Today ? topInd.Part_EMA20_Today.toFixed(0) : 0}% > 20EMA)`;

        } else {

            topSectorEl.textContent = "N/A";

            topSectorScoreEl.textContent = "No focus themes today";

        }

    }

}

function renderMarketHealthPanel(mh) {

    if (!mh) return;

    if (elements.mhpStatus) {

        elements.mhpStatus.innerText = mh.status;

        elements.mhpStatus.className = ""; // clear previous classes

        if (mh.status === "Favorable" || mh.status === "Strong") {
            elements.mhpStatus.style.color = "var(--accent-green)";
        } else if (mh.status === "Avoid" || mh.status === "Weak") {
            elements.mhpStatus.style.color = "var(--accent-red)";
        } else {
            elements.mhpStatus.style.color = "var(--accent-orange)";
        }
    }

    if (elements.mhpAgg) {
        elements.mhpAgg.innerText = mh.aggressiveness;
        if (mh.aggressiveness === "Favorable" || mh.aggressiveness === "Aggressive") {
            elements.mhpAgg.style.color = "var(--accent-green)";
        } else if (mh.aggressiveness === "Avoid" || mh.aggressiveness === "Defensive") {
            elements.mhpAgg.style.color = "var(--accent-red)";
        } else {
            elements.mhpAgg.style.color = "var(--accent-orange)";
        }

    }

    if (elements.mhpSizing) {

        elements.mhpSizing.innerText = mh.position_sizing;

    }

}

function getActionablePlaybook(ind) {

    const zone = ind.Zone || "Neutral";

    const change = ind.Change || "constant";

    const flowScore = ind.Net_Flow_Pct !== undefined ? ind.Net_Flow_Pct : 0.0;

    const ppPct = ind.Pocket_Pivot_Pct !== undefined ? ind.Pocket_Pivot_Pct : 0.0;

    

    if (zone === "Confirmed Uptrend") {
        return {
            title: "CONFIRMED UPTREND",
            desc: "Strongest stage with institutional backing. Focus on breakout buy setups in high-RS constituent leaders. Low-risk pullback buys near key EMAs are highly favored.",
            action: "BUY BREAKOUTS / PULLBACKS",
            color: "var(--accent-green)",
            bg: "rgba(16, 185, 129, 0.08)",
            border: "rgba(16, 185, 129, 0.25)"
        };
    } else if (zone === "Early Uptrend") {
        return {
            title: "EARLY UPTREND",
            desc: "Sector starting to wake up with early money flow. Early momentum is picking up as constituents cross above short-term EMAs. Good for building pilot positions.",
            action: "WATCH FOR EARLY SETUPS",
            color: "var(--accent-blue)",
            bg: "rgba(59, 130, 246, 0.08)",
            border: "rgba(59, 130, 246, 0.25)"
        };
    } else if (zone === "Consolidation") {
        return {
            title: "CONSOLIDATION",
            desc: "Sector resting sideways and holding its structure. Constituent stocks are consolidating. Look for volatility contraction patterns (VCP) breakout pivots.",
            action: "OBSERVE / HOLD",
            color: "var(--accent-teal)",
            bg: "rgba(20, 184, 166, 0.08)",
            border: "rgba(20, 184, 166, 0.25)"
        };
    } else if (zone === "Downtrend Warning") {
        return {
            title: "DOWNTREND WARNING",
            desc: "Fading breadth and negative money flow detected in group behavior. One of the genuinely negative stages. Tighten stop losses. Do not open new long positions.",
            action: "TIGHTEN STOPS / EXITS",
            color: "var(--accent-red)",
            bg: "rgba(239, 68, 68, 0.08)",
            border: "rgba(239, 68, 68, 0.25)"
        };
    } else { // Avoid
        return {
            title: "AVOID",
            desc: "Low-momentum sector building a base or underperforming. No clear statistical edge. Ignore or monitor from a distance.",
            action: "NO EDGE",
            color: "var(--text-secondary)",
            bg: "rgba(255, 255, 255, 0.02)",
            border: "var(--border-color)"
        };
    }

}

function renderFocusIndustriesGrid(industries) {

    if (!elements.focusIndustriesListGrid) return;

    if (!industries || industries.length === 0) {

        elements.focusIndustriesListGrid.innerHTML = `

            <div class="empty-state" style="grid-column: span 2; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 120px; border: 1px dashed var(--border-color); border-radius: 8px; width: 100%;">

                <i class="fa-solid fa-triangle-exclamation" style="font-size: 20px; color: var(--accent-orange); margin-bottom: 8px;"></i>

                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary); text-transform: uppercase;">no valid setup found</span>

                <span style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">No focus industries qualified under momentum criteria today.</span>

            </div>

        `;

        return;

    }

    

    elements.focusIndustriesListGrid.innerHTML = industries.map((ind, idx) => {

        const isNew = ind.Is_New ? '<span style="font-size: 8.5px; padding: 1px 4px; font-weight: bold; background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 4px; margin-left: 6px;">🆕 NEW</span>' : '';

        const pConfirmedBadge = ind.P_Confirmed ? '<span style="font-size: 9px; font-weight: bold; background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); padding: 1px 5px; border-radius: 4px; display: inline-flex; align-items: center; gap: 3px; margin-left: 6px;"><i class="fa-solid fa-circle-check"></i> ✓P confirmed</span>' : '';

        

        let zoneColor = "var(--text-secondary)";
        let zoneBg = "rgba(255, 255, 255, 0.04)";
        let zoneBorder = "rgba(255, 255, 255, 0.08)";
        
        if (ind.Zone === "Confirmed Uptrend") {
            zoneColor = "var(--accent-green)";
            zoneBg = "rgba(16, 185, 129, 0.1)";
            zoneBorder = "rgba(16, 185, 129, 0.2)";
        } else if (ind.Zone === "Early Uptrend") {
            zoneColor = "var(--accent-blue)";
            zoneBg = "rgba(59, 130, 246, 0.1)";
            zoneBorder = "rgba(59, 130, 246, 0.2)";
        } else if (ind.Zone === "Consolidation") {
            zoneColor = "var(--accent-teal)";
            zoneBg = "rgba(20, 184, 166, 0.1)";
            zoneBorder = "rgba(20, 184, 166, 0.2)";
        } else if (ind.Zone === "Downtrend Warning") {
            zoneColor = "var(--accent-red)";
            zoneBg = "rgba(239, 68, 68, 0.1)";
            zoneBorder = "rgba(239, 68, 68, 0.2)";
        }
        
        const zoneBadge = `<span style="font-size: 9.5px; font-weight: bold; color: ${zoneColor}; background: ${zoneBg}; border: 1px solid ${zoneBorder}; padding: 2px 6px; border-radius: 4px;">${ind.Zone} · streak ${ind.Streak_Days}</span>`;

        

        let changeArrow = "→";

        let changeColor = "var(--text-secondary)";

        if (ind.Change === "improving") {

            changeArrow = "▲";

            changeColor = "var(--accent-green)";

        } else if (ind.Change === "cooling") {

            changeArrow = "▼";

            changeColor = "var(--accent-red)";

        }

        const playbook = getActionablePlaybook(ind);

        let specialBadges = "";
        if (ind.Reversal_Watch) {
            specialBadges += `<span style="font-size: 8.5px; padding: 1px 4px; font-weight: bold; background: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; display: inline-flex; align-items: center; gap: 2px;"><i class="fa-solid fa-rotate-left"></i> REV</span>`;
        }
        if (ind.Tailwind_Watch) {
            specialBadges += `<span style="font-size: 8.5px; padding: 1px 4px; font-weight: bold; background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 4px; display: inline-flex; align-items: center; gap: 2px;"><i class="fa-solid fa-wind"></i> TAILWIND</span>`;
        }
        if (ind.Quality_In_Avoid) {
            specialBadges += `<span style="font-size: 8.5px; padding: 1px 4px; font-weight: bold; background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 4px; display: inline-flex; align-items: center; gap: 2px;"><i class="fa-solid fa-gem"></i> QUALITY</span>`;
        }
        if (ind.Building_Interest) {
            specialBadges += `<span style="font-size: 8.5px; padding: 1px 4px; font-weight: bold; background: rgba(139, 92, 246, 0.15); color: var(--accent-purple); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 4px; display: inline-flex; align-items: center; gap: 2px;"><i class="fa-solid fa-compass"></i> INTEREST</span>`;
        }
        if (ind.DW_Visits && ind.DW_Visits > 1) {
            specialBadges += `<span style="font-size: 8.5px; padding: 1px 4px; font-weight: bold; background: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; display: inline-flex; align-items: center; gap: 2px;"><i class="fa-solid fa-triangle-exclamation"></i> DW VISITS: ${ind.DW_Visits}</span>`;
        }
        if (ind.Failure_Days && ind.Failure_Days > 0) {
            specialBadges += `<span style="font-size: 8.5px; padding: 1px 4px; font-weight: bold; background: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; display: inline-flex; align-items: center; gap: 2px;" title="Grace Period Warning (Failure Day ${ind.Failure_Days})"><i class="fa-solid fa-clock"></i> GRACE WARNING (W)</span>`;
        }

        return `

            <div onclick="openIndustryDeepDive(${idx})" style="background: #0f111a; padding: 14px; border-radius: 8px; border: 1px solid var(--border-color); border-left: 4px solid ${zoneColor}; display: flex; flex-direction: column; justify-content: space-between; gap: 10px; cursor: pointer; transition: all 0.2s ease;" onmouseover="this.style.borderColor='rgba(139, 92, 246, 0.5)'; this.style.transform='translateY(-2px)';" onmouseout="this.style.borderColor='var(--border-color)'; this.style.transform='none';">

                <div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">

                    <div style="display: flex; flex-direction: column; gap: 2px; overflow: hidden;">

                        <span style="font-size: 10px; font-weight: bold; color: var(--text-secondary); text-transform: uppercase;">Focus Sector #${idx + 1}</span>

                        <strong style="font-size: 13px; color: var(--text-primary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${ind.Industry}">${ind.Industry}</strong>

                    </div>

                    <span style="font-size: 9.5px; font-weight: bold; color: ${changeColor};" title="Momentum Change: ${ind.Change}">${changeArrow} Rank ${ind.Overall_Rank_Str || (idx + 1)}</span>

                </div>

                

                <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 6px;">

                    ${zoneBadge}

                    ${pConfirmedBadge}

                    ${isNew}

                    ${specialBadges}

                </div>

                ${ind.Is_New && ind.New_Reason ? `<div style="font-size: 9.5px; color: var(--accent-green); font-style: italic; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">Reason: ${ind.New_Reason}</div>` : ''}

                

                <!-- Compact Card Playbook Summary -->

                <div style="background: ${playbook.bg}; border: 1px dashed ${playbook.border}; border-radius: 6px; padding: 6px 10px; font-size: 10px; color: ${playbook.color}; display: flex; flex-direction: column; gap: 2px;">

                    <span style="font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; font-size: 9px;">💡 Playbook: ${playbook.title}</span>

                    <span style="color: var(--text-secondary); line-height: 1.3;">Action: <strong>${playbook.action}</strong></span>

                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed var(--border-color); padding-top: 8px; font-size: 11px;">

                    <span style="color: var(--text-secondary); font-weight: 500;">Combined Score:</span>

                    <span style="color: var(--text-primary); font-weight: 700; font-family: monospace;">${(ind.Score !== undefined && ind.Score !== null) ? Number(ind.Score).toFixed(1) : ((ind.Combined_Score !== undefined) ? Number(ind.Combined_Score).toFixed(1) : '0.0')}</span>

                </div>

            </div>

        `;

    }).join("");

}

// Global modal triggers for industry deep dive

window.openIndustryDeepDive = function(idxOrName) {

    let ind;

    if (typeof idxOrName === "number") {

        window.currentDeepDiveIdx = idxOrName;

        ind = appState.focusIndustries[idxOrName];

    } else {

        ind = appState.sectorRotation.find(item => item.Industry === idxOrName);

        const focusIdx = appState.focusIndustries ? appState.focusIndustries.findIndex(item => item.Industry === idxOrName) : -1;

        window.currentDeepDiveIdx = focusIdx !== -1 ? focusIdx : undefined;

        window.currentDeepDiveIndObj = ind;

    }

    if (!ind) return;

    // Ensure Zone and Streak_Days are correctly set/inferred from Category if not already present
    const category = ind.Category || "Avoid";
    if (!ind.Zone) {
        ind.Zone = category;
    }
    if (ind.Streak_Days === undefined || ind.Streak_Days === null) {
        ind.Streak_Days = 0;
    }

    document.getElementById("industry-modal-title").innerHTML = `${ind.Industry}`;

    document.getElementById("industry-modal-sector").textContent = ind.Sector || "Parent Sector";

    

    const zoneEl = document.getElementById("industry-modal-zone");

    let zoneColor = "var(--text-secondary)";
    let zoneBg = "rgba(255, 255, 255, 0.05)";
    let zoneBorder = "var(--border-color)";

    if (ind.Zone === "Confirmed Uptrend") {
        zoneColor = "var(--accent-green)";
        zoneBg = "rgba(16, 185, 129, 0.1)";
        zoneBorder = "rgba(16, 185, 129, 0.2)";
    } else if (ind.Zone === "Early Uptrend") {
        zoneColor = "var(--accent-blue)";
        zoneBg = "rgba(59, 130, 246, 0.1)";
        zoneBorder = "rgba(59, 130, 246, 0.2)";
    } else if (ind.Zone === "Consolidation") {
        zoneColor = "var(--accent-teal)";
        zoneBg = "rgba(20, 184, 166, 0.1)";
        zoneBorder = "rgba(20, 184, 166, 0.2)";
    } else if (ind.Zone === "Downtrend Warning") {
        zoneColor = "var(--accent-red)";
        zoneBg = "rgba(239, 68, 68, 0.1)";
        zoneBorder = "rgba(239, 68, 68, 0.2)";
    }

    zoneEl.textContent = `${ind.Zone} · Day ${ind.Streak_Days}`;

    zoneEl.style.color = zoneColor;

    zoneEl.style.background = zoneBg;

    zoneEl.style.border = `1px solid ${zoneBorder}`;

    

    const confirmedEl = document.getElementById("industry-modal-confirmed");

    if (ind.P_Confirmed) {

        confirmedEl.style.display = "inline-flex";

    } else {

        confirmedEl.style.display = "none";

    }

    

    const scoreVal = (ind.Score !== undefined && ind.Score !== null) ? Number(ind.Score).toFixed(1) : 

                     ((ind.Combined_Score !== undefined) ? Number(ind.Combined_Score).toFixed(1) : '--');

    document.getElementById("industry-modal-score").textContent = scoreVal;

    

    const breadthVal = (ind.Breadth !== undefined) ? Number(ind.Breadth).toFixed(1) : 

                       ((ind.Part_Stacked_Today !== undefined) ? Number(ind.Part_Stacked_Today).toFixed(1) : '--');

    document.getElementById("industry-modal-breadth").textContent = breadthVal + "%";

    

    const flowScore = (ind.Net_Flow_Score_Scaled !== undefined) ? (Number(ind.Net_Flow_Score_Scaled) / 10.0).toFixed(1) : '--';

    const flowTrend = (ind.Net_Flow_Pct !== undefined) ? (ind.Net_Flow_Pct >= 0 ? "↑ Expanding" : "↓ Contracting") : "";

    const flowWarning = (ind.Failure_Days && ind.Failure_Days > 0) ? ` <span class="report-badge avoid" style="font-size: 9px; font-weight: bold; background: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); padding: 1px 4px; border-radius: 3px; margin-left: 4px; display: inline-flex; align-items: center;" title="Grace Period Warning (Failure Day ${ind.Failure_Days})">W</span>` : "";

    document.getElementById("industry-modal-flow").innerHTML = `${flowScore} <span style="font-size: 9px; font-weight: normal; color: var(--text-secondary);">${flowTrend}</span>${flowWarning}`;

    

    const ppVal = (ind.Pocket_Pivot_Pct !== undefined) ? Number(ind.Pocket_Pivot_Pct).toFixed(1) : '--';

    document.getElementById("industry-modal-pp").textContent = ppVal + "%";

    

    // Set Actionable Playbook inside modal

    const playbook = getActionablePlaybook(ind);

    const playbookContainer = document.getElementById("industry-modal-playbook-container");

    const playbookAction = document.getElementById("industry-modal-playbook-action");

    const playbookTitle = document.getElementById("industry-modal-playbook-title");

    const playbookDesc = document.getElementById("industry-modal-playbook-desc");

    

    if (playbookContainer && playbookAction && playbookTitle && playbookDesc) {

        playbookContainer.style.background = playbook.bg;

        playbookContainer.style.borderColor = playbook.border;

        

        playbookAction.textContent = playbook.action;

        playbookAction.style.color = playbook.color;

        playbookAction.style.background = playbook.bg;

        playbookAction.style.borderColor = playbook.border;

        playbookAction.style.border = `1px solid ${playbook.border}`;

        

        playbookTitle.textContent = playbook.title;

        playbookTitle.style.color = playbook.color;

        

        playbookDesc.textContent = playbook.desc;

    }

    

    // Ensure listener is bound to the filter checkbox (failsafe in case DOMContentLoaded listener setup crashed)

    const strongFilterChkFailsafe = document.getElementById("industry-modal-filter-strong");

    if (strongFilterChkFailsafe) {

        strongFilterChkFailsafe.checked = appState.showStrongLeadersOnly;

        if (!strongFilterChkFailsafe.dataset.listenerBound) {

            strongFilterChkFailsafe.dataset.listenerBound = "true";

            strongFilterChkFailsafe.addEventListener("change", () => {

                appState.showStrongLeadersOnly = strongFilterChkFailsafe.checked;

                if (window.currentDeepDiveIdx !== undefined) {

                    window.openIndustryDeepDive(window.currentDeepDiveIdx);

                } else if (window.currentDeepDiveIndObj !== undefined) {

                    window.openIndustryDeepDive(window.currentDeepDiveIndObj.Industry);

                }

            });

        }

    }

    

    const stockDetails = ind.Stock_Details || [];

    

    const filterStrong = appState.showStrongLeadersOnly;

    let renderedStocks = stockDetails;

    if (filterStrong) {

        renderedStocks = stockDetails.filter(s => {

            const hasGoodTrend = s.Stacked === 1 || (s.Above_EMA20 && s.Above_SMA50 && s.Above_SMA200);

            const isHighRS = s.High_RS === 1 || s.High_RS === true;

            const isNearHigh = s.Dist_52WH <= 15.0;

            const isPocketPivot = s.Pocket_Pivot === 1 || s.Pocket_Pivot === true;

            

            // Strict intersection: Trend AND High RS AND Near High (unless a pocket pivot is triggering today)

            return (hasGoodTrend && isHighRS && isNearHigh) || isPocketPivot;

        });

    }

    

    document.getElementById("industry-modal-stock-count").textContent = renderedStocks.length;

    

    const tbody = document.getElementById("industry-modal-stocks-body");

    tbody.innerHTML = "";

    

    if (renderedStocks.length === 0) {

        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 20px; color: var(--text-secondary); background: transparent;">No constituent stocks meeting minervini filters in this industry today.</td></tr>`;

    } else {

        renderedStocks.sort((a, b) => b.Rank_Score - a.Rank_Score);

        

        renderedStocks.forEach(s => {

            const tr = document.createElement("tr");

            tr.style.borderBottom = "1px solid var(--border-color)";

            tr.style.height = "38px";

            

            const tdSym = document.createElement("td");

            tdSym.style.padding = "8px 12px";

            tdSym.innerHTML = `<span onclick="closeIndustryModalAndOpenStock('${s.Symbol}')" style="font-weight: bold; color: var(--accent-purple); cursor: pointer; text-decoration: underline; font-family: monospace;">${s.Symbol}</span>`;

            

            const tdName = document.createElement("td");

            tdName.style.padding = "8px 12px";

            tdName.textContent = s.Company_Name || s.Symbol;

            

            const tdScore = document.createElement("td");

            tdScore.style.padding = "8px 12px";

            tdScore.style.textAlign = "right";

            tdScore.style.fontWeight = "bold";

            tdScore.style.fontFamily = "monospace";

            const scoreVal = s.Rank_Score !== undefined ? Number(s.Rank_Score).toFixed(1) : '--';

            const scoreColor = s.Rank_Score >= 70 ? "var(--accent-orange)" : (s.Rank_Score < 40 ? "var(--text-secondary)" : "var(--text-primary)");

            tdScore.innerHTML = `<span style="color: ${scoreColor};">${scoreVal}</span>`;

            

            const tdPrice = document.createElement("td");

            tdPrice.style.padding = "8px 12px";

            tdPrice.style.textAlign = "right";

            tdPrice.style.fontWeight = "bold";

            tdPrice.style.fontFamily = "monospace";

            tdPrice.textContent = "₹" + Number(s.Price || 0.0).toFixed(1);

            

            const tdRet = document.createElement("td");

            tdRet.style.padding = "8px 12px";

            tdRet.style.textAlign = "right";

            tdRet.style.fontFamily = "monospace";

            const ret = Number(s.Ret_Today || s.Return_1D || 0.0);

            const retSign = ret > 0 ? "+" : "";

            const retColor = ret > 0 ? "var(--accent-green)" : (ret < 0 ? "var(--accent-red)" : "var(--text-muted)");

            tdRet.innerHTML = `<span style="color: ${retColor}; font-weight: bold;">${retSign}${ret.toFixed(1)}%</span>`;

            

            const tdRsd = document.createElement("td");

            tdRsd.style.padding = "8px 12px";

            tdRsd.style.textAlign = "right";

            tdRsd.style.fontFamily = "monospace";

            tdRsd.style.fontWeight = "bold";

            const rsD = s.RS_D !== undefined ? s.RS_D : 50;

            const rsDColor = rsD >= 70 ? "var(--accent-green)" : (rsD < 40 ? "var(--accent-red)" : "var(--text-primary)");

            tdRsd.innerHTML = `<span style="color: ${rsDColor};">${rsD}</span>`;

            

            const tdRsw = document.createElement("td");

            tdRsw.style.padding = "8px 12px";

            tdRsw.style.textAlign = "right";

            tdRsw.style.fontFamily = "monospace";

            tdRsw.style.fontWeight = "bold";

            const rsW = s.RS_W !== undefined ? s.RS_W : 50;

            const rsWColor = rsW >= 70 ? "var(--accent-green)" : (rsW < 40 ? "var(--accent-red)" : "var(--text-primary)");

            tdRsw.innerHTML = `<span style="color: ${rsWColor};">${rsW}</span>`;

            const tdFlags = document.createElement("td");

            tdFlags.style.padding = "8px 12px";

            tdFlags.style.textAlign = "center";

            tdFlags.style.fontFamily = "monospace";

            tdFlags.style.fontWeight = "bold";

            

            const flagsList = [];

            if (s.Above_SMA50 === 1) flagsList.push("50");

            if (s.Above_SMA200 === 1) flagsList.push("200");

            if (s.SMA200_Rising === 1) flagsList.push("200↑");

            

            let flagsStr = flagsList.length > 0 ? flagsList.join(" · ") : "–";

            let flagsColor = "var(--text-secondary)";

            if (s.SMA200_Rising === 1) {

                flagsColor = "var(--accent-green)";

            } else if (s.Above_SMA50 === 1 && s.Above_SMA200 === 1) {

                flagsColor = "var(--accent-purple)";

            }

            

            // If it is a pocket pivot, add a small indicator label next to it

            if (s.Pocket_Pivot) {

                flagsStr += ` <span style="font-size: 8px; font-weight: bold; color: #ffffff; background: #e11d48; padding: 1.5px 3.5px; border-radius: 3px; margin-left: 4px;">PP</span>`;

            }

            

            tdFlags.innerHTML = `<span style="color: ${flagsColor};">${flagsStr}</span>`;

            

            const td52wh = document.createElement("td");

            td52wh.style.padding = "8px 12px";

            td52wh.style.textAlign = "right";

            td52wh.style.fontWeight = "bold";

            td52wh.style.fontFamily = "monospace";

            td52wh.textContent = "-" + Number(s.Dist_52WH || 0.0).toFixed(1) + "%";

            

            tr.appendChild(tdSym);

            tr.appendChild(tdName);

            tr.appendChild(tdScore);

            tr.appendChild(tdPrice);

            tr.appendChild(tdRet);

            tr.appendChild(tdRsd);

            tr.appendChild(tdRsw);

            tr.appendChild(tdFlags);

            tr.appendChild(td52wh);

            tbody.appendChild(tr);

        });

    }

    

    document.getElementById("industry-deep-dive-modal").style.display = "flex";

}

window.closeIndustryModalAndOpenStock = function(symbol) {

    document.getElementById("industry-deep-dive-modal").style.display = "none";

    if (typeof window.showAMSDetail === "function") {

        window.showAMSDetail(symbol);

    }

}

function renderStrategicWatchlistTable(watchlist) {

    if (!elements.strategicWatchlistBody) return;

    if (!watchlist || watchlist.length === 0) {

        elements.strategicWatchlistBody.innerHTML = `

            <tr>

                <td colspan="16" class="empty-state" style="text-align: center; padding: 40px; color: var(--text-secondary);">

                    <i class="fa-solid fa-gem" style="font-size: 24px; margin-bottom: 10px; display: block; color: var(--accent-blue);"></i>

                    <span style="font-weight: 700; color: var(--text-primary); text-transform: uppercase;">no valid setup found</span>

                </td>

            </tr>

        `;

        return;

    }

    

    elements.strategicWatchlistBody.innerHTML = watchlist.map(s => {

        return `

            <tr>

                <td style="font-weight: 700; color: var(--text-secondary); text-align: center;">${s.Industry_Rank}</td>

                <td style="font-weight: 700; color: var(--accent-purple); text-align: center;">#${s.Overall_Rank}</td>

                <td>

                    <span class="stock-symbol" onclick="showAMSDetail('${s.Symbol}')" style="cursor: pointer; font-weight: bold; color: var(--text-primary); background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border-color); font-family: monospace;">${s.Symbol}</span>

                </td>

                <td style="font-size: 11px; max-width: 140px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${s.Company_Name}">${s.Company_Name}</td>

                <td style="font-size: 11px;">${s.Industry}</td>

                <td style="font-weight: 700; color: var(--accent-blue); text-align: center;">${s.MS_Score}</td>

                <td style="text-align: center;">${s.Trend_Quality}/25</td>

                <td style="text-align: center;">${s.Relative_Strength}/10</td>

                <td style="text-align: center;">${s.Smart_Money_Score}/15</td>

                <td style="color: var(--accent-red); font-weight: bold; text-align: center;">${(s.Risk_Pct !== undefined && s.Risk_Pct !== null) ? Number(s.Risk_Pct).toFixed(1) : '0.0'}%</td>

                <td style="font-size: 11px; font-family: monospace; display: flex; align-items: center; gap: 6px; border-bottom: none;">

                    <span>${s.Setup_Type.replace("_VCP", "").replace("_SETUP", "").replace("_FLAG", "")}</span>

                    ${getVcpShrinkageHtml(s.Contractions)}

                </td>

                <td style="font-size: 11px; text-align: center;">${s.Setup_Grade}</td>

                <td style="padding: 10px 12px; text-align: center;">

                    ${(() => {

                        let earningsHtml = `<span style="color: var(--text-muted);">-</span>`;

                        if (s.Earnings_Date && s.Earnings_Date !== "N/A") {

                            const days = s.Days_To_Earnings;

                            let daysStyle = "color: var(--text-primary);";

                            let warningText = "";

                            if (days !== undefined && days !== null) {

                                if (days < 0) {

                                    daysStyle = "color: var(--text-muted);";

                                } else if (days <= 3) {

                                    daysStyle = "color: var(--accent-red); font-weight: 800; background: rgba(239, 68, 68, 0.1); padding: 1px 4px; border-radius: 3px;";

                                    warningText = " ⚠️";

                                } else if (days <= 7) {

                                    daysStyle = "color: var(--accent-orange); font-weight: 700;";

                                    warningText = " ⚠️";

                                }

                            }

                            earningsHtml = `

                                <div style="font-size: 10.5px; line-height: 1.2; text-align: center;">

                                    <div style="font-weight: 600; font-family: monospace;">${s.Earnings_Date}</div>

                                    <div style="font-size: 9.5px; ${daysStyle}">${days !== undefined && days !== null ? (days < 0 ? `Past` : `${days}d left`) : ""}${warningText}</div>

                                </div>

                            `;

                        }

                        return earningsHtml;

                    })()}

                </td>

                <td style="font-family: monospace; text-align: right; color: var(--text-primary); font-weight: 600;">₹${(s.CMP !== undefined && s.CMP !== null) ? Number(s.CMP).toFixed(2) : '0.00'}</td>

                <td style="font-family: monospace; font-weight: 700; text-align: right;">₹${(s.Entry !== undefined && s.Entry !== null) ? Number(s.Entry).toFixed(2) : '0.00'}</td>

                <td style="font-family: monospace; text-align: right; color: var(--text-secondary);">₹${(s.Stop_Loss !== undefined && s.Stop_Loss !== null) ? Number(s.Stop_Loss).toFixed(2) : '0.00'}</td>

                <td style="font-size: 11px; font-style: italic; color: var(--text-secondary); max-width: 220px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${s.Reason}">${s.Reason}</td>

                <td style="text-align: center;">

                    <button class="table-add-journal-btn" onclick="addCandidateToJournal('${s.Symbol}')" title="Add to Journal">

                        <i class="fa-solid fa-plus"></i> Add

                    </button>

                </td>

            </tr>

        `;

    }).join("");

}

function renderDailyFocusWatchlistTable(watchlist) {

    if (!elements.dailyFocusWatchlistBody) return;

    if (!watchlist || watchlist.length === 0) {

        elements.dailyFocusWatchlistBody.innerHTML = `

            <tr>

                <td colspan="16" class="empty-state" style="text-align: center; padding: 40px; color: var(--text-secondary);">

                    <i class="fa-solid fa-bullseye" style="font-size: 24px; margin-bottom: 10px; display: block; color: var(--accent-green);"></i>

                    <span style="font-weight: 700; color: var(--text-primary); text-transform: uppercase;">no valid setup found</span>

                </td>

            </tr>

        `;

        return;

    }

    

    elements.dailyFocusWatchlistBody.innerHTML = watchlist.map(s => {

        const vduClass = s.Volume_Dry_Up_Status === "VDU Confirmed" ? "trend-up" : "trend-down";

        const readinessColor = s.Execution_Readiness_Score >= 80 ? "var(--accent-green)" : (s.Execution_Readiness_Score >= 60 ? "var(--accent-purple)" : "var(--text-secondary)");

        return `

            <tr>

                <td>

                    <span class="stock-symbol" onclick="showAMSDetail('${s.Symbol}')" style="cursor: pointer; font-weight: bold; color: var(--text-primary); background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border-color); font-family: monospace;">${s.Symbol}</span>

                </td>

                <td style="font-size: 11px; max-width: 140px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${s.Company_Name}">${s.Company_Name}</td>

                <td style="font-size: 11px;">${s.Industry}</td>

                <td style="font-weight: 700; color: var(--accent-blue); text-align: center;">${s.MS_Score}</td>

                <td style="text-align: center;">${s.Industry_Rank}</td>

                <td style="font-weight: 800; color: ${readinessColor}; text-align: center;">${s.Execution_Readiness_Score}</td>

                <td style="font-size: 11px; font-family: monospace; display: flex; align-items: center; gap: 6px; border-bottom: none;">

                    <span>${s.Pattern.replace("_VCP", "").replace("_SETUP", "").replace("_FLAG", "")}</span>

                    ${getVcpShrinkageHtml(s.Contractions)}

                </td>

                <td style="font-size: 11px; text-align: center;">${s.Grade}</td>

                <td style="padding: 10px 12px; text-align: center;">

                    ${(() => {

                        let earningsHtml = `<span style="color: var(--text-muted);">-</span>`;

                        if (s.Earnings_Date && s.Earnings_Date !== "N/A") {

                            const days = s.Days_To_Earnings;

                            let daysStyle = "color: var(--text-primary);";

                            let warningText = "";

                            if (days !== undefined && days !== null) {

                                if (days < 0) {

                                    daysStyle = "color: var(--text-muted);";

                                } else if (days <= 3) {

                                    daysStyle = "color: var(--accent-red); font-weight: 800; background: rgba(239, 68, 68, 0.1); padding: 1px 4px; border-radius: 3px;";

                                    warningText = " ⚠️";

                                } else if (days <= 7) {

                                    daysStyle = "color: var(--accent-orange); font-weight: 700;";

                                    warningText = " ⚠️";

                                }

                            }

                            earningsHtml = `

                                <div style="font-size: 10.5px; line-height: 1.2; text-align: center;">

                                    <div style="font-weight: 600; font-family: monospace;">${s.Earnings_Date}</div>

                                    <div style="font-size: 9.5px; ${daysStyle}">${days !== undefined && days !== null ? (days < 0 ? `Past` : `${days}d left`) : ""}${warningText}</div>

                                </div>

                            `;

                        }

                        return earningsHtml;

                    })()}

                </td>

                <td style="font-family: monospace; font-weight: 700; text-align: center;">${s.Distance_to_Pivot}</td>

                <td class="${vduClass}" style="font-size: 11px; font-weight: bold; text-align: center;">${s.Volume_Dry_Up_Status}</td>

                <td style="font-family: monospace; text-align: right; color: var(--text-primary); font-weight: 600;">₹${(s.CMP !== undefined && s.CMP !== null) ? Number(s.CMP).toFixed(2) : '0.00'}</td>

                <td style="font-family: monospace; font-weight: 700; text-align: right;">₹${(s.Entry_Price !== undefined && s.Entry_Price !== null) ? Number(s.Entry_Price).toFixed(2) : '0.00'}</td>

                <td style="font-family: monospace; text-align: right; color: var(--text-secondary);">₹${(s.Stop_Loss !== undefined && s.Stop_Loss !== null) ? Number(s.Stop_Loss).toFixed(2) : '0.00'}</td>

                <td style="font-weight: 700; text-align: center; color: var(--accent-green);">${s.Reward_to_Risk}x</td>

                <td style="font-size: 11px; font-weight: 600; color: var(--text-primary);">${s.Position_Size_Recommendation}</td>

                <td style="font-size: 11px; font-style: italic; color: var(--text-secondary); max-width: 220px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${s.Reason}">${s.Reason}</td>

                <td style="text-align: center;">

                    <button class="table-add-journal-btn" onclick="addCandidateToJournal('${s.Symbol}')" title="Add to Journal">

                        <i class="fa-solid fa-plus"></i> Add

                    </button>

                </td>

            </tr>

        `;

    }).join("");

}

function renderTopTrades() {}

// Helper to construct a single trade card element

function createTradeCard(trade, isHighRisk) {

    const isFlag = trade.Engine_Type === "FLAG_SETUP";

    let cardClass = isFlag ? "trade-card flag-card glass" : "trade-card glass";

    if (isHighRisk) {

        cardClass += " high-risk-card";

    }

    

    const deliveryDisplay = trade.Delivery_Pct > 0 ? `${trade.Delivery_Pct}%` : "No Data";

    const target1Display = trade.Target_1 > 0 ? `Rs. ${trade.Target_1.toFixed(2)}` : "No Target";

    const target2Display = trade.Target_2 > 0 ? `Rs. ${trade.Target_2.toFixed(2)}` : "No Target";

    const durationDisplay = isFlag ? "2 - 4 Weeks (Flag Setup)" : "4 - 12 Weeks (VCP Base)";

    const tooltipHtml = generateScoreTooltipHtml(trade);

    

    const card = document.createElement("div");

    card.className = cardClass;

    card.innerHTML = `

        <div class="trade-card-header">

            <div class="ticker-title">

                <h3>${trade.Symbol}</h3>

                <span class="setup-type-label">${trade.Engine_Type.replace("_VCP", "").replace("_SETUP", "").replace("_FLAG", "")}</span>

                <div style="margin-top: 6px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">

                    <span class="industry-badge ${(trade.Industry_Category || 'Neutral').toLowerCase()}" style="font-size: 10px; padding: 2px 6px;">${trade.Industry || 'Others'}</span>

                    <span style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">${(trade.Industry_Category || 'Neutral').toUpperCase()} | ${trade.Industry_Trend || 'N/A'}</span>

                </div>

            </div>

            <div class="trade-score score-tooltip-wrapper">

                <i class="fa-solid fa-star"></i> Score: ${trade.Score}

                ${tooltipHtml}

            </div>

        </div>

        <div class="trade-metrics-table">

            <div class="metric-item">

                <span>CMP:</span>

                <strong>Rs. ${trade.CMP.toFixed(2)}</strong>

            </div>

            <div class="metric-item">

                <span>Trigger Price:</span>

                <strong>Rs. ${trade.Trigger.toFixed(2)}</strong>

            </div>

            <div class="metric-item">

                <span>Target 1 (T1):</span>

                <strong style="color: var(--accent-green);">${target1Display}</strong>

            </div>

            <div class="metric-item">

                <span>Target 2 (T2):</span>

                <strong style="color: var(--accent-green);">${target2Display}</strong>

            </div>

            <div class="metric-item">

                <span>Stop Loss (SL):</span>

                <strong>Rs. ${trade.Stop_Loss.toFixed(2)}</strong>

            </div>

            <div class="metric-item">

                <span>Risk per Share:</span>

                <strong class="risk-value ${trade.Risk_Pct > 6.0 ? 'risk-high' : (trade.Risk_Pct >= 3.0 ? 'risk-ideal' : '')}">${trade.Risk_Pct}%</strong>

            </div>

            <div class="metric-item" style="grid-column: span 2;">

                <span>NSE Delivery %age (Accumulation):</span>

                <strong class="delivery-value">${deliveryDisplay}</strong>

            </div>

            <div class="metric-item" style="grid-column: span 2;">

                <span>Approx Trade Duration:</span>

                <strong style="color: var(--accent-blue);">${durationDisplay}</strong>

            </div>

        </div>

        <div class="trade-actions" style="margin-top: 16px; display: flex;">

            <button class="card-add-journal-btn" onclick="addCandidateToJournal('${trade.Symbol}')" style="flex-grow: 1;">

                <i class="fa-solid fa-plus"></i> Add to Journal

            </button>

        </div>

    `;

    return card;

}

function renderWatchlistTable() {}

function getMSColor(score, isBg) {

    if (score >= 90) return isBg ? 'rgba(16, 185, 129, 0.15)' : '#10b881'; // 🟢

    if (score >= 80) return isBg ? 'rgba(52, 211, 153, 0.15)' : '#34d399'; // 🟩

    if (score >= 70) return isBg ? 'rgba(245, 158, 11, 0.15)' : '#f59e0b'; // 🟨

    if (score >= 60) return isBg ? 'rgba(249, 115, 22, 0.15)' : '#f97316'; // 🟧

    return isBg ? 'rgba(239, 68, 68, 0.15)' : '#ef4444'; // 🔴

}

// Smart Watchlist Query Builder & Natural Language Filter

function createCompareFilter(field, op, val) {

    return c => {

        let itemVal = 0;

        if (field === "delivery") itemVal = c.Delivery_Pct;

        else if (field === "risk") itemVal = c.Risk_Pct;

        else if (field === "score" || field === "ms") itemVal = c.MS_Score || c.Score;

        else if (field === "cmp") itemVal = c.CMP;

        else if (field === "trigger") itemVal = c.Trigger;

        else if (field === "stop") itemVal = c.Stop_Loss;

        

        if (op === "<") return itemVal < val;

        if (op === ">") return itemVal > val;

        if (op === "<=") return itemVal <= val;

        if (op === ">=") return itemVal >= val;

        if (op === "=") return itemVal === val;

        return true;

    };

}

function parseSmartQuery(queryString) {

    const query = queryString.toLowerCase().trim();

    if (!query) return null;

    

    const filters = [];

    

    // 1. Setup types

    if (query.includes("pullback")) {

        filters.push(c => c.Entry_Category === "EMA_PULLBACK");

    } else if (query.includes("vcp")) {

        filters.push(c => c.Engine_Type.includes("VCP") && c.Entry_Category !== "EMA_PULLBACK");

    } else if (query.includes("flag")) {

        filters.push(c => c.Engine_Type.includes("FLAG"));

    }

    

    // 2. Industry categories

    if (query.includes("running hot") || query.includes("running") || query.includes("hot")) {

        filters.push(c => (c.Industry_Category || "").toLowerCase() === "running hot");

    } else if (query.includes("sweet spot") || query.includes("sweet") || query.includes("spot")) {

        filters.push(c => (c.Industry_Category || "").toLowerCase() === "the sweet spot");

    } else if (query.includes("waking up") || query.includes("waking")) {

        filters.push(c => (c.Industry_Category || "").toLowerCase() === "sector waking up");

    } else if (query.includes("out of favor") || query.includes("out")) {

        filters.push(c => (c.Industry_Category || "").toLowerCase() === "out of favor");

    } else if (query.includes("neutral")) {

        filters.push(c => (c.Industry_Category || "").toLowerCase() === "neutral");

    } else if (query.includes("unscaled")) {

        filters.push(c => (c.Industry_Category || "").toLowerCase() === "unscaled");

    }

    

    // 3. Extraction comparisons (e.g. "risk < 5" or "delivery > 50")

    const regexA = /(delivery|risk|score|ms|cmp|trigger|stop)\s*(<=|>=|<|>|=)\s*([0-9.]+)/g;

    const regexB = /(<=|>=|<|>|=)\s*([0-9.]+)(?:%?)\s*(delivery|risk|score|ms|cmp|trigger|stop)/g;

    

    let match;

    while ((match = regexA.exec(query)) !== null) {

        filters.push(createCompareFilter(match[1], match[2], parseFloat(match[3])));

    }

    while ((match = regexB.exec(query)) !== null) {

        filters.push(createCompareFilter(match[3], match[1], parseFloat(match[2])));

    }

    

    // 4. Tiers

    if (query.includes("tier 1")) {

        filters.push(c => (c.Tier || "").toLowerCase() === "tier 1");

    } else if (query.includes("tier 2")) {

        filters.push(c => (c.Tier || "").toLowerCase() === "tier 2");

    } else if (query.includes("tier 3")) {

        filters.push(c => (c.Tier || "").toLowerCase() === "tier 3");

    } else if (query.includes("tier 4")) {

        filters.push(c => (c.Tier || "").toLowerCase() === "tier 4");

    }

    

    // 5. Grades

    if (query.includes("grade a")) {

        filters.push(c => c.Grade.toLowerCase() === "grade a");

    } else if (query.includes("grade b")) {

        filters.push(c => c.Grade.toLowerCase() === "grade b");

    } else if (query.includes("grade c")) {

        filters.push(c => c.Grade.toLowerCase() === "grade c");

    }

    

    // 5. Fallback search by symbol/industry name if no parameters are matched

    if (filters.length === 0) {

        return c => {

            const search = query.toUpperCase();

            return (c.Symbol || "").includes(search) || 

                   (c.Grade || "").toUpperCase().includes(search) || 

                   (c.Readiness || "").toUpperCase().includes(search) ||

                   (c.Industry || "").toUpperCase().includes(search);

        };

    }

    

    return c => filters.every(f => f(c));

}

// Search and filter logic on tables

function filterWatchlistTable() {

    const activeFilterBtn = document.querySelector(".filter-btn.active");
    if (!activeFilterBtn) return;
    const activeFilter = activeFilterBtn.getAttribute("data-filter");

    

    let candidates = [];

    if (activeFilter === "all") {

        candidates = [...appState.vcpCandidates, ...appState.flag_candidates];

    } else if (activeFilter === "vcp") {

        candidates = [...appState.vcpCandidates].filter(c => c.Entry_Category !== "EMA_PULLBACK");

    } else if (activeFilter === "flag") {

        candidates = [...appState.flag_candidates];

    } else if (activeFilter === "pullback") {

        candidates = [...appState.vcpCandidates].filter(c => c.Entry_Category === "EMA_PULLBACK");

    }

    

    // Apply search query filter or smart query builder

    const queryStr = elements.watchlistSearch.value;

    const filterFn = parseSmartQuery(queryStr);

    const filtered = filterFn ? candidates.filter(filterFn) : candidates;

    

    // Apply sorting (e.g. default high score first)

    const col = appState.sortColumn;

    const dir = appState.sortDirection;

    

    filtered.sort((a, b) => {

        let valA = a[col];

        let valB = b[col];

        

        if (col === "Engine_Type") {

            const getDisplaySetupType = (c) => {

                if (c.Entry_Category === "EMA_PULLBACK") return "PULLBACK";

                return (c.Engine_Type || "").replace("_VCP", "").replace("_SETUP", "").replace("_FLAG", "");

            };

            valA = getDisplaySetupType(a);

            valB = getDisplaySetupType(b);

        }

        

        // Handle undefined or null

        if (valA === undefined || valA === null) valA = 0;

        if (valB === undefined || valB === null) valB = 0;

        

        // String comparison

        if (typeof valA === "string") {

            valA = valA.toUpperCase();

            valB = valB.toString().toUpperCase();

            if (valA < valB) return dir === "asc" ? -1 : 1;

            if (valA > valB) return dir === "asc" ? 1 : -1;

            return 0;

        }

        

        // Numeric comparison

        return dir === "asc" ? valA - valB : valB - valA;

    });

    

    if (filtered.length === 0) {

        elements.watchlistTableBody.innerHTML = `

            <tr>

                <td colspan="15" class="empty-state" style="text-align: center;">

                    <i class="fa-solid fa-magnifying-glass"></i> No matching candidates found.

                </td>

            </tr>

        `;

        return;

    }

    

    elements.watchlistTableBody.innerHTML = "";

    filtered.forEach(c => {

        let typeDisplay = c.Engine_Type.replace("_VCP", "").replace("_SETUP", "").replace("_FLAG", "");

        if (c.Entry_Category === "EMA_PULLBACK") {

            typeDisplay = "PULLBACK";

        }

        const gradeClass = c.Grade.toLowerCase().replace(" ", "-");

        const readClass = c.Readiness.toLowerCase().includes("ready") ? "ready" : 

                          c.Readiness.toLowerCase().includes("post") ? "post" : "developing";

        

        const deliveryDisplay = c.Delivery_Pct > 0 ? `${c.Delivery_Pct}%` : "-";

        const t1Display = c.Target_1 > 0 ? `Rs. ${c.Target_1.toFixed(2)}` : "-";

        const t2Display = c.Target_2 > 0 ? `Rs. ${c.Target_2.toFixed(2)}` : "-";

        const tooltipHtml = generateScoreTooltipHtml(c);

        

        const industryName = c.Industry || "Others";

        const indCategory = (c.Industry_Category || "Neutral").toLowerCase();

        

        const tier = c.Tier || "Tier 4";

        let tierStyle = "";

        if (tier === "Tier 1") {

            tierStyle = "background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3);";

        } else if (tier === "Tier 2") {

            tierStyle = "background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); border: 1px solid rgba(59, 130, 246, 0.3);";

        } else if (tier === "Tier 3") {

            tierStyle = "background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3);";

        } else {

            tierStyle = "background: rgba(156, 163, 175, 0.15); color: var(--text-secondary); border: 1px solid rgba(156, 163, 175, 0.2);";

        }

        const tr = document.createElement("tr");

        tr.innerHTML = `

            <td><strong>${c.Symbol}</strong></td>

            <td>

                <span class="industry-badge ${indCategory}">${industryName}</span>

                <br>

                <small style="color: var(--text-secondary); font-size: 10px; margin-top: 4px; display: block; white-space: nowrap;">

                    ${indCategory.toUpperCase()} | ${c.Industry_Trend || 'N/A'}

                </small>

            </td>

            <td>

                <div class="score-tooltip-wrapper">

                    <strong>${c.Score}</strong>

                    ${tooltipHtml}

                </div>

            </td>

            <td>

                <div class="ms-wrapper" style="display: flex; flex-direction: column; align-items: center; gap: 2px; cursor: pointer;" onclick="showAMSDetail('${c.Symbol}')">

                    <span class="ms-badge" style="background: ${getMSColor(c.MS_Score, true)}; color: ${getMSColor(c.MS_Score, false)}; padding: 3px 8px; border-radius: 12px; font-weight: 700; font-size: 11px;">

                        ${c.MS_Score || 0}

                    </span>

                    <span style="font-size: 9px; color: var(--text-secondary); white-space: nowrap;">${c.MS_Rating || '★☆☆☆☆'}</span>

                </div>

            </td>

            <td>

                <span class="setup-type-label" style="${tierStyle} padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; display: inline-block;">

                    ${tier}

                </span>

            </td>

            <td><span class="setup-type-label" style="background: rgba(${typeDisplay === 'FLAG' ? '59,130,246' : (typeDisplay === 'PULLBACK' ? '16,185,129' : '139,92,246')}, 0.15); color: var(--accent-${typeDisplay === 'FLAG' ? 'blue' : (typeDisplay === 'PULLBACK' ? 'green' : 'purple')});">${typeDisplay}</span></td>

            <td><span class="table-grade ${gradeClass}">${c.Grade}</span></td>

            <td>Rs. ${c.CMP.toFixed(2)}</td>

            <td>Rs. ${c.Trigger.toFixed(2)}</td>

            <td><span style="color: var(--accent-green); font-weight: 500;">${t1Display}</span></td>

            <td><span style="color: var(--accent-green); font-weight: 500;">${t2Display}</span></td>

            <td>Rs. ${c.Stop_Loss.toFixed(2)}</td>

            <td><span class="table-risk ${c.Risk_Pct > 6.0 ? 'risk-high' : (c.Risk_Pct >= 3.0 ? 'risk-ideal' : '')}">${c.Risk_Pct}%</span></td>

            <td><span class="table-delivery">${deliveryDisplay}</span></td>

            <td><span style="color: var(--accent-blue); font-weight: 500;">${c.Duration}</span></td>

            <td>

                <button class="table-add-journal-btn" onclick="addCandidateToJournal('${c.Symbol}')" title="Add to Journal">

                    <i class="fa-solid fa-plus"></i> Add

                </button>

            </td>

        `;

        elements.watchlistTableBody.appendChild(tr);

    });

}

// Generate HTML for candidate score breakdown hover tooltip

function generateScoreTooltipHtml(c) {

    // 1. VCP Quality (Max 40)

    let vcp = 0;

    const grade = (c.Grade || "").toUpperCase();

    if (grade.includes("GRADE A") || grade === "A") vcp = 40;

    else if (grade.includes("GRADE B") || grade === "B") vcp = 30;

    else if (grade.includes("GRADE C") || grade === "C") vcp = 20;

    

    // 2. VDU Quality (Max 20)

    let vdu = 0;

    const vduPctVal = parseFloat(c.VDU_Pct || "0");

    const vduRatio = vduPctVal / 100;

    if (vduRatio <= 0.10) vdu = 20;

    else if (vduRatio <= 0.20) vdu = 15;

    else if (vduRatio <= 0.30) vdu = 10;

    else if (vduRatio <= 0.40) vdu = 5;

    

    // 3. Readiness (Max 20)

    let readiness = 0;

    const status = (c.Readiness || "").toUpperCase();

    if (status === "STRICT READY" || status === "FLAG READY") readiness = 20;

    else if (status === "FLEX READY" || status === "MINI READY") readiness = 15;

    else if (status === "DEVELOPING") readiness = 10;

    else if (status === "POST-BREAKOUT") readiness = 5;

    

    // 4. Trend Quality (Max 20) - mathematically derived from total score, adding back any penalty

    const total = parseInt(c.Score || "0");

    const riskVal = parseFloat(c.Risk_Pct || "0");

    const penalty = riskVal > 6.0 ? 15 : 0;

    

    let trend = total - (vcp + vdu + readiness) + penalty;

    if (trend < 0) trend = 0;

    if (trend > 20) trend = 20;

    trend = Math.round(trend);

    

    let penaltyItemHtml = "";

    if (penalty > 0) {

        penaltyItemHtml = `<li style="color: var(--accent-red); font-weight: 500;"><strong>Risk Penalty:</strong> -15 <span class="breakdown-details">(Risk: ${c.Risk_Pct}% > 6.0% tolerance)</span></li>`;

    }

    

    return `

        <div class="score-tooltip glass">

            <h4>Score Breakdown (Max 100)</h4>

            <ul>

                <li><strong>Trend Quality:</strong> ${trend} / 20 <span class="breakdown-details">(52w High & Relative Strength)</span></li>

                <li><strong>VCP Quality:</strong> ${vcp} / 40 <span class="breakdown-details">(Consolidation: ${c.Grade})</span></li>

                <li><strong>VDU Quality:</strong> ${vdu} / 20 <span class="breakdown-details">(VDU Ratio: ${c.VDU_Pct})</span></li>

                <li><strong>Readiness:</strong> ${readiness} / 20 <span class="breakdown-details">(Status: ${c.Readiness})</span></li>

                ${penaltyItemHtml}

            </ul>

        </div>

    `;

}

// Update sort icons on table headers

function updateHeaderSortIcons() {

    document.querySelectorAll(".watchlist-table th.sortable").forEach(th => {

        const col = th.getAttribute("data-sort");

        const icon = th.querySelector("i");

        if (icon) {

            if (appState.sortColumn === col) {

                icon.className = appState.sortDirection === "asc" 

                    ? "fa-solid fa-sort-up active-sort" 

                    : "fa-solid fa-sort-down active-sort";

            } else {

                icon.className = "fa-solid fa-sort";

            }

        }

    });

}

// Render active portfolio holdings

function renderPortfolio() {

    const body = document.getElementById("portfolio-table-body");

    if (!body) return;

    body.innerHTML = "";

    

    const countEl = document.getElementById("dashboard-portfolio-count");

    if (countEl) {

        countEl.textContent = `${appState.activePortfolio.length} Open Positions`;

    }

    

    if (appState.activePortfolio.length === 0) {

        body.innerHTML = `<tr><td colspan="13" class="text-center" style="padding: 24px; color: var(--text-muted);">No active trades currently open.</td></tr>`;

        return;

    }

    

    appState.activePortfolio.forEach(p => {

        const isProfit = p.PnL_Net >= 0;

        const pnlClass = isProfit ? "trend-up" : "trend-down";

        const pnlSign = isProfit ? "+" : "-";

        const rowColor = isProfit ? "rgba(16, 185, 129, 0.05)" : "rgba(239, 68, 68, 0.05)";

        

        const industryName = p.Industry || "Others";

        const indCategory = (p.Industry_Category || "Neutral").toLowerCase();

        

        const tr = document.createElement("tr");

        tr.style.background = rowColor;

        tr.innerHTML = `

            <td><strong>${p.Symbol}</strong></td>

            <td>

                <span class="industry-badge ${indCategory}">${industryName}</span>

                <br>

                <small style="color: var(--text-secondary); font-size: 10px; margin-top: 4px; display: block; white-space: nowrap;">

                    ${indCategory.toUpperCase()} | ${p.Industry_Trend || 'N/A'}

                </small>

            </td>

            <td><span class="badge ${p.Setup === 'VCP' ? 'badge-purple' : 'badge-blue'}">${p.Setup}</span></td>

            <td style="padding: 10px 12px; text-align: center;">

                ${(() => {

                    let earningsHtml = `<span style="color: var(--text-muted);">-</span>`;

                    if (p.Earnings_Date && p.Earnings_Date !== "N/A") {

                        const days = p.Days_To_Earnings;

                        let daysStyle = "color: var(--text-primary);";

                        let warningText = "";

                        if (days !== undefined && days !== null) {

                            if (days < 0) {

                                daysStyle = "color: var(--text-muted);";

                            } else if (days <= 3) {

                                daysStyle = "color: var(--accent-red); font-weight: 800; background: rgba(239, 68, 68, 0.1); padding: 1px 4px; border-radius: 3px;";

                                warningText = " ⚠️";

                            } else if (days <= 7) {

                                daysStyle = "color: var(--accent-orange); font-weight: 700;";

                                warningText = " ⚠️";

                            }

                        }

                        earningsHtml = `

                            <div style="font-size: 10.5px; line-height: 1.2; text-align: center;">

                                <div style="font-weight: 600; font-family: monospace;">${p.Earnings_Date}</div>

                                <div style="font-size: 9.5px; ${daysStyle}">${days !== undefined && days !== null ? (days < 0 ? `Past` : `${days}d left`) : ""}${warningText}</div>

                            </div>

                        `;

                    }

                    return earningsHtml;

                })()}

            </td>

            <td>${p.Entry_Date}</td>

            <td>${p.Shares}</td>

            <td>Rs. ${p.Entry_Price.toFixed(2)}</td>

            <td>Rs. ${p.Current_Stop.toFixed(2)}</td>

            <td>Rs. ${p.CMP.toFixed(2)}</td>

            <td class="${pnlClass}" style="font-weight: 600;">${pnlSign}Rs. ${Math.abs(p.PnL_Net).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>

            <td class="${pnlClass}" style="font-weight: 600;">${pnlSign}${Math.abs(p.R_Multiple).toFixed(2)}R</td>

            <td>Rs. ${p.Target_1.toFixed(2)}</td>

            <td>Rs. ${p.Target_2.toFixed(2)}</td>

        `;

        body.appendChild(tr);

    });

}

function renderDashboard2() {
    // 1. Check if the element exists in DOM
    const portfolioTableBody = document.getElementById("d2-portfolio-table-body");
    if (!portfolioTableBody) return;

    // 2. Initialize Subtabs Click Bindings & KPI card Click Bindings (Runs once)
    if (!window.d2SubtabsInitialized) {
        window.d2SubtabsInitialized = true;
        
        const btns = document.querySelectorAll(".dashboard2-subtab-btn");
        btns.forEach(btn => {
            btn.addEventListener("click", () => {
                btns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                
                const subtabId = btn.getAttribute("data-subtab");
                const contents = document.querySelectorAll(".dashboard2-subtab-content");
                contents.forEach(content => {
                    if (content.id === `subtab-${subtabId}`) {
                        content.style.display = "block";
                    } else {
                        content.style.display = "none";
                    }
                });
                
                // Redraw RRG / Breadth charts if switched to them
                if (subtabId === "d2-rrg") {
                    window.renderRRGChart(appState.rrgData, "rrg-canvas-d2", "rrg-legend-list-d2");
                } else if (subtabId === "d2-internals") {
                    window.renderMarketBreadthHistory(appState.marketBreadthHistory, "market-breadth-history-table-body-d2", "breadth-chart-canvas-d2", "breadth-status-badge-d2");
                }
            });
        });
        
        // Bind KPI click redirections
        const postureCard = document.getElementById("kpi2-posture-card");
        if (postureCard) {
            postureCard.addEventListener("click", () => {
                const btn = document.querySelector('[data-tab="daily_report"]');
                if (btn) btn.click();
            });
        }
        
        const setupsCard = document.getElementById("kpi2-setups-card");
        if (setupsCard) {
            setupsCard.addEventListener("click", () => {
                const btn = document.querySelector('[data-tab="stocks_filter"]');
                if (btn) btn.click();
            });
        }
        
        const sectorCard = document.getElementById("kpi2-sector-card");
        if (sectorCard) {
            sectorCard.addEventListener("click", () => {
                const btn = document.querySelector('[data-tab="sector_rotation"]');
                if (btn) btn.click();
            });
        }
    }

    // 3. Render Dashboard 2 KPI Cards
    const openJournalTrades = appState.tradeJournal ? appState.tradeJournal.filter(t => t.status === "OPEN") : [];
    let deployed = 0.0;
    openJournalTrades.forEach(t => {
        deployed += t.entry_price * (t.open_qty || 0);
    });

    let realized = 0.0;
    if (appState.tradeJournal) {
        appState.tradeJournal.forEach(t => {
            if (t.exits) {
                t.exits.forEach(e => {
                    realized += e.pnl || 0;
                });
            }
        });
    }

    let unrealized = 0.0;
    if (appState.activePortfolio) {
        appState.activePortfolio.forEach(p => {
            unrealized += p.PnL_Net || 0.0;
        });
    }

    const totalValue = appState.seedCapital + realized + unrealized;
    const netPnl = realized + unrealized;
    const netPnlPct = appState.seedCapital > 0 ? (netPnl / appState.seedCapital) * 100 : 0.0;
    const sign = netPnl >= 0 ? "+" : "";
    const color = netPnl >= 0 ? "var(--accent-green)" : "var(--accent-red)";

    const kpiValEl = document.getElementById("kpi2-portfolio-value");
    const kpiPnlEl = document.getElementById("kpi2-portfolio-pnl");
    if (kpiValEl) kpiValEl.textContent = `₹${totalValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    if (kpiPnlEl) kpiPnlEl.innerHTML = `Net P&L: <span style="color: ${color}; font-weight: bold;">${sign}₹${netPnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })} (${sign}${netPnlPct.toFixed(1)}%)</span>`;

    const posture = appState.marketHealth ? appState.marketHealth.posture : "RED";
    const score = appState.marketHealth ? appState.marketHealth.score : 0;
    const mhpStatusColor = posture === "GREEN" ? "var(--accent-green)" : "var(--accent-red)";

    const kpiPostureEl = document.getElementById("kpi2-market-posture");
    const kpiHealthEl = document.getElementById("kpi2-market-health");
    if (kpiPostureEl) {
        kpiPostureEl.textContent = posture;
        kpiPostureEl.style.color = mhpStatusColor;
    }
    if (kpiHealthEl) kpiHealthEl.textContent = `Score: ${score}/10`;

    const postureIcon = document.getElementById("kpi2-posture-icon");
    if (postureIcon) {
        postureIcon.className = `kpi-icon ${posture === "GREEN" ? "green" : "orange"}`;
    }

    const vcpCount = appState.vcpCandidates ? appState.vcpCandidates.length : 0;
    const flagCount = appState.flag_candidates ? appState.flag_candidates.length : 0;
    const pullbackCount = appState.strategicWatchlist ? appState.strategicWatchlist.filter(s => s.Setup_Type === "PULLBACK").length : 0;
    const ibCount = appState.strategicWatchlist ? appState.strategicWatchlist.filter(s => s.Setup_Type === "INSIDE_BAR_FLAG").length : 0;

    const setupsCountEl = document.getElementById("kpi2-setups-count");
    const setupsBreakdownEl = document.getElementById("kpi2-setups-breakdown");
    if (setupsCountEl) setupsCountEl.textContent = vcpCount + flagCount + pullbackCount;
    if (setupsBreakdownEl) setupsBreakdownEl.textContent = `VCP: ${vcpCount} | Pullback: ${pullbackCount} | Flag: ${flagCount} | IB: ${ibCount}`;

    const topInd = appState.focusIndustries && appState.focusIndustries.length > 0 ? appState.focusIndustries[0] : null;
    const topSectorEl = document.getElementById("kpi2-top-sector");
    const topSectorScoreEl = document.getElementById("kpi2-top-sector-score");
    if (topSectorEl && topSectorScoreEl) {
        if (topInd) {
            topSectorEl.textContent = topInd.Industry;
            topSectorScoreEl.textContent = `${topInd.Zone} (Part: ${topInd.Part_EMA20_Today ? topInd.Part_EMA20_Today.toFixed(0) : 0}% > 20EMA)`;
        } else {
            topSectorEl.textContent = "N/A";
            topSectorScoreEl.textContent = "No focus themes today";
        }
    }

    // 4. Render Portfolio Table inside Dashboard 2
    portfolioTableBody.innerHTML = "";

    const countEl = document.getElementById("d2-portfolio-count");
    if (countEl) {
        countEl.textContent = `${appState.activePortfolio.length} Open Positions`;
    }

    if (appState.activePortfolio.length === 0) {
        portfolioTableBody.innerHTML = `<tr><td colspan="9" class="text-center" style="padding: 24px; color: var(--text-muted);">No active trades currently open.</td></tr>`;
    } else {
        appState.activePortfolio.forEach(p => {
            const isProfit = p.PnL_Net >= 0;
            const pnlClass = isProfit ? "trend-up" : "trend-down";
            const pnlSign = isProfit ? "+" : "-";
            const rowColor = isProfit ? "rgba(16, 185, 129, 0.05)" : "rgba(239, 68, 68, 0.05)";
            
            const industryName = p.Industry || "Others";
            const indCategory = (p.Industry_Category || "Neutral").toLowerCase();

            const tr = document.createElement("tr");
            tr.style.background = rowColor;
            tr.innerHTML = `
                <td><strong>${p.Symbol}</strong></td>
                <td>
                    <span class="industry-badge ${indCategory}">${industryName}</span>
                    <br>
                    <small style="color: var(--text-secondary); font-size: 10px; margin-top: 4px; display: block; white-space: nowrap;">
                        ${indCategory.toUpperCase()} | ${p.Industry_Trend || 'N/A'}
                    </small>
                </td>
                <td><span class="badge ${p.Setup === 'VCP' ? 'badge-purple' : 'badge-blue'}">${p.Setup}</span></td>
                <td>Rs. ${p.CMP.toFixed(2)}</td>
                <td class="${pnlClass}" style="font-weight: 600;">${pnlSign}Rs. ${Math.abs(p.PnL_Net).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td class="${pnlClass}" style="font-weight: 600;">${pnlSign}${Math.abs(p.R_Multiple).toFixed(2)}R</td>
                <td>Rs. ${p.Current_Stop.toFixed(2)}</td>
                <td>Rs. ${p.Entry_Price.toFixed(2)}</td>
                <td>${p.Shares}</td>
            `;
            portfolioTableBody.appendChild(tr);
        });
    }

    // 5. Render Risk Allocation Summary (Right Column)
    const available = appState.seedCapital + realized - deployed;
    let riskAtStake = 0.0;
    openJournalTrades.forEach(t => {
        const risk = t.entry_price - t.stop_loss;
        if (risk > 0) {
            riskAtStake += risk * t.open_qty;
        }
    });

    const riskPct = appState.seedCapital > 0 ? (riskAtStake / appState.seedCapital) * 100 : 0;
    const exposurePct = appState.seedCapital > 0 ? (deployed / appState.seedCapital) * 100 : 0;

    const exposurePctEl = document.getElementById("d2-risk-exposure-pct");
    const exposureFillEl = document.getElementById("d2-risk-exposure-fill");
    const investedValEl = document.getElementById("d2-risk-invested-val");
    const cashValEl = document.getElementById("d2-risk-cash-val");

    if (exposurePctEl) exposurePctEl.textContent = `${exposurePct.toFixed(0)}% / ${(100 - exposurePct).toFixed(0)}%`;
    if (exposureFillEl) exposureFillEl.style.width = `${Math.min(exposurePct, 100)}%`;
    if (investedValEl) investedValEl.textContent = `Invested: ₹${deployed.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    if (cashValEl) cashValEl.textContent = `Cash: ₹${available.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

    const riskValEl = document.getElementById("d2-risk-at-stake-val");
    const riskPctEl = document.getElementById("d2-risk-at-stake-pct");
    if (riskValEl) riskValEl.textContent = `₹${riskAtStake.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    if (riskPctEl) {
        riskPctEl.textContent = `${riskPct.toFixed(1)}%`;
        if (riskPct > 2.0) {
            riskPctEl.style.color = "var(--accent-red)";
        } else if (riskPct > 1.0) {
            riskPctEl.style.color = "var(--accent-orange)";
        } else {
            riskPctEl.style.color = "var(--accent-green)";
        }
    }

    // Positions Industry Concentration list
    const concentrationListEl = document.getElementById("d2-concentration-list");
    if (concentrationListEl) {
        concentrationListEl.innerHTML = "";
        
        // Group invested funds by industry
        const industryInvested = {};
        let totalInvestedAmt = 0;
        
        openJournalTrades.forEach(t => {
            const pStock = appState.activePortfolio.find(p => p.Symbol.toUpperCase() === t.symbol.toUpperCase());
            const ind = (pStock && pStock.Industry) || "Others";
            const amt = t.entry_price * t.open_qty;
            industryInvested[ind] = (industryInvested[ind] || 0) + amt;
            totalInvestedAmt += amt;
        });

        const sortedIndustries = Object.entries(industryInvested).sort((a, b) => b[1] - a[1]);

        if (sortedIndustries.length === 0) {
            concentrationListEl.innerHTML = `<div style="font-size: 11.5px; color: var(--text-secondary); text-align: center; padding: 10px;">No open positions.</div>`;
        } else {
            sortedIndustries.forEach(([indName, amt]) => {
                const pct = totalInvestedAmt > 0 ? (amt / totalInvestedAmt) * 100 : 0;
                
                const item = document.createElement("div");
                item.className = "d2-concentration-item";
                item.innerHTML = `
                    <span style="font-weight: 600; color: var(--text-primary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 60%;" title="${indName}">${indName}</span>
                    <div style="display: flex; align-items: center; gap: 8px; font-family: monospace;">
                        <span style="color: var(--text-secondary);">₹${amt.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                        <strong style="color: var(--accent-purple);">${pct.toFixed(0)}%</strong>
                    </div>
                `;
                concentrationListEl.appendChild(item);
            });
        }
    }

    // 6. Draw active subtab details
    const activeSubtabBtn = document.querySelector(".dashboard2-subtab-btn.active");
    if (activeSubtabBtn) {
        const subtabId = activeSubtabBtn.getAttribute("data-subtab");
        if (subtabId === "d2-rrg") {
            window.renderRRGChart(appState.rrgData, "rrg-canvas-d2", "rrg-legend-list-d2");
        } else if (subtabId === "d2-internals") {
            window.renderMarketBreadthHistory(appState.marketBreadthHistory, "market-breadth-history-table-body-d2", "breadth-chart-canvas-d2", "breadth-status-badge-d2");
        }
    }
}

// Update Finance Dashboard widgets (Seed Capital, Deployed, Realized PnL, Available, Risk at Stake)

function updateFinanceDashboard() {

    if (!elements.finSeedCapital) return;

    const openJournalTrades = appState.tradeJournal.filter(t => t.status === "OPEN");

    // 1. Deployed Funds: sum of Entry Price * open_qty for active journal trades

    let deployed = 0.0;

    openJournalTrades.forEach(t => {

        deployed += t.entry_price * t.open_qty;

    });

    // 2. Realized P&L: sum of exits pnl

    let realized = 0.0;

    appState.tradeJournal.forEach(t => {

        if (t.exits) {

            t.exits.forEach(e => {

                realized += e.pnl || 0;

            });

        }

    });

    // 3. Available Funds: Seed Capital + Realized PnL - Deployed Funds

    const available = appState.seedCapital + realized - deployed;

    // 4. Risk at Stake (SL): sum of (entry_price - stop_loss) * open_qty

    let riskAtStake = 0.0;

    openJournalTrades.forEach(t => {

        const risk = t.entry_price - t.stop_loss;

        if (risk > 0) {

            riskAtStake += risk * t.open_qty;

        }

    });

    const riskPct = appState.seedCapital > 0 ? (riskAtStake / appState.seedCapital) * 100 : 0;

    // Render Values to dashboard elements

    elements.finSeedCapital.textContent = `₹${appState.seedCapital.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

    elements.finDeployedFunds.textContent = `₹${deployed.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

    

    const realizedSign = realized >= 0 ? "+" : "";

    elements.finRealizedPnl.textContent = `${realizedSign}₹${realized.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

    elements.finRealizedPnl.className = `card-value ${realized >= 0 ? 'trend-up' : 'trend-down'}`;

    

    elements.finAvailableFunds.textContent = `₹${available.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

    elements.finAvailableFunds.className = `card-value ${available >= 0 ? 'trend-up' : 'trend-down'}`;

    elements.finRiskAtStake.textContent = `₹${riskAtStake.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

    elements.riskPctBar.style.width = `${Math.min(riskPct * 5, 100)}%`; // scale visually

    elements.riskPctText.textContent = `${riskPct.toFixed(1)}% of Capital`;

    // Helper to search CMP from activePortfolio or Watchlist, fallback to entry_price

    const getCMP = (symbol) => {
        let sym = symbol.upperCase || symbol.toUpperCase();
        if (sym === "GANESH BENZO" || sym === "GANESH_BENZO") sym = "GANESHBE";

        const pStock = appState.activePortfolio.find(p => p.Symbol.toUpperCase() === sym);

        if (pStock && pStock.CMP) return pStock.CMP;

        const wlStock = (appState.vcpCandidates || []).concat(appState.flag_candidates || []).find(w => w.Symbol.toUpperCase() === sym);

        if (wlStock && wlStock.CMP) return wlStock.CMP;

        return null;

    };

    // Render Concentration list items

    if (elements.finConcentrationList) {

        elements.finConcentrationList.innerHTML = "";

        

        if (openJournalTrades.length === 0) {

            elements.finConcentrationList.innerHTML = `<div class="empty-state" style="padding: 10px; color: var(--text-secondary); font-size: 13px;">No open positions.</div>`;

        } else {

            // Sort by value descending

            const sortedPort = [...openJournalTrades].sort((a,b) => {

                const cmpA = getCMP(a.symbol) || a.entry_price;

                const cmpB = getCMP(b.symbol) || b.entry_price;

                return (b.open_qty * cmpB) - (a.open_qty * cmpA);

            });

            

            sortedPort.forEach(t => {

                const cmp = getCMP(t.symbol) || t.entry_price;

                const val = t.open_qty * cmp;

                const pctOfCapital = appState.seedCapital > 0 ? (val / appState.seedCapital) * 100 : 0;

                

                const item = document.createElement("div");

                item.className = "concentration-item";

                item.innerHTML = `

                    <span class="symbol">${t.symbol}</span>

                    <span class="val">₹${val.toLocaleString('en-IN', {maximumFractionDigits:0})} <span style="font-size:11px; color:var(--text-secondary);">(${pctOfCapital.toFixed(1)}%)</span></span>

                `;

                elements.finConcentrationList.appendChild(item);

            });

        }

    }

    

    // Render Risk Allocation Map Grid

    if (elements.finRiskMapGrid) {

        elements.finRiskMapGrid.innerHTML = "";

        

        if (openJournalTrades.length === 0) {

            elements.finRiskMapGrid.innerHTML = `<div class="empty-state" style="grid-column: span 3; padding: 10px; color: var(--text-secondary); font-size: 13px;">No risk mapped.</div>`;

        } else {

            openJournalTrades.forEach(t => {

                const risk = t.entry_price - t.stop_loss;

                const riskVal = risk > 0 ? risk * t.open_qty : 0;

                const riskPctOfCap = appState.seedCapital > 0 ? (riskVal / appState.seedCapital) * 100 : 0;

                

                let riskTier = "low";

                if (riskPctOfCap > 1.5) riskTier = "high";

                else if (riskPctOfCap > 0.5) riskTier = "medium";

                

                const item = document.createElement("div");

                item.className = `risk-map-item ${riskTier}`;

                item.innerHTML = `

                    <span class="symbol">${t.symbol}</span>

                    <span class="val">${riskPctOfCap.toFixed(1)}% Risk</span>

                `;

                elements.finRiskMapGrid.appendChild(item);

            });

        }

    }

}

function renderSectorRotation() {
    const container = elements.rotationCategoriesContainer;
    if (!container) return;

    container.innerHTML = "";

    const rotationData = appState.sectorRotation || [];
    if (rotationData.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-arrows-spin"></i> No sector rotation data available. Run scan to compute.
            </div>
        `;
        return;
    }

    // 1. Calculate dynamic ranks based on Sort_Score
    const sortedToday = [...rotationData].sort((a, b) => {
        const scoreA = (a.Avg_Return_10D || 0.0) + (a.Part_EMA20_Today || 0.0) / 10.0;
        const scoreB = (b.Avg_Return_10D || 0.0) + (b.Part_EMA20_Today || 0.0) / 10.0;
        return scoreB - scoreA;
    });

    const todayRanks = {};
    sortedToday.forEach((item, idx) => {
        todayRanks[item.Industry] = idx + 1;
    });

    // 2. Count categories for filter badges
    const counts = {
        "ALL": rotationData.length,
        "Confirmed Uptrend": 0,
        "Early Uptrend": 0,
        "Consolidation": 0,
        "Downtrend Warning": 0,
        "Avoid": 0
    };

    rotationData.forEach(item => {
        const cat = item.Category || "Avoid";
        if (counts[cat] !== undefined) {
            counts[cat]++;
        } else {
            counts["Avoid"]++;
        }
    });

    // Update filter buttons dynamically with counts
    const filterContainer = document.getElementById("sector-rotation-filters");
    if (filterContainer) {
        const btns = filterContainer.querySelectorAll(".sector-filter-btn");
        btns.forEach(btn => {
            const cat = btn.getAttribute("data-category");
            const count = counts[cat] !== undefined ? counts[cat] : 0;
            
            // Map category to a user-friendly label with color dot
            if (cat === "ALL") {
                btn.textContent = `All Categories (${count})`;
            } else if (cat === "Confirmed Uptrend") {
                btn.textContent = `🟢 Confirmed (${count})`;
            } else if (cat === "Early Uptrend") {
                btn.textContent = `🔵 Early (${count})`;
            } else if (cat === "Consolidation") {
                btn.textContent = `🟡 Consolidation (${count})`;
            } else if (cat === "Downtrend Warning") {
                btn.textContent = `🔴 Warning (${count})`;
            } else if (cat === "Avoid") {
                btn.textContent = `Avoid (${count})`;
            }
        });
    }

    // 3. Filter data
    const activeCategory = appState.selectedSectorCategory || "ALL";
    let filteredData = rotationData;
    if (activeCategory !== "ALL") {
        filteredData = rotationData.filter(item => {
            const itemCat = item.Category || "Avoid";
            return itemCat === activeCategory;
        });
    }

    // Sort filtered data by Sort_Score descending
    filteredData.sort((a, b) => {
        const scoreA = (a.Avg_Return_10D || 0.0) + (a.Part_EMA20_Today || 0.0) / 10.0;
        const scoreB = (b.Avg_Return_10D || 0.0) + (b.Part_EMA20_Today || 0.0) / 10.0;
        return scoreB - scoreA;
    });

    // Group by category
    const categoriesGroup = {};
    const categoriesOrder = ["Confirmed Uptrend", "Early Uptrend", "Consolidation", "Downtrend Warning", "Avoid"];
    
    // Initialize groups
    categoriesOrder.forEach(cat => {
        categoriesGroup[cat] = [];
    });

    filteredData.forEach(item => {
        const cat = item.Category || "Avoid";
        if (categoriesGroup[cat]) {
            categoriesGroup[cat].push(item);
        } else {
            categoriesGroup["Avoid"].push(item);
        }
    });

    // Render grouped categories
    categoriesOrder.forEach(catName => {
        const items = categoriesGroup[catName];
        if (!items || items.length === 0) return; // Skip empty groups if filtered

        // Create category wrapper
        const categorySection = document.createElement("div");
        categorySection.className = "category-section-block";
        categorySection.style.marginBottom = "20px";

        // Group metadata
        let statusClass = "neutral";
        let bannerColor = "var(--border-color)";
        let dotColor = "#94a3b8";

        if (catName === "Confirmed Uptrend") {
            statusClass = "running-hot";
            bannerColor = "var(--accent-green)";
            dotColor = "var(--accent-green)";
        } else if (catName === "Early Uptrend") {
            statusClass = "the-sweet-spot";
            bannerColor = "var(--accent-blue)";
            dotColor = "var(--accent-blue)";
        } else if (catName === "Consolidation") {
            statusClass = "waking-up";
            bannerColor = "var(--accent-yellow)";
            dotColor = "var(--accent-yellow)";
        } else if (catName === "Downtrend Warning") {
            statusClass = "out-of-favor";
            bannerColor = "#ea580c";
            dotColor = "#ea580c";
        } else if (catName === "Avoid") {
            statusClass = "out-of-favor";
            bannerColor = "var(--accent-red)";
            dotColor = "var(--accent-red)";
        }

        const safeId = catName.split(" ").join("-");

        categorySection.innerHTML = `
            <div class="category-header-banner ${statusClass}" style="background: linear-gradient(90deg, rgba(255,255,255,0.02) 0%, transparent 100%); border-left: 4px solid ${bannerColor}; margin-bottom: 12px; border-radius: 8px; padding: 10px 16px;">
                <div style="display: flex; flex-direction: column; gap: 2px;">
                    <h3 style="font-size: 14px; font-weight: 750; text-transform: uppercase; letter-spacing: 0.5px; margin: 0; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: ${dotColor}; display: inline-block;"></span>
                        ${catName} (${items.length})
                    </h3>
                </div>
            </div>
            <div class="rotation-grid-layout" id="grid-${safeId}"></div>
        `;

        container.appendChild(categorySection);

        const gridContainer = categorySection.querySelector(`#grid-${safeId}`);

        items.forEach(item => {
            const rankNum = todayRanks[item.Industry] || 99;
            const streak = item.Streak_Days || 1;
            const ema20 = item.Part_EMA20_Today || 0;
            const ema20Chg = item.Part_EMA20_Change || 0;
            const flowVal = item.Flow !== undefined ? item.Flow : (item.Net_Flow_Pct || 0);

            let chgBadgeClass = "flat";
            let chgText = "0%";
            if (ema20Chg > 0) {
                chgBadgeClass = "up";
                chgText = `+${ema20Chg.toFixed(0)}%`;
            } else if (ema20Chg < 0) {
                chgBadgeClass = "down";
                chgText = `${ema20Chg.toFixed(0)}%`;
            }

            let flowBadgeClass = "flat";
            let flowText = "Flat";
            if (flowVal > 0) {
                flowBadgeClass = "up";
                flowText = `↑ Flow`;
            } else if (flowVal < 0) {
                flowBadgeClass = "down";
                flowText = `↓ Flow`;
            }

            const card = document.createElement("div");
            card.className = "hd-sector-card";
            card.onclick = () => {
                if (typeof window.openIndustryDeepDive === "function") {
                    window.openIndustryDeepDive(item.Industry);
                }
            };

            const failureBadge = (item.Failure_Days && item.Failure_Days > 0) ? 
                `<span class="hd-meta-badge down" style="background: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); font-weight: bold; margin-left: 4px;" title="Grace Period Warning (Failure Day ${item.Failure_Days})">W</span>` : "";

            card.innerHTML = `
                <div class="hd-sector-info">
                    <div class="hd-sector-title-row">
                        <span class="hd-sector-rank">#${rankNum}</span>
                        <span class="hd-sector-name" title="${item.Industry}">${item.Industry}</span>
                        <span class="hd-sector-streak">(${streak}d)</span>
                    </div>
                </div>
                <div class="hd-sector-heatmap" title="20-EMA Participation: ${ema20.toFixed(1)}%">
                    <div class="hd-heatmap-bar-bg">
                        <div class="hd-heatmap-bar-fill" style="width: ${ema20}%; background: ${bannerColor};"></div>
                    </div>
                    <span class="hd-heatmap-val">${ema20.toFixed(0)}%</span>
                </div>
                <div class="hd-sector-meta">
                    <span class="hd-meta-badge ${chgBadgeClass}" title="EMA20 Change Today">${chgText}</span>
                    <span class="hd-meta-badge ${flowBadgeClass}" title="Net Money Flow">${flowText}</span>
                    ${failureBadge}
                </div>
            `;

            gridContainer.appendChild(card);
        });
    });
}

async function loadAndRenderSectorRotationHistory() {

    const historyBody = document.getElementById("sector-history-log");

    if (!historyBody) return;

    

    try {

        const response = await fetch("/api/sector_rotation_history");

        const historyData = await response.json();

        

        if (!historyData || historyData.length === 0) {

            historyBody.innerHTML = `

                <div style="font-size: 11.5px; color: var(--text-secondary); text-align: center; padding: 20px;">

                    No rotation history logs found. Run scans over consecutive days to build dynamic deltas.

                </div>

            `;

            return;

        }

        

        historyBody.innerHTML = historyData.map(log => {

            // Filter changes into 3 categories

            const strengthChanges = log.Changes.filter(c => c.Type === "GAIN_STRENGTH" || c.Type === "NEW_SECTOR");

            const weaknessChanges = log.Changes.filter(c => c.Type === "LOSE_LEADERSHIP" || c.Type === "DROPPED_SECTOR");

            const constantChanges = log.Changes.filter(c => c.Type === "CONSTANT" || c.Type === "STABLE");

            // Sort by magnitude of rank movement (largest change first)

            strengthChanges.sort((a, b) => {

                const deltaA = a.Rank_Delta !== undefined ? a.Rank_Delta : 0;

                const deltaB = b.Rank_Delta !== undefined ? b.Rank_Delta : 0;

                return deltaB - deltaA; // Highest positive first

            });

            

            weaknessChanges.sort((a, b) => {

                const deltaA = a.Rank_Delta !== undefined ? a.Rank_Delta : 0;

                const deltaB = b.Rank_Delta !== undefined ? b.Rank_Delta : 0;

                return deltaA - deltaB; // Most negative first (e.g. -59 before -3)

            });

            function renderChangesList(list, fallbackText) {

                if (list.length === 0) {

                    return `<div style="font-size: 11px; font-style: italic; color: var(--text-muted); padding: 8px; text-align: center; border: 1px dashed rgba(255,255,255,0.05); border-radius: 6px; background: rgba(255,255,255,0.005);">${fallbackText}</div>`;

                }

                return list.map(c => {

                    let badgeClass = "neutral";

                    let typeIcon = "→";

                    if (c.Type === "GAIN_STRENGTH") {

                        badgeClass = "running-hot";

                        typeIcon = "📈";

                    } else if (c.Type === "LOSE_LEADERSHIP") {

                        badgeClass = "out-of-favor";

                        typeIcon = "📉";

                    } else if (c.Type === "NEW_SECTOR") {

                        badgeClass = "sector-waking-up";

                        typeIcon = "🆕";

                    } else if (c.Type === "DROPPED_SECTOR") {

                        badgeClass = "neutral";

                        typeIcon = "🚫";

                    }

                    

                    let moversHtml = "";

                    if (c.Top_Movers && c.Top_Movers.length > 0) {

                        const moversList = c.Top_Movers.map(m => {

                            const retSign = m.Ret_Today >= 0 ? "↑" : "↓";

                            const retColor = m.Ret_Today >= 0 ? "var(--accent-green)" : "var(--accent-red)";

                            const absRet = Math.abs(m.Ret_Today);

                            return `

                                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 9.5px; padding: 2px 4px; border-radius: 4px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); width: 100%;">

                                    <span style="font-weight: 700; color: var(--text-primary); font-family: monospace;">${m.Symbol}</span>

                                    <span style="color: var(--text-secondary); font-size: 9px;">₹${m.Price.toFixed(0)}</span>

                                    <span style="color: ${retColor}; font-weight: 700; font-family: monospace;">${retSign}${absRet.toFixed(1)}%</span>

                                </div>

                            `;

                        }).join("");

                        

                        moversHtml = `

                            <div style="margin-top: 6px; padding-top: 6px; border-top: 1px dashed rgba(255,255,255,0.06); display: flex; flex-direction: column; gap: 4px;">

                                <span style="font-size: 8.5px; text-transform: uppercase; color: var(--text-muted); font-weight: 800; letter-spacing: 0.3px;">Top Movers:</span>

                                <div style="display: flex; flex-direction: column; gap: 3px;">

                                    ${moversList}

                                </div>

                            </div>

                        `;

                    }

                    

                    return `

                        <div class="history-item" onclick="openIndustryDeepDive('${c.Industry.replace(/'/g, "\\\'")}')" style="padding: 10px; border-radius: 8px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 4px; font-size: 11.5px; cursor: pointer; transition: all 0.2s ease;" onmouseover="this.style.borderColor='rgba(139, 92, 246, 0.4)'" onmouseout="this.style.borderColor='var(--border-color)'">

                            <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">

                                <strong style="color: var(--text-primary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 145px;" title="${c.Industry}">${typeIcon} ${c.Industry}</strong>

                                <span class="rotation-action-badge ${badgeClass}" style="font-size: 7.5px; padding: 1px 4px; text-transform: uppercase; white-space: nowrap; flex-shrink: 0;">${c.Type.replace("_", " ")}</span>

                            </div>

                            <p style="margin: 0; color: var(--text-secondary); line-height: 1.3;">${c.Description}</p>

                            ${c.Reason ? `<p style="margin: 2px 0 0 0; font-size: 10.5px; font-style: italic; color: var(--text-muted); line-height: 1.3;"><strong>Comment:</strong> ${c.Reason}</p>` : ''}

                            ${moversHtml}

                        </div>

                    `;

                }).join("");

            }

            const strengthHtml = renderChangesList(strengthChanges, "No sectors gaining strength.");

            const weaknessHtml = renderChangesList(weaknessChanges, "No sectors losing leadership.");

            const constantHtml = renderChangesList(constantChanges, "No constant sectors.");

            

            const options = { year: 'numeric', month: 'short', day: 'numeric' };

            const formattedDate = new Date(log.Date).toLocaleDateString("en-US", options);

            

            return `

                <div class="history-date-group" style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; padding-bottom: 24px; border-bottom: 1px dashed rgba(255,255,255,0.05);">

                    <div style="font-size: 12px; font-weight: 800; color: var(--accent-purple); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; padding-left: 4px;">

                        📅 Scan Session: ${formattedDate}

                    </div>

                    <div class="history-zones-grid" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">

                        <!-- Gaining Strength Column -->

                        <div class="history-zone-col" style="display: flex; flex-direction: column; gap: 8px;">

                            <h4 style="font-size: 12px; font-weight: 700; color: var(--accent-green); text-transform: uppercase; display: flex; align-items: center; gap: 6px; margin: 0 0 4px 0; padding-bottom: 6px; border-bottom: 1px solid rgba(16, 185, 129, 0.15);">

                                📈 Gaining Strength

                            </h4>

                            ${strengthHtml}

                        </div>

                        

                        <!-- Losing Leadership Column -->

                        <div class="history-zone-col" style="display: flex; flex-direction: column; gap: 8px;">

                            <h4 style="font-size: 12px; font-weight: 700; color: var(--accent-red); text-transform: uppercase; display: flex; align-items: center; gap: 6px; margin: 0 0 4px 0; padding-bottom: 6px; border-bottom: 1px solid rgba(239, 68, 68, 0.15);">

                                📉 Losing Leadership

                            </h4>

                            ${weaknessHtml}

                        </div>

                        

                        <!-- Constant Column -->

                        <div class="history-zone-col" style="display: flex; flex-direction: column; gap: 8px;">

                            <h4 style="font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; display: flex; align-items: center; gap: 6px; margin: 0 0 4px 0; padding-bottom: 6px; border-bottom: 1px solid rgba(255, 255, 255, 0.15);">

                                ⚖️ Stable / Constant

                            </h4>

                            ${constantHtml}

                        </div>

                    </div>

                </div>

            `;

        }).join("");

    } catch (err) {

        console.error("Failed to load sector rotation history:", err);

        historyBody.innerHTML = `<div style="font-size: 11.5px; color: var(--accent-red); padding: 10px;">Failed to load rotation history log.</div>`;

    }

}

// -------------------------------------------------------------

// TRADE JOURNAL IMPLEMENTATION

// -------------------------------------------------------------

let journalFilter = "ALL"; // "ALL", "OPEN", "CLOSED"

async function loadTradeJournalData() {

    try {

        const response = await fetch("/api/trade_journal");

        appState.tradeJournal = await response.json();

        

        // Also fetch active portfolio to ensure holdings and PnLs are updated!

        try {

            const portResponse = await fetch("/api/portfolio");

            appState.activePortfolio = await portResponse.json();

        } catch (portErr) {

            console.error("Failed to reload active portfolio in journal load:", portErr);

        }

        

        renderTradeJournal();

        renderTradeCalendar();

        

        // Update all dashboards to keep them in sync with the journal changes

        updateFinanceDashboard();

        renderDashboard2();

        renderPortfolio();

    } catch (err) {

        console.error("Failed to load trade journal:", err);

        appState.tradeJournal = [];

    }

}

function setupJournalEventHandlers() {

    // Filter tabs

    document.querySelectorAll(".j-filter-tab").forEach(tab => {

        tab.addEventListener("click", () => {

            document.querySelectorAll(".j-filter-tab").forEach(t => t.classList.remove("active"));

            tab.classList.add("active");

            journalFilter = tab.getAttribute("data-status");

            renderTradeJournalList();

        });

    });

    

    // Search input

    const searchInput = document.getElementById("journal-search-input");

    if (searchInput) {

        searchInput.addEventListener("input", () => {

            renderTradeJournalList();

        });

    }

    

    // Export PDF button

    const exportBtn = document.getElementById("export-pdf-btn");

    if (exportBtn) {

        exportBtn.addEventListener("click", () => {

            exportJournalToPDF();

        });

    }

    

    // Add Trade button

    const addBtn = document.getElementById("add-trade-btn");

    if (addBtn) {

        addBtn.addEventListener("click", () => {

            openTradeModal();

        });

    }

    

    // Close Modal buttons

    document.getElementById("close-trade-modal-btn").addEventListener("click", closeTradeModal);

    document.getElementById("cancel-trade-modal-btn").addEventListener("click", closeTradeModal);

    

    // Save Trade Form submit

    document.getElementById("trade-form").addEventListener("submit", handleSaveTrade);

    

    // Add Exit Row button

    document.getElementById("modal-add-exit-row").addEventListener("click", () => {

        addExitRow();

    });

    // Auto-calculate risk % on input change

    const entryInput = document.getElementById("trade-entry-price");

    const slInput = document.getElementById("trade-sl");

    const qtyInput = document.getElementById("trade-qty");

    if (entryInput && slInput) {

        const calcRisk = () => {

            const entry = parseFloat(entryInput.value) || 0;

            const sl = parseFloat(slInput.value) || 0;

            if (entry > 0 && sl > 0) {

                const risk = ((entry - sl) / entry) * 100;

                document.getElementById("trade-risk-pct").value = risk.toFixed(1);

            }

            updateModalStatusState();

        };

        entryInput.addEventListener("input", calcRisk);

        slInput.addEventListener("input", calcRisk);

    }

    if (qtyInput) {

        qtyInput.addEventListener("input", updateModalStatusState);

    }

    // Dynamic month navigation buttons

    const prevBtn = document.getElementById("calendar-prev-btn");

    const nextBtn = document.getElementById("calendar-next-btn");

    if (prevBtn && nextBtn) {

        prevBtn.addEventListener("click", () => {

            appState.calendarMonth--;

            if (appState.calendarMonth < 0) {

                appState.calendarMonth = 11;

                appState.calendarYear--;

            }

            renderTradeCalendar();

        });

        nextBtn.addEventListener("click", () => {

            appState.calendarMonth++;

            if (appState.calendarMonth > 11) {

                appState.calendarMonth = 0;

                appState.calendarYear++;

            }

            renderTradeCalendar();

        });

    }

}

function getWinningStreak() {

    const pnlByDate = {};

    appState.tradeJournal.forEach(t => {

        t.exits.forEach(e => {

            if (e.date) {

                pnlByDate[e.date] = (pnlByDate[e.date] || 0) + e.pnl;

            }

        });

    });

    

    const dates = Object.keys(pnlByDate).sort();

    if (dates.length === 0) return 0;

    

    let streak = 0;

    for (let i = dates.length - 1; i >= 0; i--) {

        if (pnlByDate[dates[i]] > 0) {

            streak++;

        } else if (pnlByDate[dates[i]] < 0) {

            break;

        }

    }

    return streak;

}

function renderTradeJournal() {

    let openTradesVal = 0;

    let profitableVal = 0;

    let lossesVal = 0;

    let netPerfVal = 0;

    let capCycleVal = 0;

    let closedCount = 0;

    let winCount = 0;

    

    appState.tradeJournal.forEach(t => {

        capCycleVal += t.invested_amount;

        if (t.status === "OPEN") {

            openTradesVal += t.entry_price * t.open_qty;

        } else {

            closedCount++;

            const tradeNetPnl = t.exits.reduce((acc, e) => acc + e.pnl, 0);

            if (tradeNetPnl > 0) winCount++;

        }

        

        t.exits.forEach(e => {

            netPerfVal += e.pnl;

            if (t.status === "CLOSED") {

                if (e.pnl > 0) profitableVal += e.pnl;

                else lossesVal += e.pnl;

            }

        });

    });

    

    const successRate = closedCount > 0 ? (winCount / closedCount) * 100 : 0;

    

    document.getElementById("j-stat-open-trades").textContent = `₹${openTradesVal.toLocaleString('en-IN', {maximumFractionDigits:0})}`;

    document.getElementById("j-stat-profitable").textContent = `+₹${profitableVal.toLocaleString('en-IN', {maximumFractionDigits:0})}`;

    document.getElementById("j-stat-losses").textContent = `-₹${Math.abs(lossesVal).toLocaleString('en-IN', {maximumFractionDigits:0})}`;

    

    const netSign = netPerfVal >= 0 ? "+" : "";

    const netEl = document.getElementById("j-stat-net-perf");

    netEl.textContent = `${netSign}₹${netPerfVal.toLocaleString('en-IN', {maximumFractionDigits:0})}`;

    netEl.className = netPerfVal >= 0 ? "card-value trend-up" : "card-value trend-down";

    

    document.getElementById("j-stat-success-rate").textContent = `${successRate.toFixed(0)}%`;

    

    // Calculate Discipline Score (starts at 100, drops for each constitution violation)

    let disciplineScore = 100;

    appState.tradeJournal.forEach(t => {

        const tViolations = calculateTradeViolations(t);

        tViolations.forEach(v => {

            if (v.rule.includes("RULE 4") && v.desc.includes("breached")) {

                disciplineScore -= 20;

            } else if (v.rule.includes("RULE 4") && v.desc.includes("suicide")) {

                disciplineScore -= 15;

            } else if (v.rule.includes("RULE #0")) {

                disciplineScore -= 20;

            } else if (v.rule.includes("RULE 5")) {

                disciplineScore -= 10;

            } else if (v.rule.includes("RULE 3") || v.rule.includes("RULE 7")) {

                disciplineScore -= 10;

            } else if (v.rule.includes("RULE 1")) {

                disciplineScore -= 5;

            }

        });

    });

    

    disciplineScore = Math.max(0, disciplineScore);

    

    let disciplineLabel = "PRISTINE (100/100) 🏆";

    let disciplineColor = "#10b981";

    

    if (disciplineScore === 100) {

        disciplineLabel = "PRISTINE (100/100) 🏆";

        disciplineColor = "#10b981";

    } else if (disciplineScore >= 80) {

        disciplineLabel = `STRONG (${disciplineScore}/100) 👍`;

        disciplineColor = "#10b981";

    } else if (disciplineScore >= 60) {

        disciplineLabel = `MODERATE (${disciplineScore}/100) ⚠️`;

        disciplineColor = "#f59e0b";

    } else if (disciplineScore >= 40) {

        disciplineLabel = `LEAKS (${disciplineScore}/100) 🚨`;

        disciplineColor = "#ef4444";

    } else {

        disciplineLabel = `COMPROMISED (${disciplineScore}/100) 💀`;

        disciplineColor = "#ef4444";

    }

    

    const dbBadgeEl = document.getElementById("j-stat-discipline-badge");

    if (dbBadgeEl) {

        dbBadgeEl.textContent = disciplineLabel;

        dbBadgeEl.style.color = disciplineColor;

        

        // Update the award icon style and color

        const dbIconEl = dbBadgeEl.parentElement.nextElementSibling;

        if (dbIconEl && dbIconEl.tagName === "I") {

            dbIconEl.style.color = disciplineColor;

            if (disciplineScore >= 80) {

                dbIconEl.className = "fa-solid fa-award";

            } else if (disciplineScore >= 60) {

                dbIconEl.className = "fa-solid fa-triangle-exclamation";

            } else {

                dbIconEl.className = "fa-solid fa-skull-crossbones";

            }

        }

    }

    

    const capCycleEl = document.getElementById("j-stat-cap-cycle");

    if (capCycleEl) {

        capCycleEl.textContent = `₹${capCycleVal.toLocaleString('en-IN', {maximumFractionDigits:0})}`;

    }

    

    const streak = getWinningStreak();

    const streakLabel = document.querySelector("#journal-calendar-card span[style*='color']");

    if (streakLabel) {

        if (streak > 0) {

            streakLabel.innerHTML = `<i class="fa-solid fa-fire"></i> ${streak} Days Winning Momentum`;

            streakLabel.style.color = "var(--accent-green)";

        } else {

            streakLabel.innerHTML = `<i class="fa-solid fa-circle-info"></i> No Active Winning Streak`;

            streakLabel.style.color = "var(--text-secondary)";

        }

    }

    

    renderTradeJournalList();

    renderJournalCharts();

    if (typeof updateFinanceDashboard === "function") {

        updateFinanceDashboard();

    }

}

function renderTradeJournalList() {

    const listContainer = document.getElementById("journal-trades-list");

    if (!listContainer) return;

    

    listContainer.innerHTML = "";

    

    const searchVal = (document.getElementById("journal-search-input")?.value || "").toUpperCase();

    

    let filtered = appState.tradeJournal;

    if (journalFilter !== "ALL") {

        filtered = filtered.filter(t => t.status === journalFilter);

    }

    

    if (searchVal) {

        filtered = filtered.filter(t => t.symbol.includes(searchVal) || t.name.toUpperCase().includes(searchVal));

    }

    

    filtered.sort((a, b) => new Date(b.entry_date) - new Date(a.entry_date));

    

    if (filtered.length === 0) {

        listContainer.innerHTML = `

            <div class="empty-state">

                <i class="fa-solid fa-magnifying-glass"></i> No matching trades found in journal.

            </div>

        `;

        return;

    }

    

    filtered.forEach(t => {

        const card = createJournalTradeCard(t);

        listContainer.appendChild(card);

    });

}

function calculateTradeViolations(t) {

    const violations = [];

    

    // Find CMP

    let cmp = null;
    let sym = t.symbol.toUpperCase();
    if (sym === "GANESH BENZO" || sym === "GANESH_BENZO") sym = "GANESHBE";

    if (appState.activePortfolio) {

        const pStock = appState.activePortfolio.find(p => p.Symbol.toUpperCase() === sym);

        if (pStock && pStock.CMP) cmp = pStock.CMP;

    }

    if (!cmp) {

        const wlStock = ((appState.vcpCandidates || []).concat(appState.flag_candidates || [])).find(w => w.Symbol.toUpperCase() === sym);

        if (wlStock && wlStock.CMP) cmp = wlStock.CMP;

    }

    

    if (t.status === "OPEN") {

        // RULE 4: Stop Loss is Sacred (Missing SL)

        if (!t.stop_loss || t.stop_loss <= 0) {

            violations.push({

                rule: "RULE 4 — STOP LOSS IS SACRED",

                desc: "Trading without a defined stop loss is financial suicide. You are operating as a gambler, not an institutional risk manager."

            });

        }

        

        // RULE 4 & RULE 15 / RULE #0: SL Breach / Ego Over Capital

        if (t.stop_loss && cmp && cmp <= t.stop_loss) {

            violations.push({

                rule: "RULE 4 — STOP LOSS IS SACRED",

                desc: `Failing to liquidate a position after your technical invalidation level (Stop Loss: ₹${t.stop_loss.toFixed(2)}) was hit (Price: ₹${cmp.toFixed(2)}) is a severe process failure. You are ignoring market reality.`

            });

            violations.push({

                rule: "RULE #0 — EGO OVER CAPITAL",

                desc: "Stop loss breached but position remains open. You are protecting your ego instead of your capital. Exit the trade immediately."

            });

        }

        

        // RULE 1: Capital Preservation (Excessive Risk)

        if (t.risk_pct && t.risk_pct > 8.0) {

            violations.push({

                rule: "RULE 1 — CAPITAL PRESERVATION",

                desc: `Risk per share is ${t.risk_pct}%, which exceeds your conservative 8% maximum threshold. A sequence of large losses will permanently impair capital.`

            });

        }

        

        // RULE 3: Trading is not Investing

        const containsInvestingWords = /long-term|good company|good results|will recover|recovery/i.test((t.comments || "") + " " + (t.technical_desc || ""));

        if (containsInvestingWords) {

            violations.push({

                rule: "RULE 3 — TRADING IS NOT INVESTING",

                desc: "Justifying holding a trade by arguing the company is 'good' or has 'strong results' is a strategy shift. A trade must never morph into an investment."

            });

        }

        

        // RULE 7: No Hope (detecting hope statements)

        const containsHopeWords = /it will recover|it can't fall|exit after recovery|already down|temporary fall/i.test((t.comments || "") + " " + (t.technical_desc || ""));

        if (containsHopeWords) {

            violations.push({

                rule: "RULE 7 — NO HOPE",

                desc: "Hope statements detected in rationales. Hope is not a trading strategy. Cut the loss according to your system."

            });

        }

        // RULE 5: Never Average Losers

        if (t.comments && t.comments.includes("RULE 5 — NEVER AVERAGE LOSERS")) {

            violations.push({

                rule: "RULE 5 — NEVER AVERAGE LOSERS",

                desc: "Averaging down on a losing position compounds exposure. You are allocating good capital to a setup that has already failed."

            });

        }

    }

    

    return violations;

}

function createJournalTradeCard(t) {

    const card = document.createElement("div");

    const netPnl = t.exits.reduce((acc, e) => acc + e.pnl, 0);

    const hasPnl = netPnl !== 0;

    const isProfit = netPnl >= 0;

    

    function getDaysDiff(d1, d2) {
        if (!d1 || !d2) return 0;
        const date1 = new Date(d1);
        const date2 = new Date(d2);
        date1.setHours(12, 0, 0, 0);
        date2.setHours(12, 0, 0, 0);
        const diffTime = date2 - date1;
        const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
        return diffDays;
    }

    const todayStr = new Date().toISOString().split('T')[0];
    let holdingPeriodHtml = "";

    if (t.status === "OPEN") {
        if (t.exits && t.exits.length > 0) {
            const daysOpen = getDaysDiff(t.entry_date, todayStr);
            const trancheDays = t.exits.map((e, idx) => {
                const days = getDaysDiff(t.entry_date, e.date);
                let plLabel = "";
                if (t.entry_price) {
                    const pct = ((e.price - t.entry_price) / t.entry_price) * 100;
                    const typeChar = pct >= 0 ? "P" : "L";
                    const signStr = pct >= 0 ? "+" : "";
                    plLabel = ` (${typeChar}: ${signStr}${pct.toFixed(1)}%)`;
                }
                return `T${idx+1}: ${days}d${plLabel}`;
            });
            holdingPeriodHtml = `Holding: <span style="color: var(--accent-orange); font-weight: 600;">${daysOpen}d open (Exits: ${trancheDays.join(", ")})</span>`;
        } else {
            const daysOpen = getDaysDiff(t.entry_date, todayStr);
            holdingPeriodHtml = `Holding: <span style="color: var(--accent-purple); font-weight: 600;">${daysOpen}d open</span>`;
        }
    } else {
        if (t.exits && t.exits.length > 0) {
            const trancheDays = t.exits.map((e, idx) => {
                const days = getDaysDiff(t.entry_date, e.date);
                let plLabel = "";
                if (t.entry_price) {
                    const pct = ((e.price - t.entry_price) / t.entry_price) * 100;
                    const typeChar = pct >= 0 ? "P" : "L";
                    const signStr = pct >= 0 ? "+" : "";
                    plLabel = ` (${typeChar}: ${signStr}${pct.toFixed(1)}%)`;
                }
                return `T${idx+1}: ${days}d${plLabel}`;
            });
            holdingPeriodHtml = `Holding: <span style="color: var(--accent-green); font-weight: 600;">${trancheDays.join(" | ")}</span>`;
        } else {
            holdingPeriodHtml = `Holding: <span style="color: var(--text-secondary); font-weight: 600;">-</span>`;
        }
    }

    let statusClass = "status-open";
    let statusLabel = "OPEN";

    if (t.status === "OPEN" && t.exits && t.exits.length > 0) {
        statusClass = "status-partial";
        statusLabel = "PARTIAL";
    } else if (t.status === "CLOSED") {
        statusClass = isProfit ? "status-win" : "status-loss";
        statusLabel = isProfit ? "CLOSED (WIN)" : "CLOSED (LOSS)";
    }

    

    card.className = `j-trade-card glass ${statusClass}`;

    card.id = `j-card-${t.id}`;

    

    const pnlSign = isProfit ? "+" : "";

    const pnlDisplay = hasPnl 

        ? `<div class="j-card-pnl ${isProfit ? 'trend-up' : 'trend-down'}" style="font-size: 15px;">${pnlSign}₹${netPnl.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>`

        : '<div class="j-card-pnl text-muted" style="font-size: 15px;">-</div>';

        

    let exitsHtml = "";

    if (t.exits && t.exits.length > 0) {

        exitsHtml = `

            <div class="j-card-exits-breakdown">

                <strong>Exits:</strong>

                ${t.exits.map(e => `

                    <span class="exit-badge ${e.pnl >= 0 ? 'win' : 'loss'}">

                        ${e.date}: ${e.qty} shares @ ₹${e.price.toFixed(1)} (${e.pnl >= 0 ? '+' : ''}₹${e.pnl.toFixed(0)})

                    </span>

                `).join(" ")}

            </div>

        `;

    }

    

    const violations = calculateTradeViolations(t);

    const hasViolations = violations.length > 0;

    

    let violationsHtml = "";

    if (hasViolations) {

        violationsHtml = `

            <div class="j-card-violations-list" style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); padding: 12px; border-radius: 8px; margin-bottom: 15px;">

                <h4 style="color: #ef4444; margin: 0 0 8px 0; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 6px;">

                    <i class="fa-solid fa-circle-exclamation"></i> Trading Constitution Violations

                </h4>

                <ul style="margin: 0; padding-left: 18px; font-size: 11.5px; color: #f8fafc; line-height: 1.5; display: flex; flex-direction: column; gap: 6px;">

                    ${violations.map(v => `

                        <li><strong style="color: #ef4444;">${v.rule}:</strong> ${v.desc}</li>

                    `).join("")}

                </ul>

            </div>

        `;

    }

    

    card.innerHTML = `

        <div class="j-card-summary-row" onclick="toggleJournalCard('${t.id}')">

            <div class="j-card-summary-info">

                <h3 style="display: flex; flex-direction: column; gap: 2px;">${t.symbol} <span style="margin: 0; font-size: 11px;">${t.name}</span></h3>

                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">

                    <span class="j-status-badge ${statusClass}" style="margin: 0;">${statusLabel}</span>

                    ${hasViolations ? `

                        <span class="j-viol-pill" style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; width: fit-content;">

                            <i class="fa-solid fa-triangle-exclamation"></i> ${violations.length} VIOLATION${violations.length > 1 ? 'S' : ''}

                        </span>

                    ` : ''}

                    ${t.status === "OPEN" && t.MS_Score !== undefined ? `

                        <span class="j-ms-pill" style="background: ${getMSColor(t.MS_Score, true)}; color: ${getMSColor(t.MS_Score, false)}; border: 1px solid ${getMSColor(t.MS_Score, false)}4D; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; cursor: pointer; width: fit-content;" onclick="event.stopPropagation(); showAMSDetail('${t.symbol}')">

                            <i class="fa-solid fa-bolt"></i> MS: ${t.MS_Score} (${t.MS_Rating})

                        </span>

                    ` : ''}

                </div>

                

                <div class="j-card-summary-row-metrics" style="margin-top: 6px; display: flex; gap: 15px; font-size: 12px; color: #94a3b8; flex-wrap: wrap;">

                    <div>Entry Date: <span style="color: #e2e8f0; font-weight: 600;">${t.entry_date}</span></div>

                    <div>Invested: <span style="color: #e2e8f0; font-weight: 600;">₹${t.invested_amount.toLocaleString('en-IN', {maximumFractionDigits:0})}</span></div>

                    <div>Qty: <span style="color: #e2e8f0; font-weight: 600;">${t.total_qty}</span></div>

                    <div>${holdingPeriodHtml}</div>

                </div>

            </div>

            <div class="j-card-summary-actions">

                ${pnlDisplay}

                ${t.status === "OPEN" ? `

                    <button class="j-quick-btn check-btn" onclick="event.stopPropagation(); quickCloseTrade('${t.id}', true)" title="Mark as Worked (Target Hit)">

                        <i class="fa-solid fa-check"></i>

                    </button>

                    <button class="j-quick-btn cross-btn" onclick="event.stopPropagation(); quickCloseTrade('${t.id}', false)" title="Mark as Failed (SL Hit)">

                        <i class="fa-solid fa-xmark"></i>

                    </button>

                ` : ''}

                <i class="fa-solid fa-chevron-down j-expand-icon"></i>

            </div>

        </div>

        

        <div class="j-card-details-wrapper">

            ${violationsHtml}

            <div class="j-card-metrics" style="margin-top: 0;">

                <div class="j-metric">

                    <span class="label">Entry Price</span>

                    <span class="value">₹${t.entry_price.toFixed(2)}</span>

                </div>

                <div class="j-metric">

                    <span class="label">Open Qty</span>

                    <span class="value">${t.open_qty}</span>

                </div>

                <div class="j-metric">

                    <span class="label">Stop Loss</span>

                    <span class="value">${t.stop_loss ? '₹' + t.stop_loss.toFixed(2) : '-'}</span>

                </div>

                <div class="j-metric">

                    <span class="label">Targets</span>

                    <span class="value">${t.target_1 ? '₹' + t.target_1.toFixed(2) : '-'} / ${t.target_2 ? '₹' + t.target_2.toFixed(2) : '-'}</span>

                </div>

                <div class="j-metric">

                    <span class="label">Risk per share</span>

                    <span class="value ${t.risk_pct > 6 ? 'trend-down' : (t.risk_pct <= 6 && t.risk_pct > 0 ? 'trend-up' : '')}">${t.risk_pct ? t.risk_pct + '%' : '-'}</span>

                </div>

                <div class="j-metric">

                    <span class="label">Actions</span>

                    <div style="display: flex; gap: 8px;">

                        <button class="j-edit-btn" onclick="event.stopPropagation(); openTradeModal('${t.id}')" style="padding: 4px 10px; width: fit-content;">

                            <i class="fa-solid fa-pen-to-square"></i> Edit

                        </button>

                        <button class="j-delete-btn" onclick="event.stopPropagation(); deleteTradeJournalEntry('${t.id}')" style="padding: 4px 10px; width: fit-content; background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='rgba(239, 68, 68, 0.3)'" onmouseout="this.style.background='rgba(239, 68, 68, 0.15)'">

                            <i class="fa-solid fa-trash-can"></i> Delete

                        </button>

                    </div>

                </div>

            </div>

            ${t.technical_desc ? `

                <div class="j-card-desc">

                    <strong>Setup Rationale:</strong> ${t.technical_desc}

                </div>

            ` : ''}

            ${t.comments ? `

                <div class="j-card-comments">

                    <strong>My Rationale / Thoughts:</strong> ${t.comments}

                </div>

            ` : ''}

            ${exitsHtml}

        </div>

    `;

    

    return card;

}

async function deleteTradeJournalEntry(tradeId) {

    if (!confirm("Are you sure you want to permanently delete this trade journal entry?")) {

        return;

    }

    

    const updatedJournal = appState.tradeJournal.filter(t => t.id.toString() !== tradeId.toString());

    

    try {

        const response = await fetch("/api/trade_journal", {

            method: "POST",

            headers: {

                "Content-Type": "application/json"

            },

            body: JSON.stringify(updatedJournal)

        });

        

        if (response.ok) {

            showToast("Trade deleted successfully!", "success");

            await loadTradeJournalData();

        } else {

            showToast("Failed to delete trade from server.", "error");

        }

    } catch (e) {

        console.error("Delete trade error:", e);

        showToast("Error: " + e.message, "error");

    }

}

function openTradeModal(tradeId = null) {

    const modal = document.getElementById("trade-modal");

    const form = document.getElementById("trade-form");

    const title = document.getElementById("modal-title");

    

    form.reset();

    document.getElementById("modal-exits-container").innerHTML = "";

    

    if (tradeId) {

        title.textContent = "Edit Trade Details";

        const t = appState.tradeJournal.find(item => item.id === tradeId.toString());

        if (!t) return;

        

        document.getElementById("trade-id-field").value = t.id;

        document.getElementById("trade-symbol").value = t.symbol;

        document.getElementById("trade-name").value = t.name;

        document.getElementById("trade-entry-date").value = t.entry_date;

        document.getElementById("trade-exit-date").value = t.exit_date || "";

        document.getElementById("trade-entry-price").value = t.entry_price;

        document.getElementById("trade-qty").value = t.total_qty;

        document.getElementById("trade-t1").value = t.target_1 || "";

        document.getElementById("trade-t2").value = t.target_2 || "";

        document.getElementById("trade-sl").value = t.stop_loss || "";

        document.getElementById("trade-risk-pct").value = t.risk_pct || "";

        document.getElementById("trade-status").value = t.status;

        document.getElementById("trade-tech-desc").value = t.technical_desc || "";

        document.getElementById("trade-comments").value = t.comments || "";

        

        if (t.exits) {

            t.exits.forEach(e => {

                addExitRow(e.date, e.qty, e.price, e.pnl);

            });

        }

    } else {

        title.textContent = "Add New Trade";

        document.getElementById("trade-id-field").value = "";

        document.getElementById("trade-status").value = "OPEN";

        document.getElementById("trade-entry-date").value = new Date().toISOString().split('T')[0];

    }

    

    modal.style.display = "flex";

}

function closeTradeModal() {

    document.getElementById("trade-modal").style.display = "none";

}

function updateModalStatusState() {

    const totalQty = parseFloat(document.getElementById("trade-qty").value) || 0;

    let exitedQty = 0;

    document.querySelectorAll(".modal-exit-row").forEach(row => {

        exitedQty += parseFloat(row.querySelector(".exit-row-qty").value) || 0;

    });

    

    const statusSelect = document.getElementById("trade-status");

    if (exitedQty >= totalQty && totalQty > 0) {

        statusSelect.value = "CLOSED";

    }

}

function addExitRow(date = "", qty = "", price = "", pnl = 0) {

    const container = document.getElementById("modal-exits-container");

    const row = document.createElement("div");

    row.className = "modal-exit-row";

    row.style.display = "flex";

    row.style.gap = "10px";

    row.style.alignItems = "center";

    row.style.marginBottom = "8px";

    

    const formattedPnl = pnl !== undefined ? pnl : 0;

    const pnlClass = formattedPnl >= 0 ? "trend-up" : "trend-down";

    const pnlSign = formattedPnl >= 0 ? "+" : "";

    

    row.innerHTML = `

        <input type="date" class="exit-row-date" required value="${date}" style="padding: 6px; border-radius: 6px; border: 1px solid var(--border-color); background: rgba(0,0,0,0.3); color: var(--text-primary); font-size: 12px; outline: none; width: 130px; color-scheme: dark;">

        <input type="number" class="exit-row-qty" required value="${qty}" style="padding: 6px; border-radius: 6px; border: 1px solid var(--border-color); background: rgba(0,0,0,0.3); color: var(--text-primary); font-size: 12px; outline: none; width: 80px;" placeholder="Qty">

        <input type="number" step="0.01" class="exit-row-price" required value="${price}" style="padding: 6px; border-radius: 6px; border: 1px solid var(--border-color); background: rgba(0,0,0,0.3); color: var(--text-primary); font-size: 12px; outline: none; width: 100px;" placeholder="Price">

        <span class="exit-row-pnl ${pnlClass}" style="font-size: 12px; font-weight: 600; width: 90px; text-align: right; font-family: monospace;">₹${formattedPnl.toLocaleString('en-IN', {maximumFractionDigits:0})}</span>

        <button type="button" class="remove-exit-row-btn" style="background: none; border: none; color: var(--accent-red); font-size: 18px; cursor: pointer; padding: 4px; line-height: 1;">&times;</button>

    `;

    

    row.querySelector(".remove-exit-row-btn").addEventListener("click", () => {

        row.remove();

        updateModalStatusState();

    });

    

    const updatePnl = () => {

        const entryPrice = parseFloat(document.getElementById("trade-entry-price").value) || 0;

        const exitQty = parseFloat(row.querySelector(".exit-row-qty").value) || 0;

        const exitPrice = parseFloat(row.querySelector(".exit-row-price").value) || 0;

        

        const rowPnl = (exitPrice - entryPrice) * exitQty;

        const pnlSpan = row.querySelector(".exit-row-pnl");

        

        pnlSpan.textContent = `₹${rowPnl.toLocaleString('en-IN', {maximumFractionDigits:0})}`;

        pnlSpan.className = `exit-row-pnl ${rowPnl >= 0 ? 'trend-up' : 'trend-down'}`;

        updateModalStatusState();

    };

    

    row.querySelector(".exit-row-qty").addEventListener("input", updatePnl);

    row.querySelector(".exit-row-price").addEventListener("input", updatePnl);

    

    container.appendChild(row);

    updateModalStatusState();

}

function showRiskViolationModal({ rule, danger, bias, consequence, correctAction, onCorrect, onBypass }) {

    const modalId = "risk-violation-modal";

    let modal = document.getElementById(modalId);

    if (modal) modal.remove();

    

    if (!document.getElementById("risk-violation-styles")) {

        const style = document.createElement("style");

        style.id = "risk-violation-styles";

        style.textContent = `

            .risk-viol-overlay {

                position: fixed;

                top: 0;

                left: 0;

                width: 100%;

                height: 100%;

                background: rgba(10, 10, 15, 0.85);

                backdrop-filter: blur(8px);

                z-index: 99999;

                display: flex;

                align-items: center;

                justify-content: center;

                font-family: 'Inter', sans-serif;

                color: #e2e8f0;

            }

            .risk-viol-card {

                background: #1a1a24;

                border: 2px solid #ef4444;

                border-radius: 12px;

                padding: 28px;

                max-width: 550px;

                width: 90%;

                box-shadow: 0 10px 25px rgba(239, 68, 68, 0.25);

                animation: scaleUp 0.3s ease-out;

            }

            @keyframes scaleUp {

                from { transform: scale(0.95); opacity: 0; }

                to { transform: scale(1); opacity: 1; }

            }

            .risk-viol-header {

                font-size: 20px;

                font-weight: 800;

                color: #ef4444;

                margin-bottom: 18px;

                display: flex;

                align-items: center;

                gap: 8px;

                text-transform: uppercase;

                letter-spacing: 0.5px;

            }

            .risk-viol-title {

                font-size: 16px;

                font-weight: 700;

                color: #f8fafc;

                margin-bottom: 12px;

                border-bottom: 1px solid #334155;

                padding-bottom: 6px;

            }

            .risk-viol-section {

                margin-bottom: 14px;

                font-size: 13.5px;

                line-height: 1.5;

            }

            .risk-viol-label {

                font-weight: 700;

                color: #94a3b8;

                font-size: 11px;

                text-transform: uppercase;

                margin-bottom: 3px;

                letter-spacing: 0.5px;

            }

            .risk-viol-text {

                color: #e2e8f0;

            }

            .risk-viol-buttons {

                display: flex;

                flex-direction: column;

                gap: 10px;

                margin-top: 24px;

            }

            .risk-viol-correct-btn {

                background: #ef4444;

                color: #ffffff;

                border: none;

                border-radius: 6px;

                padding: 12px;

                font-weight: 700;

                font-size: 14px;

                cursor: pointer;

                transition: background 0.2s;

                text-align: center;

            }

            .risk-viol-correct-btn:hover {

                background: #dc2626;

            }

            .risk-viol-bypass-btn {

                background: transparent;

                color: #64748b;

                border: none;

                font-weight: 600;

                font-size: 12px;

                cursor: pointer;

                text-align: center;

                text-decoration: underline;

                padding: 6px;

            }

            .risk-viol-bypass-btn:hover {

                color: #94a3b8;

            }

        `;

        document.head.appendChild(style);

    }

    

    modal = document.createElement("div");

    modal.id = modalId;

    modal.className = "risk-viol-overlay";

    

    modal.innerHTML = `

        <div class="risk-viol-card">

            <div class="risk-viol-header">

                <i class="fa-solid fa-triangle-exclamation"></i> TRADING CONSTITUTION VIOLATION

            </div>

            <div class="risk-viol-title">${rule}</div>

            

            <div class="risk-viol-section">

                <div class="risk-viol-label">Why this is dangerous:</div>

                <div class="risk-viol-text">${danger}</div>

            </div>

            

            <div class="risk-viol-section">

                <div class="risk-viol-label">What psychological bias is causing it:</div>

                <div class="risk-viol-text">${bias}</div>

            </div>

            

            <div class="risk-viol-section">

                <div class="risk-viol-label">Potential long-term consequence:</div>

                <div class="risk-viol-text">${consequence}</div>

            </div>

            

            <div class="risk-viol-section" style="background: rgba(239, 68, 68, 0.08); padding: 10px; border-left: 3px solid #ef4444; border-radius: 0 4px 4px 0;">

                <div class="risk-viol-label" style="color: #ef4444;">Correct action:</div>

                <div class="risk-viol-text" style="font-weight: 600;">${correctAction}</div>

            </div>

            

            <div class="risk-viol-buttons">

                <button class="risk-viol-correct-btn" id="risk-viol-correct">I Will Correct It</button>

                <button class="risk-viol-bypass-btn" id="risk-viol-bypass">Proceed Anyway (Bypass CRO Under Protest)</button>

            </div>

        </div>

    `;

    

    document.body.appendChild(modal);

    

    document.getElementById("risk-viol-correct").addEventListener("click", () => {

        modal.remove();

        if (onCorrect) onCorrect();

    });

    

    document.getElementById("risk-viol-bypass").addEventListener("click", () => {

        modal.remove();

        if (onBypass) onBypass();

    });

}

async function handleSaveTrade(e) {

    e.preventDefault();

    

    const id = document.getElementById("trade-id-field").value;

    const symbol = document.getElementById("trade-symbol").value.toUpperCase().trim();

    const name = document.getElementById("trade-name").value.trim();

    const entry_date = document.getElementById("trade-entry-date").value;

    let exit_date = document.getElementById("trade-exit-date").value || null;

    const entry_price = parseFloat(document.getElementById("trade-entry-price").value);

    const total_qty = parseInt(document.getElementById("trade-qty").value);

    const target_1 = parseFloat(document.getElementById("trade-t1").value) || null;

    const target_2 = parseFloat(document.getElementById("trade-t2").value) || null;

    const stop_loss = parseFloat(document.getElementById("trade-sl").value) || null;

    const risk_pct = parseFloat(document.getElementById("trade-risk-pct").value) || 0;

    let status = document.getElementById("trade-status").value;

    const technical_desc = document.getElementById("trade-tech-desc").value.trim();

    let comments = document.getElementById("trade-comments").value.trim();

    

    const exits = [];

    let exitedQty = 0;

    let latestExitDate = null;

    

    document.querySelectorAll(".modal-exit-row").forEach(row => {

        const exitDate = row.querySelector(".exit-row-date").value;

        const exitQty = parseInt(row.querySelector(".exit-row-qty").value) || 0;

        const exitPrice = parseFloat(row.querySelector(".exit-row-price").value) || 0;

        const exitPnl = (exitPrice - entry_price) * exitQty;

        

        exits.push({

            date: exitDate,

            qty: exitQty,

            price: exitPrice,

            pnl: exitPnl

        });

        

        exitedQty += exitQty;

        if (!latestExitDate || exitDate > latestExitDate) {

            latestExitDate = exitDate;

        }

    });

    

    const open_qty = Math.max(0, total_qty - exitedQty);

    if (open_qty === 0) {

        status = "CLOSED";

        if (latestExitDate) {

            exit_date = latestExitDate;

        }

    }

    

    const invested_amount = entry_price * total_qty;

    

    let days_active = 0;

    const entryDateObj = new Date(entry_date);

    const endDateObj = exit_date ? new Date(exit_date) : new Date();

    const diffTime = Math.abs(endDateObj - entryDateObj);

    days_active = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    

    const tradeData = {

        id: id || Date.now().toString(),

        symbol,

        name,

        entry_date,

        exit_date,

        days_active,

        entry_price,

        invested_amount,

        target_1,

        target_2,

        stop_loss,

        risk_pct,

        total_qty,

        open_qty,

        status,

        technical_desc,

        comments,

        exits

    };

    // --- Trading Constitution Rules Check (Chief Risk Officer Validation) ---

    const getCMP = (sym) => {
        if (!appState.activePortfolio) return null;
        let s = sym.toUpperCase();
        if (s === "GANESH BENZO" || s === "GANESH_BENZO") s = "GANESHBE";

        const pStock = appState.activePortfolio.find(p => p.Symbol.toUpperCase() === s);

        if (pStock && pStock.CMP) return pStock.CMP;

        const wlStock = ((appState.vcpCandidates || []).concat(appState.flag_candidates || [])).find(w => w.Symbol.toUpperCase() === s);

        if (wlStock && wlStock.CMP) return wlStock.CMP;

        return null;

    };

    let violation = null;

    // RULE 4: STOP LOSS IS SACRED

    if (status === "OPEN" && (!stop_loss || stop_loss <= 0)) {

        violation = {

            rule: "RULE 4 — STOP LOSS IS SACRED",

            danger: "Entering or keeping a trade without a stop loss invalidates your system and exposes your account to unlimited risk. Hope is replacing discipline.",

            bias: "Loss Aversion & Denial (fear of taking a loss and being proven wrong).",

            consequence: "Uncontrolled drawdown, single trade blow-ups, and complete failure of risk parameters.",

            correctAction: "Define your technical invalidation level and enter a valid Stop Loss."

        };

    }

    // RULE 5: NEVER AVERAGE LOSERS

    if (!violation && id) {

        const original = appState.tradeJournal.find(item => item.id.toString() === id.toString());

        if (original && original.status === "OPEN" && total_qty > original.total_qty) {

            const cmp = getCMP(symbol);

            if (cmp && cmp < original.entry_price) {

                violation = {

                    rule: "RULE 5 — NEVER AVERAGE LOSERS",

                    danger: "Averaging down on a losing trade compounds your exposure. You are adding size to a setup the market has already proven wrong.",

                    bias: "Sunk Cost Fallacy & Ego (trying to get back to even faster).",

                    consequence: "Turning minor, controlled losses into major account-damaging write-downs.",

                    correctAction: "Do not add size. Keep the position size exactly as it is, or exit if your technical setup invalidation stop loss is hit."

                };

            }

        }

    }

    // RULE 10: NO GREED (Moving targets higher)

    if (!violation && id) {

        const original = appState.tradeJournal.find(item => item.id.toString() === id.toString());

        if (original && original.status === "OPEN" && original.target_1 && target_1 > original.target_1) {

            violation = {

                rule: "RULE 10 — NO GREED",

                danger: "Moving targets higher during a run because of greed violates your pre-determined exit plan. You risk giving back all paper profits when the stock reverses.",

                bias: "Overconfidence & Greed.",

                consequence: "Failing to lock in gains, turning winning trades into losers, and reducing profit factor.",

                correctAction: "Lock in profits at your predetermined target levels. If you want to ride a trend, use a trailing stop loss on a partial position instead of shifting targets."

            };

        }

    }

    // RULE 1: CAPITAL PRESERVATION (High risk pct)

    if (!violation && status === "OPEN" && risk_pct > 8.0) {

        violation = {

            rule: "RULE 1 — CAPITAL PRESERVATION",

            danger: "Taking a risk of greater than 8% on a single trade violates the fundamental rule of keeping losses small. A string of a few consecutive losses will cause deep, hard-to-recover drawdowns.",

            bias: "Overconfidence, impatience, and underestimating market risk.",

            consequence: "Severe drawdown, permanent impairment of capital, and loss of confidence.",

            correctAction: "Reduce your position size (qty) or tighten your stop loss to ensure the risk per trade is kept small (ideally <= 5-6%)."

        };

    }

    // RULE 3: TRADING IS NOT INVESTING

    if (!violation && status === "OPEN") {

        const containsInvestingWords = /long-term|good company|good results|will recover|recovery/i.test(comments + " " + technical_desc);

        if (containsInvestingWords) {

            violation = {

                rule: "RULE 3 — TRADING IS NOT INVESTING",

                danger: "Holding onto a losing trade by calling it a 'long-term investment' shifts your strategy mid-trade without a plan. You become an accidental investor, locked in a losing stock.",

                bias: "Cognitive dissonance (rationalizing a mistake by shifting long-term frames).",

                consequence: "Dead capital locked up for years, massive opportunity cost, and holding onto toxic losers.",

                correctAction: "Exit the trade immediately as defined by your system. If you want to invest, create a separate investment account with separate valuation metrics."

            };

        }

    }

    const saveExecution = async () => {

        let updatedJournal = [...appState.tradeJournal];

        if (id) {

            const idx = updatedJournal.findIndex(item => item.id.toString() === id.toString());

            if (idx !== -1) {

                updatedJournal[idx] = tradeData;

            }

        } else {

            updatedJournal.push(tradeData);

        }

        

        try {

            const response = await fetch("/api/trade_journal", {

                method: "POST",

                headers: {

                    "Content-Type": "application/json"

                },

                body: JSON.stringify(updatedJournal)

            });

            

            if (response.ok) {

                closeTradeModal();

                showToast("Trade saved successfully!", "success");

                await loadTradeJournalData();

            } else {

                showToast("Failed to save trade to server.", "error");

            }

        } catch (err) {

            console.error("Save trade error:", err);

            showToast("Error saving trade: " + err.message, "error");

        }

    };

    if (violation) {

        // Proceed and save directly, show warning toast, and prepend notice to comments

        tradeData.comments = `[🚨 RISK BYPASS: ${violation.rule} bypassed] ` + (tradeData.comments || "");

        showToast(`Warning: ${violation.rule} detected! Saved under protest.`, "warning");

    }

    saveExecution();

}

function renderTradeCalendar() {

    const grid = document.getElementById("journal-calendar-days-grid");

    if (!grid) return;

    grid.innerHTML = "";

    

    const year = appState.calendarYear || new Date().getFullYear();

    const month = appState.calendarMonth !== undefined ? appState.calendarMonth : new Date().getMonth();

    

    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

    const labelEl = document.getElementById("calendar-header-label");

    if (labelEl) {

        labelEl.textContent = `${monthNames[month]} ${year}`;

    }

    

    const firstDay = new Date(year, month, 1).getDay();

    const numDays = new Date(year, month + 1, 0).getDate();

    const prevNumDays = new Date(year, month, 0).getDate();

    

    const pnlByDate = {};

    appState.tradeJournal.forEach(t => {

        if (t.exits) {

            t.exits.forEach(e => {

                if (e.date) {

                    pnlByDate[e.date] = (pnlByDate[e.date] || 0) + e.pnl;

                }

            });

        }

    });

    

    for (let i = firstDay - 1; i >= 0; i--) {

        const dayNum = prevNumDays - i;

        const cell = document.createElement("div");

        cell.className = "calendar-cell other-month";

        cell.innerHTML = `<span class="day-num">${dayNum}</span>`;

        grid.appendChild(cell);

    }

    

    for (let d = 1; d <= numDays; d++) {

        const dateStr = `${year}-${(month + 1).toString().padStart(2, '0')}-${d.toString().padStart(2, '0')}`;

        const dayPnl = pnlByDate[dateStr];

        

        const cell = document.createElement("div");

        cell.className = "calendar-cell";

        

        const todayStr = new Date().toISOString().split('T')[0];

        if (dateStr === todayStr) {

            cell.classList.add("today");

        }

        

        let pnlHtml = "";

        if (dayPnl !== undefined && dayPnl !== 0) {

            const isPos = dayPnl > 0;

            const sign = isPos ? "+" : "";

            const pnlClass = isPos ? "positive" : "negative";

            pnlHtml = `<span class="day-pnl ${pnlClass}">${sign}₹${Math.abs(dayPnl).toLocaleString('en-IN', {maximumFractionDigits:0})}</span>`;

        }

        

        cell.innerHTML = `

            <span class="day-num">${d}</span>

            ${pnlHtml}

        `;

        grid.appendChild(cell);

    }

    

    const totalCells = grid.children.length;

    const remaining = 42 - totalCells;

    for (let i = 1; i <= remaining; i++) {

        const cell = document.createElement("div");

        cell.className = "calendar-cell other-month";

        cell.innerHTML = `<span class="day-num">${i}</span>`;

        grid.appendChild(cell);

    }

}

function loadHtml2Pdf() {

    return new Promise((resolve, reject) => {

        if (window.html2pdf) {

            resolve(window.html2pdf);

            return;

        }

        const script = document.createElement("script");

        script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";

        script.onload = () => resolve(window.html2pdf);

        script.onerror = () => reject(new Error("Failed to load html2pdf.js"));

        document.head.appendChild(script);

    });

}

async function exportJournalToPDF() {

    try {

        showToast("Generating PDF report...", "info");

        const html2pdf = await loadHtml2Pdf();

        

        const element = document.createElement("div");

        element.style.padding = "30px";

        element.style.color = "#111827";

        element.style.background = "#ffffff";

        element.style.fontFamily = "'Outfit', 'Segoe UI', Arial, sans-serif";

        

        const style = document.createElement("style");

        style.innerHTML = `

            .pdf-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #8b5cf6; padding-bottom: 15px; margin-bottom: 20px; }

            .pdf-title h1 { margin: 0; font-size: 24px; color: #1e1b4b; }

            .pdf-title p { margin: 5px 0 0 0; font-size: 13px; color: #6b7280; }

            .pdf-logo { font-size: 20px; font-weight: 800; color: #8b5cf6; }

            

            .pdf-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px; }

            .pdf-metric-card { padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; }

            .pdf-metric-card .label { font-size: 10px; text-transform: uppercase; color: #6b7280; font-weight: 600; margin-bottom: 4px; }

            .pdf-metric-card .value { font-size: 16px; font-weight: 700; color: #111827; }

            .pdf-metric-card .value.positive { color: #10b981; }

            .pdf-metric-card .value.negative { color: #ef4444; }

            

            .pdf-badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 700; text-transform: uppercase; }

            .pdf-badge.status-open { background: #dbeafe; color: #1e40af; }

            .pdf-badge.status-win { background: #d1fae5; color: #065f46; }

            .pdf-badge.status-loss { background: #fee2e2; color: #991b1b; }

            

            .pdf-pnl-pos { color: #10b981; font-weight: 600; }

            .pdf-pnl-neg { color: #ef4444; font-weight: 600; }

            

            .pdf-section-title { font-size: 14px; font-weight: 700; margin: 25px 0 10px 0; color: #1e1b4b; border-left: 3px solid #8b5cf6; padding-left: 8px; }

            

            .pdf-trade-row { margin-bottom: 15px; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; page-break-inside: avoid; }

            .pdf-trade-header { display: flex; justify-content: space-between; font-weight: 700; margin-bottom: 8px; border-bottom: 1px dashed #e5e7eb; padding-bottom: 4px; font-size: 12px; }

            .pdf-trade-details { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; font-size: 10px; color: #4b5563; }

            .pdf-trade-exits { margin-top: 8px; padding-top: 6px; border-top: 1px dashed #e5e7eb; font-size: 9.5px; }

            .pdf-comments { margin-top: 6px; font-style: italic; color: #6b7280; font-size: 10px; background: #f9fafb; padding: 6px; border-radius: 4px; }

        `;

        element.appendChild(style);

        

        const dateStr = new Date().toLocaleDateString("en-US", { year: 'numeric', month: 'long', day: 'numeric' });

        

        const header = document.createElement("div");

        header.className = "pdf-header";

        header.innerHTML = `

            <div class="pdf-title">

                <h1>Minervini OS - Trade Journal Report</h1>

                <p>Generated on ${dateStr} | Trading Dashboard</p>

            </div>

            <div class="pdf-logo">Minervini OS</div>

        `;

        element.appendChild(header);

        

        let openTradesVal = 0;

        let profitableVal = 0;

        let lossesVal = 0;

        let netPerfVal = 0;

        let capCycleVal = 0;

        let closedCount = 0;

        let winCount = 0;

        

        appState.tradeJournal.forEach(t => {

            capCycleVal += t.invested_amount;

            if (t.status === "OPEN") {

                openTradesVal += t.entry_price * t.open_qty;

            } else {

                closedCount++;

                const tradeNetPnl = t.exits.reduce((acc, e) => acc + e.pnl, 0);

                if (tradeNetPnl > 0) winCount++;

            }

            

            t.exits.forEach(e => {

                netPerfVal += e.pnl;

                if (t.status === "CLOSED") {

                    if (e.pnl > 0) profitableVal += e.pnl;

                    else lossesVal += e.pnl;

                }

            });

        });

        

        const successRate = closedCount > 0 ? (winCount / closedCount) * 100 : 0;

        

        const metrics = document.createElement("div");

        metrics.className = "pdf-metrics";

        metrics.innerHTML = `

            <div class="pdf-metric-card">

                <div class="label">Open Trades</div>

                <div class="value">₹${openTradesVal.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>

            </div>

            <div class="pdf-metric-card">

                <div class="label">Profitable (Closed)</div>

                <div class="value positive">+₹${profitableVal.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>

            </div>

            <div class="pdf-metric-card">

                <div class="label">Losses (Closed)</div>

                <div class="value negative">-₹${Math.abs(lossesVal).toLocaleString('en-IN', {maximumFractionDigits:0})}</div>

            </div>

            <div class="pdf-metric-card">

                <div class="label">Net Realized P&L</div>

                <div class="value ${netPerfVal >= 0 ? 'positive' : 'negative'}">${netPerfVal >= 0 ? '+' : ''}₹${netPerfVal.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>

            </div>

            <div class="pdf-metric-card">

                <div class="label">Success Rate</div>

                <div class="value">${successRate.toFixed(1)}%</div>

            </div>

            <div class="pdf-metric-card">

                <div class="label">Capital Cycle</div>

                <div class="value">₹${capCycleVal.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>

            </div>

        `;

        element.appendChild(metrics);

        

        const activeTitle = document.createElement("div");

        activeTitle.className = "pdf-section-title";

        activeTitle.textContent = "Open Positions";

        element.appendChild(activeTitle);

        

        const openTrades = appState.tradeJournal.filter(t => t.status === "OPEN");

        if (openTrades.length === 0) {

            const empty = document.createElement("p");

            empty.style.fontSize = "11px";

            empty.style.color = "#6b7280";

            empty.textContent = "No open positions.";

            element.appendChild(empty);

        } else {

            openTrades.forEach(t => {

                const tradeDiv = createPDFTradeRow(t);

                element.appendChild(tradeDiv);

            });

        }

        

        const closedTitle = document.createElement("div");

        closedTitle.className = "pdf-section-title";

        closedTitle.textContent = "Completed Trades";

        element.appendChild(closedTitle);

        

        const closedTrades = appState.tradeJournal.filter(t => t.status === "CLOSED");

        if (closedTrades.length === 0) {

            const empty = document.createElement("p");

            empty.style.fontSize = "11px";

            empty.style.color = "#6b7280";

            empty.textContent = "No completed trades.";

            element.appendChild(empty);

        } else {

            closedTrades.forEach(t => {

                const tradeDiv = createPDFTradeRow(t);

                element.appendChild(tradeDiv);

            });

        }

        

        const opt = {

            margin:       10,

            filename:     'Trade_Journal_Report.pdf',

            image:        { type: 'jpeg', quality: 0.98 },

            html2canvas:  { scale: 2, useCORS: true },

            jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }

        };

        

        await html2pdf().from(element).set(opt).save();

        showToast("PDF Exported successfully!", "success");

    } catch (err) {

        console.error("PDF Export error:", err);

        showToast("Failed to export PDF: " + err.message, "error");

    }

}

function createPDFTradeRow(t) {

    const div = document.createElement("div");

    div.className = "pdf-trade-row";

    

    const isClosed = t.status === "CLOSED";

    const netPnl = t.exits.reduce((acc, e) => acc + e.pnl, 0);

    const pnlDisplay = netPnl !== 0 

        ? `<span class="${netPnl >= 0 ? 'pdf-pnl-pos' : 'pdf-pnl-neg'}">${netPnl >= 0 ? '+' : ''}₹${netPnl.toLocaleString('en-IN', {maximumFractionDigits:0})}</span>`

        : '';

        

    let statusClass = "status-open";

    if (t.status === "CLOSED") {

        statusClass = netPnl >= 0 ? "status-win" : "status-loss";

    }

    

    let exitsHtml = "";

    if (t.exits && t.exits.length > 0) {

        exitsHtml = `

            <div class="pdf-trade-exits">

                <strong>Exits Breakdown:</strong>

                <table style="width:100%; margin-top:4px; font-size:9px; border-collapse:collapse;">

                    <thead>

                        <tr style="background:#f3f4f6;">

                            <th style="padding:2px 4px; border:1px solid #e5e7eb;">Date</th>

                            <th style="padding:2px 4px; border:1px solid #e5e7eb;">Qty</th>

                            <th style="padding:2px 4px; border:1px solid #e5e7eb;">Exit Price</th>

                            <th style="padding:2px 4px; border:1px solid #e5e7eb;">PnL</th>

                        </tr>

                    </thead>

                    <tbody>

                        ${t.exits.map(e => `

                            <tr>

                                <td style="padding:2px 4px; border:1px solid #e5e7eb;">${e.date}</td>

                                <td style="padding:2px 4px; border:1px solid #e5e7eb;">${e.qty}</td>

                                <td style="padding:2px 4px; border:1px solid #e5e7eb;">₹${e.price.toFixed(2)}</td>

                                <td style="padding:2px 4px; border:1px solid #e5e7eb;" class="${e.pnl >= 0 ? 'pdf-pnl-pos' : 'pdf-pnl-neg'}">${e.pnl >= 0 ? '+' : ''}₹${e.pnl.toLocaleString('en-IN', {maximumFractionDigits:0})}</td>

                            </tr>

                        `).join("")}

                    </tbody>

                </table>

            </div>

        `;

    }

    

    div.innerHTML = `

        <div class="pdf-trade-header">

            <span>${t.symbol} - ${t.name}</span>

            <span>

                <span class="pdf-badge ${statusClass}">${t.status}</span>

                ${pnlDisplay ? ' | ' + pnlDisplay : ''}

            </span>

        </div>

        <div class="pdf-trade-details">

            <div><strong>Entry Date:</strong> ${t.entry_date}</div>

            <div><strong>Entry Price:</strong> ₹${t.entry_price.toFixed(2)}</div>

            <div><strong>Total Qty:</strong> ${t.total_qty}</div>

            <div><strong>Open Qty:</strong> ${t.open_qty}</div>

            <div><strong>Invested:</strong> ₹${t.invested_amount.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>

            <div><strong>Stop Loss:</strong> ${t.stop_loss ? '₹' + t.stop_loss.toFixed(2) : '-'}</div>

            <div><strong>T1 / T2:</strong> ${t.target_1 ? '₹' + t.target_1.toFixed(2) : '-'} / ${t.target_2 ? '₹' + t.target_2.toFixed(2) : '-'}</div>

            <div><strong>Risk per Share:</strong> ${t.risk_pct ? t.risk_pct + '%' : '-'}</div>

        </div>

        ${t.technical_desc ? `<div style="margin-top:6px; font-size:10px;"><strong>Technical Setup:</strong> ${t.technical_desc}</div>` : ''}

        ${t.comments ? `<div class="pdf-comments"><strong>Comments:</strong> ${t.comments}</div>` : ''}

        ${exitsHtml}

    `;

    return div;

}

function showToast(message, type = "success") {

    let toast = document.getElementById("app-toast");

    if (!toast) {

        toast = document.createElement("div");

        toast.id = "app-toast";

        toast.className = "toast";

        document.body.appendChild(toast);

    }

    toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : (type === 'error' ? 'fa-circle-xmark' : 'fa-circle-info')}"></i> ${message}`;

    toast.className = `toast show`;

    if (type === "error") {

        toast.style.background = "var(--accent-red)";

    } else if (type === "info") {

        toast.style.background = "var(--accent-blue)";

    } else {

        toast.style.background = "var(--accent-green)";

    }

    setTimeout(() => {

        toast.classList.remove("show");

    }, 3000);

}

function addCandidateToJournal(symbol) {
    const cleanSym = (symbol || "").toUpperCase().trim();
    const candidate = (appState.vcpCandidates || []).find(c => (c.Symbol || "").toUpperCase().trim() === cleanSym) || 
                      (appState.flag_candidates || []).find(c => (c.Symbol || "").toUpperCase().trim() === cleanSym) ||
                      (appState.allScannedCandidates && appState.allScannedCandidates.find(c => (c.Symbol || "").toUpperCase().trim() === cleanSym)) ||
                      (appState.strategicWatchlist && appState.strategicWatchlist.find(c => (c.Symbol || "").toUpperCase().trim() === cleanSym)) ||
                      (appState.dailyFocusWatchlist && appState.dailyFocusWatchlist.find(c => (c.Symbol || "").toUpperCase().trim() === cleanSym)) ||
                      (appState.lowRiskTrades || []).find(c => (c.Symbol || "").toUpperCase().trim() === cleanSym) ||
                      (appState.highRiskTrades || []).find(c => (c.Symbol || "").toUpperCase().trim() === cleanSym);

    if (!candidate) {
        showToast("Candidate data not found", "error");
        return;
    }

    let name = candidate.Symbol;
    const existing = appState.tradeJournal.find(t => t.symbol.toUpperCase() === cleanSym);
    if (existing) {
        name = existing.name;
    }

    openTradeModal();
    
    document.getElementById("modal-title").textContent = "Add Trade from Candidate";
    document.getElementById("trade-symbol").value = candidate.Symbol;
    document.getElementById("trade-name").value = name;
    
    // Check if there is an active paper trade to copy actual targets/stop loss from
    const openPaperTrade = appState.truePaperOpenTrades && appState.truePaperOpenTrades.find(t => t.symbol.toUpperCase() === cleanSym);
    
    let entryPrice = 0;
    let stopLoss = 0;
    let target1 = "";
    let target2 = "";
    
    if (openPaperTrade) {
        entryPrice = openPaperTrade.entry_price || openPaperTrade.trigger_price || 0;
        stopLoss = openPaperTrade.stop_loss || 0;
        target1 = openPaperTrade.t1 || "";
        target2 = openPaperTrade.t2 || "";
        console.log("Matched open paper trade for targets sync:", openPaperTrade);
    } else {
        entryPrice = candidate.Trigger || candidate.Entry || candidate.Entry_Price || candidate.CMP || 0;
        stopLoss = candidate.Stop_Loss || candidate.stop_loss || 0;
        target1 = candidate.Target_1 || candidate.target_1 || candidate.Target1 || "";
        target2 = candidate.Target_2 || candidate.target_2 || candidate.Target2 || "";
    }
    
    document.getElementById("trade-entry-price").value = entryPrice || "";
    document.getElementById("trade-sl").value = stopLoss || "";
    document.getElementById("trade-t1").value = target1 || "";
    document.getElementById("trade-t2").value = target2 || "";

    

    let riskPct = candidate.Risk_Pct || "";

    if (!riskPct && entryPrice > 0 && stopLoss > 0) {

        riskPct = (((entryPrice - stopLoss) / entryPrice) * 100).toFixed(2);

    }

    document.getElementById("trade-risk-pct").value = riskPct;

    

    // Format professional setup description

    const rawPattern = candidate.Engine_Type || candidate.Setup_Type || candidate.Pattern || "VCP";

    const pattern = rawPattern.replace("_SETUP", "").replace("_VCP", "").replace("_FLAG", "") + " Setup";

    const grade = candidate.Grade || candidate.Setup_Grade || "Grade C";

    const contractions = candidate.Contractions || "None";

    const delivery = (candidate.Delivery_Pct !== undefined && candidate.Delivery_Pct !== null) ? `${candidate.Delivery_Pct}%` : "N/A";

    const vdu = candidate.VDU_Pct || "N/A";

    const msScore = candidate.MS_Score || candidate.Score || 0;

    const readScore = candidate.Execution_Readiness_Score || 0;

    const posSize = candidate.Position_Size_Recommendation || "6.0% Allocation";

    const pocketPivot = (candidate.Pocket_Pivot === 1 || candidate.Pocket_Pivot === "1" || candidate.Pocket_Pivot === true) ? "Yes" : "No";

    

    let breakDownStr = "";

    if (candidate.MS_Breakdown) {

        breakDownStr = ` (Trend: ${candidate.MS_Breakdown.Trend || 0}, RS: ${candidate.MS_Breakdown.RS || 0}, SmartMoney: ${candidate.MS_Breakdown.SmartMoney || 0})`;

    } else if (candidate.Trend_Quality !== undefined) {

        breakDownStr = ` (Trend: ${candidate.Trend_Quality || 0}, RS: ${candidate.Relative_Strength || 0}, SmartMoney: ${candidate.Smart_Money_Score || 0})`;

    }

    

    const ind = candidate.Industry || "Others";

    const indCat = candidate.Industry_Category || "Neutral";

    const indRank = candidate.Industry_Rank || "N/A";

    const indStr = `${ind} [Rank ${indRank}, ${indCat}]`;

    

    const desc = `Pattern: ${pattern} (${grade})
Minervini Score: ${msScore}/100${breakDownStr}
Contractions: ${contractions}
Volume Dry Up (VDU): ${vdu}
Delivery %: ${delivery}
Pocket Pivot: ${pocketPivot}
Industry Strength: ${indStr}
Execution Readiness: ${readScore}/100 (Recommended Size: ${posSize})`;

    document.getElementById("trade-tech-desc").value = desc;

    

    const journalNavBtn = document.querySelector(".nav-btn[data-tab='trade_journal']");

    if (journalNavBtn) {

        journalNavBtn.click();

    }

}

window.openTradeModal = openTradeModal;

window.closeTradeModal = closeTradeModal;

window.addCandidateToJournal = addCandidateToJournal;

function renderTickerDrawer(data) {

    const drawer = document.getElementById("ticker-detail-drawer");

    if (!drawer) return;

    // Set fields

    document.getElementById("drawer-symbol").textContent = data.Symbol;

    document.getElementById("drawer-company-name").textContent = data.Company_Name || "N/A";

    

    // Industry Badge

    const indBadge = document.getElementById("drawer-industry-badge");

    if (indBadge) {

        indBadge.textContent = data.Industry || "Others";

        indBadge.className = `industry-badge ${(data.Industry_Category || 'Neutral').toLowerCase()}`;

    }

    

    // Setup Badge

    const setupBadge = document.getElementById("drawer-setup-badge");

    if (setupBadge) {

        setupBadge.textContent = (data.Setup_Type || "VCP").replace("_VCP", "").replace("_SETUP", "").replace("_FLAG", "");

        setupBadge.className = `setup-type-label ${data.Setup_Type === 'INSIDE_BAR_FLAG' ? 'ib' : (data.Setup_Type === 'FLAG_SETUP' ? 'flag' : 'vcp')}`;

    }

    

    // Grade Badge

    const gradeBadge = document.getElementById("drawer-grade-badge");

    if (gradeBadge) {

        gradeBadge.textContent = data.Setup_Grade || "Grade C";

    }

    // RS

    const rsEl = document.getElementById("drawer-rs");

    if (rsEl) {

        rsEl.textContent = `${data.Relative_Strength || 0}/10`;

    }

    // Distance High

    const distEl = document.getElementById("drawer-dist-high");

    if (distEl) {

        distEl.textContent = data.Distance || "0.0%";

    }

    // Trend Stacked

    const trendEl = document.getElementById("drawer-trend-stacked");

    if (trendEl) {

        const stacked = data.Trend_Quality >= 15;

        trendEl.innerHTML = stacked ? `<span style="color: var(--accent-green);">YES ✅</span>` : `<span style="color: var(--accent-orange);">NO ⚠️</span>`;

    }

    // Volume Dry-up

    const vduEl = document.getElementById("drawer-vdu");

    if (vduEl) {

        const isVdu = data.Volume_Dry_Up_Status === "VDU Confirmed" || (data.MS_Breakdown && data.MS_Breakdown.SmartMoney >= 10);

        vduEl.innerHTML = isVdu ? `<span style="color: var(--accent-green);">VDU ✅</span>` : `<span style="color: var(--text-muted);">NORMAL</span>`;

    }

    // Execution values

    const cmpVal = data.CMP || 0;

    const triggerVal = data.Entry || 0;

    const stopVal = data.Stop_Loss || 0;

    const riskPct = data.Risk_Pct || 0;

    document.getElementById("drawer-cmp").textContent = `₹${cmpVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    document.getElementById("drawer-trigger").textContent = `₹${triggerVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    document.getElementById("drawer-stop").textContent = `₹${stopVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    

    const riskEl = document.getElementById("drawer-risk");

    if (riskEl) {

        riskEl.textContent = `${riskPct.toFixed(1)}%`;

        riskEl.className = `table-risk ${riskPct <= 8 ? 'low' : 'high'}`;

    }

    // Next Earnings Date

    const earningsEl = document.getElementById("drawer-earnings");

    if (earningsEl) {

        if (data.Earnings_Date && data.Earnings_Date !== "N/A") {

            const days = data.Days_To_Earnings;

            let daysText = "";

            if (days !== undefined && days !== null) {

                daysText = days < 0 ? " (Past)" : ` (${days} days left)`;

            }

            earningsEl.textContent = `${data.Earnings_Date}${daysText}`;

        } else {

            earningsEl.textContent = "N/A";

        }

    }

    // Add to journal action button click handler

    const journalBtn = document.getElementById("drawer-add-journal-btn");

    if (journalBtn) {

        // Clone button to strip old event listeners

        const newBtn = journalBtn.cloneNode(true);

        journalBtn.parentNode.replaceChild(newBtn, journalBtn);

        newBtn.addEventListener("click", () => {

            if (typeof addCandidateToJournal === "function") {

                addCandidateToJournal(data.Symbol);

            }

        });

    }

    // Add slide-out drawer active class

    drawer.classList.add("active");

}

function showAMSDetail(symbol) {

    if (!symbol) return;

    

    fetch(`/api/stock_detail?symbol=${symbol}`)

        .then(response => {

            if (!response.ok) throw new Error("Stock detail fetch failed");

            return response.json();

        })

        .then(data => {

            renderTickerDrawer(data);

        })

        .catch(err => {

            console.error("Error loading stock detail:", err);

            showToast(`Could not load details for ${symbol}`, "error");

        });

}

function renderAMSDetailCard(data) {

    document.getElementById("ams-modal-symbol").textContent = data.Symbol;

    

    // Priority badge based on score

    let priority = "P3";

    if (data.MS_Score >= 90) priority = "P1";

    else if (data.MS_Score >= 80) priority = "P2";

    elements.amsModalPriority.textContent = priority;

    elements.amsModalPriority.style.background = priority === "P1" ? "rgba(16, 185, 129, 0.15)" : (priority === "P2" ? "rgba(245, 158, 11, 0.15)" : "rgba(139, 92, 246, 0.15)");

    elements.amsModalPriority.style.color = priority === "P1" ? "var(--accent-green)" : (priority === "P2" ? "var(--accent-orange)" : "var(--accent-purple)");

    elements.amsModalPriority.style.borderColor = priority === "P1" ? "rgba(16, 185, 129, 0.3)" : (priority === "P2" ? "rgba(245, 158, 11, 0.3)" : "rgba(139, 92, 246, 0.3)");

    // Industry and Company

    elements.amsModalIndustry.textContent = data.Industry + (data.Industry_Rank !== "N/A" ? ` (Rank ${data.Industry_Rank})` : "");

    elements.amsModalCompany.textContent = data.Company_Name;

    elements.amsModalScore.textContent = data.MS_Score;

    

    // Score color

    let scoreColor = "var(--accent-green)";

    if (data.MS_Score < 60) scoreColor = "var(--accent-red)";

    else if (data.MS_Score < 80) scoreColor = "var(--accent-orange)";

    elements.amsModalScore.style.color = scoreColor;

    

    // Setup tags container

    const container = elements.amsModalTagsContainer;

    container.innerHTML = "";

    

    // 1. Setup tag (e.g. LVP, VCP, FLAG)

    const lvpTag = document.createElement("span");

    lvpTag.textContent = data.Setup_Type === "FLAG_SETUP" ? "FLAG" : (data.Setup_Type === "VCP" ? "VCP" : (data.Setup_Type === "INSIDE_BAR_FLAG" ? "INSIDE BAR" : "LVP"));

    lvpTag.style = "font-size: 10px; font-weight: bold; background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); padding: 2px 6px; border-radius: 4px; font-family: monospace;";

    container.appendChild(lvpTag);

    

    // 2. Industry category tag (SW = Sector Waking Up / Running Hot / The Sweet Spot)

    if (data.Industry_Category) {

        const catTag = document.createElement("span");

        const isHot = ["Confirmed Uptrend", "Early Uptrend", "Running Hot", "The Sweet Spot", "Sector Waking Up"].includes(data.Industry_Category);
        catTag.textContent = isHot ? "SW" : "NEUTRAL";

        catTag.style = `font-size: 10px; font-weight: bold; background: ${isHot ? "rgba(6, 182, 212, 0.15)" : "rgba(255,255,255,0.05)"}; color: ${isHot ? "#06b6d4" : "var(--text-secondary)"}; border: 1px solid ${isHot ? "rgba(6, 182, 212, 0.3)" : "var(--border-color)"}; padding: 2px 6px; border-radius: 4px; font-family: monospace;`;

        container.appendChild(catTag);

    }

    

    // 3. Volatility contraction index (NR13 or similar)

    const nrTag = document.createElement("span");

    const nrVal = Math.max(10, Math.min(15, Math.floor(data.MS_Breakdown.VCP / 1.1) || 13));

    nrTag.textContent = `NR${nrVal}`;

    nrTag.style = "font-size: 10px; font-weight: bold; background: rgba(139, 92, 246, 0.15); color: var(--accent-purple); border: 1px solid rgba(139, 92, 246, 0.3); padding: 2px 6px; border-radius: 4px; font-family: monospace;";

    container.appendChild(nrTag);

    

    // 4. SMA slope status (50↑ if CMP > 50 SMA)

    const slopeTag = document.createElement("span");

    slopeTag.textContent = "50↑";

    slopeTag.style = "font-size: 10px; font-weight: bold; background: rgba(16, 185, 129, 0.1); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.2); padding: 2px 6px; border-radius: 4px; font-family: monospace;";

    container.appendChild(slopeTag);

    

    // 5. Relative Strength tag

    const rsTag = document.createElement("span");

    const rsPct = Math.round(data.MS_Breakdown.RS * 9.5);

    rsTag.textContent = `RS+${rsPct}%`;

    rsTag.style = "font-size: 10px; font-weight: bold; background: rgba(245, 158, 11, 0.15); color: var(--accent-orange); border: 1px solid rgba(245, 158, 11, 0.3); padding: 2px 6px; border-radius: 4px; font-family: monospace;";

    container.appendChild(rsTag);

    

    // 6. Accumulation count

    const accTag = document.createElement("span");

    accTag.textContent = `Acc${data.Acc_Up || 4}/${data.Acc_Down || 2}`;

    accTag.style = "font-size: 10px; font-weight: bold; background: rgba(16, 185, 129, 0.1); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.2); padding: 2px 6px; border-radius: 4px; font-family: monospace;";

    container.appendChild(accTag);

    

    // Core pricing values

    elements.amsModalEntryVal.textContent = `₹${data.Trigger_Price.toFixed(2)}`;

    elements.amsModalSlVal.textContent = `₹${data.Stop_Loss.toFixed(2)}`;

    elements.amsModalRiskVal.textContent = `${data.Risk_Pct.toFixed(2)}%`;

    

    // Allocation Sizing Calculation

    let seedCapVal = 1000000;

    if (elements.finSeedCapital) {

        const txt = elements.finSeedCapital.textContent.replace(/[^0-9.]/g, "");

        if (txt) {

            seedCapVal = parseFloat(txt);

            if (elements.finSeedCapital.textContent.includes("L")) seedCapVal *= 100000;

            else if (elements.finSeedCapital.textContent.includes("Cr")) seedCapVal *= 10000000;

            else if (seedCapVal < 10000) seedCapVal *= 1000; // fallback multiplier

        }

    }

    const standardPositionSize = seedCapVal * 0.05; // 5% allocation standard

    const shareCount = Math.floor(standardPositionSize / data.Trigger_Price) || 1;

    const actualAllocation = shareCount * data.Trigger_Price;

    let allocationStr = "";

    if (actualAllocation >= 10000000) allocationStr = `₹${(actualAllocation / 10000000).toFixed(2)}Cr`;

    else if (actualAllocation >= 100000) allocationStr = `₹${(actualAllocation / 100000).toFixed(1)}L`;

    else allocationStr = `₹${(actualAllocation / 1000).toFixed(1)}K`;

    

    elements.amsModalAllocationText.textContent = `${allocationStr} • ${shareCount} shares (5% standard sizing)`;

    

    // TradingView link

    elements.amsModalChartBtn.href = `https://in.tradingview.com/chart/?symbol=NSE:${data.Symbol}`;

    

    // Add position button click binding

    elements.amsModalAddPositionBtn.onclick = () => {

        document.getElementById("ams-modal").style.display = "none";

        

        const inCandidates = appState.vcpCandidates.find(c => c.Symbol.toUpperCase() === data.Symbol.toUpperCase()) || 

                             appState.flag_candidates.find(c => c.Symbol.toUpperCase() === data.Symbol.toUpperCase());

        

        if (inCandidates) {

            addCandidateToJournal(data.Symbol);

        } else {

            openTradeModal();

            document.getElementById("modal-title").textContent = "Add Trade from Detail Analysis";

            document.getElementById("trade-symbol").value = data.Symbol;

            document.getElementById("trade-name").value = data.Company_Name;

            document.getElementById("trade-entry-price").value = data.Trigger_Price.toFixed(2);

            document.getElementById("trade-sl").value = data.Stop_Loss.toFixed(2);

            document.getElementById("trade-t1").value = data.Target_1.toFixed(2);

            document.getElementById("trade-t2").value = data.Target_2.toFixed(2);

            document.getElementById("trade-risk-pct").value = data.Risk_Pct.toFixed(2);

            

            const desc = `${data.Setup_Type} Setup (${data.Grade}). Pullback: ${data.Pullback_Pct.toFixed(1)}%. Vol Dry Up: ${data.VDU_Pct_Str}.`;

            document.getElementById("trade-tech-desc").value = desc;

            

            const journalNavBtn = document.querySelector(".nav-btn[data-tab='trade_journal']");

            if (journalNavBtn) {

                journalNavBtn.click();

            }

        }

    };

    

    // Pullback Badge and Desc

    const pbBadge = elements.amsModalPullbackBadge;

    const pbVal = data.Pullback_Pct;

    pbBadge.textContent = `${pbVal.toFixed(1)}%`;

    pbBadge.style.background = pbVal <= -10.0 ? "rgba(239, 68, 68, 0.15)" : (pbVal <= -3.0 ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)");

    pbBadge.style.color = pbVal <= -10.0 ? "var(--accent-red)" : (pbVal <= -3.0 ? "var(--accent-green)" : "var(--accent-orange)");

    pbBadge.style.borderColor = pbVal <= -10.0 ? "rgba(239, 68, 68, 0.3)" : (pbVal <= -3.0 ? "rgba(16, 185, 129, 0.3)" : "rgba(245, 158, 11, 0.3)");

    elements.amsModalPullbackDesc.textContent = `${data.Pullback_Lbl} (<= -3% = E +7.5%)`;

    

    // Avg Vol 5D Badge and Desc

    const avBadge = elements.amsModalAvgVolBadge;

    const avVal = data.Avg_Vol_5D;

    avBadge.textContent = `${avVal.toFixed(2)}x`;

    avBadge.style.background = avVal <= 0.85 ? "rgba(16, 185, 129, 0.15)" : (avVal <= 1.15 ? "rgba(245, 158, 11, 0.15)" : "rgba(239, 68, 68, 0.15)");

    avBadge.style.color = avVal <= 0.85 ? "var(--accent-green)" : (avVal <= 1.15 ? "var(--accent-orange)" : "var(--accent-red)");

    avBadge.style.borderColor = avVal <= 0.85 ? "rgba(16, 185, 129, 0.3)" : (avVal <= 1.15 ? "rgba(245, 158, 11, 0.3)" : "rgba(239, 68, 68, 0.3)");

    elements.amsModalAvgVolDesc.textContent = `${data.Avg_Vol_Lbl} (E +1.8%)`;

    

    // SMA20 Dist Badge and Desc

    const sdBadge = elements.amsModalSmaDistBadge;

    const sdVal = data.SMA20_Dist_Pct;

    sdBadge.textContent = `${sdVal >= 0 ? "+" : ""}${sdVal.toFixed(1)}%`;

    sdBadge.style.background = sdVal > 5.0 ? "rgba(245, 158, 11, 0.15)" : (sdVal < -2.0 ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)");

    sdBadge.style.color = sdVal > 5.0 ? "var(--accent-orange)" : (sdVal < -2.0 ? "var(--accent-red)" : "var(--accent-green)");

    sdBadge.style.borderColor = sdVal > 5.0 ? "rgba(245, 158, 11, 0.3)" : (sdVal < -2.0 ? "rgba(239, 68, 68, 0.3)" : "rgba(16, 185, 129, 0.3)");

    elements.amsModalSmaDistDesc.textContent = `${data.SMA20_Dist_Lbl} (WR 58%)`;

    

    // Day RVOL Badge and Desc

    const rvBadge = elements.amsModalRvolBadge;

    const rvVal = data.Day_RVOL;

    rvBadge.textContent = `${rvVal.toFixed(2)}x`;

    rvBadge.style.background = rvVal <= 0.50 ? "rgba(16, 185, 129, 0.15)" : (rvVal <= 1.0 ? "rgba(245, 158, 11, 0.15)" : "rgba(239, 68, 68, 0.15)");

    rvBadge.style.color = rvVal <= 0.50 ? "var(--accent-green)" : (rvVal <= 1.0 ? "var(--accent-orange)" : "var(--accent-red)");

    rvBadge.style.borderColor = rvVal <= 0.50 ? "rgba(16, 185, 129, 0.3)" : (rvVal <= 1.0 ? "rgba(245, 158, 11, 0.3)" : "rgba(239, 68, 68, 0.3)");

    elements.amsModalRvolDesc.textContent = `${data.Day_RVOL_Lbl} (E +4.8%)`;

    

    // Recommendation text

    elements.amsModalAlgoDesc.textContent = `${data.Setup_Type} Grade ${data.Grade} setup coiling in ${data.Industry} (${data.Volume_Dry_Up_Status}).`;

    

    // Show Modal overlay

    document.getElementById("ams-modal").style.display = "flex";

}

window.showAMSDetail = showAMSDetail;

// Collapsible Trade Cards toggle

function toggleJournalCard(id) {

    const card = document.getElementById(`j-card-${id}`);

    if (card) {

        card.classList.toggle("expanded");

    }

}

window.toggleJournalCard = toggleJournalCard;

// Quick Close Trade Outcome Handler (Tick / Cross)

async function quickCloseTrade(tradeId, isWin) {

    const t = appState.tradeJournal.find(item => item.id === tradeId.toString());

    if (!t) return;

    

    const todayStr = new Date().toISOString().split('T')[0];

    const qty = t.open_qty;

    

    // Calculate exit price: target 1 for win, stop loss for loss (with defaults)

    let exitPrice = 0;

    if (isWin) {

        exitPrice = t.target_1 || (t.entry_price * 1.10); // 10% gain default

    } else {

        exitPrice = t.stop_loss || (t.entry_price * 0.95); // 5% loss default

    }

    

    const pnl = (exitPrice - t.entry_price) * qty;

    

    if (!t.exits) t.exits = [];

    t.exits.push({

        date: todayStr,

        qty: qty,

        price: exitPrice,

        pnl: pnl

    });

    

    t.open_qty = 0;

    t.status = "CLOSED";

    t.exit_date = todayStr;

    

    try {

        const response = await fetch("/api/trade_journal", {

            method: "POST",

            headers: { "Content-Type": "application/json" },

            body: JSON.stringify(appState.tradeJournal)

        });

        

        if (response.ok) {

            showToast(`Trade closed as ${isWin ? 'WIN' : 'LOSS'} successfully!`, "success");

            await loadTradeJournalData();

        } else {

            showToast("Failed to save exit to server.", "error");

        }

    } catch (err) {

        console.error("Quick close trade error:", err);

        showToast("Error saving exit: " + err.message, "error");

    }

}

window.quickCloseTrade = quickCloseTrade;

// Chart.js Instances

let equityChartInstance = null;

let winLossChartInstance = null;

function renderJournalCharts() {

    const equityCtx = document.getElementById("equity-curve-chart")?.getContext("2d");

    const winLossCtx = document.getElementById("win-loss-chart")?.getContext("2d");

    if (!equityCtx || !winLossCtx) return;

    

    if (equityChartInstance) equityChartInstance.destroy();

    if (winLossChartInstance) winLossChartInstance.destroy();

    

    const exits = [];

    appState.tradeJournal.forEach(t => {

        t.exits.forEach(e => {

            if (e.date) {

                exits.push({ date: e.date, pnl: e.pnl });

            }

        });

    });

    

    exits.sort((a, b) => new Date(a.date) - new Date(b.date));

    

    const dates = [];

    const pnlValues = [];

    let cumulative = 0;

    

    dates.push("Start");

    pnlValues.push(0);

    

    exits.forEach(e => {

        cumulative += e.pnl;

        const dt = new Date(e.date);

        const dateStr = dt.toLocaleDateString("en-US", { month: "short", day: "numeric" });

        dates.push(dateStr);

        pnlValues.push(cumulative);

    });

    

    equityChartInstance = new Chart(equityCtx, {

        type: 'line',

        data: {

            labels: dates,

            datasets: [{

                label: 'Cumulative Realized P&L',

                data: pnlValues,

                borderColor: '#8b5cf6',

                backgroundColor: 'rgba(139, 92, 246, 0.05)',

                borderWidth: 2.5,

                tension: 0.3,

                fill: true,

                pointBackgroundColor: '#8b5cf6',

                pointRadius: pnlValues.length > 15 ? 1 : 3

            }]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {

                legend: { display: false },

                tooltip: {

                    callbacks: {

                        label: function(context) {

                            return ' P&L: ' + (context.parsed.y >= 0 ? '+' : '') + '₹' + context.parsed.y.toLocaleString('en-IN');

                        }

                    }

                }

            },

            scales: {

                x: {

                    grid: { display: false },

                    ticks: { color: '#9ca3af', font: { family: 'Outfit', size: 10 } }

                },

                y: {

                    grid: { color: 'rgba(255, 255, 255, 0.03)' },

                    ticks: {

                        color: '#9ca3af',

                        font: { family: 'Outfit', size: 10 },

                        callback: function(value) {

                            return (value >= 0 ? '+' : '') + '₹' + value.toLocaleString('en-IN', { maximumFractionDigits: 0 });

                        }

                    }

                }

            }

        }

    });

    

    let closedCount = 0;

    let winCount = 0;

    let lossCount = 0;

    

    appState.tradeJournal.forEach(t => {

        if (t.status === "CLOSED") {

            closedCount++;

            const tradeNetPnl = t.exits.reduce((acc, e) => acc + e.pnl, 0);

            if (tradeNetPnl > 0) winCount++;

            else if (tradeNetPnl < 0) lossCount++;

        }

    });

    

    winLossChartInstance = new Chart(winLossCtx, {

        type: 'doughnut',

        data: {

            labels: ['Wins', 'Losses'],

            datasets: [{

                data: [winCount, lossCount],

                backgroundColor: ['#10b981', '#ef4444'],

                borderWidth: 0,

                hoverOffset: 4

            }]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            cutout: '70%',

            plugins: {

                legend: {

                    position: 'bottom',

                    labels: {

                        color: '#f3f4f6',

                        font: { family: 'Outfit', size: 11 },

                        padding: 10

                    }

                },

                tooltip: {

                    callbacks: {

                        label: function(context) {

                            const val = context.parsed;

                            const total = winCount + lossCount;

                            const pct = total > 0 ? ((val / total) * 100).toFixed(0) : 0;

                            return ` ${context.label}: ${val} (${pct}%)`;

                        }

                    }

                }

            }

        }

    });

}

// AI Chat Assistant Logic

function setupChatEventHandlers() {

    const sendBtn = document.getElementById("chat-send-btn");

    const inputField = document.getElementById("chat-input-field");

    

    if (sendBtn && inputField) {

        const sendMessage = async () => {

            const text = inputField.value.trim();

            if (!text) return;

            

            // Append user message

            appendChatMessage(text, true);

            inputField.value = "";

            

            // Append loading indicator

            const loadingBubble = appendChatMessage('<i class="fa-solid fa-spinner fa-spin"></i> Assistant is analyzing...', false);

            

            try {

                const response = await fetch("/api/chat", {

                    method: "POST",

                    headers: { "Content-Type": "application/json" },

                    body: JSON.stringify({ message: text })

                });

                

                if (!response.ok) throw new Error("HTTP " + response.status);

                

                const data = await response.json();

                

                // Remove loading bubble

                loadingBubble.remove();

                

                // Append assistant message

                appendChatMessage(data.response, false);

            } catch (err) {

                console.error("Chat API error:", err);

                loadingBubble.remove();

                appendChatMessage("I encountered an error connecting to the Minervini OS backend. Please check if the server is running.", false);

            }

        };

        

        sendBtn.addEventListener("click", sendMessage);

        inputField.addEventListener("keydown", (e) => {

            if (e.key === "Enter") {

                sendMessage();

            }

        });

    }

    // API key status and save handlers

    const keyStatusEl = document.getElementById("api-key-status");

    const keyInputEl = document.getElementById("api-key-input");

    const saveKeyBtn = document.getElementById("save-key-btn");

    

    const checkApiKeyStatus = async () => {

        if (!keyStatusEl) return;

        try {

            const res = await fetch("/api/config/gemini_key");

            if (res.ok) {

                const data = await res.json();

                if (data.set) {

                    keyStatusEl.textContent = "Enabled (Active)";

                    keyStatusEl.style.color = "var(--accent-green)";

                    if (keyInputEl) {

                        keyInputEl.placeholder = "••••••••••••••••";

                        keyInputEl.value = "";

                    }

                    if (saveKeyBtn) {

                        saveKeyBtn.textContent = "Update";

                    }

                } else {

                    keyStatusEl.textContent = "Not Set (Fallback Mode)";

                    keyStatusEl.style.color = "var(--accent-red)";

                    if (keyInputEl) {

                        keyInputEl.placeholder = "Paste Gemini API key...";

                    }

                    if (saveKeyBtn) {

                        saveKeyBtn.textContent = "Enable";

                    }

                }

            }

        } catch (err) {

            console.error("Error checking API key status:", err);

        }

    };

    

    if (saveKeyBtn && keyInputEl) {

        saveKeyBtn.addEventListener("click", async () => {

            const newKey = keyInputEl.value.trim();

            if (!newKey) {

                alert("Please enter a valid API key.");

                return;

            }

            

            saveKeyBtn.disabled = true;

            saveKeyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

            

            try {

                const res = await fetch("/api/config/gemini_key", {

                    method: "POST",

                    headers: { "Content-Type": "application/json" },

                    body: JSON.stringify({ api_key: newKey })

                });

                

                if (res.ok) {

                    const data = await res.json();

                    if (data.status === "success") {

                        alert("Gemini API Key updated successfully! Global AI intelligence is now active.");

                        keyInputEl.value = "";

                        await checkApiKeyStatus();

                    } else {

                        throw new Error(data.message || "Failed to update key");

                    }

                } else {

                    throw new Error("HTTP " + res.status);

                }

            } catch (err) {

                console.error("Error saving API key:", err);

                alert("Error saving API key: " + err.message);

            } finally {

                saveKeyBtn.disabled = false;

                saveKeyBtn.textContent = "Update";

            }

        });

    }

    

    // Check key status immediately

    checkApiKeyStatus();

}

function appendChatMessage(text, isUser) {

    const container = document.getElementById("chat-messages");

    if (!container) return null;

    

    const msg = document.createElement("div");

    msg.className = `chat-message ${isUser ? 'user' : 'assistant'}`;

    

    const avatarIcon = isUser ? 'fa-user' : 'fa-robot';

    const content = isUser ? escapeHtml(text) : formatMarkdown(text);

    

    msg.innerHTML = `

        <div class="avatar"><i class="fa-solid ${avatarIcon}"></i></div>

        <div class="message-bubble glass">${content}</div>

    `;

    

    container.appendChild(msg);

    container.scrollTop = container.scrollHeight;

    

    return msg;

}

function escapeHtml(text) {

    const div = document.createElement('div');

    div.textContent = text;

    return div.innerHTML;

}

function formatMarkdown(text) {

    if (!text) return "";

    

    // Replace escape double-newlines first

    let html = text.replace(/\\n/g, '\n');

    

    // Replace headers

    html = html.replace(/^### (.*$)/gim, '<h4 style="margin: 12px 0 6px 0; font-weight: 700; font-size: 14px; color: var(--accent-purple);">$1</h4>');

    html = html.replace(/^## (.*$)/gim, '<h3 style="margin: 16px 0 8px 0; font-weight: 700; font-size: 16px; color: var(--accent-blue);">$1</h3>');

    html = html.replace(/^# (.*$)/gim, '<h2 style="margin: 20px 0 10px 0; font-weight: 800; font-size: 18px; color: var(--text-primary);">$1</h2>');

    

    // Replace bold

    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    

    // Replace bullets

    html = html.replace(/^\s*-\s*(.*$)/gim, '<li style="margin-left: 16px; list-style-type: disc; margin-bottom: 4px;">$1</li>');

    

    // Parse tables

    const lines = html.split('\n');

    let inTable = false;

    let tableHtml = '<table style="width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 12px; border: 1px solid var(--border-color);">';

    let newLines = [];

    

    for (let line of lines) {

        if (line.trim().startsWith('|') && line.includes('---')) {

            continue;

        } else if (line.trim().startsWith('|')) {

            if (!inTable) {

                inTable = true;

            }

            const parts = line.split('|').map(p => p.trim()).filter((p, i, arr) => i > 0 && i < arr.length - 1);

            const isHeader = line.includes('Symbol') || line.includes('Invested') || line.includes('Entry Price');

            const tag = isHeader ? 'th' : 'td';

            const rowStyle = isHeader ? 'background: rgba(139, 92, 246, 0.08); font-weight: 700; border-bottom: 1px solid var(--border-color);' : 'border-bottom: 1px solid rgba(255,255,255,0.03);';

            let rowHtml = `<tr style="${rowStyle}">`;

            for (let part of parts) {

                rowHtml += `<${tag} style="padding: 6px 10px; text-align: left; border-right: 1px solid rgba(255,255,255,0.03);">${part}</${tag}>`;

            }

            rowHtml += '</tr>';

            tableHtml += rowHtml;

        } else {

            if (inTable) {

                inTable = false;

                tableHtml += '</table>';

                newLines.push(tableHtml);

                tableHtml = '<table style="width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 12px; border: 1px solid var(--border-color);">';

            }

            newLines.push(line);

        }

    }

    if (inTable) {

        tableHtml += '</table>';

        newLines.push(tableHtml);

    }

    html = newLines.join('\n');

    

    // Replace newlines with breaks

    html = html.replace(/\n\n/g, '<br><br>');

    html = html.replace(/\n/g, '<br>');

    

    return html;

}

let disciplineHistoryChart = null;

async function renderRiskManagerTab() {

    // 1. Calculate Active Violations and Capital Metrics

    let disciplineScore = 100;

    let capitalExposed = 0; // Sum of entry_price * open_qty for stop_loss <= 0

    let excessBreachDamage = 0; // Sum of (stop_loss - CMP) * open_qty for CMP <= stop_loss

    

    const grouped = {};

    const openTrades = appState.tradeJournal.filter(t => t.status === "OPEN");

    

    openTrades.forEach(t => {

        const violations = calculateTradeViolations(t);

        if (violations.length === 0) return;

        

        // Find CMP

        let cmp = null;
        let sym = t.symbol.toUpperCase();
        if (sym === "GANESH BENZO" || sym === "GANESH_BENZO") sym = "GANESHBE";

        if (appState.activePortfolio) {

            const pStock = appState.activePortfolio.find(p => p.Symbol.toUpperCase() === sym);

            if (pStock && pStock.CMP) cmp = pStock.CMP;

        }

        if (!cmp) {

            const wlStock = ((appState.vcpCandidates || []).concat(appState.flag_candidates || [])).find(w => w.Symbol.toUpperCase() === sym);

            if (wlStock && wlStock.CMP) cmp = wlStock.CMP;

        }

        if (!cmp) cmp = t.entry_price;

        

        const posValue = t.entry_price * t.open_qty;

        const cmpValue = cmp * t.open_qty;

        

        // Capital Exposed (No stop loss)

        if (!t.stop_loss || t.stop_loss <= 0) {

            capitalExposed += posValue;

        }

        

        // Excess Breach Damage

        if (t.stop_loss && cmp && cmp <= t.stop_loss) {

            excessBreachDamage += (t.stop_loss - cmp) * t.open_qty;

        }

        

        if (!grouped[t.symbol]) {

            grouped[t.symbol] = {

                symbol: t.symbol,

                violations: [],

                totalPenalty: 0,

                capitalImpacts: [],

                trade: t,

                cmp: cmp

            };

        }

        

        violations.forEach(v => {

            let penalty = 0;

            if (v.rule.includes("RULE 4") && v.desc.includes("breached")) {

                penalty = 20;

                const damage = (t.stop_loss - cmp) * t.open_qty;

                grouped[t.symbol].capitalImpacts.push(`Exiting at stop loss (₹${t.stop_loss.toFixed(2)}) would have saved <strong>₹${damage.toLocaleString('en-IN', {maximumFractionDigits:0})}</strong>.`);

            } else if (v.rule.includes("RULE 4") && v.desc.includes("suicide")) {

                penalty = 15;

                const fivePctRisk = posValue * 0.05;

                grouped[t.symbol].capitalImpacts.push(`Setting a standard 5% stop loss caps capital risk at <strong>₹${fivePctRisk.toLocaleString('en-IN', {maximumFractionDigits:0})}</strong> instead of ₹${posValue.toLocaleString('en-IN', {maximumFractionDigits:0})} (100% exposed).`);

            } else if (v.rule.includes("RULE #0")) {

                penalty = 20;

            } else if (v.rule.includes("RULE 5")) {

                penalty = 10;

                const avgDownTrapped = posValue * 0.3; // estimate portion Trapped

                grouped[t.symbol].capitalImpacts.push(`Avoiding averaging down would have kept <strong>₹${avgDownTrapped.toLocaleString('en-IN', {maximumFractionDigits:0})}</strong> free.`);

            } else if (v.rule.includes("RULE 3") || v.rule.includes("RULE 7")) {

                penalty = 10;

                grouped[t.symbol].capitalImpacts.push(`Exiting when setup failed would have freed <strong>₹${cmpValue.toLocaleString('en-IN', {maximumFractionDigits:0})}</strong> of trapped capital.`);

            } else if (v.rule.includes("RULE 1")) {

                penalty = 5;

                const actualRiskVal = (t.risk_pct / 100) * posValue;

                const cappedRiskVal = 0.08 * posValue;

                grouped[t.symbol].capitalImpacts.push(`Keeping risk to conservative 8% limit restricts maximum risk to <strong>₹${cappedRiskVal.toLocaleString('en-IN', {maximumFractionDigits:0})}</strong> instead of ₹${actualRiskVal.toLocaleString('en-IN', {maximumFractionDigits:0})}.`);

            }

            

            grouped[t.symbol].totalPenalty += penalty;

            grouped[t.symbol].violations.push({

                rule: v.rule,

                desc: v.desc,

                penalty: penalty

            });

            disciplineScore -= penalty;

        });

    });

    

    disciplineScore = Math.max(0, disciplineScore);

    

    // Update Score display

    const scoreEl = document.getElementById("risk-discipline-score");

    if (scoreEl) {

        scoreEl.textContent = `${disciplineScore}/100`;

        if (disciplineScore >= 80) scoreEl.style.color = "var(--accent-green)";

        else if (disciplineScore >= 60) scoreEl.style.color = "var(--accent-yellow)";

        else scoreEl.style.color = "var(--accent-red)";

    }

    

    // Update Capital metrics

    const capExposedEl = document.getElementById("risk-capital-exposed");

    if (capExposedEl) {

        capExposedEl.textContent = `₹${capitalExposed.toLocaleString('en-IN', {maximumFractionDigits:0})}`;

        capExposedEl.style.color = capitalExposed > 0 ? "var(--accent-red)" : "var(--text-primary)";

    }

    

    const breachDamageEl = document.getElementById("risk-breach-damage");

    if (breachDamageEl) {

        breachDamageEl.textContent = `₹${excessBreachDamage.toLocaleString('en-IN', {maximumFractionDigits:0})}`;

        breachDamageEl.style.color = excessBreachDamage > 0 ? "var(--accent-red)" : "var(--accent-green)";

    }

    

    // Render Violations list

    const listEl = document.getElementById("risk-violations-list");

    if (listEl) {

        const stocksWithViolations = Object.values(grouped);

        if (stocksWithViolations.length === 0) {

            listEl.innerHTML = `

                <div style="text-align: center; padding: 40px; color: var(--text-secondary);">

                    <i class="fa-solid fa-circle-check" style="font-size: 48px; color: var(--accent-green); margin-bottom: 12px;"></i>

                    <p style="font-size: 14px; font-weight: 600; margin: 0; color: var(--text-primary);">Pristine Process Execution</p>

                    <p style="font-size: 12px; margin: 4px 0 0 0;">Zero Trading Constitution rule violations detected in active positions.</p>

                </div>

            `;

        } else {

            let html = `

                <table style="width: 100%; border-collapse: collapse; font-size: 13px; color: var(--text-primary);">

                    <thead>

                        <tr style="border-bottom: 1px solid var(--border-color); text-align: left;">

                            <th style="padding: 12px 8px; color: var(--text-secondary); font-weight: 600; font-size: 11px; text-transform: uppercase; width: 110px;">Stock</th>

                            <th style="padding: 12px 8px; color: var(--text-secondary); font-weight: 600; font-size: 11px; text-transform: uppercase; width: 100px; text-align: center;">Total Penalty</th>

                            <th style="padding: 12px 8px; color: var(--text-secondary); font-weight: 600; font-size: 11px; text-transform: uppercase;">Violations & CRO Warning Details</th>

                            <th style="padding: 12px 8px; color: var(--text-secondary); font-weight: 600; font-size: 11px; text-transform: uppercase; text-align: right; width: 320px;">Capital Impact (If Followed)</th>

                        </tr>

                    </thead>

                    <tbody>

            `;

            

            stocksWithViolations.forEach(sv => {

                let vHtml = `<ul style="margin: 0; padding: 0 0 0 16px; display: flex; flex-direction: column; gap: 8px;">`;

                sv.violations.forEach(v => {

                    vHtml += `

                        <li style="line-height: 1.4;">

                            <strong style="color: var(--accent-red);">${v.rule}:</strong> ${v.desc}

                            <span style="color: var(--text-secondary); font-size: 11px; margin-left: 6px;">(-${v.penalty} pts)</span>

                        </li>

                    `;

                });

                vHtml += `</ul>`;

                

                let ciHtml = `<ul style="margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; text-align: right; list-style-type: none;">`;

                sv.capitalImpacts.forEach(ci => {

                    ciHtml += `<li style="line-height: 1.4; color: var(--accent-green); font-size: 12px;"><i class="fa-solid fa-circle-info" style="font-size: 11px; margin-right: 4px; color: var(--accent-purple);"></i>${ci}</li>`;

                });

                if (sv.capitalImpacts.length === 0) {

                    ciHtml += `<li style="line-height: 1.4; color: var(--text-secondary);">None (Process Warning only)</li>`;

                }

                ciHtml += `</ul>`;

                

                html += `

                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); vertical-align: top; transition: background 0.2s;">

                        <td style="padding: 16px 8px; font-weight: 700; color: var(--text-primary); font-size: 14px;">${sv.symbol}</td>

                        <td style="padding: 16px 8px; text-align: center; font-weight: 700; color: var(--accent-red); font-size: 13px;">-${sv.totalPenalty} pts</td>

                        <td style="padding: 16px 8px;">${vHtml}</td>

                        <td style="padding: 16px 8px; text-align: right;">${ciHtml}</td>

                    </tr>

                `;

            });

            

            html += `

                    </tbody>

                </table>

            `;

            listEl.innerHTML = html;

        }

    }

    

    // Fetch and Render Chart

    try {

        const response = await fetch("/api/discipline_history");

        if (!response.ok) throw new Error("HTTP " + response.status);

        const data = await response.json();

        

        // Render Chart.js

        renderDisciplineHistoryChart(data);

    } catch (err) {

        console.error("Error loading discipline history chart data:", err);

    }

}

function renderDisciplineHistoryChart(data) {

    const ctx = document.getElementById("discipline-history-chart");

    if (!ctx) return;

    

    if (disciplineHistoryChart) {

        disciplineHistoryChart.destroy();

    }

    

    const labels = data.map(d => {

        const dateObj = new Date(d.date);

        return dateObj.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'});

    });

    const scores = data.map(d => d.score);

    

    const ctx2d = ctx.getContext('2d');

    const gradient = ctx2d.createLinearGradient(0, 0, 0, 200);

    gradient.addColorStop(0, 'rgba(139, 92, 246, 0.4)');

    gradient.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

    

    disciplineHistoryChart = new Chart(ctx, {

        type: 'line',

        data: {

            labels: labels,

            datasets: [{

                label: 'Discipline Score',

                data: scores,

                borderColor: '#8b5cf6',

                borderWidth: 2,

                pointBackgroundColor: '#a78bfa',

                pointBorderColor: '#8b5cf6',

                pointRadius: 4,

                pointHoverRadius: 6,

                fill: true,

                backgroundColor: gradient,

                tension: 0.3

            }]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {

                legend: { display: false },

                tooltip: {

                    backgroundColor: 'rgba(17, 24, 39, 0.95)',

                    titleColor: '#fff',

                    bodyColor: '#a78bfa',

                    borderColor: 'rgba(255,255,255,0.1)',

                    borderWidth: 1,

                    padding: 10,

                    displayColors: false,

                    callbacks: {

                        label: function(context) {

                            return `Score: ${context.parsed.y} / 100`;

                        }

                    }

                }

            },

            scales: {

                y: {

                    min: 0,

                    max: 100,

                    grid: { color: 'rgba(255, 255, 255, 0.05)' },

                    ticks: {

                        color: 'rgba(255, 255, 255, 0.4)',

                        font: { size: 10 }

                    }

                },

                x: {

                    grid: { display: false },

                    ticks: {

                        color: 'rgba(255, 255, 255, 0.4)',

                        font: { size: 10 }

                    }

                }

            }

        }

    });

}

async function loadAndRenderEarningsCalendar() {

    const tbody = document.getElementById("earnings-calendar-body");

    const countSpan = document.getElementById("earnings-total-count");

    if (!tbody) return;

    

    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 30px; color: var(--text-secondary);"><i class="fa-solid fa-spinner fa-spin" style="margin-right: 8px;"></i>Loading earnings data...</td></tr>`;

    

    try {

        const response = await fetch("/api/earnings_calendar");

        const data = await response.json();

        

        // Also load portfolio to identify type of each symbol

        

        const journalResponse = await fetch("/api/trade_journal");

        const journalData = await journalResponse.json();

        

        const activePortfolioSymbols = new Set(

            (journalData || []).filter(t => t.status !== "CLOSED" && t.symbol).map(t => t.symbol.toUpperCase().trim())

        );

        

        const items = Object.values(data);

        if (items.length === 0) {

            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 30px; color: var(--text-secondary);">No upcoming earnings tracked.</td></tr>`;

            if (countSpan) countSpan.textContent = "0 Tracked Stocks";

            return;

        }

        

        // Sort items by Days_To_Earnings ascending (soonest first)

        items.sort((a, b) => {

            const dA = a.Days_To_Earnings !== undefined ? a.Days_To_Earnings : 9999;

            const dB = b.Days_To_Earnings !== undefined ? b.Days_To_Earnings : 9999;

            return dA - dB;

        });

        

        if (countSpan) countSpan.textContent = `${items.length} Tracked Stocks`;

        

        tbody.innerHTML = "";

        items.forEach(item => {

            const sym = item.Symbol.toUpperCase().trim();

            let typeLabel = "Watchlist Candidate";

            let typeBg = "rgba(59, 130, 246, 0.15)";

            let typeColor = "var(--accent-blue)";

            

            if (activePortfolioSymbols.has(sym)) {

                typeLabel = "Active Portfolio Position";

                typeBg = "rgba(139, 92, 246, 0.15)";

                typeColor = "var(--accent-purple)";

            }

            

            const days = item.Days_To_Earnings;

            let riskStatus = "Normal";

            let riskColor = "var(--accent-green)";

            let rowStyle = "";

            

            if (days !== undefined && days !== null) {

                if (days < 0) {

                    riskStatus = "Announced / Past";

                    riskColor = "var(--text-muted)";

                } else if (days <= 3) {

                    riskStatus = "⚠️ IMMEDIATE BINARY RISK (NEVER BUY)";

                    riskColor = "var(--accent-red)";

                    rowStyle = "background: rgba(239, 68, 68, 0.05);";

                } else if (days <= 7) {

                    riskStatus = "⚠️ High Alert (Close to Earnings)";

                    riskColor = "var(--accent-orange)";

                    rowStyle = "background: rgba(245, 158, 11, 0.03);";

                } else if (days <= 14) {

                    riskStatus = "Upcoming (Monitor)";

                    riskColor = "var(--accent-blue)";

                }

            }

            

            const tr = document.createElement("tr");

            if (rowStyle) tr.setAttribute("style", rowStyle);

            tr.style.borderBottom = "1px solid var(--border-color)";

            tr.style.height = "42px";

            

            tr.innerHTML = `

                <td style="padding: 10px 12px; font-weight: bold; font-family: monospace;">${sym}</td>

                <td style="padding: 10px 12px;">

                    <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: ${typeBg}; color: ${typeColor}; text-transform: uppercase;">

                        ${typeLabel}

                    </span>

                </td>

                <td style="padding: 10px 12px; text-align: right; font-family: monospace; font-weight: bold;">

                    ${item.Earnings_Date || "N/A"}

                </td>

                <td style="padding: 10px 12px; text-align: right; font-family: monospace; font-weight: bold;">

                    ${days !== undefined && days !== null ? (days < 0 ? `Past (${Math.abs(days)}d ago)` : `${days} days`) : "N/A"}

                </td>

                <td style="padding: 10px 12px; text-align: center; font-weight: bold; color: ${riskColor};">

                    ${riskStatus}

                </td>

            `;

            tbody.appendChild(tr);

        });

    } catch (e) {

        console.error("Error loading earnings calendar:", e);

        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 30px; color: var(--accent-red); font-weight: bold;">Error loading earnings calendar.</td></tr>`;

    }

}

window.openTradingViewWatchlistModal = function() {

    const symbols = new Set();

    

    if (appState.strategicWatchlist) {

        appState.strategicWatchlist.forEach(s => {

            const stop = s.Stop_Loss;

            const entry = s.Entry;

            if (stop > 0 && entry > 0 && s.Symbol) {

                symbols.add(s.Symbol.toUpperCase().trim());

            }

        });

    }

    

    if (appState.dailyFocusWatchlist) {

        appState.dailyFocusWatchlist.forEach(s => {

            const stop = s.Stop_Loss;

            const entry = s.Entry_Price;

            if (stop > 0 && entry > 0 && s.Symbol) {

                symbols.add(s.Symbol.toUpperCase().trim());

            }

        });

    }

    

    const symList = Array.from(symbols);

    const formattedList = symList.map(s => {

        if (!s.startsWith("NSE:") && !s.startsWith("BSE:")) {

            return "NSE:" + s;

        }

        return s;

    });

    

    const textarea = document.getElementById("tv-tickers-textarea");

    const countSpan = document.getElementById("tv-tickers-count");

    

    if (!textarea || !countSpan) return;

    

    if (formattedList.length === 0) {

        textarea.value = "No watchlist stocks have both Stop Loss and Trigger Price marked.";

        countSpan.textContent = "0";

    } else {

        textarea.value = formattedList.join(",");

        countSpan.textContent = formattedList.length;

    }

    

    document.getElementById("tv-watchlist-modal").style.display = "flex";

};

window.copyTradingViewTickersToClipboard = function() {

    const textarea = document.getElementById("tv-tickers-textarea");

    if (textarea && textarea.value && !textarea.value.startsWith("No watchlist")) {

        navigator.clipboard.writeText(textarea.value).then(() => {

            const btn = document.getElementById("btn-copy-tv-tickers");

            if (btn) {

                const oldHtml = btn.innerHTML;

                btn.innerHTML = `<i class="fa-solid fa-check"></i> Copied & Opening TV!`;

                btn.style.background = "var(--accent-green)";

                setTimeout(() => {

                    btn.innerHTML = oldHtml;

                    btn.style.background = "var(--accent-purple)";

                }, 2000);

            }

            

            // Extract the first symbol if present and open the preloaded chart URL

            const tickers = textarea.value.split(",");

            const firstTicker = tickers.length > 0 ? tickers[0] : "";

            const tvUrl = firstTicker ? `https://www.tradingview.com/chart/?symbol=${firstTicker}` : "https://www.tradingview.com/chart/";

            window.open(tvUrl, "_blank");

        }).catch(err => {

            console.error("Clipboard copy failed:", err);

            window.open("https://www.tradingview.com/chart/", "_blank");

        });

    }

};

window.downloadTradingViewWatchlistFile = function() {

    const textarea = document.getElementById("tv-tickers-textarea");

    if (textarea && textarea.value && !textarea.value.startsWith("No watchlist")) {

        const content = textarea.value.split(",").join("\n");

        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });

        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");

        a.href = url;

        a.download = `TradingView_Watchlist_${new Date().toISOString().slice(0, 10)}.txt`;

        document.body.appendChild(a);

        a.click();

        document.body.removeChild(a);

        URL.revokeObjectURL(url);

    }

};

window.renderRRGChart = function(rrgData, canvasId = "rrg-canvas", legendListId = "rrg-legend-list") {

    const canvas = document.getElementById(canvasId);

    if (!canvas) return;

    

    // Support High-DPI (Retina) scaling for razor-sharp rendering

    const dpr = window.devicePixelRatio || 1;

    const logicalWidth = canvas.clientWidth || 550;

    const logicalHeight = canvas.clientHeight || 550;

    

    canvas.width = logicalWidth * dpr;

    canvas.height = logicalHeight * dpr;

    canvas.style.width = logicalWidth + "px";

    canvas.style.height = logicalHeight + "px";

    

    const ctx = canvas.getContext("2d");

    ctx.scale(dpr, dpr);

    

    const width = logicalWidth;

    const height = logicalHeight;

    

    // Clear canvas

    ctx.clearRect(0, 0, width, height);

    

    const margin = 50;

    const minVal = 94.0;

    const maxVal = 106.0;

    const centerVal = 100.0;

    

    // Helper to map RRG data coordinates to canvas pixels

    function mapX(xVal) {

        return margin + ((xVal - minVal) / (maxVal - minVal)) * (width - 2 * margin);

    }

    

    function mapY(yVal) {

        return height - margin - ((yVal - minVal) / (maxVal - minVal)) * (height - 2 * margin);

    }

    

    const cx = mapX(centerVal);

    const cy = mapY(centerVal);

    

    // 1. Draw Quadrant Backgrounds

    // Top-Right: Leading (green)

    ctx.fillStyle = "rgba(16, 185, 129, 0.04)";

    ctx.fillRect(cx, margin, width - margin - cx, cy - margin);

    

    // Top-Left: Improving (blue)

    ctx.fillStyle = "rgba(59, 130, 246, 0.04)";

    ctx.fillRect(margin, margin, cx - margin, cy - margin);

    

    // Bottom-Left: Lagging (red)

    ctx.fillStyle = "rgba(239, 68, 68, 0.04)";

    ctx.fillRect(margin, cy, cx - margin, height - margin - cy);

    

    // Bottom-Right: Weakening (yellow)

    ctx.fillStyle = "rgba(245, 158, 11, 0.04)";

    ctx.fillRect(cx, cy, width - margin - cx, height - margin - cy);

    

    // 2. Draw Quadrant Border & Grid Lines

    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";

    ctx.lineWidth = 1;

    ctx.strokeRect(margin, margin, width - 2 * margin, height - 2 * margin);

    

    // Center cross lines

    ctx.beginPath();

    ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";

    ctx.lineWidth = 1.5;

    ctx.setLineDash([4, 4]);

    // Horizontal center line

    ctx.moveTo(margin, cy);

    ctx.lineTo(width - margin, cy);

    // Vertical center line

    ctx.moveTo(cx, margin);

    ctx.lineTo(cx, height - margin);

    ctx.stroke();

    ctx.setLineDash([]); // Reset dash

    

    // 3. Draw Quadrant Labels

    ctx.font = "bold 13px 'Inter', sans-serif";

    ctx.textBaseline = "middle";

    

    // LEADING (Top-Right)

    ctx.fillStyle = "#10b981";

    ctx.textAlign = "right";

    ctx.fillText("LEADING", width - margin - 15, margin + 15);

    

    // IMPROVING (Top-Left)

    ctx.fillStyle = "#3b82f6";

    ctx.textAlign = "left";

    ctx.fillText("IMPROVING", margin + 15, margin + 15);

    

    // LAGGING (Bottom-Left)

    ctx.fillStyle = "#ef4444";

    ctx.textAlign = "left";

    ctx.fillText("LAGGING", margin + 15, height - margin - 15);

    

    // WEAKENING (Bottom-Right)

    ctx.fillStyle = "#f59e0b";

    ctx.textAlign = "right";

    ctx.fillText("WEAKENING", width - margin - 15, height - margin - 15);

    

    // Axis helper labels

    ctx.font = "bold 10px monospace";

    ctx.fillStyle = "rgba(255, 255, 255, 0.4)";

    ctx.textAlign = "center";

    ctx.fillText("RS-Ratio (Strength Score)", cx, height - 18);

    

    ctx.save();

    ctx.translate(18, cy);

    ctx.rotate(-Math.PI / 2);

    ctx.fillText("RS-Momentum", 0, 0);

    ctx.restore();

    

    // Grid reference labels (95, 100, 105)

    ctx.font = "9px monospace";

    ctx.fillStyle = "rgba(255,255,255,0.3)";

    ctx.textAlign = "center";

    ctx.fillText("100.0 (Benchmark)", cx, cy + 15);

    ctx.fillText("95.0", mapX(95.0), cy + 15);

    ctx.fillText("105.0", mapX(105.0), cy + 15);

    

    ctx.textAlign = "right";

    ctx.fillText("95.0", cx - 8, mapY(95.0));

    ctx.fillText("105.0", cx - 8, mapY(105.0));

    

    if (!rrgData || rrgData.length === 0) return;

    

    // Colors for industry trails

    const colors = [

        "#c084fc", // Purple

        "#2dd4bf", // Teal

        "#38bdf8", // Sky Blue

        "#f472b6", // Pink

        "#34d399", // Emerald

        "#818cf8", // Indigo

        "#fbbf24", // Amber

        "#fb7185"  // Rose

    ];

    

    const legendList = document.getElementById(legendListId);

    if (legendList) legendList.innerHTML = "";

    

    // 4. Draw Trails for each Industry

    rrgData.forEach((ind, index) => {

        const color = colors[index % colors.length];

        const trail = ind.trail || [];

        if (trail.length === 0) return;

        

        // Draw line trail connecting historical coordinates

        ctx.beginPath();

        ctx.strokeStyle = color;

        ctx.lineWidth = 2.5;

        

        trail.forEach((pt, idx) => {

            const px = mapX(pt.x);

            const py = mapY(pt.y);

            if (idx === 0) {

                ctx.moveTo(px, py);

            } else {

                ctx.lineTo(px, py);

            }

        });

        ctx.stroke();

        

        // Draw circles for historical points along trail

        trail.forEach((pt, idx) => {

            if (idx === trail.length - 1) return; // skip latest point

            const px = mapX(pt.x);

            const py = mapY(pt.y);

            ctx.beginPath();

            ctx.arc(px, py, 3.5, 0, 2 * Math.PI);

            ctx.fillStyle = color;

            ctx.globalAlpha = 0.3 + (idx / trail.length) * 0.7;

            ctx.fill();

            ctx.globalAlpha = 1.0;

        });

        

        // Draw latest position as a beautiful numbered badge

        const latest = trail[trail.length - 1];

        const lpx = mapX(latest.x);

        const lpy = mapY(latest.y);

        

        // Draw glowing background circle

        ctx.beginPath();

        ctx.arc(lpx, lpy, 10, 0, 2 * Math.PI);

        ctx.fillStyle = color;

        ctx.shadowBlur = 10;

        ctx.shadowColor = color;

        ctx.fill();

        ctx.shadowBlur = 0; // Reset shadow

        

        // Draw sharp white border

        ctx.strokeStyle = "rgba(255, 255, 255, 0.85)";

        ctx.lineWidth = 1.5;

        ctx.stroke();

        

        // Center text label inside circle (index starts at 0, display 1-based index)

        ctx.font = "bold 10px 'Inter', sans-serif";

        ctx.fillStyle = "#111827"; // Dark contrast color

        ctx.textAlign = "center";

        ctx.textBaseline = "middle";

        ctx.fillText((index + 1).toString(), lpx, lpy);

        

        // 5. Add to Legend list

        if (legendList) {

            let quadrant = "";

            let qColor = "";

            if (latest.x >= 100 && latest.y >= 100) { quadrant = "Leading"; qColor = "var(--accent-green)"; }

            else if (latest.x >= 100 && latest.y < 100) { quadrant = "Weakening"; qColor = "var(--accent-orange)"; }

            else if (latest.x < 100 && latest.y < 100) { quadrant = "Lagging"; qColor = "var(--accent-red)"; }

            else { quadrant = "Improving"; qColor = "var(--accent-blue)"; }

            

            const legendItem = document.createElement("div");

            legendItem.className = "rrg-legend-item";

            

            legendItem.innerHTML = `

                <div style="display: flex; align-items: center; gap: 10px; max-width: 70%; overflow: hidden;">

                    <span class="rrg-legend-badge" style="background: ${color}; box-shadow: 0 0 5px ${color};">${index + 1}</span>

                    <span style="font-size: 12px; font-weight: bold; color: var(--text-primary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${ind.industry}">${ind.industry}</span>

                </div>

                <div style="display: flex; align-items: center; gap: 8px; font-size: 11px;">

                    <span style="font-weight: 800; color: ${qColor};">${quadrant}</span>

                    <span style="font-family: monospace; color: var(--text-muted); font-size: 10.5px;">[${latest.x.toFixed(1)}, ${latest.y.toFixed(1)}]</span>

                </div>

            `;

            legendList.appendChild(legendItem);

        }

    });

};

window.renderMarketBreadthHistory = function(breadthHistory, tbodyId = "market-breadth-history-table-body", canvasId = "breadth-chart-canvas", statusBadgeId = "breadth-status-badge") {
    if (!breadthHistory || breadthHistory.length === 0) return;

    // 1. Render Breadth History Table (Past 7 Sessions)
    const tbody = document.getElementById(tbodyId);
    if (tbody) {
        tbody.innerHTML = "";
        
        // Show last 7 sessions, latest first
        const tableData = [...breadthHistory].reverse().slice(0, 7);
        tbody.innerHTML = tableData.map(d => {
            const idx = d.Index || 0.0;
            let idxColor = "var(--text-primary)";
            if (idx >= 50.0) idxColor = "var(--accent-green)";
            else if (idx <= 30.0) idxColor = "var(--accent-red)";
            else idxColor = "var(--accent-orange)";
            
            function formatVal(v) {
                if (v === undefined || v === null) return "-";
                const num = Number(v);
                let color = "var(--text-secondary)";
                if (num >= 50.0) color = "#10b981"; // Strong green
                else if (num <= 30.0) color = "#ef4444"; // Weak red
                return `<span style="color: ${color}; font-weight: bold;">${num.toFixed(1)}%</span>`;
            }
            
            return `
                <tr>
                    <td style="font-family: monospace; font-weight: bold; color: var(--text-primary);">${d.AsOfDate}</td>
                    <td style="font-family: monospace; font-weight: 800; color: ${idxColor}; text-align: center; font-size: 13px;">${idx.toFixed(1)}%</td>
                    <td style="text-align: center;">${formatVal(d.Indicators?.Above20EMA)}</td>
                    <td style="text-align: center;">${formatVal(d.Indicators?.Above50SMA)}</td>
                    <td style="text-align: center;">${formatVal(d.Indicators?.Above200SMA)}</td>
                    <td style="text-align: center;">${formatVal(d.Indicators?.Stacked)}</td>
                    <td style="text-align: center;">${formatVal(d.Indicators?.AdvancesDeclines)}</td>
                    <td style="text-align: center;">${formatVal(d.Indicators?.Near52WH)}</td>
                    <td style="text-align: center;">${formatVal(d.Indicators?.HighRS)}</td>
                </tr>
            `;
        }).join("");
    }
    
    // 2. Render Breadth Trend Graph
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    // Support High-DPI (Retina) scaling for razor-sharp rendering
    const dpr = window.devicePixelRatio || 1;
    const parent = canvas.parentElement;
    const logicalWidth = parent.clientWidth - 32; // deduct padding
    const logicalHeight = 250;
    
    canvas.width = logicalWidth * dpr;
    canvas.height = logicalHeight * dpr;
    canvas.style.width = logicalWidth + "px";
    canvas.style.height = logicalHeight + "px";
    
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    
    const width = logicalWidth;
    const height = logicalHeight;
    
    ctx.clearRect(0, 0, width, height);
    
    const margin = 40;
    
    // Render status badge at the top
    const statusBadge = document.getElementById(statusBadgeId);
    const latest = breadthHistory[breadthHistory.length - 1];
    if (statusBadge && latest) {
        statusBadge.textContent = `STATUS: ${latest.Status?.toUpperCase()} (${latest.Index?.toFixed(1)}%)`;
        statusBadge.className = `badge ${latest.StatusColor}`;
    }
    
    // Dynamic status color mapping for graph visualization (Red / Yellow / Green)
    let chartColor = "#10b981"; // Strong Green (Default)
    let fillGradStart = "rgba(16, 185, 129, 0.22)";
    let textValColor = "rgba(16, 185, 129, 0.9)";
    
    if (latest) {
        const statStr = (latest.Status || "").toLowerCase();
        if (statStr === "caution") {
            chartColor = "#f59e0b"; // Caution Yellow
            fillGradStart = "rgba(245, 158, 11, 0.22)";
            textValColor = "rgba(245, 158, 11, 0.95)";
        } else if (statStr === "weak") {
            chartColor = "#ef4444"; // Weak Red
            fillGradStart = "rgba(239, 68, 68, 0.22)";
            textValColor = "rgba(239, 68, 68, 0.95)";
        }
    }
    
    // Draw chart axes & grid lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    ctx.lineWidth = 1;
    
    for (let pct = 0; pct <= 100; pct += 20) {
        const y = height - margin - (pct / 100) * (height - 2 * margin);
        ctx.beginPath();
        ctx.moveTo(margin, y);
        ctx.lineTo(width - margin, y);
        ctx.stroke();
        
        ctx.font = "9px monospace";
        ctx.fillStyle = "rgba(255,255,255,0.3)";
        ctx.textAlign = "right";
        ctx.fillText(pct + "%", margin - 8, y + 3);
    }
    
    // Plot Line
    ctx.beginPath();
    ctx.strokeStyle = chartColor; 
    ctx.lineWidth = 3.5;
    
    // Glow effect
    ctx.shadowBlur = 12;
    ctx.shadowColor = chartColor;
    
    const xStep = (width - 2 * margin) / (breadthHistory.length - 1 || 1);
    
    breadthHistory.forEach((pt, idx) => {
        const px = margin + idx * xStep;
        const indexVal = pt.Index || 0.0;
        const py = height - margin - (indexVal / 100) * (height - 2 * margin);
        
        if (idx === 0) {
            ctx.moveTo(px, py);
        } else {
            ctx.lineTo(px, py);
        }
    });
    ctx.stroke();
    
    // Reset shadow blur
    ctx.shadowBlur = 0;
    
    // Draw glow area gradient under line
    const gradient = ctx.createLinearGradient(0, margin, 0, height - margin);
    gradient.addColorStop(0, fillGradStart);
    gradient.addColorStop(1, "rgba(255, 255, 255, 0.0)");
    ctx.fillStyle = gradient;
    
    ctx.beginPath();
    ctx.moveTo(margin, height - margin);
    breadthHistory.forEach((pt, idx) => {
        const px = margin + idx * xStep;
        const indexVal = pt.Index || 0.0;
        const py = height - margin - (indexVal / 100) * (height - 2 * margin);
        ctx.lineTo(px, py);
    });
    ctx.lineTo(margin + (breadthHistory.length - 1) * xStep, height - margin);
    ctx.closePath();
    ctx.fill();
    
    // Draw dots and dates
    breadthHistory.forEach((pt, idx) => {
        const px = margin + idx * xStep;
        const indexVal = pt.Index || 0.0;
        const py = height - margin - (indexVal / 100) * (height - 2 * margin);
        
        // Point dot
        ctx.beginPath();
        ctx.arc(px, py, 4.5, 0, 2 * Math.PI);
        ctx.fillStyle = chartColor;
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(px, py, 2, 0, 2 * Math.PI);
        ctx.fillStyle = "#111827";
        ctx.fill();
        
        // Date labels on X axis
        if (idx % 2 === 0 || idx === breadthHistory.length - 1) {
            ctx.font = "bold 9.5px monospace";
            ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
            ctx.textAlign = "center";
            const shortDate = pt.AsOfDate.slice(5); // e.g. "07-29"
            ctx.fillText(shortDate, px, height - margin + 18);
        }
        
        // Values above dots
        ctx.font = "bold 9px monospace";
        ctx.fillStyle = textValColor;
        ctx.textAlign = "center";
        ctx.fillText(indexVal.toFixed(0) + "%", px, py - 10);
    });
};

/* ==========================================
   STOCKS FILTER TAB LOGIC
   ========================================== */

function populateFilterIndustries(candidates) {
    const select = document.getElementById("filter-industry-select");
    if (!select) return;
    
    const currentVal = select.value;
    const industries = new Set();
    
    candidates.forEach(c => {
        if (c.Industry) {
            industries.add(c.Industry.trim());
        }
    });
    
    const sortedIndustries = Array.from(industries).sort();
    let html = '<option value="ALL">Show All Industries</option>';
    sortedIndustries.forEach(ind => {
        html += `<option value="${ind}">${ind}</option>`;
    });
    
    select.innerHTML = html;
    
    if (sortedIndustries.includes(currentVal)) {
        select.value = currentVal;
    } else {
        select.value = "ALL";
    }
}

window.setScreenerScope = function(scope) {
    appState.screenerScope = scope;
    
    const btnCurated = document.getElementById("scope-curated");
    const btnAll = document.getElementById("scope-all");
    
    if (btnCurated && btnAll) {
        if (scope === "all") {
            btnAll.style.background = "var(--accent-purple)";
            btnAll.style.color = "white";
            btnAll.style.border = "none";
            
            btnCurated.style.background = "rgba(255,255,255,0.05)";
            btnCurated.style.color = "var(--text-secondary)";
            btnCurated.style.border = "1px solid var(--border-color)";
        } else {
            btnCurated.style.background = "var(--accent-purple)";
            btnCurated.style.color = "white";
            btnCurated.style.border = "none";
            
            btnAll.style.background = "rgba(255,255,255,0.05)";
            btnAll.style.color = "var(--text-secondary)";
            btnAll.style.border = "1px solid var(--border-color)";
        }
    }
    
    renderFilteredWatchlist();
    showToast(`Switched scope to ${scope === 'all' ? 'All Scanned Candidates' : 'Curated Watchlist'}.`, "info");
};

// ─── MBI PRIORITY ENGINE ────────────────────────────────────────────────────
function classifySetupType(engineType, grade, entryCategory, score) {
    const eng = (engineType || '').toUpperCase();
    const gr  = (grade || '').toUpperCase();
    const cat = (entryCategory || '').toUpperCase();
    const sc  = parseFloat(score) || 50;
    if ((eng.includes('STRICT_VCP') || cat.includes('TIGHT_CHEAT')) && gr.includes('GRADE A')) return 'A';
    if (eng.includes('STRICT_VCP') && gr.includes('GRADE B') && sc >= 70) return 'A';
    if ((eng.includes('FLAG_SETUP') || eng.includes('INSIDE_BAR_FLAG') || eng.includes('FLEX_VCP') || eng.includes('MINI_VCP')) && (gr.includes('GRADE A') || gr.includes('GRADE B'))) return 'B';
    if (cat.includes('TIGHT_CHEAT') && gr.includes('GRADE B')) return 'B';
    if (eng.includes('PULLBACK_EMA10') && gr.includes('GRADE A')) return 'B';
    if (eng.includes('PULLBACK_EMA20') && gr.includes('GRADE A')) return 'B';
    return 'C';
}

function getMBIPriorityRules(mbiIndex) {
    const idx = parseFloat(mbiIndex) || 50;
    if (idx >= 70) return { label:'TRENDING', color:'#10b981', priority:['A','B','C'], sizeMap:{A:'1.5%',B:'1.0%',C:'0.5%'}, tradeThis:'Type A STRICT VCP + Tight Cheat. Then Type B Flag / EMA10. Full aggression.', avoid:'Low-quality Type C in weak sectors' };
    if (idx >= 55) return { label:'MODERATE', color:'#3b82f6', priority:['B','A','C'], sizeMap:{A:'1.0%',B:'1.0%',C:'0.5%'}, tradeThis:'Type B Flag / Flex VCP / EMA10 Pullback. Selective Type A with perfect structure.', avoid:'High-risk entries in consolidating sectors' };
    if (idx >= 45) return { label:'CAUTION',  color:'#f59e0b', priority:['B','C'],     sizeMap:{A:'0%', B:'0.75%',C:'0.5%'}, tradeThis:'Type B EMA10 Pullbacks & Inside Bar. Type C EMA20 with tight 2-3% SL.', avoid:'Type A breakouts — market too weak to sustain them' };
    if (idx >= 30) return { label:'WEAK',     color:'#f97316', priority:['C'],         sizeMap:{A:'0%', B:'0.5%', C:'0.5%'}, tradeThis:'Type C EMA20/50 support plays ONLY. Tight 2-3% SL. Half size.', avoid:'Type A and most Type B breakouts' };
    return             { label:'DANGER',   color:'#ef4444', priority:[],           sizeMap:{A:'0%', B:'0%',   C:'0%'},   tradeThis:'CASH. No new longs. Exit weak positions.', avoid:'Everything' };
}

function computeSetupTargets(setupType, entry, stopLoss) {
    const ep = parseFloat(entry) || 0;
    const sl = parseFloat(stopLoss) || 0;
    if (ep <= 0 || sl <= 0 || sl >= ep) return { t1: null, t2: null, riskPct: null, t1Pct: null, t2Pct: null };
    let risk = ep - sl;
    if (risk <= 0) risk = ep * 0.05;
    const mults = setupType === 'A' ? [2.0, 3.0] : setupType === 'B' ? [1.5, 2.5] : [1.0, 2.0];
    const t1 = ep + mults[0] * risk;
    const t2 = ep + mults[1] * risk;
    return {
        t1: t1.toFixed(2), t2: t2.toFixed(2),
        riskPct: (risk / ep * 100).toFixed(1),
        t1Pct: ((t1 - ep) / ep * 100).toFixed(1),
        t2Pct: ((t2 - ep) / ep * 100).toFixed(1)
    };
}

function renderMBICommandBar() {
    const container = document.getElementById('mbi-command-bar');
    if (!container) return;
    const mb = appState.marketBreadth || {};
    const idx = parseFloat(mb.Index) || 0;
    const change1d = parseFloat(mb.Change_1D) || 0;
    const indicators = mb.Indicators || {};
    const asOf = mb.AsOfDate || '';
    const rules = getMBIPriorityRules(idx);
    const priorityBadges = rules.priority.map(t => {
        const colors = {A:'#10b981',B:'#3b82f6',C:'#f59e0b'};
        return `<span style="display:inline-flex;align-items:center;background:rgba(255,255,255,0.07);border:1px solid ${colors[t]};color:${colors[t]};font-weight:800;font-size:11px;padding:3px 12px;border-radius:20px;letter-spacing:0.5px;">TYPE ${t}</span>`;
    }).join('<span style="color:var(--text-muted);margin:0 5px;font-size:10px;">&rsaquo;</span>');
    const indPills = Object.entries({'EMA20':indicators.Above20EMA,'SMA50':indicators.Above50SMA,'SMA200':indicators.Above200SMA,'Stacked':indicators.Stacked,'A/D':indicators.AdvancesDeclines,'52WH':indicators.Near52WH,'Hi-RS':indicators.HighRS}).map(([label,val]) => {
        const v = parseFloat(val) || 0;
        const color = v >= 60 ? '#10b981' : v >= 45 ? '#f59e0b' : '#ef4444';
        return `<span style="font-size:9.5px;background:rgba(255,255,255,0.05);border:1px solid ${color}40;color:${color};padding:2px 7px;border-radius:10px;font-weight:600;white-space:nowrap;">${label}: ${v.toFixed(0)}%</span>`;
    }).join('');
    container.innerHTML = `
        <div style="background:linear-gradient(135deg,var(--surface-card),rgba(20,20,40,0.98));border:1px solid ${rules.color}40;border-radius:12px;padding:16px 20px;margin-bottom:14px;box-shadow:0 4px 24px ${rules.color}18;">
            <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:12px;flex-shrink:0;">
                    <div style="width:64px;height:64px;border-radius:50%;background:conic-gradient(${rules.color} ${idx*3.6}deg,rgba(255,255,255,0.05) 0deg);display:flex;align-items:center;justify-content:center;box-shadow:0 0 18px ${rules.color}40;">
                        <div style="width:50px;height:50px;border-radius:50%;background:var(--surface-card);display:flex;flex-direction:column;align-items:center;justify-content:center;">
                            <span style="font-size:17px;font-weight:900;color:${rules.color};line-height:1;">${idx.toFixed(0)}</span>
                            <span style="font-size:7px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;">MBI</span>
                        </div>
                    </div>
                    <div>
                        <div style="font-size:14px;font-weight:900;color:${rules.color};text-transform:uppercase;letter-spacing:1.5px;">${rules.label}</div>
                        <div style="font-size:10.5px;color:var(--text-secondary);margin-top:2px;">${change1d >= 0 ? '&#9650;' : '&#9660;'} ${Math.abs(change1d).toFixed(1)} pts today &nbsp;|&nbsp; ${asOf}</div>
                    </div>
                </div>
                <div style="width:1px;height:50px;background:var(--border-color);flex-shrink:0;"></div>
                <div style="flex:1;min-width:200px;">
                    <div style="font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Setup Priority Today</div>
                    <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">${priorityBadges || '<span style="color:var(--accent-red);font-weight:700;font-size:12px;">CASH ONLY</span>'}</div>
                </div>
                <div style="width:1px;height:50px;background:var(--border-color);flex-shrink:0;"></div>
                <div style="flex-shrink:0;">
                    <div style="font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px;">Risk Per Trade</div>
                    ${Object.entries(rules.sizeMap).map(([t,sz]) => { const colors={A:'#10b981',B:'#3b82f6',C:'#f59e0b'}; const active=rules.priority.includes(t); return `<div style="font-size:10.5px;color:${active?colors[t]:'var(--text-muted)'};${active?'':' opacity:0.4;text-decoration:line-through;'}"><span style="font-weight:800;">Type ${t}:</span> ${sz} capital</div>`; }).join('')}
                </div>
            </div>
            <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px;">${indPills}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.25);border-radius:8px;padding:9px 12px;">
                    <div style="font-size:9px;font-weight:700;color:#10b981;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">&#9989; TRADE THIS</div>
                    <div style="font-size:10.5px;color:var(--text-primary);line-height:1.4;">${rules.tradeThis}</div>
                </div>
                <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.25);border-radius:8px;padding:9px 12px;">
                    <div style="font-size:9px;font-weight:700;color:#ef4444;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">&#128683; AVOID</div>
                    <div style="font-size:10.5px;color:var(--text-primary);line-height:1.4;">${rules.avoid}</div>
                </div>
            </div>
        </div>
    `;
}
window.renderMBICommandBar = renderMBICommandBar;

// ─── GATE VALIDATION ENGINE ──────────────────────────────────────────────────
// Banned combos = negative EV from 947-setup grade backtest (4 months)
const BANNED_COMBOS = {
    'A': ['PULLBACK_EMA10'],
    'B': ['PULLBACK_EMA10','INSIDE_BAR_FLAG','FLEX_VCP'],
    'C': ['PULLBACK_EMA20','INSIDE_BAR_FLAG']
};
function validateSetupGates(s, mbiRules) {
    const gradeRaw = (s.Grade || s.Setup_Grade || 'Grade C').toUpperCase();
    const gradeKey = gradeRaw.includes('GRADE A') ? 'A' : gradeRaw.includes('GRADE B') ? 'B' : 'C';
    const pattern  = (s.Engine_Type || s.Setup_Type || '').toUpperCase().replace(/_/g,'');
    const category = s.Industry_Category || '';
    const riskPct  = parseFloat(s.Risk_Pct) || parseFloat((s._targets || {}).riskPct) || 0;
    // Gate 1 — MBI: grade allowed by today's market posture?
    const mbiOk = mbiRules.priority.includes(gradeKey);
    const mbiReason = mbiOk ? '' : `Grade ${gradeKey} blocked — MBI is ${mbiRules.label}`;
    // Gate 2 — Sector: must be leading zone
    const sectorOk = ['Confirmed Uptrend','Early Uptrend'].includes(category);
    const sectorReason = sectorOk ? '' : `Zone "${category}" not leading`;
    // Gate 3 — Pattern: reject negative-EV combos
    const isBanned = (BANNED_COMBOS[gradeKey] || []).some(b => pattern.includes(b.replace(/_/g,'')));
    const patternOk = !isBanned;
    const patternReason = isBanned ? `Grade ${gradeKey} + this pattern = negative EV` : '';
    // Gate 4 — SL band
    let slOk = true, slReason = '';
    if (gradeKey === 'A') {
        if (riskPct >= 3 && riskPct < 4) { slOk = false; slReason = `SL ${riskPct.toFixed(1)}% in 3-4% death zone for A`; }
        else if (riskPct > 7) { slOk = false; slReason = `SL ${riskPct.toFixed(1)}% too wide`; }
    } else if (gradeKey === 'B') {
        if (riskPct > 7) { slOk = false; slReason = `SL ${riskPct.toFixed(1)}% too wide`; }
    } else {
        if (riskPct > 3.5) { slOk = false; slReason = `SL ${riskPct.toFixed(1)}% too wide for Grade C (max 3.5%)`; }
    }
    const allPass = mbiOk && sectorOk && patternOk && slOk;
    const gatesPassed = [mbiOk,sectorOk,patternOk,slOk].filter(Boolean).length;
    const reasons = [mbiReason,sectorReason,patternReason,slReason].filter(Boolean);
    return { mbiOk, sectorOk, patternOk, slOk, allPass, gatesPassed, reasons, gradeKey };
}
window.validateSetupGates = validateSetupGates;
// ─── END GATE VALIDATION ENGINE ──────────────────────────────────────────────

function renderFilteredWatchlist() {
    renderMBICommandBar();
    const tableBody = document.getElementById("filtered-watchlist-table-body");
    const countSpan = document.getElementById("filtered-stocks-count");
    if (!tableBody) return;

    const _mb = appState.marketBreadth || {};
    const _mbiRules = getMBIPriorityRules(_mb.Index);

    let sourceCandidates = [];

    if (appState.screenerScope === "all") {
        sourceCandidates = appState.allScannedCandidates || [];
    } else {
        const seen = new Set();
        const srcList1 = appState.strategicWatchlist || [];
        srcList1.forEach(item => {
            const sym = (item.Symbol || "").trim().toUpperCase();
            if (sym && !seen.has(sym)) {
                seen.add(sym);
                sourceCandidates.push({
                    ...item,
                    Entry: item.Trigger || item.Entry || item.Entry_Price || 0.0,
                    Setup_Type: item.Setup_Type || item.Engine_Type || "VCP",
                    Setup_Grade: item.Grade || item.Setup_Grade || "Grade C",
                    Overall_Rank: item.Overall_Rank || "N/A"
                });
            }
        });
        
        const srcList2 = appState.dailyFocusWatchlist || [];
        srcList2.forEach(item => {
            const sym = (item.Symbol || "").trim().toUpperCase();
            if (sym && !seen.has(sym)) {
                seen.add(sym);
                sourceCandidates.push({
                    ...item,
                    Entry: item.Trigger || item.Entry_Price || item.Entry || 0.0,
                    Setup_Type: item.Setup_Type || item.Engine_Type || "VCP",
                    Setup_Grade: item.Grade || item.Setup_Grade || "Grade C",
                    Overall_Rank: item.Overall_Rank || "N/A"
                });
            }
        });
    }

    populateFilterIndustries(sourceCandidates);

    const filterVcp = document.getElementById("filter-vcp")?.checked ?? true;
    const filterFlag = document.getElementById("filter-flag")?.checked ?? true;
    const filterPb10 = document.getElementById("filter-pb10")?.checked ?? true;
    const filterPb20 = document.getElementById("filter-pb20")?.checked ?? true;
    const filterPb50 = document.getElementById("filter-pb50")?.checked ?? true;
    const filterIb = document.getElementById("filter-ib")?.checked ?? true;
    const filterPp = document.getElementById("filter-pp")?.checked ?? true;
    
    const filterLeading = document.getElementById("filter-leading-sectors")?.checked ?? true;
    const filterOther = document.getElementById("filter-other-sectors")?.checked ?? true;
    const filterCircuit20 = document.getElementById("filter-circuit-20")?.checked ?? true;
    const filterCircuit10 = document.getElementById("filter-circuit-10")?.checked ?? true;
    const filterCircuit5 = document.getElementById("filter-circuit-5")?.checked ?? true;
    const filterCircuit2 = document.getElementById("filter-circuit-2")?.checked ?? true;
    const filterCircuitNoBand = document.getElementById("filter-circuit-noband")?.checked ?? true;
    const selectedInd = document.getElementById("filter-industry-select")?.value ?? "ALL";
    const searchQuery = document.getElementById("watchlist-search")?.value.trim().toUpperCase() || "";

    const filterFocusTop3Conf = document.getElementById("filter-focus-top3conf")?.checked ?? true;
    const filterFocusTop5Conf = document.getElementById("filter-focus-top5conf")?.checked ?? true;
    const filterFocusTop3Early = document.getElementById("filter-focus-top3early")?.checked ?? true;
    const filterFocusTop5Early = document.getElementById("filter-focus-top5early")?.checked ?? true;

    const filterGradeA = document.getElementById("filter-grade-a")?.checked ?? true;
    const filterGradeB = document.getElementById("filter-grade-b")?.checked ?? true;
    const filterGradeC = document.getElementById("filter-grade-c")?.checked ?? true;

    // Sort all industries by score descending to find leaderboards
    const rotationData = appState.sectorRotation || [];
    const sortedIndustries = [...rotationData].sort((a, b) => {
        const scoreA = (a.Avg_Return_10D || 0.0) + (a.Part_EMA20_Today || 0.0) / 10.0;
        const scoreB = (b.Avg_Return_10D || 0.0) + (b.Part_EMA20_Today || 0.0) / 10.0;
        return scoreB - scoreA;
    });

    const topConfirmedInds = sortedIndustries.filter(ind => ind.Category === "Confirmed Uptrend").map(ind => ind.Industry);
    const topEarlyInds = sortedIndustries.filter(ind => ind.Category === "Early Uptrend").map(ind => ind.Industry);

    // Annotate each candidate with setup type + priority score + computed targets
    sourceCandidates = sourceCandidates.map(s => {
        const setupType = classifySetupType(s.Engine_Type || s.Setup_Type, s.Grade || s.Setup_Grade, s.Entry_Category || '', s.MS_Score || 50);
        const entry = parseFloat(s.Entry || s.Trigger || s.Entry_Price || 0);
        const stop  = parseFloat(s.Stop_Loss || s.stop_price || 0);
        const targets = computeSetupTargets(setupType, entry, stop);
        const sectorStreakDays = (rotationData.find(r => r.Industry === s.Industry) || {}).Streak_Days || 0;
        // Priority score: higher = show first
        let pScore = 0;
        const cat = s.Industry_Category || '';
        if (setupType === 'A') pScore += _mbiRules.priority.indexOf('A') === 0 ? 1000 : 400;
        else if (setupType === 'B') pScore += _mbiRules.priority.indexOf('B') === 0 ? 1000 : (_mbiRules.priority.indexOf('B') === 1 ? 700 : 200);
        else pScore += _mbiRules.priority.indexOf('C') === 0 ? 1000 : 300;
        if (cat === 'Confirmed Uptrend') pScore += 500;
        else if (cat === 'Early Uptrend') pScore += 350;
        else if (cat === 'Consolidation') pScore += 100;
        else pScore -= 400;
        if (topConfirmedInds.slice(0,3).includes(s.Industry)) pScore += 300;
        else if (topConfirmedInds.slice(0,5).includes(s.Industry)) pScore += 150;
        if (topEarlyInds.slice(0,3).includes(s.Industry)) pScore += 200;
        else if (topEarlyInds.slice(0,5).includes(s.Industry)) pScore += 100;
        pScore += Math.min(sectorStreakDays * 30, 150);
        pScore += (parseFloat(s.MS_Score) || 0) * 5;
        if (setupType === 'A' && !_mbiRules.priority.includes('A')) pScore -= 2000;
        const _gates = validateSetupGates(s, _mbiRules);
        if (!_gates.allPass) pScore -= (4 - _gates.gatesPassed) * 600;
        return { ...s, _setupType: setupType, _targets: targets, _priorityScore: pScore, _gates };
    });

    const filtered = sourceCandidates.filter(s => {
        const type = (s.Engine_Type || s.Setup_Type || "").toUpperCase();
        let matchesPattern = false;
        
        if (filterVcp && (type.includes("VCP") || type === "STRICT_VCP" || type === "FLEX_VCP")) {
            matchesPattern = true;
        }
        if (filterFlag && (type.includes("FLAG") || type === "FLAG_SETUP" || type === "HIGH_TIGHT_FLAG")) {
            // Exclude INSIDE_BAR_FLAG from standard flag to let it filter independently
            if (type !== "INSIDE_BAR_FLAG") {
                matchesPattern = true;
            }
        }
        if (filterPb10 && type === "PULLBACK_EMA10") {
            matchesPattern = true;
        }
        if (filterPb20 && type === "PULLBACK_EMA20") {
            matchesPattern = true;
        }
        if (filterPb50 && type === "PULLBACK_EMA50") {
            matchesPattern = true;
        }
        if (filterIb && (type.includes("INSIDE_BAR") || type === "INSIDE_BAR_FLAG")) {
            matchesPattern = true;
        }
        if (filterPp && (s.Pocket_Pivot === 1 || s.Pocket_Pivot === true || type.includes("POCKET_PIVOT") || type.includes("POCKET"))) {
            matchesPattern = true;
        }
        
        if (!matchesPattern) return false;

        const category = s.Industry_Category || "Avoid";
        const isLeadingCat = ["Confirmed Uptrend", "Early Uptrend", "Running Hot", "The Sweet Spot", "Sector Waking Up", "Leading Sector", "Leading"].includes(category);
        
        let matchesCategory = false;
        if (filterLeading && isLeadingCat) {
            matchesCategory = true;
        }
        if (filterOther && !isLeadingCat) {
            matchesCategory = true;
        }
        
        if (!matchesCategory) return false;

        // Circuit Filter check
        const bandVal = String(s.Band || "No Band").trim();
        let matchesCircuit = false;
        if (filterCircuit20 && bandVal === "20") {
            matchesCircuit = true;
        }
        if (filterCircuit10 && bandVal === "10") {
            matchesCircuit = true;
        }
        if (filterCircuit5 && bandVal === "5") {
            matchesCircuit = true;
        }
        if (filterCircuit2 && bandVal === "2") {
            matchesCircuit = true;
        }
        if (filterCircuitNoBand && (bandVal === "No Band" || bandVal === "ALL" || bandVal === "")) {
            matchesCircuit = true;
        }
        
        if (!matchesCircuit) return false;

        if (selectedInd !== "ALL" && s.Industry !== selectedInd) {
            return false;
        }

        // Focus Leaderboard check
        const anyFocusChecked = filterFocusTop3Conf || filterFocusTop5Conf || filterFocusTop3Early || filterFocusTop5Early;
        const allFocusChecked = filterFocusTop3Conf && filterFocusTop5Conf && filterFocusTop3Early && filterFocusTop5Early;
        
        if (anyFocusChecked && !allFocusChecked) {
            let matchesFocus = false;
            if (filterFocusTop3Conf && topConfirmedInds.slice(0, 3).includes(s.Industry)) {
                matchesFocus = true;
            }
            if (filterFocusTop5Conf && topConfirmedInds.slice(0, 5).includes(s.Industry)) {
                matchesFocus = true;
            }
            if (filterFocusTop3Early && topEarlyInds.slice(0, 3).includes(s.Industry)) {
                matchesFocus = true;
            }
            if (filterFocusTop5Early && topEarlyInds.slice(0, 5).includes(s.Industry)) {
                matchesFocus = true;
            }
            if (!matchesFocus) return false;
        }

        // Grade check
        const grade = (s.Grade || s.Setup_Grade || "").toUpperCase();
        if (!filterGradeA && (grade.includes("GRADE A") || grade === "A")) {
            return false;
        }
        if (!filterGradeB && (grade.includes("GRADE B") || grade === "B")) {
            return false;
        }
        if (!filterGradeC && (grade.includes("GRADE C") || grade === "C")) {
            return false;
        }

        if (searchQuery !== "") {
            const sym = (s.Symbol || "").toUpperCase();
            const ind = (s.Industry || "").toUpperCase();
            const comp = (s.Company_Name || "").toUpperCase();
            if (!sym.includes(searchQuery) && !ind.includes(searchQuery) && !comp.includes(searchQuery)) {
                return false;
            }
        }

        return true;
    });

    // Valid-only filter
    const filterValidOnly = document.getElementById('filter-valid-only')?.checked ?? false;
    const displayList = filterValidOnly ? filtered.filter(s => s._gates && s._gates.allPass) : filtered;

    // Apply sorting — default to priority score (gate-pass stocks float to top via pScore)
    const col = appState.screenerSortColumn || "_priorityScore";
    const dir = appState.screenerSortDirection || "desc";

    displayList.sort((a, b) => {
        let valA, valB;
        if (col === "Distance") {
            valA = parseFloat((a.Distance || "0").replace(/%/g, "")) || 0;
            valB = parseFloat((b.Distance || "0").replace(/%/g, "")) || 0;
        } else if (col === "VDU_Pct") {
            valA = parseFloat((a.VDU_Pct || "0").replace(/%/g, "")) || 0;
            valB = parseFloat((b.VDU_Pct || "0").replace(/%/g, "")) || 0;
        } else if (col === "Setup_Type") {
            valA = a.Engine_Type || a.Setup_Type || "";
            valB = b.Engine_Type || b.Setup_Type || "";
        } else if (col === "Setup_Grade") {
            valA = a.Grade || a.Setup_Grade || "";
            valB = b.Grade || b.Setup_Grade || "";
        } else if (col === "Entry") {
            valA = a.Entry || a.Trigger || a.Entry_Price || 0;
            valB = b.Entry || b.Trigger || b.Entry_Price || 0;
        } else {
            valA = a[col]; valB = b[col];
        }
        if (valA === undefined || valA === null) valA = (typeof valB === "string") ? "" : 0;
        if (valB === undefined || valB === null) valB = (typeof valA === "string") ? "" : 0;
        if (typeof valA === "string") {
            valA = valA.toUpperCase(); valB = valB.toString().toUpperCase();
            if (valA < valB) return dir === "asc" ? -1 : 1;
            if (valA > valB) return dir === "asc" ? 1 : -1;
            return 0;
        }
        if (col === "Overall_Rank") {
            const numA = (valA === "N/A" || isNaN(valA)) ? 9999 : Number(valA);
            const numB = (valB === "N/A" || isNaN(valB)) ? 9999 : Number(valB);
            return dir === "asc" ? numA - numB : numB - numA;
        }
        return dir === "asc" ? valA - valB : valB - valA;
    });

    updateScreenerHeaderSortIcons();

    const validCount = filtered.filter(s => s._gates?.allPass).length;
    if (countSpan) {
        countSpan.innerHTML = `${displayList.length} <span style="font-size:9.5px;color:var(--text-muted);">candidates</span>&nbsp;<span style="font-size:10px;background:rgba(16,185,129,0.12);color:#10b981;font-weight:700;padding:2px 8px;border-radius:8px;border:1px solid rgba(16,185,129,0.3);">&#10003; ${validCount} ready</span>`;
    }

    if (displayList.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="18" class="empty-state" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                    <i class="fa-solid fa-filter" style="font-size: 24px; margin-bottom: 10px; display: block; color: var(--accent-purple);"></i>
                    <span style="font-weight: 700; color: var(--text-primary); text-transform: uppercase;">no matching setups found</span>
                    <p style="font-size: 12px; margin-top: 4px; color: var(--text-muted);">Adjust your filters above to see watchlist stocks.</p>
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = displayList.map((s, idx) => {
        let displayType = (s.Engine_Type || s.Setup_Type || "").replace("_SETUP", "").replace("_VCP", "");
        if (displayType === "PULLBACK_EMA10") displayType = "EMA 10 PB";
        if (displayType === "PULLBACK_EMA20") displayType = "EMA 20 PB";
        if (displayType === "PULLBACK_EMA50") displayType = "EMA 50 PB";
        if (displayType === "INSIDE_BAR_FLAG") displayType = "Inside Bar";

        // ── Setup Type badge (A/B/C) ──
        const setupType = s._setupType || 'C';
        const stColors = {A:'#10b981', B:'#3b82f6', C:'#f59e0b'};
        const stColor  = stColors[setupType];
        const isRecommended = _mbiRules.priority.includes(setupType);
        const stBadge = `<span style="
            display:inline-block; font-size:10px; font-weight:900;
            background:${isRecommended ? stColor+'22' : 'rgba(255,255,255,0.04)'};
            color:${isRecommended ? stColor : 'var(--text-muted)'};
            border:1px solid ${isRecommended ? stColor+'60' : 'var(--border-color)'};
            padding:1px 7px; border-radius:10px; letter-spacing:0.5px;
            ${isRecommended ? '' : 'opacity:0.5; text-decoration: line-through;'}
        ">${isRecommended ? '&#10003; ' : ''}Type ${setupType}</span>`;

        // ── Computed T1 / T2 ──
        const tg = s._targets || {};
        const t1Html = tg.t1
            ? `<div style="font-family:monospace;font-weight:700;color:#10b981;font-size:11px;">&#8377;${tg.t1}</div>
               <div style="font-size:9px;color:var(--text-muted);">+${tg.t1Pct}%</div>`
            : `<span style="color:var(--text-muted);">—</span>`;
        const t2Html = tg.t2
            ? `<div style="font-family:monospace;font-weight:700;color:#3b82f6;font-size:11px;">&#8377;${tg.t2}</div>
               <div style="font-size:9px;color:var(--text-muted);">+${tg.t2Pct}%</div>`
            : `<span style="color:var(--text-muted);">—</span>`;

        // ── Priority indicator ──
        const pRank = isRecommended ? idx + 1 : null;
        const rankHtml = isRecommended
            ? `<span style="color:${stColor};font-weight:900;font-size:12px;">#${idx+1}</span>`
            : `<span style="color:var(--text-muted);font-size:11px;opacity:0.5;">#${idx+1}</span>`;

        let bandBadgeHtml = "";
        const bandVal = String(s.Band || "No Band").trim();
        if (bandVal === "20") {
            bandBadgeHtml = `<span style="font-size: 8px; font-weight: bold; background: rgba(16, 185, 129, 0.15); color: var(--accent-green); padding: 1px 4px; border-radius: 3px; margin-left: 4px;">20%</span>`;
        } else if (bandVal === "10") {
            bandBadgeHtml = `<span style="font-size: 8px; font-weight: bold; background: rgba(245, 158, 11, 0.15); color: var(--accent-orange); padding: 1px 4px; border-radius: 3px; margin-left: 4px;">10%</span>`;
        } else if (bandVal === "5") {
            bandBadgeHtml = `<span style="font-size: 8px; font-weight: bold; background: rgba(239, 68, 68, 0.15); color: var(--accent-red); padding: 1px 4px; border-radius: 3px; margin-left: 4px;">5%</span>`;
        } else if (bandVal === "2") {
            bandBadgeHtml = `<span style="font-size: 8px; font-weight: bold; background: rgba(239, 68, 68, 0.25); color: var(--accent-red); padding: 1px 4px; border-radius: 3px; border: 1px solid rgba(239, 68, 68, 0.5); margin-left: 4px;">2%</span>`;
        } else {
            bandBadgeHtml = `<span style="font-size: 8px; font-weight: bold; background: rgba(255, 255, 255, 0.1); color: var(--text-secondary); padding: 1px 4px; border-radius: 3px; margin-left: 4px;">F&O</span>`;
        }
        
        let typeBadgeBg = "rgba(59, 130, 246, 0.1)";
        let typeBadgeColor = "var(--accent-blue)";
        if (displayType.includes("PB")) {
            typeBadgeBg = "rgba(16, 185, 129, 0.1)";
            typeBadgeColor = "var(--accent-green)";
        } else if (displayType.includes("FLAG")) {
            typeBadgeBg = "rgba(245, 158, 11, 0.1)";
            typeBadgeColor = "var(--accent-orange)";
        } else if (displayType === "Inside Bar") {
            typeBadgeBg = "rgba(139, 92, 246, 0.15)";
            typeBadgeColor = "var(--accent-purple)";
        }

        let earningsHtml = `<span style="color: var(--text-muted);">-</span>`;
        if (s.Earnings_Date && s.Earnings_Date !== "N/A") {
            const days = s.Days_To_Earnings;
            let daysStyle = "color: var(--text-primary);";
            let warningText = "";
            if (days !== undefined && days !== null) {
                if (days < 0) {
                    daysStyle = "color: var(--text-muted);";
                } else if (days <= 3) {
                    daysStyle = "color: var(--accent-red); font-weight: 800; background: rgba(239, 68, 68, 0.1); padding: 1px 4px; border-radius: 3px;";
                    warningText = " ⚠️";
                } else if (days <= 7) {
                    daysStyle = "color: var(--accent-orange); font-weight: 700;";
                    warningText = " ⚠️";
                }
            }
            earningsHtml = `
                <div style="font-size: 10.5px; line-height: 1.2;">
                    <div style="font-weight: 600; font-family: monospace;">${s.Earnings_Date}</div>
                    <div style="font-size: 9.5px; ${daysStyle}">${days !== undefined && days !== null ? (days < 0 ? `Past` : `${days}d left`) : ""}${warningText}</div>
                </div>
            `;
        }

        const distColor = parseFloat(s.Distance) >= 0 ? "var(--accent-green)" : "var(--accent-red)";

        // ── Gate validation cell ──
        const gates = s._gates || validateSetupGates(s, _mbiRules);
        const gIcon = ok => ok
            ? '<span style="color:#10b981;font-weight:900;font-size:11px;">&#10003;</span>'
            : '<span style="color:#ef4444;font-weight:900;font-size:10px;">&#10007;</span>';
        const gRow = (ok, lbl) => `<div style="display:flex;align-items:center;gap:2px;font-size:8.5px;color:${ok?'#10b981':'#ef4444'};line-height:1.5;">${gIcon(ok)}<span>${lbl}</span></div>`;
        const tooltipTxt = gates.allPass ? 'All 4 gates pass — ready to trade' : ('BLOCKED: ' + gates.reasons.join(' | '));
        const gatesCell = `<div title="${tooltipTxt.replace(/"/g,"'")}" style="cursor:help;min-width:60px;">
            ${gRow(gates.mbiOk,'MBI')}
            ${gRow(gates.sectorOk,'Sector')}
            ${gRow(gates.patternOk,'Pattern')}
            ${gRow(gates.slOk,'SL Band')}
        </div>`;

        const allPass = gates.allPass;
        const rowStyle = allPass
            ? (isRecommended ? `background:${stColor}09;border-left:3px solid ${stColor}65;` : 'border-left:3px solid transparent;')
            : 'border-left:3px solid rgba(239,68,68,0.5);opacity:0.45;';

        return `
            <tr style="${rowStyle}">
                <td style="text-align: center;">${rankHtml}</td>
                <td style="text-align:center;padding:4px 6px;">${stBadge}</td>
                <td>
                    <span class="stock-symbol" onclick="showAMSDetail('${s.Symbol}')" style="cursor: pointer; font-weight: bold; color: var(--text-primary); background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border-color); font-family: monospace;">${s.Symbol}</span>${bandBadgeHtml}
                </td>
                <td style="font-size: 11px; max-width: 130px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${s.Company_Name}">${s.Company_Name}</td>
                <td style="font-size: 11px;">
                    <div style="font-weight: 600; font-size:10.5px;">${s.Industry}</div>
                    <span style="font-size: 9px; color: var(--text-secondary); text-transform: uppercase;">${s.Industry_Category || 'Neutral'}</span>
                </td>
                <td>
                    <span class="badge" style="background: ${typeBadgeBg}; color: ${typeBadgeColor}; font-size: 9.5px; text-transform: uppercase;">${displayType}</span>
                </td>
                <td style="font-size: 11px; text-align: center;">${s.Setup_Grade || s.Grade || 'Grade C'}</td>
                <td style="text-align: center; font-weight: 700; color: var(--accent-blue);">${s.MS_Score || 0}</td>
                <td style="text-align: center; font-family: monospace; color: ${distColor}; font-weight: bold;">${s.Distance || '0.0%'}</td>
                <td style="text-align: center; font-family: monospace;">${s.VDU_Pct || '0.0%'}</td>
                <td style="text-align: center; font-family: monospace;">
                    <span style="color: var(--accent-red); font-weight: bold;">${(s.Risk_Pct !== undefined && s.Risk_Pct !== null) ? Number(s.Risk_Pct).toFixed(1) : (tg.riskPct || '0.0')}%</span>
                </td>
                <td style="text-align: center;">${earningsHtml}</td>
                <td style="font-family: monospace; text-align: right; color: var(--text-primary); font-weight: 600;">&#8377;${(s.CMP !== undefined && s.CMP !== null) ? Number(s.CMP).toFixed(2) : '0.00'}</td>
                <td style="font-family: monospace; font-weight: 700; text-align: right; color: var(--accent-green);">&#8377;${(s.Entry !== undefined && s.Entry !== null) ? Number(s.Entry).toFixed(2) : '0.00'}</td>
                <td style="font-family: monospace; text-align: right; color: var(--accent-red);">&#8377;${(s.Stop_Loss !== undefined && s.Stop_Loss !== null) ? Number(s.Stop_Loss).toFixed(2) : '0.00'}</td>
                <td style="text-align:center;">${t1Html}</td>
                <td style="text-align:center;">${t2Html}</td>
                <td style="padding:4px 6px;">${gatesCell}</td>
                <td style="text-align: center;">
                    <button class="table-add-journal-btn" onclick="addCandidateToJournal('${s.Symbol}')" title="Add to Journal">
                        <i class="fa-solid fa-plus"></i> Add
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

window.renderFilteredWatchlist = renderFilteredWatchlist;

function sortScreener(column) {
    if (appState.screenerSortColumn === column) {
        appState.screenerSortDirection = appState.screenerSortDirection === "asc" ? "desc" : "asc";
    } else {
        appState.screenerSortColumn = column;
        if (["Overall_Rank", "MS_Score", "CMP", "Entry", "Stop_Loss", "Risk_Pct", "Days_To_Earnings"].includes(column)) {
            appState.screenerSortDirection = (column === "Overall_Rank" || column === "Days_To_Earnings") ? "asc" : "desc";
        } else {
            appState.screenerSortDirection = "asc";
        }
    }
    renderFilteredWatchlist();
}

function updateScreenerHeaderSortIcons() {
    const headers = document.querySelectorAll("#screener-table-header th[onclick]");
    headers.forEach(th => {
        const onclickAttr = th.getAttribute("onclick");
        if (!onclickAttr) return;
        const match = onclickAttr.match(/sortScreener\('([^']+)'\)/);
        if (!match) return;
        const colName = match[1];

        const iconSpan = th.querySelector(".sort-icon");
        if (!iconSpan) return;

        if (appState.screenerSortColumn === colName) {
            iconSpan.innerHTML = appState.screenerSortDirection === "asc" 
                ? ' <i class="fa-solid fa-sort-up" style="color: var(--accent-purple); margin-left: 4px;"></i>' 
                : ' <i class="fa-solid fa-sort-down" style="color: var(--accent-purple); margin-left: 4px;"></i>';
        } else {
            iconSpan.innerHTML = ' <i class="fa-solid fa-sort" style="color: var(--text-muted); opacity: 0.3; margin-left: 4px;"></i>';
        }
    });
}

window.sortScreener = sortScreener;
window.updateScreenerHeaderSortIcons = updateScreenerHeaderSortIcons;

window.applyStocksFilters = function() {
    window.renderFilteredWatchlist();
    showToast("Watchlist filters applied!", "success");
};

window.resetStocksFilters = function() {
    const checkboxes = document.querySelectorAll(".filter-checkbox");
    checkboxes.forEach(chk => chk.checked = true);
    
    const select = document.getElementById("filter-industry-select");
    if (select) select.value = "ALL";
    
    
    
    window.renderFilteredWatchlist();
    showToast("Filters reset to default.", "info");
};

window.openTradingViewWatchlistFilterModal = function() {
    const symbols = new Set();
    const rows = document.querySelectorAll("#filtered-watchlist-table-body tr");
    rows.forEach(row => {
        const symbolCell = row.querySelector("span.stock-symbol");
        if (symbolCell) {
            const symText = symbolCell.textContent.trim().toUpperCase();
            if (symText) {
                symbols.add(symText);
            }
        }
    });

    const symList = Array.from(symbols);
    const formattedList = symList.map(s => {
        if (!s.startsWith("NSE:") && !s.startsWith("BSE:")) {
            return "NSE:" + s;
        }
        return s;
    });

    const textarea = document.getElementById("tv-tickers-textarea");
    const countSpan = document.getElementById("tv-tickers-count");
    
    if (!textarea || !countSpan) return;
    
    if (formattedList.length === 0) {
        textarea.value = "No filtered stocks found.";
        countSpan.textContent = "0";
    } else {
        textarea.value = formattedList.join(",");
        countSpan.textContent = formattedList.length;
    }
    
    document.getElementById("tv-watchlist-modal").style.display = "flex";
};

// Daily Action Report Renderer
async function renderDailyReport() {
    const loadingState = document.getElementById("daily-report-loading-state");
    const contentArea = document.getElementById("daily-report-content");
    if (!loadingState || !contentArea) return;

    loadingState.style.display = "block";
    contentArea.style.display = "none";

    try {
        const activeDate = appState.date || "";
        
        // 1. Fetch Market Breadth
        let mbData = appState.marketBreadth;
        if (!mbData) {
            let mbUrl = `/api/market_breadth`;
            if (activeDate) mbUrl += `?date=${activeDate}`;
            const mbRes = await fetch(mbUrl);
            mbData = await mbRes.json();
        }

        // 2. Fetch Sector Rotation (all industries)
        let rotData = appState.sectorRotation;
        if (!rotData || rotData.length === 0) {
            let rotUrl = `/api/sector_rotation`;
            if (activeDate) rotUrl += `?date=${activeDate}`;
            const rotRes = await fetch(rotUrl);
            rotData = await rotRes.json();
        }

        // 3. Fetch Sector Rotation History (for exits and warning logs)
        let historyData = [];
        try {
            const historyRes = await fetch("/api/sector_rotation_history");
            historyData = await historyRes.json();
        } catch (hErr) {
            console.error("Failed to load rotation history:", hErr);
        }

        // RENDER MARKET HEALTH
        let marketHealthHtml = "";
        if (mbData) {
            const index = mbData.Index !== undefined ? mbData.Index : 0;
            const status = mbData.Status || "Neutral";
            const chg1d = mbData.Change_1D || 0;
            const chg3d = mbData.Change_3D || 0;
            const chg5d = mbData.Change_5D || 0;

            const formatChg = (val) => {
                if (val > 0) return `<span style="color: var(--accent-green);">+${val.toFixed(1)}</span>`;
                if (val < 0) return `<span style="color: var(--accent-red);">${val.toFixed(1)}</span>`;
                return `<span>0.0</span>`;
            };

            const indicators = mbData.Indicators || {};
            const formatBar = (pct, label, colorClass) => {
                return `
                    <div class="mhealth-indicator-row">
                        <div class="mhealth-indicator-header">
                            <span>${label}</span>
                            <span>${pct !== undefined ? pct.toFixed(1) : 0}%</span>
                        </div>
                        <div class="mhealth-indicator-bar-bg">
                            <div class="mhealth-indicator-bar-fill" style="width: ${pct || 0}%; background: ${colorClass};"></div>
                        </div>
                    </div>
                `;
            };

            // Custom posture recommendation text matching report
            let recText = "Caution: Be selective: reduced size, A-setups only — prefer ✓P-confirmed focus industries. REV signals remain valid.";
            if (status === "Green" || status === "Strong") {
                recText = "Favorable: Selectively add exposure, focus on strong leader breakouts in primary focus groups.";
            } else if (status === "Red" || status === "Avoid") {
                recText = "Defensive: High risk of capital loss. Avoid new positions, raise cash, protect capital.";
            }

            marketHealthHtml = `
                <div class="report-section">
                    <h3 class="report-section-title"><i class="fa-solid fa-heart-pulse" style="color: var(--accent-red);"></i> 1 Market Health</h3>
                    <div class="market-health-container">
                        <div class="mhealth-score-card">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Market Breadth Index</div>
                            <div class="mhealth-score-num">${index.toFixed(1)}</div>
                            <div class="mhealth-deltas">
                                <span>1D ${formatChg(chg1d)}</span>
                                <span>3D ${formatChg(chg3d)}</span>
                                <span>5D ${formatChg(chg5d)}</span>
                            </div>
                            <div class="badge ${status.toLowerCase()}" style="font-size: 13px; padding: 6px 16px; font-weight: 700; border-radius: 6px;">${status}</div>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 16px;">
                            <div class="mhealth-indicators-grid">
                                ${formatBar(indicators.Above20EMA || 0, "Stocks above 20-SMA", "var(--accent-blue)")}
                                ${formatBar(indicators.Above50SMA || 0, "Stocks above 50-SMA", "var(--accent-yellow)")}
                                ${formatBar(indicators.Above200SMA || 0, "Stocks above 200-SMA", "var(--accent-purple)")}
                                ${formatBar(indicators.AdvancesDeclines || 0, "Advance / decline", "var(--accent-blue)")}
                                ${formatBar(indicators.Near52WH || 0, "Net new 52w highs-lows", "var(--accent-green)")}
                                ${formatBar(indicators.HighRS || 0, "Stocks with RS ≥ 70", "var(--accent-purple)")}
                            </div>
                            <div style="padding: 12px 16px; border-radius: 8px; background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.2); font-size: 12.5px; line-height: 1.5; color: var(--text-primary);">
                                <strong>Guidance:</strong> ${recText}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        // RENDER FOCUS INDUSTRIES (Ranked top 10)
        let focusHtml = "";
        const focusIndustries = appState.focusIndustries || [];
        if (focusIndustries.length > 0) {
            focusHtml = `
                <div class="report-section">
                    <h3 class="report-section-title"><i class="fa-solid fa-crosshairs" style="color: var(--accent-green);"></i> 2 Focus Industries</h3>
                    <p class="report-section-subtitle">Fresh Early Uptrend entries (streak day 1–3) and Confirmed Uptrend holders, ranked TOGETHER by a validated quality floor — participation ≥ 40% and at least one stock within 10% of its 52-week high — then ✓P confirmation, then combined score.</p>
                    <div class="report-cards-grid">
            `;

            focusIndustries.forEach((item, index) => {
                const rankNum = item.Rank_Num || (index + 1);
                const category = item.Category || "Early Uptrend";
                const streak = item.Streak_Days || 1;
                const isConfirmed = item.P_Confirmed || false;

                let badgeText = "";
                let badgeClass = "";
                if (category === "Confirmed Uptrend") {
                    badgeText = `Confirmed Uptrend · day ${streak}`;
                    badgeClass = "confirmed";
                } else {
                    badgeText = `Early Uptrend · day ${streak}`;
                    badgeClass = "early";
                }

                const formatArrow = (val) => {
                    if (val > 0) return `<span style="color: var(--accent-green); font-weight: 700;">↑</span>`;
                    if (val < 0) return `<span style="color: var(--accent-red); font-weight: 700;">↓</span>`;
                    return `<span>→</span>`;
                };

                const flowVal = item.Flow !== undefined ? item.Flow : (item.Net_Flow_Pct || 0);
                const flowArrow = formatArrow(flowVal);

                // Bar variables
                const ema20 = item.Part_EMA20_Today || 0;
                const sma50 = item.Part_SMA50_Today || 0;
                const highRS = item.Part_RS_Today || 0;
                const near52w = item.Part_52WH_Today || 0;

                const ema20Chg = item.Part_EMA20_Change || 0;
                const sma50Chg = item.Part_SMA50_Change || 0;
                const rsChg = item.Part_RS_Change || 0;
                const whChg = item.Part_52WH_Change || 0;

                const formatChgStr = (val) => {
                    if (val > 0) return ` (+${val.toFixed(0)})`;
                    if (val < 0) return ` (${val.toFixed(0)})`;
                    return "";
                };

                focusHtml += `
                    <div class="report-card">
                        <div class="report-card-header">
                            <div class="report-card-title-section">
                                <span class="report-card-idx">${rankNum}</span>
                                <div>
                                    <h4 class="report-card-name">${item.Industry}</h4>
                                    <div class="report-card-badges">
                                        <span class="report-badge ${badgeClass}">${badgeText}</span>
                                        ${isConfirmed ? `<span class="report-badge confirmed"><i class="fa-solid fa-circle-check"></i> ✓P confirmed</span>` : ""}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <p class="report-card-desc">${item.Explanation || `Day ${streak} · structure + flow already dual-confirmed — established context.`}</p>

                        <div class="report-card-metrics">
                            <div class="report-metric-col">
                                <span class="report-metric-lbl">Breadth</span>
                                <span class="report-metric-val">${(item.Breadth || 0).toFixed(1)}%</span>
                            </div>
                            <div class="report-metric-col">
                                <span class="report-metric-lbl">Flow</span>
                                <span class="report-metric-val" style="display: inline-flex; align-items: center; gap: 3px;">
                                    ${flowArrow} ${flowVal > 0 ? '+' : ''}${flowVal.toFixed(1)}
                                    ${item.Failure_Days > 0 ? `<span style="font-size: 8.5px; font-weight: bold; background: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); padding: 0px 3px; border-radius: 2px;" title="Grace Period Warning (Failure Day ${item.Failure_Days})">W</span>` : ''}
                                </span>
                            </div>
                            <div class="report-metric-col">
                                <span class="report-metric-lbl">Part.</span>
                                <span class="report-metric-val">${(item.Part_EMA20_Today || 0).toFixed(0)}%</span>
                            </div>
                            <div class="report-metric-col">
                                <span class="report-metric-lbl">Score</span>
                                <span class="report-metric-val">${(item.Sort_Score || 0).toFixed(0)}</span>
                            </div>
                            <div class="report-metric-col">
                                <span class="report-metric-lbl">Avg RS</span>
                                <span class="report-metric-val">${(item.Part_RS_Today || 0).toFixed(0)}</span>
                            </div>
                        </div>

                        <div class="report-card-bars-grid">
                            <div class="report-card-bar-row">
                                <div class="report-card-bar-lbl">
                                    <span>ABOVE 50-SMA</span>
                                    <span>${sma50.toFixed(0)}%<span class="change" style="color: ${sma50Chg >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'};">${formatChgStr(sma50Chg)}</span></span>
                                </div>
                                <div class="report-card-bar-bg">
                                    <div class="report-card-bar-fill" style="width: ${sma50}%; background: var(--accent-yellow);"></div>
                                </div>
                            </div>
                            <div class="report-card-bar-row">
                                <div class="report-card-bar-lbl">
                                    <span>RS ≥ 70</span>
                                    <span>${highRS.toFixed(0)}%<span class="change" style="color: ${rsChg >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'};">${formatChgStr(rsChg)}</span></span>
                                </div>
                                <div class="report-card-bar-bg">
                                    <div class="report-card-bar-fill" style="width: ${highRS}%; background: var(--accent-purple);"></div>
                                </div>
                            </div>
                            <div class="report-card-bar-row">
                                <div class="report-card-bar-lbl">
                                    <span>ABOVE 20-SMA</span>
                                    <span>${ema20.toFixed(0)}%<span class="change" style="color: ${ema20Chg >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'};">${formatChgStr(ema20Chg)}</span></span>
                                </div>
                                <div class="report-card-bar-bg">
                                    <div class="report-card-bar-fill" style="width: ${ema20}%; background: var(--accent-blue);"></div>
                                </div>
                            </div>
                            <div class="report-card-bar-row">
                                <div class="report-card-bar-lbl">
                                    <span>NEAR 52W HIGH</span>
                                    <span>${near52w.toFixed(0)}%<span class="change" style="color: ${whChg >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'};">${formatChgStr(whChg)}</span></span>
                                </div>
                                <div class="report-card-bar-bg">
                                    <div class="report-card-bar-fill" style="width: ${near52w}%; background: var(--accent-green);"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });

            focusHtml += `
                    </div>
                </div>
            `;
        }

        // RENDER BUILDING INTEREST
        let buildingInterestHtml = "";
        const biList = rotData.filter(item => {
            const hasLeader = (item.Part_52WH_Today > 0.0);
            const cat = item.Category || "Avoid";
            const ema20 = item.Part_EMA20_Today || 0;
            return (cat === "Avoid" || cat === "Consolidation") && hasLeader && ema20 < 40.0;
        });

        if (biList.length > 0) {
            buildingInterestHtml = `
                <div class="report-section">
                    <h3 class="report-section-title"><i class="fa-solid fa-hourglass-start" style="color: var(--accent-blue);"></i> 3 Building Interest</h3>
                    <p class="report-section-subtitle">Industries that correctly missed the quality floor on participation alone — real leadership already exists (a constituent within 10% of its 52-week high), broader participation just hasn't caught up yet.</p>
                    <div class="building-interest-grid">
            `;

            biList.forEach(item => {
                const near52w = item.Part_52WH_Today || 0;
                const part = item.Part_EMA20_Today || 0;
                const streak = item.Streak_Days || 1;
                const score = item.Sort_Score || (item.Avg_Return_10D + item.Part_EMA20_Today / 10);

                buildingInterestHtml += `
                    <div class="building-interest-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
                            <h4 style="font-size: 13px; font-weight: 750; color: var(--text-primary); margin: 0; line-height: 1.4;">${item.Industry}</h4>
                            <span class="report-badge early" style="font-size: 9px; padding: 1px 4px; white-space: nowrap;">Early Stage · ${streak}d</span>
                        </div>
                        <p style="font-size: 11px; color: var(--text-secondary); margin: 0; line-height: 1.4;">Leadership confirmed — ${near52w.toFixed(0)}% near 52w high; participation still at ${part.toFixed(0)}%.</p>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px; margin-top: 4px;">
                            <div><span style="color: var(--text-secondary);">Near 52W:</span> <strong>${near52w.toFixed(0)}%</strong></div>
                            <div><span style="color: var(--text-secondary);">Score:</span> <strong>${score.toFixed(0)}</strong></div>
                            <div><span style="color: var(--text-secondary);">Part:</span> <strong>${part.toFixed(0)}%</strong></div>
                            <div><span style="color: var(--text-secondary);">Pocket Pivots:</span> <strong>${(item.Pocket_Pivot_Pct || 0).toFixed(0)}%</strong></div>
                        </div>
                    </div>
                `;
            });

            buildingInterestHtml += `
                    </div>
                </div>
            `;
        }

        // RENDER QUALITY IN AVOID & SECTOR TAILWIND WATCH
        let qualityAvoidHtml = "";
        const qaList = rotData.filter(item => {
            const hasLeader = (item.Part_52WH_Today > 0.0);
            const cat = item.Category || "Avoid";
            const ema20 = item.Part_EMA20_Today || 0;
            return (cat === "Avoid" || cat === "Consolidation") && ema20 >= 40.0 && hasLeader;
        });

        // Tailwind watch: Avoid zone industries sitting in a focus sector
        const focusSectors = new Set(focusIndustries.map(x => (x.Sector || "Others").trim().toUpperCase()));
        const twList = rotData.filter(item => {
            const cat = item.Category || "Avoid";
            const parentSec = (item.Sector || "Others").trim().toUpperCase();
            return cat === "Avoid" && focusSectors.has(parentSec);
        });

        if (qaList.length > 0 || twList.length > 0) {
            qualityAvoidHtml = `
                <div class="daily-report-grid-2col">
                    <div class="report-section">
                        <h3 class="report-section-title"><i class="fa-solid fa-arrow-trend-up" style="color: var(--accent-purple);"></i> 4 Quality in Avoid</h3>
                        <p class="report-section-subtitle">Avoid/Consolidation-zone industries whose internals clear the focus-grade quality floor today.</p>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
            `;

            if (qaList.length === 0) {
                qualityAvoidHtml += `<div style="font-size: 12px; color: var(--text-secondary); text-align: center; padding: 20px;">No candidates qualified today.</div>`;
            } else {
                qaList.slice(0, 10).forEach(item => {
                    qualityAvoidHtml += `
                        <div class="glass" style="padding: 12px 16px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border-color);">
                            <span style="font-size: 12.5px; font-weight: 700; color: var(--text-primary);">${item.Industry}</span>
                            <span style="font-size: 11px; color: var(--text-secondary);">part. ${item.Part_EMA20_Today.toFixed(0)}% · 52wH ${item.Part_52WH_Today.toFixed(0)}% · score ${(item.Sort_Score || 0).toFixed(0)}</span>
                        </div>
                    `;
                });
            }

            qualityAvoidHtml += `
                        </div>
                    </div>
                    <div class="report-section">
                        <h3 class="report-section-title"><i class="fa-solid fa-wind" style="color: var(--accent-blue);"></i> 6 Sector Tailwind Watch</h3>
                        <p class="report-section-subtitle">Avoid-zone industries sitting in an already-constructive sector.</p>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
            `;

            if (twList.length === 0) {
                qualityAvoidHtml += `<div style="font-size: 12px; color: var(--text-secondary); text-align: center; padding: 20px;">No candidates qualified today.</div>`;
            } else {
                twList.slice(0, 10).forEach(item => {
                    qualityAvoidHtml += `
                        <div class="glass" style="padding: 12px 16px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border-color);">
                            <span style="font-size: 12.5px; font-weight: 700; color: var(--text-primary);">${item.Industry}</span>
                            <span style="font-size: 11px; color: var(--text-secondary);">sector ${item.Sector} · score ${(item.Sort_Score || 0).toFixed(0)}</span>
                        </div>
                    `;
                });
            }

            qualityAvoidHtml += `
                        </div>
                    </div>
                </div>
            `;
        }

        // RENDER SECTOR CONTEXT
        let sectorContextHtml = "";
        if (rotData.length > 0) {
            const categories = {
                "Confirmed Uptrend": [],
                "Early Uptrend": [],
                "Consolidation": [],
                "Downtrend Warning": [],
                "Avoid": [],
                "Neutral": []
            };

            rotData.forEach(item => {
                const cat = item.Category || "Neutral";
                if (categories[cat]) {
                    categories[cat].push(item);
                } else {
                    categories["Neutral"].push(item);
                }
            });

            const total = rotData.length;
            const confirmedPct = (categories["Confirmed Uptrend"].length / total) * 100;
            const earlyPct = (categories["Early Uptrend"].length / total) * 100;
            const steadyPct = (categories["Consolidation"].length / total) * 100;
            const distPct = (categories["Downtrend Warning"].length / total) * 100;
            const avoidPct = (categories["Avoid"].length / total) * 100;
            const neutralPct = (categories["Neutral"].length / total) * 100;

            sectorContextHtml = `
                <div class="report-section">
                    <h3 class="report-section-title"><i class="fa-solid fa-chart-pie" style="color: var(--accent-purple);"></i> 5 Sector Context</h3>
                    <p class="report-section-subtitle">Zone mix across ${total} industries (${((distPct + avoidPct)).toFixed(0)}% under downtrend warning/avoid).</p>
                    
                    <div class="sector-stack-container">
                        ${confirmedPct > 0 ? `<div class="sector-stack-bar" style="width: ${confirmedPct}%; background: var(--accent-green);" title="Confirmed Uptrend: ${categories["Confirmed Uptrend"].length} industries"></div>` : ''}
                        ${earlyPct > 0 ? `<div class="sector-stack-bar" style="width: ${earlyPct}%; background: var(--accent-blue);" title="Early Uptrend: ${categories["Early Uptrend"].length} industries"></div>` : ''}
                        ${steadyPct > 0 ? `<div class="sector-stack-bar" style="width: ${steadyPct}%; background: var(--accent-yellow);" title="Consolidation: ${categories["Consolidation"].length} industries"></div>` : ''}
                        ${distPct > 0 ? `<div class="sector-stack-bar" style="width: ${distPct}%; background: #ea580c;" title="Downtrend Warning: ${categories["Downtrend Warning"].length} industries"></div>` : ''}
                        ${avoidPct > 0 ? `<div class="sector-stack-bar" style="width: ${avoidPct}%; background: var(--accent-red);" title="Avoid: ${categories["Avoid"].length} industries"></div>` : ''}
                        ${neutralPct > 0 ? `<div class="sector-stack-bar" style="width: ${neutralPct}%; background: #6b7280;" title="No Data: ${categories["Neutral"].length} industries"></div>` : ''}
                    </div>

                    <div class="sector-legend">
                        <div class="sector-legend-item"><span class="sector-legend-color" style="background: var(--accent-green);"></span> Confirmed Uptrend (${categories["Confirmed Uptrend"].length})</div>
                        <div class="sector-legend-item"><span class="sector-legend-color" style="background: var(--accent-blue);"></span> Early Uptrend (${categories["Early Uptrend"].length})</div>
                        <div class="sector-legend-item"><span class="sector-legend-color" style="background: var(--accent-yellow);"></span> Consolidation (${categories["Consolidation"].length})</div>
                        <div class="sector-legend-item"><span class="sector-legend-color" style="background: #ea580c;"></span> Downtrend Warning (${categories["Downtrend Warning"].length})</div>
                        <div class="sector-legend-item"><span class="sector-legend-color" style="background: var(--accent-red);"></span> Avoid (${categories["Avoid"].length})</div>
                        ${categories["Neutral"].length > 0 ? `<div class="sector-legend-item"><span class="sector-legend-color" style="background: #6b7280;"></span> No Data (${categories["Neutral"].length})</div>` : ''}
                    </div>

                    <div class="sector-grid">
            `;

            // Display a few key focus industries with badges
            const keySectors = rotData.filter(x => x.Category !== "Avoid" && x.Category !== "Neutral").slice(0, 15);
            if (keySectors.length === 0) {
                sectorContextHtml += `<div style="grid-column: span 5; font-size: 12px; color: var(--text-secondary); text-align: center; padding: 20px;">No active sectors in constructive zones today.</div>`;
            } else {
                keySectors.forEach(item => {
                    let dotColor = "var(--accent-red)";
                    if (item.Category === "Confirmed Uptrend") dotColor = "var(--accent-green)";
                    else if (item.Category === "Early Uptrend") dotColor = "var(--accent-blue)";
                    else if (item.Category === "Consolidation") dotColor = "var(--accent-yellow)";
                    else if (item.Category === "Downtrend Warning") dotColor = "#ea580c";

                    sectorContextHtml += `
                        <div class="sector-grid-item">
                            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 130px;" title="${item.Industry}">${item.Industry}</span>
                            <span style="display: inline-flex; align-items: center; gap: 4px; font-size: 10px; color: var(--text-secondary);">
                                <span style="width: 6px; height: 6px; border-radius: 50%; background: ${dotColor};"></span>
                                ${item.Streak_Days}d
                            </span>
                        </div>
                    `;
                });
            }

            sectorContextHtml += `
                    </div>
                </div>
            `;
        }

        // RENDER WARNINGS & EXITS (From History logs)
        let warningsHtml = "";
        const exits = [];
        const distWarnings = [];

        if (historyData && historyData.length > 0) {
            // Get today's changes
            const latestLog = historyData[0];
            if (latestLog && latestLog.Changes) {
                latestLog.Changes.forEach(change => {
                    const desc = change.Description || "";
                    if (change.Type === "LOSE_LEADERSHIP" || desc.includes("Category changed")) {
                        // Check if it exited from Confirmed Uptrend or Early Uptrend
                        if (desc.includes("changed from 'Confirmed Uptrend'") || desc.includes("changed from 'Early Uptrend'") || desc.includes("faded")) {
                            exits.push({
                                industry: change.Industry,
                                description: change.Description,
                                reason: change.Reason
                            });
                        } else if (desc.includes("to 'Downtrend Warning'") || desc.includes("to 'Avoid'")) {
                            distWarnings.push({
                                industry: change.Industry,
                                description: change.Description,
                                reason: change.Reason
                            });
                        }
                    }
                });
            }
        }

        if (exits.length > 0 || distWarnings.length > 0) {
            warningsHtml = `
                <div class="report-section">
                    <h3 class="report-section-title"><i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-yellow);"></i> 7 Warnings</h3>
                    <div style="display: flex; flex-direction: column; gap: 12px;">
            `;

            if (exits.length > 0) {
                exits.forEach(w => {
                    warningsHtml += `
                        <div class="warning-item red">
                            <i class="fa-solid fa-ban warning-icon red"></i>
                            <div class="warning-text">
                                <strong>${w.industry}</strong> broke into distribution today (confirmed exit from focus zones).
                                <span class="details">${w.description}. Reason: ${w.reason || 'Broad participation deterioration.'}</span>
                            </div>
                        </div>
                    `;
                });
            }

            if (distWarnings.length > 0) {
                distWarnings.forEach(w => {
                    warningsHtml += `
                        <div class="warning-item yellow">
                            <i class="fa-solid fa-triangle-exclamation warning-icon yellow"></i>
                            <div class="warning-text">
                                <strong>${w.industry}</strong> entered distribution warning zone.
                                <span class="details">${w.description}. Reason: ${w.reason || 'Breadth drop below critical thresholds.'}</span>
                            </div>
                        </div>
                    `;
                });
            }

            warningsHtml += `
                    </div>
                </div>
            `;
        }

        // RENDER PERFORMANCE TRACKING
        let perfHtml = `
            <div class="report-section">
                <h3 class="report-section-title"><i class="fa-solid fa-chart-line" style="color: var(--accent-green);"></i> 8 Performance Tracking</h3>
                <p class="report-section-subtitle">Verification check on how prior day's Focus Industries have actually done since first flagged.</p>
                <div class="table-container glass" style="margin: 0; padding: 0; border: 1px solid var(--border-color); border-radius: 10px; overflow: hidden; background: rgba(0,0,0,0.15);">
                    <table class="watchlist-table" style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12px;">
                        <thead>
                            <tr style="background: rgba(255,255,255,0.02); border-bottom: 1px solid var(--border-color);">
                                <th style="padding: 12px; font-weight: 700; color: var(--text-secondary);">Industry</th>
                                <th style="padding: 12px; font-weight: 700; color: var(--text-secondary); text-align: center;">Days Featured</th>
                                <th style="padding: 12px; font-weight: 700; color: var(--text-secondary); text-align: center;">Since Appearance</th>
                                <th style="padding: 12px; font-weight: 700; color: var(--text-secondary); text-align: center;">Today</th>
                                <th style="padding: 12px; font-weight: 700; color: var(--text-secondary); text-align: center;">Adv / Dec</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        // Render rows for the top focus industries
        const focusItems = focusIndustries.slice(0, 8);
        if (focusItems.length === 0) {
            perfHtml += `<tr><td colspan="5" style="padding: 20px; text-align: center; color: var(--text-secondary);">No focus industries under tracking.</td></tr>`;
        } else {
            focusItems.forEach(item => {
                const streak = item.Streak_Days || 1;
                const return10 = item.Avg_Return_10D || 0;
                const returnToday = item.Avg_Return_Today || 0;
                
                // Count advances and declines in constituents
                let adv = 0, dec = 0;
                (item.Stock_Details || []).forEach(s => {
                    const ret = s.Ret_Today || 0;
                    if (ret > 0) adv++;
                    else if (ret < 0) dec++;
                });
                const totalStocks = (item.Stock_Details || []).length || item.ActiveStocks || 0;

                const formatColor = (val) => {
                    if (val > 0) return `color: var(--accent-green); font-weight: 700;`;
                    if (val < 0) return `color: var(--accent-red); font-weight: 700;`;
                    return `color: var(--text-primary);`;
                };

                perfHtml += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.02);">
                        <td style="padding: 12px; font-weight: 700; color: var(--text-primary);">${item.Industry}</td>
                        <td style="padding: 12px; text-align: center; color: var(--text-secondary);">${streak} (new)</td>
                        <td style="padding: 12px; text-align: center; ${formatColor(return10)}">${return10 > 0 ? '+' : ''}${return10.toFixed(1)}%</td>
                        <td style="padding: 12px; text-align: center; ${formatColor(returnToday)}">${returnToday > 0 ? '+' : ''}${returnToday.toFixed(1)}%</td>
                        <td style="padding: 12px; text-align: center; color: var(--text-secondary);">${adv}↑ / ${dec}↓ of ${totalStocks}</td>
                    </tr>
                `;
            });
        }

        perfHtml += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        // Assemble the full report layout
        contentArea.innerHTML = `
            <div class="daily-report-grid">
                ${marketHealthHtml}
                ${focusHtml}
                ${buildingInterestHtml}
                ${qualityAvoidHtml}
                ${sectorContextHtml}
                ${warningsHtml}
                ${perfHtml}
            </div>
        `;

        loadingState.style.display = "none";
        contentArea.style.display = "flex";

    } catch (err) {
        console.error("Failed to render daily action report:", err);
        loadingState.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation fa-3x" style="color: var(--accent-red); margin-bottom: 15px;"></i>
            <span style="display: block; font-weight: 700; color: var(--text-primary);">Failed to Load Action Report</span>
            <span style="font-size: 12px; color: var(--text-secondary); margin-top: 5px; display: block;">${err.message}</span>
        `;
    }
}

// Search and stock to find its industry and scores
window.handleSectorStockSearch = function(query) {
    const inputVal = query.trim().toUpperCase();
    const resultsContainer = document.getElementById("sector-stock-search-results");
    if (!resultsContainer) return;

    if (!inputVal) {
        resultsContainer.style.display = "none";
        resultsContainer.innerHTML = "";
        return;
    }

    const rotationData = appState.sectorRotation || [];
    const matchedStocks = [];

    rotationData.forEach(ind => {
        const stocks = ind.Stock_Details || [];
        stocks.forEach(s => {
            if (s.Symbol.toUpperCase().includes(inputVal)) {
                matchedStocks.push({
                    symbol: s.Symbol,
                    companyName: s.Company_Name,
                    industry: ind.Industry,
                    category: ind.Category,
                    score: s.Rank_Score
                });
            }
        });
    });

    if (matchedStocks.length === 0) {
        resultsContainer.style.display = "flex";
        resultsContainer.innerHTML = `
            <span style="font-size: 12px; color: var(--text-secondary);">No matching stocks found in any industry.</span>
        `;
        return;
    }

    // Limit to top 5 results for clean UI
    const displayed = matchedStocks.slice(0, 5);

    let html = `
        <span style="font-size: 12px; color: var(--text-secondary); font-weight: bold; margin-right: 8px;">Matches:</span>
    `;

    displayed.forEach(stock => {
        let dotColor = "#94a3b8";
        if (stock.category === "Confirmed Uptrend") dotColor = "var(--accent-green)";
        else if (stock.category === "Early Uptrend") dotColor = "var(--accent-blue)";
        else if (stock.category === "Consolidation") dotColor = "var(--accent-yellow)";
        else if (stock.category === "Downtrend Warning") dotColor = "#ea580c";
        else if (stock.category === "Avoid") dotColor = "var(--accent-red)";

        html += `
            <div class="glass" style="display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border: 1px solid var(--border-color); border-radius: 6px; font-size: 12px; background: rgba(255, 255, 255, 0.03); margin-right: 6px; margin-bottom: 4px;">
                <strong style="color: var(--text-primary); font-family: monospace;">${stock.symbol}</strong>
                <span style="color: var(--text-secondary); font-size: 11px;">(${stock.companyName})</span>
                <span style="color: var(--text-secondary);">→</span>
                <span onclick="if (typeof window.openIndustryDeepDive === 'function') { window.openIndustryDeepDive('${stock.industry.replace(/'/g, "\\'")}'); }" style="cursor: pointer; font-weight: bold; color: var(--accent-purple); text-decoration: underline; display: inline-flex; align-items: center; gap: 4px;">
                    <span style="width: 6px; height: 6px; border-radius: 50%; background: ${dotColor};"></span>
                    ${stock.industry}
                </span>
            </div>
        `;
    });

    if (matchedStocks.length > 5) {
        html += `
            <span style="font-size: 11px; color: var(--text-secondary); margin-left: 4px; display: inline-block;">+ ${matchedStocks.length - 5} more</span>
        `;
    }

    resultsContainer.style.display = "flex";
    resultsContainer.innerHTML = html;
};

// ============================================================================
// POST-ENTRY TRADE MANAGEMENT ENGINE UI
// ============================================================================
let pmCorrelationChartInstance = null;

if (window.pmTimelineLimitTo10Days === undefined) {
    window.pmTimelineLimitTo10Days = true;
}
if (window.pmSelectedTimelineSymbol === undefined) {
    window.pmSelectedTimelineSymbol = null;
}
if (window.pmHistoryPositions === undefined) {
    window.pmHistoryPositions = [];
}

async function renderPortfolioManagement() {
    const tableBody = document.getElementById("pm-active-trades-table-body");
    const alertsContainer = document.getElementById("pm-alerts-container");
    if (!tableBody || !alertsContainer) return;

    // Set up action filter change listener
    const actionFilter = document.getElementById("pm-filter-action");
    if (actionFilter && !actionFilter.dataset.listenerBound) {
        actionFilter.dataset.listenerBound = "true";
        actionFilter.addEventListener("change", () => {
            if (window.pmLastReportTrades) {
                renderPortfolioManagementTable(window.pmLastReportTrades, actionFilter.value);
            }
        });
    }

    try {
        const response = await fetch("/api/portfolio_management");
        if (!response.ok) throw new Error("Failed to fetch trade management report");
        const data = await response.json();
        
        const trades = data.trades || [];
        window.pmLastReportTrades = trades; // Cache globally

        const totalTrades = trades.length;
        let avgEqs = 100;
        let avgTbs = 100;
        let avgFci = 0;
        let dominantRegime = "Category 2 (Strong)";

        if (totalTrades > 0) {
            avgEqs = Math.round(trades.reduce((sum, t) => sum + (t.eqs !== undefined ? t.eqs : 100), 0) / totalTrades);
            avgTbs = Math.round(trades.reduce((sum, t) => sum + (t.tbs !== undefined ? t.tbs : 100), 0) / totalTrades);
            avgFci = Math.round(trades.reduce((sum, t) => sum + (t.fci !== undefined ? t.fci : 0), 0) / totalTrades);

            const counts = {};
            trades.forEach(t => {
                const reg = t.expectancy_regime || "Category 2 (Strong)";
                counts[reg] = (counts[reg] || 0) + 1;
            });
            let maxCount = -1;
            for (const reg in counts) {
                if (counts[reg] > maxCount) {
                    maxCount = counts[reg];
                    dominantRegime = reg;
                }
            }
        }

        // Set KPI Text Contents
        document.getElementById("pm-avg-eqs").textContent = totalTrades > 0 ? avgEqs : "N/A";
        document.getElementById("pm-avg-tbs").textContent = totalTrades > 0 ? avgTbs : "N/A";
        document.getElementById("pm-fci").textContent = totalTrades > 0 ? `${avgFci}%` : "0%";
        document.getElementById("pm-expectancy-regime").textContent = dominantRegime;
        document.getElementById("pm-regime-desc").textContent = totalTrades > 0 ? `Dominant regime for ${totalTrades} open positions` : "No active positions";

        // Style KPI colors dynamically
        const eqsEl = document.getElementById("pm-avg-eqs");
        if (eqsEl) {
            if (avgEqs >= 85) eqsEl.style.color = "var(--accent-green)";
            else if (avgEqs >= 70) eqsEl.style.color = "var(--accent-blue)";
            else eqsEl.style.color = "var(--accent-red)";
        }

        const tbsEl = document.getElementById("pm-avg-tbs");
        if (tbsEl) {
            if (avgTbs >= 85) tbsEl.style.color = "var(--accent-green)";
            else if (avgTbs >= 70) tbsEl.style.color = "var(--accent-blue)";
            else tbsEl.style.color = "var(--accent-red)";
        }

        // Set last updated timestamp
        const lastUpdatedEl = document.getElementById("pm-last-updated");
        if (lastUpdatedEl) {
            lastUpdatedEl.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        }

        // Fetch history data for explainable timeline
        try {
            const histRes = await fetch("/api/portfolio_management_history");
            if (histRes.ok) {
                const histData = await histRes.json();
                window.pmHistoryPositions = histData.positions || [];
                
                // Set default selected symbol if none selected
                if (window.pmHistoryPositions.length > 0) {
                    const activeSymbols = window.pmHistoryPositions.map(p => p.symbol.toUpperCase());
                    if (!window.pmSelectedTimelineSymbol || !activeSymbols.includes(window.pmSelectedTimelineSymbol.toUpperCase())) {
                        window.pmSelectedTimelineSymbol = window.pmHistoryPositions[0].symbol;
                    }
                }
            } else {
                console.error("Failed to fetch portfolio management history");
            }
        } catch (histError) {
            console.error("Error loading portfolio management history:", histError);
        }

        // Render sections
        renderPortfolioManagementAlerts(trades, alertsContainer);
        renderPortfolioManagementTable(trades, actionFilter ? actionFilter.value : "ALL");
        renderExpectancyRegimeStats(trades);
        renderPortfolioManagementCorrelationChart(trades);
        renderPortfolioManagementTimeline();

    } catch (error) {
        console.error("Error loading portfolio management dashboard:", error);
        if (typeof showToast === "function") {
            showToast("Failed to load Trade Management report.", "error");
        }
    }
}

function renderPortfolioManagementAlerts(trades, container) {
    const alertTrades = trades.filter(t => t.action !== "HOLD");
    
    if (alertTrades.length === 0) {
        container.innerHTML = `
            <div class="no-alerts-state glass" style="grid-column: 1 / -1; padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                <i class="fa-solid fa-check-circle" style="color: var(--accent-green); font-size: 20px; margin-bottom: 8px; display: block;"></i>
                All open trades are aligned. No active exit or trailing stop adjustments required.
            </div>
        `;
        return;
    }

    let html = "";
    alertTrades.forEach(t => {
        let borderLeftColor = "var(--accent-blue)";
        let iconHtml = '<i class="fa-solid fa-circle-info" style="color: var(--accent-blue);"></i>';

        if (t.action.includes("EXIT")) {
            borderLeftColor = "var(--accent-red)";
            iconHtml = '<i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-red);"></i>';
        } else if (t.action === "ADD") {
            borderLeftColor = "var(--accent-purple)";
            iconHtml = '<i class="fa-solid fa-circle-plus" style="color: var(--accent-purple);"></i>';
        }

        const pnl = ((t.current_price - t.entry_price) / t.entry_price * 100);

        html += `
            <div class="glass alert-card" style="padding: 16px; border-radius: 8px; border-left: 4px solid ${borderLeftColor}; display: flex; flex-direction: column; gap: 8px; background: rgba(255, 255, 255, 0.02); border-top: 1px solid var(--border-color); border-right: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        ${iconHtml}
                        <strong style="font-size: 14px; color: var(--text-primary); cursor: pointer;" onclick="selectPMTimelineSymbol('${t.symbol}')">${t.symbol}</strong>
                        <span class="badge" style="font-size: 10px; background: rgba(255,255,255,0.05); color: var(--text-secondary); padding: 2px 6px; border-radius: 4px;">${t.setup_type}</span>
                    </div>
                    <span style="font-size: 12px; font-weight: bold; color: ${pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'};">
                        ${pnl >= 0 ? '+' : ''}${pnl.toFixed(1)}% (${t.r_multiple.toFixed(1)}R)
                    </span>
                </div>
                <div style="font-size: 13px; font-weight: 600; color: var(--text-primary);">
                    Action: ${t.action} ${t.partial_exit_pct ? `(${t.partial_exit_pct}%)` : ''}
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4;">
                    <strong>Stop Recommendation:</strong> ${t.recommended_stop.toFixed(2)} (${t.stop_reason})
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 6px; margin-top: 4px;">
                    <strong>Rationale:</strong> ${t.reasons.join("; ")}
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function toggleActiveTradeHistory(symbol, tradeId) {
    try {
        const targetId = `pm-expand-${tradeId}`;
        const el = document.getElementById(targetId);
        
        if (el) {
            if (el.style.display === "none") {
                // Close any other open sub-tables first
                const allSubTables = document.querySelectorAll('tr[id^="pm-expand-"]');
                allSubTables.forEach(st => st.style.display = "none");
                
                // Build the combined sub-table HTML dynamically on open
                const containerTd = document.getElementById(`pm-expand-content-${tradeId}`);
                if (containerTd) {
                    containerTd.innerHTML = getHistorySubTableHtml(symbol, tradeId);
                }
                
                el.style.display = "table-row";
            } else {
                el.style.display = "none";
            }
        }
    } catch (e) {
        console.error("Error in toggleActiveTradeHistory:", e);
    }
}
window.toggleActiveTradeHistory = toggleActiveTradeHistory;

window.togglePMRowDetails = function(idx) {
    const el = document.getElementById(`pm-detail-${idx}`);
    const chevron = document.getElementById(`pm-chevron-${idx}`);
    if (el) {
        if (el.style.display === "none") {
            el.style.display = "table-row";
            if (chevron) chevron.style.transform = "rotate(180deg)";
        } else {
            el.style.display = "none";
            if (chevron) chevron.style.transform = "rotate(0deg)";
        }
    }
};

function getHistorySubTableHtml(symbol, tradeId) {
    try {
        const position = window.pmHistoryPositions.find(p => p.id === tradeId);
        if (!position) {
            return `
                <div style="padding: 16px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                    <i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-orange); margin-right: 6px; font-size: 15px;"></i>
                    Audit history logs are not loaded yet for ${symbol} (Trade ID: ${tradeId}). Run a daily scan.
                </div>
            `;
        }

        let history = [...position.history];
        history.sort((a, b) => new Date(b.date) - new Date(a.date));

        let rowsHtml = "";
        history.forEach((day, idx) => {
            const prevDay = idx < history.length - 1 ? history[idx + 1] : null;
            const m = day.metrics || {};
            const pm = prevDay && prevDay.metrics ? prevDay.metrics : null;

            // ── P&L ──────────────────────────────────────────────
            const pnl = ((day.current_price - position.entry_price) / position.entry_price * 100);
            const pnlSign = pnl >= 0 ? "+" : "";
            const pnlColor = pnl >= 0 ? "var(--accent-green)" : "var(--accent-red)";
            const rMultSign = day.r_multiple >= 0 ? "+" : "";
            const rColor = day.r_multiple >= 0 ? "var(--accent-green)" : "var(--accent-red)";

            // ── Decision column ───────────────────────────────────
            let decisionIcon = "✅";
            let decisionColor = "var(--accent-green)";
            if (day.action.includes("EXIT")) { decisionIcon = "❌"; decisionColor = "var(--accent-red)"; }
            else if (day.action === "BUY MORE" || day.action === "ADD") { decisionIcon = "➕"; decisionColor = "var(--accent-blue)"; }
            else if (day.action.includes("TRAIL")) { decisionIcon = "🚨"; decisionColor = "var(--accent-orange)"; }

            const decisionHtml = `<span style="color:${decisionColor}; font-weight:800; font-size:12px;">${decisionIcon} ${day.action}</span>
                <div style="color:var(--text-secondary); font-size:10px; margin-top:2px;">
                    <span style="color:${pnlColor}">${pnlSign}${pnl.toFixed(2)}%</span>
                    <span style="color:${rColor}; margin-left:4px;">(${rMultSign}${day.r_multiple.toFixed(2)}R)</span>
                </div>`;

            // ── What Changed Today? (summary label) ───────────────
            const summary = day.day_summary || "Holding Pattern";
            const summaryColor = {
                "Trend Strengthened":    "var(--accent-green)",
                "Breakout Accelerated":  "var(--accent-green)",
                "Trend Confirmed":       "var(--accent-green)",
                "Holding Strong":        "var(--accent-green)",
                "Healthy Pullback":      "var(--accent-blue)",
                "Healthy Consolidation": "var(--accent-blue)",
                "Recovery Attempt":      "var(--accent-blue)",
                "Momentum Slowed":       "var(--accent-orange)",
                "Climax Warning":        "var(--accent-orange)",
                "SL Touched Intraday":   "var(--accent-orange)",
                "Holding Pattern":       "var(--text-secondary)",
                "Partial Profit Taken":  "var(--accent-purple)",
                "Climax — Partial Exit": "var(--accent-purple)",
                "Distribution — Partial Exit": "var(--accent-orange)",
                "Distribution Day":      "var(--accent-red)",
                "SL Breached (Close)":   "var(--accent-red)",
                "Climax Reversal Exit":  "var(--accent-red)",
                "Technical Breakdown":   "var(--accent-red)",
                "Exit Signal":           "var(--accent-red)",
            }[summary] || "var(--text-secondary)";

            // ── Why? (Evidence) ───────────────────────────────────
            let evidence = [];

            // RS delta
            if (m.rs_score !== undefined) {
                const rsPrev = pm ? pm.rs_score : null;
                if (rsPrev !== null) {
                    const rsDiff = parseFloat((m.rs_score - rsPrev).toFixed(1));
                    const rsArrow = rsDiff > 0 ? "↑" : "↓";
                    const rsColor = rsDiff > 0 ? "var(--accent-green)" : "var(--accent-red)";
                    const rsSign = rsDiff > 0 ? "+" : "";
                    evidence.push(`<span style="color:${rsColor}">RS ${rsArrow} (${rsSign}${rsDiff})</span>`);
                }
            }

            // Volume description
            if (m.vol_ratio !== undefined) {
                if (m.is_up_day && m.vol_ratio > 1.2)
                    evidence.push(`<span style="color:var(--accent-green)">Institutional Buying (Vol +${Math.round((m.vol_ratio-1)*100)}%)</span>`);
                else if (!m.is_up_day && m.vol_ratio > 1.2)
                    evidence.push(`<span style="color:var(--accent-red)">Selling Volume ↑ (Vol +${Math.round((m.vol_ratio-1)*100)}%)</span>`);
                else if (m.vdu_ratio < 0.6)
                    evidence.push(`<span style="color:var(--accent-blue)">Selling Volume ↓ (Vol ${Math.round(m.vdu_ratio*100)}% of avg)</span>`);
            }

            // Higher High
            if (m.higher_high)
                evidence.push(`<span style="color:var(--accent-green)">Higher High ✓</span>`);

            // EMA10 distance
            if (m.ema10_dist_pct !== undefined) {
                const distSign = m.ema10_dist_pct >= 0 ? "+" : "";
                const distColor = m.ema10_dist_pct >= 0 ? "var(--accent-green)" : "var(--accent-red)";
                const prevDist = pm ? pm.ema10_dist_pct : null;
                if (prevDist !== null) {
                    evidence.push(`<span style="color:var(--text-secondary)">EMA10 Dist: <span style="color:${distColor}">${prevDist > 0 ? "+" : ""}${prevDist}% → ${distSign}${m.ema10_dist_pct}%</span></span>`);
                }
            }

            // Constitution warnings — always shown red
            (day.reasons || []).filter(r => r.includes("WARNING") || r.includes("Violates") || r.includes("Breach")).forEach(r => {
                evidence.push(`<span style="color:var(--accent-red); font-weight:700"><i class="fa-solid fa-triangle-exclamation"></i> ${r}</span>`);
            });

            const evidenceHtml = evidence.length > 0
                ? evidence.join(`<span style="color:rgba(255,255,255,0.15); margin:0 4px">•</span>`)
                : `<span style="color:var(--text-secondary); font-style:italic">No significant change.</span>`;

            // ── Stop column ───────────────────────────────────────
            let stopHtml;
            if (pm && m.recommended_stop !== pm.recommended_stop) {
                const stopArrow = m.recommended_stop > pm.recommended_stop ? "▲" : "▼";
                const stopColor = m.recommended_stop > pm.recommended_stop ? "var(--accent-green)" : "var(--accent-red)";
                stopHtml = `<span style="color:var(--text-secondary)">₹${pm.recommended_stop}</span> → <strong style="color:${stopColor}">₹${m.recommended_stop} ${stopArrow}</strong>`;
            } else {
                stopHtml = `<span style="color:var(--text-secondary)">No Change</span><div style="font-size:10px; color:var(--text-secondary); margin-top:1px;">(₹${m.recommended_stop || day.recommended_stop})</div>`;
            }

            // ── Confidence column ─────────────────────────────────
            const conf = day.confidence || day.tbs;
            const confColor = conf >= 85 ? "var(--accent-green)" : conf >= 65 ? "var(--accent-orange)" : "var(--accent-red)";

            rowsHtml += `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.04); transition: background 0.15s;" onmouseover="this.style.background='rgba(255,255,255,0.02)'" onmouseout="this.style.background='transparent'">
                    <td style="padding: 10px 12px; font-weight: bold; color: var(--text-secondary); font-size: 11px; white-space: nowrap;">Day ${day.days_active}</td>
                    <td style="padding: 10px 12px; white-space: nowrap;">${decisionHtml}</td>
                    <td style="padding: 10px 12px; font-weight: 700; font-size: 12px; white-space: nowrap; color:${summaryColor};">${summary}</td>
                    <td style="padding: 10px 12px; font-size: 11px; line-height: 1.7; white-space: normal; max-width: 420px;">${evidenceHtml}</td>
                    <td style="padding: 10px 12px; font-size: 11px; white-space: nowrap;">${stopHtml}</td>
                    <td style="padding: 10px 12px; text-align: center; white-space: nowrap;">
                        <span style="font-size: 13px; font-weight: 800; color:${confColor};">${conf}%</span>
                    </td>
                </tr>
            `;
        });

        const initialStop = position.stop_loss || 0;

        return `
            <div style="background: rgba(139, 92, 246, 0.01); border: 1px dashed rgba(255, 255, 255, 0.08); padding: 16px; border-radius: 8px; margin: 4px 0; width: calc(100% - 32px);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px;">
                    <div style="font-size: 12px; text-transform: uppercase; color: var(--accent-purple); font-weight: 800; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-clock-rotate-left"></i> EOD Audit History & Today's Changes: ${symbol}
                    </div>
                    <div style="font-size: 11px; color: var(--text-secondary); background: rgba(0, 0, 0, 0.22); padding: 5px 12px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; gap: 14px; align-items: center;">
                        <span>Entry Price: <strong style="color: var(--text-primary);">₹${position.entry_price.toFixed(2)}</strong></span>
                        <span style="color: rgba(255,255,255,0.15)">|</span>
                        <span>Initial Stop: <strong style="color: var(--accent-orange);">₹${initialStop.toFixed(2)}</strong></span>
                    </div>
                </div>
                <div style="max-height: 400px; overflow-y: auto;">
                    <table class="watchlist-table" style="width: 100%; border-collapse: collapse; text-align: left; background: transparent;">
                        <thead>
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); font-size: 10.5px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600; position: sticky; top: 0; background: var(--bg-dark); z-index: 1;">
                                <th style="padding: 8px 12px; width: 70px;">Day</th>
                                <th style="padding: 8px 12px; width: 110px;">Decision</th>
                                <th style="padding: 8px 12px; width: 160px;">What Changed Today?</th>
                                <th style="padding: 8px 12px;">Why? (Evidence)</th>
                                <th style="padding: 8px 12px; width: 140px;">Stop</th>
                                <th style="padding: 8px 12px; width: 90px; text-align:center;">Confidence</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rowsHtml}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch (e) {
        fetch('/api/client_error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `FATAL ERROR in getHistorySubTableHtml: ${e.message}`,
                stack: e.stack,
                source: 'app.js'
            })
        }).catch(() => {});
        return `<div style="color: var(--accent-red); padding: 12px; font-weight: bold;">Error building history sub-table: ${e.message}</div>`;
    }
}
window.getHistorySubTableHtml = getHistorySubTableHtml;

function renderPortfolioManagementTable(trades, filterVal) {
    const tableBody = document.getElementById("pm-active-trades-table-body");
    if (!tableBody) return;

    let filtered = trades;
    if (filterVal === "EXIT") {
        filtered = trades.filter(t => t.action.includes("EXIT"));
    } else if (filterVal === "TRAIL") {
        filtered = trades.filter(t => t.action.includes("TRAIL"));
    } else if (filterVal === "ADD") {
        filtered = trades.filter(t => t.action === "ADD");
    } else if (filterVal === "HOLD") {
        filtered = trades.filter(t => t.action === "HOLD");
    }

    if (filtered.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 30px; color: var(--text-secondary); font-size: 13px;">
                    No positions found matching the "${filterVal}" action filter.
                </td>
            </tr>
        `;
        return;
    }

    let html = "";
    filtered.forEach(t => {
        const pnl = ((t.current_price - t.entry_price) / t.entry_price * 100);
        const pnlSign = pnl >= 0 ? "+" : "";
        const pnlColor = pnl >= 0 ? "var(--accent-green)" : "var(--accent-red)";
        const rColor = t.r_multiple >= 0 ? "var(--accent-green)" : "var(--accent-red)";

        const getBadgeStyle = (score) => {
            if (score >= 85) return "background: rgba(16, 185, 129, 0.1); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.2);";
            if (score >= 70) return "background: rgba(59, 130, 246, 0.1); color: var(--accent-blue); border: 1px solid rgba(59, 130, 246, 0.2);";
            return "background: rgba(239, 68, 68, 0.1); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.2);";
        };

        let actionBg = "rgba(255,255,255,0.05)";
        let actionColor = "var(--text-secondary)";
        if (t.action.includes("EXIT")) {
            actionBg = "rgba(239, 68, 68, 0.1)";
            actionColor = "var(--accent-red)";
        } else if (t.action === "ADD" || t.action === "BUY MORE") {
            actionBg = "rgba(139, 92, 246, 0.1)";
            actionColor = "var(--accent-purple)";
        } else if (t.action.includes("TRAIL")) {
            actionBg = "rgba(59, 130, 246, 0.1)";
            actionColor = "var(--accent-blue)";
        }

        html += `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s; cursor: pointer;" onclick="toggleActiveTradeHistory('${t.symbol}', '${t.id}')" onmouseover="this.style.background='rgba(255,255,255,0.02)'" onmouseout="this.style.background='transparent'">
                <td style="padding: 12px 10px; font-weight: bold;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="color: var(--accent-blue); font-size: 13px; font-weight: 800;" title="Click row to view chronological audit trail">
                            ${t.symbol}
                        </span>
                        <i class="fa-solid fa-chart-line" onclick="event.stopPropagation(); showAMSDetail('${t.symbol}')" style="cursor: pointer; color: var(--text-secondary); opacity: 0.6; font-size: 11px; transition: opacity 0.2s;" title="View Technical Chart Analysis" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6"></i>
                    </div>
                </td>
                <td style="padding: 12px 10px; font-size: 12px;">
                    <div style="font-weight: 600; color: var(--text-primary);">${t.setup_type}</div>
                    <div style="color: var(--text-secondary); font-size: 11px;">${t.grade} | ${t.days_active} days active</div>
                </td>
                <td style="padding: 12px 10px; font-size: 12px;">
                    <div style="font-weight: bold; color: var(--accent-orange);">${t.earnings_date || 'N/A'}</div>
                    <div style="font-size: 10px; color: var(--text-secondary);">${t.days_to_earnings !== undefined && t.days_to_earnings !== null ? (t.days_to_earnings + 'd left') : ''}</div>
                </td>
                <td style="padding: 12px 10px; font-weight: 600; color: ${pnlColor}; font-size: 13px;">
                    ${pnlSign}${pnl.toFixed(2)}%
                </td>
                <td style="padding: 12px 10px; font-weight: 600; color: ${rColor}; font-size: 13px;">
                    ${t.r_multiple.toFixed(2)}R
                </td>
                <td style="padding: 12px 10px; text-align: center;">
                    <span class="badge" style="padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; ${getBadgeStyle(t.eqs)}">
                        ${t.eqs}
                    </span>
                </td>
                <td style="padding: 12px 10px; text-align: center;">
                    <span class="badge" style="padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; ${getBadgeStyle(t.tbs)}">
                        ${t.tbs}
                    </span>
                </td>
                <td style="padding: 12px 10px; font-size: 12px;">
                    <div style="font-weight: bold; color: var(--accent-orange);">${t.recommended_stop.toFixed(2)}</div>
                    <div style="font-size: 10px; color: var(--text-secondary); max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t.stop_reason}">
                        ${t.stop_reason}
                    </div>
                </td>
                <td style="padding: 12px 10px;">
                    <span class="badge" style="padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; background: ${actionBg}; color: ${actionColor}; border: 1px solid ${actionColor}20;">
                        ${t.action}
                    </span>
                </td>
                <td style="padding: 12px 10px; font-size: 11px; color: var(--text-secondary); max-width: 250px; line-height: 1.3;">
                    ${t.reasons.join("; ")}
                </td>
            </tr>
            
            <!-- Expandable Sub-table Row -->
            <tr id="pm-expand-${t.id}" style="display: none; background: rgba(0,0,0,0.25);">
                <td colspan="10" style="padding: 12px 15px; border-bottom: 1px solid rgba(255,255,255,0.05);" id="pm-expand-content-${t.id}">
                    <!-- Built dynamically on expand -->
                </td>
            </tr>
        `;
    });
    tableBody.innerHTML = html;
}

function selectPMTimelineSymbol(symbol) {
    if (!symbol) return;
    window.pmSelectedTimelineSymbol = symbol;
    
    // Switch to trade_management tab if it is not selected
    const pmTabBtn = document.querySelector('.nav-btn[data-tab="trade_management"]');
    if (pmTabBtn) {
        pmTabBtn.click();
    }
    
    renderPortfolioManagementTimeline();
}
window.selectPMTimelineSymbol = selectPMTimelineSymbol;

function renderPortfolioManagementTimeline() {
    const container = document.getElementById("pm-timeline-container");
    if (!container) return;

    if (!window.pmHistoryPositions || window.pmHistoryPositions.length === 0) {
        container.innerHTML = `
            <div class="no-alerts-state glass" style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                <i class="fa-solid fa-circle-info" style="color: var(--text-secondary); font-size: 20px; margin-bottom: 8px; display: block;"></i>
                No historical positions or audits found. Run a daily scan to populate history.
            </div>
        `;
        return;
    }

    const selectedSymbol = window.pmSelectedTimelineSymbol || window.pmHistoryPositions[0].symbol;
    const position = window.pmHistoryPositions.find(p => p.symbol.toUpperCase() === selectedSymbol.toUpperCase());

    if (!position) {
        container.innerHTML = `
            <div class="no-alerts-state glass" style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                <i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-red); font-size: 20px; margin-bottom: 8px; display: block;"></i>
                Position ${selectedSymbol} not found in history logs.
            </div>
        `;
        return;
    }

    // Process history array. Chronological day by day since entry.
    // Latest day is first.
    let historyToShow = [...position.history];
    historyToShow.sort((a, b) => new Date(b.date) - new Date(a.date));

    // Calculate metadata
    let cmp = 0.0;
    let pnl = 0.0;
    let rMult = 0.0;
    let latestDay = null;

    if (historyToShow.length > 0) {
        latestDay = historyToShow[0];
        cmp = latestDay.current_price;
        pnl = ((cmp - position.entry_price) / position.entry_price * 100);
        rMult = latestDay.r_multiple;
    }

    const pnlSign = pnl >= 0 ? "+" : "";
    const pnlColor = pnl >= 0 ? "var(--accent-green)" : "var(--accent-red)";

    // Build the Top Level Audit Card (Today's snapshot, always visible)
    let snapshotHtml = "";
    if (latestDay) {
        let actionBg = "rgba(255,255,255,0.05)";
        let actionColor = "var(--text-secondary)";
        if (latestDay.action.includes("EXIT")) {
            actionBg = "rgba(239, 68, 68, 0.15)";
            actionColor = "var(--accent-red)";
        } else if (latestDay.action === "BUY MORE" || latestDay.action === "ADD") {
            actionBg = "rgba(139, 92, 246, 0.15)";
            actionColor = "var(--accent-purple)";
        } else if (latestDay.action.includes("TRAIL")) {
            actionBg = "rgba(59, 130, 246, 0.15)";
            actionColor = "var(--accent-blue)";
        }

        let bulletPoints = latestDay.reasons.map(r => {
            const isWarning = r.includes("Violates") || r.includes("Breach") || r.includes("WARNING");
            const icon = isWarning 
                ? `<i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-red); font-size: 12px;"></i>` 
                : `<i class="fa-solid fa-circle-check" style="color: var(--accent-green); font-size: 12px;"></i>`;
            const fontColor = isWarning ? "var(--accent-red)" : "var(--text-primary)";
            const bgColor = isWarning ? "rgba(239, 68, 68, 0.05)" : "rgba(255, 255, 255, 0.01)";
            const borderColor = isWarning ? "rgba(239, 68, 68, 0.15)" : "rgba(255, 255, 255, 0.04)";
            
            return `
                <div style="display: flex; gap: 8px; align-items: flex-start; padding: 6px 10px; border-radius: 6px; background: ${bgColor}; border: 1px solid ${borderColor}; margin-bottom: 4px; font-size: 11.5px; line-height: 1.35; color: ${fontColor};">
                    <span style="margin-top: 1px;">${icon}</span>
                    <span>${r}</span>
                </div>
            `;
        }).join('');

        snapshotHtml = `
            <!-- EOD Audit Snapshot -->
            <div class="glass" style="padding: 14px; border-radius: 12px; border: 1px solid var(--border-color); background: rgba(139, 92, 246, 0.02); display: flex; flex-direction: column; gap: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <h4 style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin: 0;">${position.symbol}</h4>
                        <span class="badge" style="font-size: 9px; background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); padding: 1px 4px; border-radius: 3px; font-weight: bold;">${position.setup_type}</span>
                        <span class="badge" style="font-size: 9px; background: rgba(255, 255, 255, 0.05); color: var(--text-secondary); padding: 1px 4px; border-radius: 3px;">${position.grade}</span>
                    </div>
                    
                    <select id="pm-timeline-select" style="background: var(--bg-dark); border: 1px solid var(--border-color); color: var(--text-primary); padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; outline: none; cursor: pointer;">
                        ${window.pmHistoryPositions.map(p => `<option value="${p.symbol}" ${p.symbol.toUpperCase() === selectedSymbol.toUpperCase() ? 'selected' : ''}>${p.symbol}</option>`).join('')}
                    </select>
                </div>

                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; background: rgba(0,0,0,0.18); padding: 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.03); text-align: center;">
                    <div>
                        <div style="font-size: 8.5px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Action Signal</div>
                        <span class="badge" style="padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; background: ${actionBg}; color: ${actionColor}; border: 1px solid ${actionColor}20; display: inline-block; margin-top: 2px;">
                            ${latestDay.action}
                        </span>
                    </div>
                    <div>
                        <div style="font-size: 8.5px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">CMP (PnL)</div>
                        <div style="font-size: 11px; font-weight: bold; color: ${pnlColor}; margin-top: 3px;">Rs. ${cmp.toFixed(2)} (${pnlSign}${pnl.toFixed(1)}%)</div>
                    </div>
                    <div>
                        <div style="font-size: 8.5px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Recommended Stop</div>
                        <div style="font-size: 11px; font-weight: bold; color: var(--accent-orange); margin-top: 3px;">Rs. ${latestDay.recommended_stop.toFixed(2)}</div>
                    </div>
                </div>

                <div style="margin-top: 2px;">
                    <div style="font-size: 10px; text-transform: uppercase; color: var(--accent-purple); font-weight: 800; margin-bottom: 6px; letter-spacing: 0.5px;">
                        <i class="fa-solid fa-circle-info" style="margin-right: 4px;"></i>EOD Audit Insights (${latestDay.date})
                    </div>
                    <div style="max-height: 180px; overflow-y: auto; padding-right: 2px;">
                        ${bulletPoints}
                    </div>
                </div>
            </div>
        `;
    }

    if (window.pmTimelineLimitTo10Days && historyToShow.length > 10) {
        historyToShow = historyToShow.slice(0, 10);
    }

    // Build timeline table for historical changes
    let tableHtml = `
        <div style="margin-top: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-size: 11px; text-transform: uppercase; color: var(--text-secondary); font-weight: 800; letter-spacing: 0.5px;">
                    <i class="fa-solid fa-clock-rotate-left" style="margin-right: 4px;"></i>Historical Audit Trail
                </div>
                <div style="display: flex; gap: 6px;">
                    <button id="btn-timeline-10d" class="btn" style="padding: 2px 6px; font-size: 9px; border-radius: 3px; font-weight: 600; background: ${window.pmTimelineLimitTo10Days ? 'var(--accent-purple)' : 'rgba(255,255,255,0.05)'}; color: var(--text-primary); border: 1px solid ${window.pmTimelineLimitTo10Days ? 'var(--accent-purple)' : 'var(--border-color)'}; cursor: pointer; transition: all 0.2s;">
                        Last 10d
                    </button>
                    <button id="btn-timeline-all" class="btn" style="padding: 2px 6px; font-size: 9px; border-radius: 3px; font-weight: 600; background: ${!window.pmTimelineLimitTo10Days ? 'var(--accent-purple)' : 'rgba(255,255,255,0.05)'}; color: var(--text-primary); border: 1px solid ${!window.pmTimelineLimitTo10Days ? 'var(--accent-purple)' : 'var(--border-color)'}; cursor: pointer; transition: all 0.2s;">
                        All
                    </button>
                </div>
            </div>
            
            <div class="table-container glass" style="max-height: 250px; overflow-y: auto;">
                <table class="watchlist-table" style="width: 100%; border-collapse: collapse; text-align: left;">
                    <thead>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); position: sticky; top: 0; background: var(--bg-dark); z-index: 1;">
                            <th style="padding: 8px 6px; font-size: 9.5px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Date</th>
                            <th style="padding: 8px 6px; font-size: 9.5px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Price (Δ)</th>
                            <th style="padding: 8px 6px; font-size: 9.5px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600; text-align: center;">TBS</th>
                            <th style="padding: 8px 6px; font-size: 9.5px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Action</th>
                            <th style="padding: 8px 6px; font-size: 9.5px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Stop (Δ)</th>
                            <th style="padding: 8px 6px; font-size: 9.5px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600; text-align: center;">Detail</th>
                        </tr>
                    </thead>
                    <tbody>
    `;

    historyToShow.forEach((day, idx) => {
        let arrowHtml = "";
        if (idx < historyToShow.length - 1) {
            const prevDayClose = historyToShow[idx + 1].current_price;
            if (day.current_price > prevDayClose) {
                arrowHtml = `<span style="color: var(--accent-green); margin-right: 2px; font-size: 8px;">▲</span>`;
            } else if (day.current_price < prevDayClose) {
                arrowHtml = `<span style="color: var(--accent-red); margin-right: 2px; font-size: 8px;">▼</span>`;
            } else {
                arrowHtml = `<span style="color: var(--text-secondary); margin-right: 2px; font-size: 8px;">■</span>`;
            }
        } else {
            if (day.current_price > position.entry_price) {
                arrowHtml = `<span style="color: var(--accent-green); margin-right: 2px; font-size: 8px;">▲</span>`;
            } else if (day.current_price < position.entry_price) {
                arrowHtml = `<span style="color: var(--accent-red); margin-right: 2px; font-size: 8px;">▼</span>`;
            } else {
                arrowHtml = `<span style="color: var(--text-secondary); margin-right: 2px; font-size: 8px;">■</span>`;
            }
        }

        // Price Delta
        let priceChangeHtml = "";
        let stopChangeHtml = "";
        const prevDay = (idx < historyToShow.length - 1) ? historyToShow[idx + 1] : null;

        if (prevDay) {
            const priceDiff = day.current_price - prevDay.current_price;
            const pricePctDiff = (priceDiff / prevDay.current_price * 100);
            const priceSign = priceDiff >= 0 ? "+" : "";
            const priceColor = priceDiff >= 0 ? "var(--accent-green)" : "var(--accent-red)";
            priceChangeHtml = `<span style="font-size: 8px; color: ${priceColor}; font-weight: bold; margin-left: 2px;">${priceSign}${pricePctDiff.toFixed(1)}%</span>`;

            const stopDiff = day.recommended_stop - prevDay.recommended_stop;
            if (stopDiff !== 0) {
                const stopSign = stopDiff > 0 ? "+" : "";
                const stopColor = stopDiff > 0 ? "var(--accent-green)" : "var(--accent-red)";
                stopChangeHtml = `<span style="font-size: 8px; color: ${stopColor}; font-weight: bold; margin-left: 2px;">${stopSign}${stopDiff.toFixed(1)}</span>`;
            }
        }

        const getBadgeStyle = (score) => {
            if (score >= 85) return "background: rgba(16, 185, 129, 0.15); color: var(--accent-green);";
            if (score >= 70) return "background: rgba(59, 130, 246, 0.15); color: var(--accent-blue);";
            return "background: rgba(239, 68, 68, 0.15); color: var(--accent-red);";
        };

        let actionBg = "rgba(255,255,255,0.03)";
        let actionColor = "var(--text-secondary)";
        if (day.action.includes("EXIT")) {
            actionBg = "rgba(239, 68, 68, 0.12)";
            actionColor = "var(--accent-red)";
        } else if (day.action === "BUY MORE" || day.action === "ADD") {
            actionBg = "rgba(139, 92, 246, 0.12)";
            actionColor = "var(--accent-purple)";
        } else if (day.action.includes("TRAIL")) {
            actionBg = "rgba(59, 130, 246, 0.12)";
            actionColor = "var(--accent-blue)";
        }

        let reasonsHtml = day.reasons.map(r => {
            const isWarning = r.includes("Violates") || r.includes("Breach") || r.includes("WARNING");
            const icon = isWarning 
                ? `<i class="fa-solid fa-triangle-exclamation" style="color: var(--accent-red); margin-right: 6px;"></i>` 
                : `<i class="fa-solid fa-circle-check" style="color: var(--accent-green); margin-right: 6px;"></i>`;
            const fontColor = isWarning ? "var(--accent-red)" : "var(--text-secondary)";
            return `
                <li style="margin-bottom: 4px; font-size: 11px; color: ${fontColor}; display: flex; align-items: flex-start; line-height: 1.3;">
                    <span style="margin-top: 1px;">${icon}</span>
                    <span style="margin-left: 2px;">${r}</span>
                </li>
            `;
        }).join('');

        tableHtml += `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.04); transition: background 0.2s; cursor: pointer;" onclick="togglePMRowDetails(${idx})">
                <td style="padding: 8px 6px; font-size: 11px; font-weight: bold; white-space: nowrap;">
                    ${day.date.substring(5)}
                </td>
                <td style="padding: 8px 6px; font-size: 11px; white-space: nowrap;">
                    <div style="display: flex; align-items: center; font-weight: bold; color: var(--text-primary);">
                        ${arrowHtml}${day.current_price.toFixed(1)}${priceChangeHtml}
                    </div>
                </td>
                <td style="padding: 8px 6px; text-align: center; font-size: 11px;">
                    <span style="padding: 1px 4px; border-radius: 3px; font-size: 9px; font-weight: bold; ${getBadgeStyle(day.tbs)}">
                        ${day.tbs}
                    </span>
                </td>
                <td style="padding: 8px 6px; white-space: nowrap;">
                    <span style="padding: 2px 4px; border-radius: 3px; font-size: 9px; font-weight: bold; background: ${actionBg}; color: ${actionColor};">
                        ${day.action}
                    </span>
                </td>
                <td style="padding: 8px 6px; font-size: 11px; white-space: nowrap;">
                    <span style="color: var(--accent-orange); font-weight: bold;">${day.recommended_stop.toFixed(1)}</span>${stopChangeHtml}
                </td>
                <td style="padding: 8px 6px; text-align: center;">
                    <button class="table-log-btn" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; padding: 2px; font-size: 9px;">
                        <i id="pm-chevron-${idx}" class="fa-solid fa-chevron-down" style="transition: transform 0.2s;"></i>
                    </button>
                </td>
            </tr>
            
            <!-- Detail Row -->
            <tr id="pm-detail-${idx}" style="display: none; background: rgba(0,0,0,0.2);">
                <td colspan="6" style="padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.04);">
                    <div style="background: rgba(255, 255, 255, 0.005); border: 1px dashed rgba(255, 255, 255, 0.05); padding: 8px 12px; border-radius: 6px;">
                        <div style="font-size: 9px; text-transform: uppercase; color: var(--accent-purple); font-weight: 800; margin-bottom: 6px; letter-spacing: 0.5px;">
                            Audit Details (${day.date})
                        </div>
                        <ul style="list-style: none; margin: 0; padding: 0;">
                            ${reasonsHtml}
                        </ul>
                    </div>
                </td>
            </tr>
        `;
    });

    tableHtml += `
                    </tbody>
                </table>
            </div>
        </div>
    `;

    container.innerHTML = snapshotHtml + tableHtml;

    // Attach event listeners for controls
    const selectEl = document.getElementById("pm-timeline-select");
    if (selectEl) {
        selectEl.addEventListener("change", (e) => {
            window.pmSelectedTimelineSymbol = e.target.value;
            renderPortfolioManagementTimeline();
        });
    }

    const btn10d = document.getElementById("btn-timeline-10d");
    if (btn10d) {
        btn10d.addEventListener("click", (e) => {
            e.stopPropagation();
            window.pmTimelineLimitTo10Days = true;
            renderPortfolioManagementTimeline();
        });
    }

    const btnAll = document.getElementById("btn-timeline-all");
    if (btnAll) {
        btnAll.addEventListener("click", (e) => {
            e.stopPropagation();
            window.pmTimelineLimitTo10Days = false;
            renderPortfolioManagementTimeline();
        });
    }
}


function renderExpectancyRegimeStats(trades) {
    const container = document.getElementById("pm-regime-stats-container");
    if (!container) return;

    const total = trades.length;
    let cat3 = 0, cat2 = 0, cat1 = 0;

    trades.forEach(t => {
        const regime = (t.expectancy_regime || "").toLowerCase();
        if (regime.includes("category 3")) cat3++;
        else if (regime.includes("category 2")) cat2++;
        else if (regime.includes("category 1")) cat1++;
        else cat2++;
    });

    const pct3 = total > 0 ? (cat3 / total * 100) : 0;
    const pct2 = total > 0 ? (cat2 / total * 100) : 0;
    const pct1 = total > 0 ? (cat1 / total * 100) : 0;

    container.innerHTML = `
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                <span style="color: var(--text-primary); font-weight: 500;">Category 3 (Super Performance Regime)</span>
                <strong style="color: var(--accent-green);">${cat3} trades (${pct3.toFixed(0)}%)</strong>
            </div>
            <div style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                <div style="height: 100%; width: ${pct3}%; background: var(--accent-green); border-radius: 3px;"></div>
            </div>
        </div>
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                <span style="color: var(--text-primary); font-weight: 500;">Category 2 (Strong/Constructive Regime)</span>
                <strong style="color: var(--accent-blue);">${cat2} trades (${pct2.toFixed(0)}%)</strong>
            </div>
            <div style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                <div style="height: 100%; width: ${pct2}%; background: var(--accent-blue); border-radius: 3px;"></div>
            </div>
        </div>
        <div>
            <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                <span style="color: var(--text-primary); font-weight: 500;">Category 1 (Average/Poor Expectancy)</span>
                <strong style="color: var(--accent-orange);">${cat1} trades (${pct1.toFixed(0)}%)</strong>
            </div>
            <div style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                <div style="height: 100%; width: ${pct1}%; background: var(--accent-orange); border-radius: 3px;"></div>
            </div>
        </div>
    `;
}

function renderPortfolioManagementCorrelationChart(trades) {
    const canvas = document.getElementById("pm-correlation-chart");
    if (!canvas) return;

    if (pmCorrelationChartInstance) {
        pmCorrelationChartInstance.destroy();
    }

    const chartData = trades.map(t => {
        const pnl = ((t.current_price - t.entry_price) / t.entry_price * 100);
        return {
            x: t.eqs !== undefined ? t.eqs : 100,
            y: t.tbs !== undefined ? t.tbs : 100,
            symbol: t.symbol,
            pnl: pnl,
            r: t.r_multiple
        };
    });

    const ctx = canvas.getContext("2d");
    pmCorrelationChartInstance = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Positions',
                data: chartData,
                backgroundColor: chartData.map(d => d.pnl >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)'),
                borderColor: chartData.map(d => d.pnl >= 0 ? '#10b981' : '#ef4444'),
                borderWidth: 1.5,
                pointRadius: 8,
                pointHoverRadius: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const d = context.raw;
                            return `${d.symbol}: EQS=${d.x}, TBS=${d.y}, PnL=${d.pnl.toFixed(1)}%, R=${d.r.toFixed(2)}R`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Entry Quality Score (EQS)',
                        color: 'rgba(255, 255, 255, 0.6)',
                        font: { size: 11, weight: 'bold' }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.6)'
                    }
                },
                y: {
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Trade Behavior Score (TBS)',
                        color: 'rgba(255, 255, 255, 0.6)',
                        font: { size: 11, weight: 'bold' }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.6)'
                    }
                }
            }
        }
    });
}

async function loadTruePaperPortfolio() {
    try {
        const response = await fetch("/api/true_paper_portfolio");
        if (!response.ok) throw new Error("Failed to fetch true paper portfolio data");
        const data = await response.json();

        // 1. Overview metrics
        const cash = parseFloat(data.cash) || 0.0;
        const openTrades = data.open_trades || [];
        appState.truePaperOpenTrades = openTrades;
        const closedTrades = data.closed_trades || [];
        const logs = data.process_log || [];

        let openValue = 0.0;
        openTrades.forEach(t => {
            const qty = parseFloat(t.open_qty) || 0;
            const cmp = parseFloat(t.cmp) || parseFloat(t.entry_price) || 0;
            openValue += qty * cmp;
        });

        const totalEquity = cash + openValue;
        const initialCapital = 100000.0;
        const totalReturnPct = ((totalEquity - initialCapital) / initialCapital) * 100;
        const realizedPnL = closedTrades.reduce((sum, t) => sum + (parseFloat(t.pnl_net) || 0), 0);

        // Update Overview HTML Elements
        document.getElementById("tpp-total-equity").textContent = `₹${totalEquity.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        
        const returnPctSpan = document.getElementById("tpp-total-return-pct");
        returnPctSpan.textContent = `${totalReturnPct >= 0 ? '+' : ''}${totalReturnPct.toFixed(2)}% Overall`;
        returnPctSpan.style.color = totalReturnPct >= 0 ? '#10b981' : 'var(--accent-red)';

        document.getElementById("tpp-cash").textContent = `₹${cash.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        
        document.getElementById("tpp-open-value").textContent = `₹${openValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        document.getElementById("tpp-positions-count").textContent = `${openTrades.length} open positions`;

        const realizedSpan = document.getElementById("tpp-realized-pnl");
        realizedSpan.textContent = `₹${realizedPnL.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        realizedSpan.style.color = realizedPnL >= 0 ? '#10b981' : 'var(--accent-red)';
        document.getElementById("tpp-closed-count").textContent = `${closedTrades.length} closed trades`;

        // 2. Compute and Render Performance Metrics
        const totalClosed = closedTrades.length;
        const wins = closedTrades.filter(t => (parseFloat(t.pnl_net) || 0) > 0);
        const winRate = totalClosed > 0 ? (wins.length / totalClosed) * 100 : 0.0;

        let t1Hits = 0, t2Hits = 0, slHits = 0;
        closedTrades.forEach(t => {
            const hasT1 = (t.partial_exits || []).some(pe => pe.target === 'T1');
            const hasT2 = (t.partial_exits || []).some(pe => pe.target === 'T2');
            if (hasT1) t1Hits++;
            if (hasT2) t2Hits++;
            if (t.exit_reason && t.exit_reason.toLowerCase().includes("stop")) slHits++;
        });

        // Current open trades also contribute to T1/T2 hit stats
        openTrades.forEach(t => {
            if (t.t1_hit) t1Hits++;
            if (t.t2_hit) t2Hits++;
        });

        const totalPositionsAll = totalClosed + openTrades.length;
        const t1Rate = totalPositionsAll > 0 ? (t1Hits / totalPositionsAll) * 100 : 0.0;
        const t2Rate = totalPositionsAll > 0 ? (t2Hits / totalPositionsAll) * 100 : 0.0;
        const slRate = totalClosed > 0 ? (slHits / totalClosed) * 100 : 0.0;

        const avgR = totalClosed > 0 ? closedTrades.reduce((sum, t) => sum + (parseFloat(t.r_multiple) || 0), 0) / totalClosed : 0.0;
        const ev = avgR; // Expectancy per trade in R units

        document.getElementById("tpp-win-rate").textContent = `${winRate.toFixed(1)}%`;
        document.getElementById("tpp-t1-rate").textContent = `${t1Rate.toFixed(1)}%`;
        document.getElementById("tpp-t2-rate").textContent = `${t2Rate.toFixed(1)}%`;
        document.getElementById("tpp-sl-rate").textContent = `${slRate.toFixed(1)}%`;
        
        const avgRSpan = document.getElementById("tpp-avg-r");
        avgRSpan.textContent = `${avgR >= 0 ? '+' : ''}${avgR.toFixed(2)}R`;
        avgRSpan.style.color = avgR >= 0 ? '#10b981' : 'var(--accent-red)';

        const evSpan = document.getElementById("tpp-ev");
        evSpan.textContent = `${ev >= 0 ? '+' : ''}${ev.toFixed(2)}R`;
        evSpan.style.color = ev >= 0 ? '#10b981' : 'var(--accent-red)';

        // 3. Render Open Trades Table
        const openBody = document.getElementById("tpp-open-trades-body");
        if (openTrades.length === 0) {
            openBody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: var(--text-muted); padding: 20px;">No active holdings currently.</td></tr>`;
        } else {
            openBody.innerHTML = openTrades.map(t => {
                const cmp = parseFloat(t.cmp) || parseFloat(t.entry_price) || 0;
                const entry = parseFloat(t.entry_price) || 0;
                const qty = parseFloat(t.open_qty) || 0;
                
                const pnlNet = parseFloat(t.unrealized_pnl) || 0;
                const rMult = parseFloat(t.unrealized_r) || 0;
                const pnlClass = pnlNet >= 0 ? 'color: #10b981; font-weight: 600;' : 'color: var(--accent-red); font-weight: 600;';
                const sign = pnlNet >= 0 ? '+' : '';

                // Phase highlight style
                const phaseColor = t.phase === 'PRE-T1' ? '#f59e0b' : t.phase === 'POST-T1' ? '#10b981' : '#3b82f6';

                return `
                    <tr style="border-left: 3px solid ${phaseColor};">
                        <td><strong>${t.symbol}</strong><br><span style="font-size:10px;color:var(--text-muted);">${t.engine_type}</span></td>
                        <td><span class="badge" style="font-size:10px;background:rgba(255,255,255,0.05);">${t.grade}</span></td>
                        <td>₹${entry.toFixed(2)}</td>
                        <td>${qty}</td>
                        <td>₹${cmp.toFixed(2)}</td>
                        <td style="color:var(--accent-red);">₹${parseFloat(t.trailing_sl).toFixed(2)}</td>
                        <td style="color:#10b981;">₹${parseFloat(t.t1).toFixed(2)}${t.t1_hit ? ' ✓' : ''}</td>
                        <td style="color:#3b82f6;">₹${parseFloat(t.t2).toFixed(2)}${t.t2_hit ? ' ✓' : ''}</td>
                        <td style="${pnlClass}">${sign}₹${pnlNet.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td style="${pnlClass}">${sign}${rMult.toFixed(2)}R</td>
                        <td><span style="padding: 2px 6px; background: rgba(255,255,255,0.04); border-radius: 4px; font-size:11px;">${t.days_active}d</span></td>
                    </tr>
                `;
            }).join("");
        }

        // 4. Render Closed Trades Table
        const closedBody = document.getElementById("tpp-closed-trades-body");
        if (closedTrades.length === 0) {
            closedBody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 20px;">No historical trades closed yet.</td></tr>`;
        } else {
            closedBody.innerHTML = closedTrades.map(t => {
                const entry = parseFloat(t.entry_price) || 0;
                const exit = parseFloat(t.exit_price) || 0;
                const pnl = parseFloat(t.pnl_net) || 0;
                const rMult = parseFloat(t.r_multiple) || 0;
                const pnlClass = pnl >= 0 ? 'color: #10b981;' : 'color: var(--accent-red);';
                const sign = pnl >= 0 ? '+' : '';

                return `
                    <tr>
                        <td><strong>${t.symbol}</strong><br><span style="font-size:10px;color:var(--text-muted);">${t.engine_type}</span></td>
                        <td><span style="font-size:10px;padding:2px 6px;background:rgba(255,255,255,0.05);border-radius:4px;">${t.grade}</span></td>
                        <td style="font-size:11px;">${t.entry_date}</td>
                        <td style="font-size:11px;">${t.exit_date}</td>
                        <td>₹${entry.toFixed(2)}</td>
                        <td>₹${exit.toFixed(2)}</td>
                        <td style="${pnlClass}">${sign}₹${pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td style="${pnlClass}">${sign}${rMult.toFixed(2)}R</td>
                        <td style="font-size:11px;color:var(--text-secondary);max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${t.exit_reason || ''}">${t.exit_reason || 'Exit'}</td>
                    </tr>
                `;
            }).join("");
        }

        // 5. Render Process Log Terminal
        const logContainer = document.getElementById("tpp-process-log");
        if (logs.length === 0) {
            logContainer.textContent = "Waiting for daily EOD scan run to ingest logs...";
        } else {
            logContainer.textContent = logs.slice().reverse().join("\n");
        }

    } catch (error) {
        console.error("Error loading True Paper Portfolio:", error);
    }
}
window.loadTruePaperPortfolio = loadTruePaperPortfolio;