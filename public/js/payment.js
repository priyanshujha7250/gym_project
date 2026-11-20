/**
 * Payment & Razorpay Integration Handler
 * Handles both Razorpay online checkout and Cash-at-Gym reservation workflow.
 */

const PaymentHandler = {
  /**
   * Initiates payment flow based on selected mode
   */
  async processRegistration(payload, onStatusUpdate, onCompleted) {
    onStatusUpdate("Registering membership details...", "info");

    try {
      // 1. Send registration to backend
      const res = await fetch("/api/members/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Failed to register membership");
      }

      // If user selected CASH AT GYM
      if (payload.payment_choice === "cash") {
        onStatusUpdate("Cash registration reserved!", "success");
        onCompleted({
          mode: "cash",
          member_id: data.member_id,
          pricing: data.pricing,
          message: data.message
        });
        return;
      }

      // If user selected ONLINE RAZORPAY
      const order = data.order;
      onStatusUpdate("Opening secure payment gateway...", "info");

      // Check if Razorpay SDK is loaded
      if (typeof Razorpay === "undefined") {
        // Fallback for sandboxed / offline testing environments
        console.warn("Razorpay SDK not loaded from CDN, providing simulated payment verification flow.");
        this.handleSimulatedOnlinePayment(order, onStatusUpdate, onCompleted);
        return;
      }

      const options = {
        key: order.key_id,
        amount: order.amount, // in paise
        currency: order.currency,
        name: "FIT NATION",
        description: `${order.plan_summary.name} Membership`,
        order_id: order.order_id,
        prefill: {
          name: order.customer.name,
          contact: order.customer.phone,
          email: order.customer.email
        },
        theme: {
          color: "#e2f10b"
        },
        handler: async (response) => {
          onStatusUpdate("Verifying payment signature with server...", "info");
          try {
            const verifyRes = await fetch("/api/payments/verify", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                order_id: response.razorpay_order_id,
                payment_id: response.razorpay_payment_id,
                signature: response.razorpay_signature
              })
            });

            const verifyData = await verifyRes.json();
            if (!verifyRes.ok) {
              throw new Error(verifyData.error || "Server payment verification failed");
            }

            onStatusUpdate("Payment verified successfully!", "success");
            onCompleted({
              mode: "online",
              ...verifyData
            });
          } catch (verifyErr) {
            onStatusUpdate(`Verification error: ${verifyErr.message}`, "error");
          }
        },
        modal: {
          ondismiss: () => {
            onStatusUpdate("Payment window closed. You can retry or choose Cash at Gym.", "error");
          }
        }
      };

      try {
        const rzp = new Razorpay(options);
        rzp.on("payment.failed", (resp) => {
          onStatusUpdate(`Payment failed: ${resp.error.description}`, "error");
        });
        rzp.open();
      } catch (sdkErr) {
        console.warn("Razorpay initialization warning, falling back to simulated verification:", sdkErr);
        this.handleSimulatedOnlinePayment(order, onStatusUpdate, onCompleted);
      }

    } catch (err) {
      onStatusUpdate(`Error: ${err.message}`, "error");
    }
  },

  /**
   * Simulated online payment confirmation for local testing / demo mode
   */
  async handleSimulatedOnlinePayment(order, onStatusUpdate, onCompleted) {
    const confirmPay = confirm(
      `[Test Mode Payment Simulator]\n\nPay ₹${order.amount_inr} for ${order.plan_summary.name}?\n\nOrder ID: ${order.order_id}\n\nClick OK to simulate successful Razorpay payment with server verification.`
    );

    if (!confirmPay) {
      onStatusUpdate("Payment cancelled by user.", "error");
      return;
    }

    onStatusUpdate("Verifying simulated payment signature on backend...", "info");

    try {
      const mockPaymentId = `pay_mock_${Date.now()}`;
      const verifyRes = await fetch("/api/payments/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: order.order_id,
          payment_id: mockPaymentId,
          signature: "demo_verified_signature"
        })
      });

      const verifyData = await verifyRes.json();
      if (!verifyRes.ok) {
        throw new Error(verifyData.error || "Simulated payment verification failed");
      }

      onStatusUpdate("Payment verified successfully!", "success");
      onCompleted({
        mode: "online",
        ...verifyData
      });
    } catch (err) {
      onStatusUpdate(`Verification failed: ${err.message}`, "error");
    }
  }
};
