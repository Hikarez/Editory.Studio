// Menu di layar kecil
const toggle = document.querySelector('.nav-toggle');
const nav = document.getElementById('nav');
if (toggle && nav) {
  toggle.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(open));
    toggle.textContent = open ? 'Tutup' : 'Menu';
  });
}

// Estimasi total di form proposal (perhitungan sama dengan server)
const estimateForm = document.querySelector('[data-estimate]');
if (estimateForm) {
  const fmt = (n) => 'Rp' + Math.round(n).toLocaleString('id-ID');
  const qty = estimateForm.querySelector('#qty');
  const discount = estimateForm.querySelector('#discount');
  const qtyLabel = estimateForm.querySelector('[data-qty-label]');
  const total = estimateForm.querySelector('[data-total]');
  const detail = estimateForm.querySelector('[data-total-detail]');

  const update = () => {
    const pkg = estimateForm.querySelector('input[name="package_id"]:checked');
    if (!pkg) return;
    const price = Number(pkg.dataset.price);
    const q = Math.min(24, Math.max(1, parseInt(qty.value, 10) || 1));
    const d = discount ? Math.min(50, Math.max(0, parseInt(discount.value, 10) || 0)) : 0;
    qtyLabel.textContent = pkg.dataset.qtyLabel;
    total.textContent = fmt(Math.floor((price * q * (100 - d)) / 100));
    detail.textContent = `${fmt(price)} ${pkg.dataset.unitLabel} x ${q}` + (d ? `, diskon ${d}%` : '');
  };
  estimateForm.addEventListener('input', update);
  estimateForm.addEventListener('change', update);
  update();
}

// Salin link proposal
document.querySelectorAll('[data-copy]').forEach((btn) => {
  btn.addEventListener('click', async () => {
    const original = btn.textContent;
    try {
      await navigator.clipboard.writeText(btn.dataset.copy);
      btn.textContent = 'Link tersalin';
    } catch (err) {
      window.prompt('Salin link ini:', btn.dataset.copy);
    }
    setTimeout(() => { btn.textContent = original; }, 2000);
  });
});

// Cetak proposal
document.querySelectorAll('[data-print]').forEach((btn) => {
  btn.addEventListener('click', () => window.print());
});
