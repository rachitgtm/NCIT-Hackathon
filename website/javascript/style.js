/* ===================== Mobile nav toggle ===================== */
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      links.classList.toggle("open");
    });
    links.querySelectorAll("a").forEach((a) =>
      a.addEventListener("click", () => links.classList.remove("open"))
    );
  }

  initSlider();
  initSearch();
  initTherapistFilter();
  initBooking();
  initReviewForm();
});

/* ===================== Hero image slider ===================== */
function initSlider() {
  const slides = document.querySelectorAll(".slide");
  const dots = document.querySelectorAll(".dot");
  if (!slides.length) return;

  let current = 0;
  let timer;

  function show(index) {
    slides.forEach((s) => s.classList.remove("active"));
    dots.forEach((d) => d.classList.remove("active"));
    current = (index + slides.length) % slides.length;
    slides[current].classList.add("active");
    if (dots[current]) dots[current].classList.add("active");
  }

  function next() { show(current + 1); }
  function prev() { show(current - 1); }

  function restart() {
    clearInterval(timer);
    timer = setInterval(next, 5000);
  }

  document.querySelector(".slider-arrow.next")?.addEventListener("click", () => { next(); restart(); });
  document.querySelector(".slider-arrow.prev")?.addEventListener("click", () => { prev(); restart(); });
  dots.forEach((dot, i) => dot.addEventListener("click", () => { show(i); restart(); }));

  show(0);
  restart();
}

/* ===================== "Tell us about your problem" search ===================== */
function initSearch() {
  const form = document.querySelector(".search-form");
  const result = document.querySelector(".search-result");
  const tagButtons = document.querySelectorAll(".search-tags button");
  if (!form) return;

  const suggestions = {
    anxiety: "We found 8 therapists specializing in anxiety. Heading to the therapist list…",
    depression: "We found 11 therapists specializing in depression support. Heading to the therapist list…",
    stress: "We found 9 therapists who help with academic & work stress. Heading to the therapist list…",
    sleep: "We found 5 therapists who help with sleep & insomnia issues. Heading to the therapist list…",
    relationship: "We found 7 therapists who specialize in relationship counselling. Heading to the therapist list…",
    default: "Thanks for sharing. Connecting you with the right therapist for you…",
  };

  function handleQuery(value) {
    const lower = value.toLowerCase();
    let message = suggestions.default;
    for (const key in suggestions) {
      if (lower.includes(key)) { message = suggestions[key]; break; }
    }
    if (result) result.textContent = message;
    setTimeout(() => {
      window.location.href = "therapists.html";
    }, 900);
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const input = form.querySelector("input");
    if (!input.value.trim()) {
      if (result) result.textContent = "Please tell us a little about how you're feeling.";
      return;
    }
    handleQuery(input.value.trim());
  });

  tagButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = form.querySelector("input");
      input.value = btn.textContent.trim();
      handleQuery(btn.textContent.trim());
    });
  });
}

/* ===================== Therapist filter ===================== */
function initTherapistFilter() {
  const buttons = document.querySelectorAll(".filter-bar button");
  const cards = document.querySelectorAll(".therapist-card");
  if (!buttons.length) return;

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const filter = btn.dataset.filter;

      cards.forEach((card) => {
        const tags = card.dataset.tags || "";
        if (filter === "all" || tags.includes(filter)) {
          card.style.display = "";
        } else {
          card.style.display = "none";
        }
      });
    });
  });
}

/* ===================== Book a session ===================== */
function initBooking() {
  const buttons = document.querySelectorAll(".book-btn");
  const toast = document.querySelector(".toast");
  if (!buttons.length) return;

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.name || "your therapist";
      if (toast) {
        toast.textContent = `Session request sent to ${name}. They'll reach out to confirm a time. 🌿`;
        toast.classList.add("show");
        clearTimeout(window.__toastTimer);
        window.__toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
      }
    });
  });
}

/* ===================== Review / feedback form ===================== */
function initReviewForm() {
  const form = document.querySelector(".review-form");
  const starInput = document.querySelector(".star-input");
  const grid = document.querySelector(".reviews-grid");
  if (!form || !starInput) return;

  let rating = 0;
  const stars = starInput.querySelectorAll("button");

  stars.forEach((star, i) => {
    star.addEventListener("click", () => {
      rating = i + 1;
      stars.forEach((s, j) => s.classList.toggle("selected", j <= i));
    });
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const nameInput = form.querySelector("[name='name']");
    const textInput = form.querySelector("[name='message']");
    const name = nameInput.value.trim() || "Anonymous";
    const message = textInput.value.trim();
    if (!message || rating === 0) {
      alert("Please add a rating and a short message before submitting.");
      return;
    }

    const card = document.createElement("div");
    card.className = "review-card";
    card.innerHTML = `
      <div class="review-stars">${"★".repeat(rating)}${"☆".repeat(5 - rating)}</div>
      <p class="review-text">"${message}"</p>
      <div class="review-author">
        <div class="review-avatar">${name.charAt(0).toUpperCase()}</div>
        <div>
          <strong>${name}</strong>
          <span>Just now</span>
        </div>
      </div>
    `;
    grid.prepend(card);

    form.reset();
    rating = 0;
    stars.forEach((s) => s.classList.remove("selected"));
    form.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}