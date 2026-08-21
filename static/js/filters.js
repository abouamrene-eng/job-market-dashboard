const Filters = (() => {
  function checkedValues(containerId) {
    return Array.from(
      document.querySelectorAll(`#${containerId} input[type=checkbox]:checked`)
    ).map((el) => el.value);
  }

  function allChecked(containerId) {
    const boxes = document.querySelectorAll(`#${containerId} input[type=checkbox]`);
    return Array.from(boxes).every((el) => el.checked);
  }

  function read() {
    // All boxes checked (the default) means "no preference" - send no
    // filter at all rather than an exhaustive allow-list, since real-world
    // sector/location text is far more varied than these few checkboxes.
    return {
      sector: allChecked("filter-sector") ? [] : checkedValues("filter-sector"),
      location: allChecked("filter-location") ? [] : checkedValues("filter-location"),
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
