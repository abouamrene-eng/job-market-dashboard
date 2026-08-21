const Filters = (() => {
  function checkedValues(containerId) {
    return Array.from(
      document.querySelectorAll(`#${containerId} input[type=checkbox]:checked`)
    ).map((el) => el.value);
  }

  function read() {
    return {
      sector: checkedValues("filter-sector"),
      location: checkedValues("filter-location"),
      min_salary: document.getElementById("filter-salary").value,
      score: document.getElementById("filter-score").value,
      status: document.getElementById("filter-status").value,
    };
  }

  function reset() {
    document.querySelectorAll("#filter-sector input, #filter-location input").forEach((el) => {
      el.checked = true;
    });
    document.getElementById("filter-salary").value = 60000;
    document.getElementById("filter-salary-value").textContent = "60 000€";
    document.getElementById("filter-score").value = "all";
    document.getElementById("filter-status").value = "all";
  }

  function bindSalarySlider() {
    const slider = document.getElementById("filter-salary");
    const label = document.getElementById("filter-salary-value");
    slider.addEventListener("input", () => {
      label.textContent = `${Number(slider.value).toLocaleString("fr-FR")}€`;
    });
  }

  return { read, reset, bindSalarySlider };
})();
