/* Handles the register and login forms. */
document.addEventListener("DOMContentLoaded", () => {
  const registerForm = document.getElementById("register-form");
  const loginForm = document.getElementById("login-form");

  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById("form-error");
      errorEl.textContent = "";

      const payload = {
        full_name: registerForm.full_name.value.trim(),
        email: registerForm.email.value.trim(),
        password: registerForm.password.value,
      };

      try {
        await apiRequest("/api/auth/register", { method: "POST", body: JSON.stringify(payload) });
        window.location.href = "/dashboard";
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });
  }

  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById("form-error");
      errorEl.textContent = "";

      const payload = {
        email: loginForm.email.value.trim(),
        password: loginForm.password.value,
      };

      try {
        await apiRequest("/api/auth/login", { method: "POST", body: JSON.stringify(payload) });
        window.location.href = "/dashboard";
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });
  }

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      await apiRequest("/api/auth/logout", { method: "POST" });
      window.location.href = "/login";
    });
  }
});
