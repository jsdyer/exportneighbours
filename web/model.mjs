export function monthsFor(end, mode, available) {
  const selected = mode === 'month' ? [end] : available.filter(m => m.slice(0,4) === end.slice(0,4) && m <= end);
  const previous = selected.map(m => String(Number(m.slice(0,4)) - 1) + m.slice(4));
  return {selected, previous: previous.every(m => available.includes(m)) ? previous : []};
}
export function totals(data, months) {
  const countries = new Map();
  for (const month of months) {
    for (const [country, value] of Object.entries(data[month] || {})) {
      countries.set(country, (countries.get(country) || 0) + value);
    }
  }
  return {countries, total:[...countries.values()].reduce((a,b) => a+b,0)};
}
export function compare(data, periods) {
  const current = totals(data, periods.selected);
  const past = totals(data, periods.previous);
  const countries = new Set([...current.countries.keys(), ...past.countries.keys()]);
  const rows = [...countries].map(code => {
    const value = current.countries.get(code) ?? 0, prior = past.countries.get(code) ?? 0;
    const share = current.total > 0 ? 100 * value / current.total : null;
    const oldShare = past.total > 0 ? 100 * prior / past.total : null;
    return {code, value, prior, share, oldShare, change:share !== null && oldShare !== null ? share-oldShare : null};
  }).sort((a,b) => b.value-a.value || b.prior-a.prior || a.code.localeCompare(b.code));
  return {rows, current, past};
}
export function csv(rows) {
  return rows.map(row => row.map(v => '"' + String(v ?? '').replaceAll('"','""') + '"').join(',')).join('\r\n')+'\r\n';
}
