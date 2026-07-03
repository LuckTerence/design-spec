// Unified extraction JS — computed styles + CSS vars + pixel sampling by DOM role
(() => {
  const result = {
    body: {},
    colors: [],
    fonts: [],
    rounded: [],
    elements: [],
    textColors: [],
    bgColors: [],
    brandColors: [],
    fontSizes: [],
    cssVars: {},
    pixelSamples: {}
  };
  const colorSet = new Set();
  const fontSet = new Set();
  const roundedSet = new Set();
  const elementSigSet = new Set();

  // Helper: rgba -> #RRGGBB
  function toHex(r, g, b) {
    return '#' + [Math.round(r), Math.round(g), Math.round(b)]
      .map(x => x.toString(16).padStart(2, '0'))
      .join('');
  }

  function parseColor(s) {
    if (!s || s === 'transparent' || s === 'rgba(0, 0, 0, 0)') return null;
    if (s.startsWith('#')) return s.slice(0, 7).toLowerCase();
    const m = s.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    return m ? toHex(+m[1], +m[2], +m[3]) : null;
  }

  function isVisible(el) {
    const s = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    if (rect.width < 5 || rect.height < 5) return false;
    const t = el.tagName.toLowerCase();
    return !['script', 'style', 'link', 'meta', 'noscript'].includes(t) &&
           s.display !== 'none' &&
           s.visibility !== 'hidden';
  }

  // Body styles
  const bs = getComputedStyle(document.body);
  result.body = {
    fontFamily: bs.fontFamily,
    fontSize: bs.fontSize,
    color: parseColor(bs.color),
    backgroundColor: parseColor(bs.backgroundColor),
    lineHeight: bs.lineHeight
  };

  // CSS custom properties
  try {
    const rootStyle = getComputedStyle(document.documentElement);
    const probes = [
      '--primary', '--brand', '--accent', '--primary-color',
      '--text-color', '--bg-color', '--background-color', '--surface-color',
      '--secondary', '--secondary-color', '--font-family', '--font-sans',
      '--radius', '--spacing'
    ];
    probes.forEach(p => {
      const v = rootStyle.getPropertyValue(p).trim();
      if (v) result.cssVars[p] = v;
    });
    // 收集前 100 个自定义属性
    for (let i = 0; i < rootStyle.length && i < 100; i++) {
      const p = rootStyle[i];
      if (p.startsWith('--') && !result.cssVars[p]) {
        const v = rootStyle.getPropertyValue(p).trim();
        if (v) result.cssVars[p] = v;
      }
    }
  } catch (e) {}

  // Element sampling
  let elementCount = 0;
  for (const el of document.querySelectorAll('*')) {
    if (!isVisible(el)) continue;

    const s = getComputedStyle(el);
    const tag = el.tagName.toLowerCase();
    const rect = el.getBoundingClientRect();
    const bg = parseColor(s.backgroundColor);
    const fg = parseColor(s.color);
    const bc = parseColor(s.borderColor);

    if (bg && bg !== '#000000' && bg !== '#ffffff') {
      colorSet.add(bg);
      result.bgColors.push(bg);
    }
    if (fg && fg !== '#000000' && fg !== '#ffffff') {
      colorSet.add(fg);
      result.textColors.push(fg);
    }
    if (bc && bc !== '#000000' && bc !== '#ffffff') colorSet.add(bc);

    const role = el.getAttribute('role') || '';
    const isBtn = tag === 'button' || role === 'button' || (tag === 'a' && el.href);
    const isInput = tag === 'input' || tag === 'textarea' || tag === 'select';
    const isHeading = /^h[1-6]$/.test(tag);

    if (isBtn && bg && bg !== '#000000' && bg !== '#ffffff') {
      result.brandColors.push(bg);
    }
    if (s.borderRadius && s.borderRadius !== '0px') {
      roundedSet.add(s.borderRadius);
    }
    if (s.fontFamily) {
      fontSet.add(s.fontFamily);
    }
    if (s.fontSize) {
      result.fontSizes.push({
        size: s.fontSize,
        tag: tag,
        weight: s.fontWeight
      });
    }

    // Pixel sampling for key semantic elements
    if (isBtn && !result.pixelSamples.buttonColor && bg) {
      result.pixelSamples.buttonColor = bg;
    }
    if (isInput && !result.pixelSamples.inputBg && bg) {
      result.pixelSamples.inputBg = bg;
    }
    if (isHeading && !result.pixelSamples.headingColor && fg) {
      result.pixelSamples.headingColor = fg;
    }
    if ((tag === 'div' || tag === 'section' || tag === 'article') &&
        rect.width > 200 && rect.height > 100 &&
        !result.pixelSamples.cardBg && bg && bg !== '#000000') {
      result.pixelSamples.cardBg = bg;
    }

    const sig = tag + s.fontSize + (fg || '') + (bg || '');
    if (!elementSigSet.has(sig) && elementCount < 150) {
      elementSigSet.add(sig);
      elementCount++;
      result.elements.push({
        tag: tag,
        bg: bg,
        fg: fg,
        bc: bc,
        fontSize: s.fontSize,
        fontFamily: s.fontFamily,
        fontWeight: s.fontWeight,
        borderRadius: s.borderRadius,
        padding: s.padding,
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        text: (el.textContent || '').trim().slice(0, 30)
      });
    }
  }

  result.colors = [...colorSet];
  result.rounded = [...roundedSet].sort();
  result.fonts = [...fontSet];
  return JSON.stringify(result);
})();
