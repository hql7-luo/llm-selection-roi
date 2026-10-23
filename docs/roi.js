// The same ROI model as src/llmroi/roi.py. tests/test_project.py checks that both give the same numbers.
(function (root) {
  // Fully loaded labor cost of a salesperson, USD per hour
  function hourlyCost(inp) {
    return inp.monthly_salary_cny * inp.employer_overhead / inp.hours_per_month / inp.usd_cny;
  }

  // One inquiry handled as "AI draft + human review" compared with doing it by hand
  function perInquiry(inp, errorRate, apiCost) {
    const wage = hourlyCost(inp);
    const minutesSaved = inp.manual_minutes - inp.review_minutes - errorRate * inp.catch_rate * inp.fix_minutes;
    const laborSaved = minutesSaved * wage / 60;
    const errorCost = (errorRate * (1 - inp.catch_rate) - inp.manual_error_rate) * inp.escaped_error_cost_usd;
    return {
      manual_cost: inp.manual_minutes * wage / 60,
      minutes_saved: minutesSaved,
      labor_saved: laborSaved,
      api_cost: apiCost,
      error_cost: errorCost,
      net: laborSaved - apiCost - errorCost,
    };
  }

  function monthly(inp, errorRate, apiCost) {
    const unit = perInquiry(inp, errorRate, apiCost);
    const net = inp.monthly_volume * unit.net - inp.monthly_maintenance_usd;
    return Object.assign({}, unit, { net_month: net, payback_months: net > 0 ? inp.setup_cost_usd / net : null });
  }

  // Highest critical error rate at which the monthly net benefit is still zero or better
  function breakevenErrorRate(inp, apiCost) {
    const wage = hourlyCost(inp);
    const gain = (inp.manual_minutes - inp.review_minutes) * wage / 60 - apiCost
      + inp.manual_error_rate * inp.escaped_error_cost_usd
      - inp.monthly_maintenance_usd / inp.monthly_volume;
    const lossPerError = inp.catch_rate * inp.fix_minutes * wage / 60 + (1 - inp.catch_rate) * inp.escaped_error_cost_usd;
    return Math.max(gain / lossPerError, 0);
  }

  const api = { hourlyCost, perInquiry, monthly, breakevenErrorRate };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.RoiModel = api;
})(this);
