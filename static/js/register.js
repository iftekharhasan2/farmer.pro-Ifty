document.getElementById("registerForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim();
  const number = document.getElementById("number").value.trim();
  const password = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirmPassword").value;
  const submitBtn = document.getElementById("submitBtn");

  if (password !== confirmPassword) {
    alert("Passwords do not match.");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Registering...";

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, number, password }),
    });

    const data = await res.json();
    alert(data.message || data.error);

    if (res.ok) {
      window.location.href = "/login";
    }
  } catch (error) {
    alert("Something went wrong.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Register";
  }
});
