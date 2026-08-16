(function () {
  'use strict';

  const { Interpreter } = window.BasicInterpreter;
  const ZONE_WIDTH = 14;
  const STORAGE_KEY = 'basic-emulator-code';

  class Terminal {
    constructor(el) {
      this.el = el;
      this.column = 0;
    }
    write(text) {
      this.el.textContent += text;
      const nl = text.lastIndexOf('\n');
      this.column = nl === -1 ? this.column + text.length : text.length - nl - 1;
      this._scroll();
    }
    newline() {
      this.el.textContent += '\n';
      this.column = 0;
      this._scroll();
    }
    printLine(text) { this.write(text); this.newline(); }
    clear() { this.el.textContent = ''; this.column = 0; }
    tabToNextZone() {
      const target = (Math.floor(this.column / ZONE_WIDTH) + 1) * ZONE_WIDTH;
      this.write(' '.repeat(Math.max(1, target - this.column)));
    }
    tabToColumn(n) {
      const target = Math.max(0, Math.floor(n) - 1);
      if (this.column < target) this.write(' '.repeat(target - this.column));
    }
    _scroll() { this.el.scrollTop = this.el.scrollHeight; }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const editor = document.getElementById('code-editor');
    const presetSelect = document.getElementById('preset-select');
    const presetDesc = document.getElementById('preset-desc');
    const runBtn = document.getElementById('run-btn');
    const stopBtn = document.getElementById('stop-btn');
    const clearBtn = document.getElementById('clear-btn');
    const newBtn = document.getElementById('new-btn');
    const termOutput = document.getElementById('terminal-output');
    const inputRow = document.getElementById('input-row');
    const inputPrompt = document.getElementById('input-prompt');
    const inputField = document.getElementById('input-field');
    const statusEl = document.getElementById('status');

    const terminal = new Terminal(termOutput);
    let interpreter = null;
    let pendingInputResolve = null;

    for (const preset of window.PRESET_LIST) {
      const opt = document.createElement('option');
      opt.value = preset.id;
      opt.textContent = preset.name;
      presetSelect.appendChild(opt);
    }

    function findPreset(id) {
      return window.PRESET_LIST.find((p) => p.id === id);
    }

    function loadPreset(id) {
      const preset = findPreset(id);
      if (!preset) return;
      presetDesc.textContent = preset.desc;
      editor.value = preset.code;
    }

    function setStatus(text, isError) {
      statusEl.textContent = text;
      statusEl.classList.toggle('status-error', !!isError);
    }

    function setRunningState(isRunning) {
      runBtn.disabled = isRunning;
      stopBtn.disabled = !isRunning;
      presetSelect.disabled = isRunning;
    }

    const io = {
      write: (t) => terminal.write(t),
      newline: () => terminal.newline(),
      printLine: (t) => terminal.printLine(t),
      clear: () => terminal.clear(),
      tabToNextZone: () => terminal.tabToNextZone(),
      tabToColumn: (n) => terminal.tabToColumn(n),
      input: (label) => {
        inputPrompt.textContent = (label || '?').trim() + ' ';
        inputRow.hidden = false;
        inputField.value = '';
        inputField.focus();
        return new Promise((resolve) => { pendingInputResolve = resolve; });
      },
      onEnd: () => {
        setRunningState(false);
        inputRow.hidden = true;
        setStatus('Programme terminé.');
      },
    };

    inputField.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && pendingInputResolve) {
        const value = inputField.value;
        terminal.write(inputPrompt.textContent + value);
        terminal.newline();
        inputRow.hidden = true;
        const resolve = pendingInputResolve;
        pendingInputResolve = null;
        resolve(value);
      }
    });

    async function runProgram() {
      terminal.clear();
      setStatus('Exécution en cours…');
      setRunningState(true);
      interpreter = new Interpreter(io);
      try {
        interpreter.load(editor.value);
      } catch (e) {
        terminal.printLine('ERREUR DE SYNTAXE' + (e.lineNo ? ' ligne ' + e.lineNo : '') + ' : ' + e.message);
        setRunningState(false);
        setStatus('Erreur de compilation.', true);
        return;
      }
      await interpreter.run();
    }

    runBtn.addEventListener('click', runProgram);
    stopBtn.addEventListener('click', () => { if (interpreter) interpreter.stop(); });
    clearBtn.addEventListener('click', () => terminal.clear());
    newBtn.addEventListener('click', () => {
      editor.value = '10 REM Nouveau programme\n20 PRINT "Bonjour !"\n30 END\n';
      presetSelect.value = '';
      presetDesc.textContent = '';
      editor.focus();
    });

    presetSelect.addEventListener('change', () => {
      if (presetSelect.value) loadPreset(presetSelect.value);
    });

    editor.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runProgram();
      }
      if (e.key === 'Tab') {
        e.preventDefault();
        const start = editor.selectionStart, end = editor.selectionEnd;
        editor.value = editor.value.substring(0, start) + '  ' + editor.value.substring(end);
        editor.selectionStart = editor.selectionEnd = start + 2;
      }
    });

    editor.addEventListener('input', () => {
      try { localStorage.setItem(STORAGE_KEY, editor.value); } catch (e) { /* stockage indisponible */ }
    });

    (async function init() {
      let saved = null;
      try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) { /* stockage indisponible */ }
      if (saved) {
        editor.value = saved;
        setStatus('Programme précédent restauré.');
      } else {
        presetSelect.value = 'hello';
        await loadPreset('hello');
      }
    })();
  });
})();
