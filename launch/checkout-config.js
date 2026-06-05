/**
 * CYB-208 — single source of truth for checkout wiring.
 * CTO/CFO: replace REPLACE_* values with live Stripe Payment Links when CYB-33/39 opens.
 * Set Stripe success URL to: https://cybernative.ai/launch/checkout-success
 */
window.CYBERNATIVE_CHECKOUT = {
  conciergeSlot: "https://buy.stripe.com/REPLACE_CONCIERGE_SLOT_LINK",
  sponsoredSlot: "https://buy.stripe.com/REPLACE_SPONSORED_SLOT_LINK",
  fitCall: "https://cal.com/REPLACE_FIT_CALL_LINK",
  successUrl: "https://cybernative.ai/launch/checkout-success",
  intakeThanksUrl: "https://cybernative.ai/launch/thanks"
};
