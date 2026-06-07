(function () {
  const MEASUREMENT_ID = document.documentElement.dataset.gaMeasurementId || "";

  function initAnalytics() {
    if (!MEASUREMENT_ID || typeof window.gtag === "function") {
      return;
    }
    const script = document.createElement("script");
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${MEASUREMENT_ID}`;
    document.head.appendChild(script);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      window.dataLayer.push(arguments);
    };
    window.gtag("js", new Date());
    window.gtag("config", MEASUREMENT_ID, { send_page_view: false });
  }

  initAnalytics();
})();
