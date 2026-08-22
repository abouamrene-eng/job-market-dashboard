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
    // All boxes checked (the default) means "no preference" for role/company/
    // location - send no filter at all rather than an exhaustive allow-list.
    return {
      role: allChecked("filter-role") ? [] : checkedValues("filter-role"),
      company_type: allChecked("filter-company") ? [] : checkedValues("filter-company"),
      location: allChecked("filter-location") ? [] : checkedValues("filter-location"),
      min_salary: document.getElementById("filter-salary").value,
      aeronautique: document.getElementById("filter-aero").checked ? "true" : "false",
      enac: document.getElementById("filter-enac").checked ? "true" : "false",
    };
  }

  function reset() {
    document.querySelectorAll("#filter-role input, #filter-company input, #filter-location input").forEach((el) => {
      el.checked = true;
    });
    document.getElementById("filter-salary").value = 40000;
    document.getElementById("filter-salary-value").textContent = "40 000 €";
    document.getElementById("filter-aero").checked = true;
    document.getElementById("filter-enac").checked = false;
  }

  function bindSalarySlider() {
    const slider = document.getElementById("filter-salary");
    const label = document.getElementById("filter-salary-value");
    slider.addEventListener("input", () => {
      label.textContent = `${Number(slider.value).toLocaleString("fr-FR")} €`;
    });
  }

  function countActive() {
    let n = 0;
    if (!allChecked("filter-role")) n += 1;
    if (!allChecked("filter-company")) n += 1;
    if (!allChecked("filter-location")) n += 1;
    if (Number(document.getElementById("filter-salary").value) > 40000) n += 1;
    if (!document.getElementById("filter-aero").checked) n += 1;
    if (document.getElementById("filter-enac").checked) n += 1;
    return n;
  }

  return { read, reset, bindSalarySlider, countActive };
})();
