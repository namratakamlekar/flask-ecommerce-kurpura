// Shared on every page: "Add to cart" buttons (talks to the Flask backend) + toast popup.
const csrf = document.querySelector('meta[name="csrf-token"]').content;

let toastTimer;
function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2000);
}

function setCartCount(n) {
  const badge = document.getElementById("cartCount");
  if (badge.textContent !== String(n)) {
    badge.textContent = n;
    badge.classList.remove("bump"); void badge.offsetWidth; badge.classList.add("bump");
  }
}

async function addToCart(id, qty = 1) {
  const res = await fetch(`/cart/add/${id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ qty })
  });
  if (!res.ok) { toast("Could not add to cart. Please refresh the page."); return null; }
  const data = await res.json();
  setCartCount(data.count);
  return data;
}

// Any button with data-add="ID" adds that product (data-qty-from="#q" reads the quantity from the page)
document.addEventListener("click", async e => {
  const button = e.target.closest("[data-add]");
  if (!button) return;
  const qtyEl = button.dataset.qtyFrom && document.querySelector(button.dataset.qtyFrom);
  const qty = qtyEl ? Number(qtyEl.textContent) : 1;
  const data = await addToCart(Number(button.dataset.add), qty);
  if (!data) return;
  if (button.dataset.go) location.href = button.dataset.go;      // "Buy now" -> go to cart
  else toast(`${qty > 1 ? qty + " × " : ""}${data.name} added to cart`);
});
