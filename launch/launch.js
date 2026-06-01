(function () {
  const params = new URLSearchParams(window.location.search);
  const utmFields = ["utm_source", "utm_medium", "utm_campaign", "utm_content"];

  utmFields.forEach((field) => {
    const input = document.querySelector(`input[name="${field}"]`);
    if (input) {
      input.value = params.get(field) || "";
    }
  });

  function pushEvent(name, params) {
    window.cybernativeLaunchEvents = window.cybernativeLaunchEvents || [];
    window.cybernativeLaunchEvents.push({ event: name, ...params, timestamp: new Date().toISOString() });
    if (typeof window.gtag === "function") {
      window.gtag("event", name, params);
    }
  }

  document.querySelectorAll("[data-event]").forEach((el) => {
    el.addEventListener("click", () => {
      pushEvent(el.dataset.event, {
        offer_type: el.dataset.offer || document.body.dataset.offerPage,
        page_path: window.location.pathname,
        link_source: el.dataset.trackSource || document.body.dataset.offerPage
      });
    });
  });

  document.querySelectorAll('a[href*="github.com/CyberNativeAI/agentic-connect"]').forEach((el) => {
    if (el.dataset.event) {
      return;
    }
    el.addEventListener("click", () => {
      pushEvent("github_connector_click", {
        link_source: document.body.dataset.offerPage || "launch",
        page_path: window.location.pathname
      });
    });
  });

  document.querySelectorAll("[data-offer]").forEach((link) => {
    link.addEventListener("click", () => {
      pushEvent("pricing_deposit_click", {
        offer_type: link.dataset.offer,
        page_path: window.location.pathname
      });
    });
  });

  const form = document.querySelector("form");
  if (form) {
    form.addEventListener("submit", () => {
      pushEvent("signup_start", {
        link_source: document.body.dataset.offerPage || "launch",
        page_path: window.location.pathname
      });
      const data = new FormData(form);
      pushEvent("lead_form_submit", {
        offer_interest: data.get("offer"),
        launch_category: data.get("category"),
        page_path: window.location.pathname
      });
    });
  }

  pushEvent("seo_landing_view", {
    page_name: document.body.dataset.offerPage || "hub",
    landing_page: document.body.dataset.offerPage || "hub",
    page_path: window.location.pathname
  });

  if (document.body.classList.contains("thanks-page")) {
    pushEvent("signup_complete", {
      link_source: "launch_thanks",
      page_path: window.location.pathname
    });
  }
})();
