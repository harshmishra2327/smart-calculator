const display = document.getElementById('display');
const displayValue = display.querySelector('.display-value');
const keys = document.querySelectorAll('.key');
const exprInput = document.getElementById('expr');
const sendBtn = document.getElementById('send');
const resultDiv = document.getElementById('result');
const clearBtn = document.getElementById('clear');
const evalBtn = document.getElementById('eval');
const voiceBtn = document.getElementById('voice');
const copyBtn = document.getElementById('copy');
const historyList = document.getElementById('historyList');
const clearHistoryBtn = document.getElementById('clearHistory');

let current = '';

function updateDisplay() {
  displayValue.textContent = current || '0';
}

keys.forEach(k => {
  k.addEventListener('click', () => {
    const v = k.dataset.value;
    if (v) {
      current += v;
      exprInput.value = current;
      updateDisplay();
    }
  });
});

clearBtn.addEventListener('click', () => {
  current = '';
  exprInput.value = '';
  updateDisplay();
  resultDiv.textContent = '';
});

evalBtn.addEventListener('click', () => {
  exprInput.value = current;
  sendExpression();
});

sendBtn.addEventListener('click', () => {
  sendExpression();
});

async function sendExpression() {
  const expr = exprInput.value.trim();
  if (!expr) return;
  resultDiv.textContent = 'Calculating...';
  try {
    const r = await fetch('/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expression: expr })
    });
    const data = await r.json();
    if (data.ok) {
      resultDiv.textContent = `${data.expression} = ${data.result}`;
      speak(`Result is ${data.result}`);
      current = String(data.result);
      exprInput.value = current;
      updateDisplay();
    } else {
      resultDiv.textContent = 'Error: ' + (data.error || 'unknown');
      speak('I could not calculate that');
    }
  } catch (err) {
    resultDiv.textContent = 'Error communicating with server';
  }
}

function speak(text) {
  if (!('speechSynthesis' in window)) return;
  const ut = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(ut);
}

// Voice recognition
let recognizing = false;
let recognition = null;
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRec();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    recognizing = true;
    voiceBtn.textContent = '⏹️ Stop Voice';
    resultDiv.textContent = '🎤 Listening...';
  };

  recognition.onresult = (ev) => {
    const text = ev.results[0][0].transcript;
    exprInput.value = text;
    sendExpression();
  };

  recognition.onerror = (ev) => {
    resultDiv.textContent = 'Voice error: ' + ev.error;
  };

  recognition.onend = () => {
    recognizing = false;
    voiceBtn.textContent = '🎤 Voice';
  };
}

// disable voice button early if unsupported
if (!recognition) {
  voiceBtn.disabled = true;
  voiceBtn.textContent = 'Voice Unsupported';
}

voiceBtn.addEventListener('click', () => {
  if (!recognition) {
    resultDiv.textContent = 'Speech recognition not supported in this browser.';
    return;
  }
  if (recognizing) {
    recognition.stop();
    return;
  }
  recognition.start();
});

updateDisplay();

// -- History management --
function loadHistory() {
  try {
    const raw = localStorage.getItem('calc_history') || '[]';
    return JSON.parse(raw);
  } catch (e) { return []; }
}

function saveHistory(arr) {
  localStorage.setItem('calc_history', JSON.stringify(arr.slice(0,50))); // keep 50
}

function pushHistory(expr, result) {
  const h = loadHistory();
  h.unshift({expr, result, ts: Date.now()});
  saveHistory(h);
  renderHistory();
}

function renderHistory() {
  const h = loadHistory();
  historyList.innerHTML = '';
  for (let item of h) {
    const li = document.createElement('li');
    li.textContent = `${item.expr} = ${item.result}`;
    li.addEventListener('click', () => {
      exprInput.value = item.expr;
      current = item.expr;
      updateDisplay();
    });
    historyList.appendChild(li);
  }
}

clearHistoryBtn.addEventListener('click', () => {
  localStorage.removeItem('calc_history');
  renderHistory();
});

if (copyBtn) {
  copyBtn.addEventListener('click', () => {
    const text = resultDiv.textContent || '';
    if (!text) return;
    navigator.clipboard?.writeText(text).then(() => {
      const orig = resultDiv.textContent;
      resultDiv.textContent = orig + ' ✓ Copied!';
      setTimeout(() => {
        resultDiv.textContent = orig;
      }, 1500);
    }).catch(()=>{});
  });
}

// render existing history on load
renderHistory();

// show keyboard enter to evaluate
exprInput.addEventListener('keydown', (ev) => {
  if (ev.key === 'Enter') {
    sendExpression();
  }
});

// update: push to history on successful responses
async function sendExpression() {
  const expr = exprInput.value.trim();
  if (!expr) return;
  resultDiv.textContent = 'Calculating...';
  try {
    const r = await fetch('/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expression: expr })
    });
    const data = await r.json();
    if (data.ok) {
      resultDiv.textContent = `${data.expression} = ${data.result}`;
      speak(`Result is ${data.result}`);
      current = String(data.result);
      exprInput.value = current;
      updateDisplay();
      pushHistory(data.expression, data.result);
    } else {
      resultDiv.textContent = 'Error: ' + (data.error || 'unknown');
      speak('I could not calculate that');
    }
  } catch (err) {
    resultDiv.textContent = 'Error communicating with server';
  }
}

