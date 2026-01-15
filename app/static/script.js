function toggleMobileMenu() {
  const mobileNav = document.getElementById("mobileNav");
  mobileNav.classList.toggle("ehome-active");
}

// Close mobile menu when clicking on a link
document
  .querySelectorAll(".ehome-mobile-nav .ehome-nav-link")
  .forEach((link) => {
    link.addEventListener("click", toggleMobileMenu);
  });
