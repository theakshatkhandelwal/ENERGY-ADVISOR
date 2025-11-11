// Minimal interactive helpers
(() => {
	const typeInput = document.getElementById('applianceType');
	const powerInput = document.getElementById('powerW');
	const hint = document.getElementById('powerHint');
	if (!typeInput || !powerInput) return;

	const defaults = {
		bulb: { w: 9, note: 'LED bulb ~9W (incandescent ~60W)' },
		tube: { w: 18, note: 'LED tube ~18W' },
		fan: { w: 70, note: 'Ceiling fan ~60–75W' },
		ac: { w: 1200, note: 'Split AC ~1.2kW while cooling' },
		'air conditioner': { w: 1200, note: 'Split AC ~1.2kW while cooling' },
		fridge: { w: 120, note: 'Fridge average draw ~100–150W' },
		refrigerator: { w: 120, note: 'Fridge average draw ~100–150W' },
		tv: { w: 90, note: 'LED TV ~70–120W' },
		router: { w: 10, note: 'Router ~8–12W' },
		laptop: { w: 60, note: 'Laptop charging ~45–65W' },
		monitor: { w: 30, note: 'Monitor ~25–40W' },
		wm: { w: 500, note: 'Washing machine (avg) ~500W' },
		'washing machine': { w: 500, note: 'Washing machine (avg) ~500W' },
		geyser: { w: 2000, note: 'Water heater ~2kW' },
		'microwave': { w: 1200, note: 'Microwave ~1.2kW while heating' }
	};

	function suggestPower() {
		const key = (typeInput.value || '').toLowerCase().trim();
		if (!key) return;
		let match = defaults[key];
		if (!match) {
			// loose matching
			for (const k of Object.keys(defaults)) {
				if (key.includes(k)) { match = defaults[k]; break; }
			}
		}
		if (match) {
			if (!powerInput.value) powerInput.value = match.w;
			if (hint) hint.textContent = `Suggested: ${match.w} W — ${match.note}`;
		} else if (hint) {
			hint.textContent = '';
		}
	}

	typeInput.addEventListener('change', suggestPower);
	typeInput.addEventListener('blur', suggestPower);
})();

// Tariff preview sparkline on Profile
(() => {
	const canvas = document.getElementById('tariffSpark');
	const slider = document.getElementById('tariffPreview');
	const sliderVal = document.getElementById('tariffPreviewVal');
	const previewCost = document.getElementById('previewCost');
	if (!canvas || !slider) return;
	const monthlyKwh = parseFloat(canvas.dataset.kwh || '0');
	const ef = parseFloat(canvas.dataset.ef || '0.7');
	const ctx = canvas.getContext('2d');

	function genData() {
		const tariffs = [];
		const costs = [];
		for (let t = 5; t <= 15; t += 0.5) {
			tariffs.push(t.toFixed(1));
			costs.push(parseFloat((monthlyKwh * t).toFixed(2)));
		}
		return { tariffs, costs };
	}

	const d = genData();
	const chart = new Chart(ctx, {
		type: 'line',
		data: {
			labels: d.tariffs,
			datasets: [{
				label: '₹/month',
				data: d.costs,
				borderColor: '#4e79a7',
				backgroundColor: 'rgba(78,121,167,0.15)',
				fill: true,
				pointRadius: 0,
				tension: 0.3
			}]
		},
		options: { plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display: false } } }
	});

	function updatePreview() {
		const t = parseFloat(slider.value);
		if (sliderVal) sliderVal.textContent = t.toFixed(1);
		if (previewCost) previewCost.textContent = (monthlyKwh * t).toFixed(2);
	}
	updatePreview();
	slider.addEventListener('input', updatePreview);
})();


