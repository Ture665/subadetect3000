console.log("Subaharan Detector 3000 website loaded.");

const profileBtn = document.getElementById("profileBtn");
const profileDropdown = document.getElementById("profileDropdown");

if (profileBtn && profileDropdown) {
  profileBtn.addEventListener("click", function (event) {
    event.stopPropagation();
    profileDropdown.classList.toggle("open");
  });

  document.addEventListener("click", function () {
    profileDropdown.classList.remove("open");
  });

  profileDropdown.addEventListener("click", function (event) {
    event.stopPropagation();
  });
}
