/**
 * Interpréteur BASIC (dialecte simplifié inspiré du GW-BASIC / Applesoft BASIC).
 * Zéro dépendance, conçu pour tourner directement dans le navigateur.
 *
 * Commandes supportées : LET, PRINT, INPUT, IF/THEN/ELSE, FOR/NEXT/STEP,
 * GOTO, GOSUB/RETURN, DIM, DATA/READ/RESTORE, CLS, END/STOP, REM.
 * Fonctions : ABS INT SGN SQR SIN COS TAN ATN LOG EXP RND
 *             LEN LEFT$ RIGHT$ MID$ CHR$ ASC STR$ VAL INSTR SPACE$ STRING$ TAB
 */

class BasicError extends Error {
  constructor(message, lineNo) {
    super(message);
    this.name = 'BasicError';
    this.lineNo = lineNo;
  }
}

const FUNCTION_NAMES = new Set([
  'ABS', 'INT', 'SGN', 'SQR', 'SIN', 'COS', 'TAN', 'ATN', 'LOG', 'EXP', 'RND',
  'LEN', 'LEFT$', 'RIGHT$', 'MID$', 'CHR$', 'ASC', 'STR$', 'VAL', 'INSTR',
  'SPACE$', 'STRING$', 'TAB',
]);

const KEYWORDS = new Set([
  'LET', 'PRINT', 'INPUT', 'IF', 'THEN', 'ELSE', 'FOR', 'TO', 'STEP', 'NEXT',
  'GOTO', 'GOSUB', 'RETURN', 'END', 'STOP', 'DIM', 'REM', 'DATA', 'READ',
  'RESTORE', 'CLS', 'AND', 'OR', 'NOT', 'MOD',
]);

// ----------------------------- Lexer -----------------------------------

function tokenize(text) {
  const tokens = [];
  let i = 0;
  const n = text.length;
  const isDigit = (c) => c >= '0' && c <= '9';
  const isAlpha = (c) => /[A-Za-z]/.test(c);

  while (i < n) {
    const c = text[i];
    if (c === ' ' || c === '\t') { i++; continue; }

    if (c === '"') {
      let j = i + 1;
      let s = '';
      while (j < n && text[j] !== '"') { s += text[j]; j++; }
      tokens.push({ type: 'STRING', value: s });
      i = j + 1;
      continue;
    }

    if (isDigit(c) || (c === '.' && isDigit(text[i + 1]))) {
      let j = i;
      let s = '';
      while (j < n && (isDigit(text[j]) || text[j] === '.')) { s += text[j]; j++; }
      if (j < n && (text[j] === 'E' || text[j] === 'e')) {
        s += text[j]; j++;
        if (j < n && (text[j] === '+' || text[j] === '-')) { s += text[j]; j++; }
        while (j < n && isDigit(text[j])) { s += text[j]; j++; }
      }
      tokens.push({ type: 'NUMBER', value: parseFloat(s) });
      i = j;
      continue;
    }

    if (isAlpha(c)) {
      let j = i;
      let s = '';
      while (j < n && /[A-Za-z0-9]/.test(text[j])) { s += text[j]; j++; }
      if (text[j] === '$' || text[j] === '%') { s += text[j]; j++; }
      tokens.push({ type: 'IDENT', value: s.toUpperCase() });
      i = j;
      continue;
    }

    if (c === '<' && text[i + 1] === '=') { tokens.push({ type: 'OP', value: '<=' }); i += 2; continue; }
    if (c === '>' && text[i + 1] === '=') { tokens.push({ type: 'OP', value: '>=' }); i += 2; continue; }
    if (c === '<' && text[i + 1] === '>') { tokens.push({ type: 'OP', value: '<>' }); i += 2; continue; }
    if ('+-*/^=<>(),;:'.includes(c)) { tokens.push({ type: 'OP', value: c }); i++; continue; }

    i++; // caractère inconnu ignoré
  }
  return tokens;
}

// ----------------------------- Parser -----------------------------------

class Parser {
  constructor(tokens, lineNo) {
    this.tokens = tokens;
    this.pos = 0;
    this.lineNo = lineNo;
  }

  peek(offset = 0) { return this.tokens[this.pos + offset]; }
  next() { return this.tokens[this.pos++]; }
  atEnd() { return this.pos >= this.tokens.length; }

  error(msg) { throw new BasicError(msg, this.lineNo); }

  expectOp(value) {
    const t = this.next();
    if (!t || t.type !== 'OP' || t.value !== value) {
      this.error(`"${value}" attendu`);
    }
  }

  isKeyword(token, word) {
    return token && token.type === 'IDENT' && token.value === word;
  }

  parseProgramLine() {
    const statements = [];
    while (!this.atEnd()) {
      const stmt = this.parseStatement();
      if (stmt) statements.push(stmt);
      if (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ':') {
        this.next();
        continue;
      }
      break;
    }
    return statements;
  }

  // Parse une liste de statements jusqu'à ELSE ou la fin des tokens (pour IF).
  parseStmtListUntilElse() {
    const statements = [];
    while (!this.atEnd()) {
      if (this.isKeyword(this.peek(), 'ELSE')) break;
      const stmt = this.parseStatement();
      if (stmt) statements.push(stmt);
      if (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ':') {
        this.next();
        continue;
      }
      break;
    }
    return statements;
  }

  parseStatement() {
    if (this.atEnd()) return null;
    const t = this.peek();

    if (t.type === 'IDENT' && KEYWORDS.has(t.value) && t.value !== 'MOD' && t.value !== 'AND' && t.value !== 'OR' && t.value !== 'NOT') {
      switch (t.value) {
        case 'LET': this.next(); return this.parseAssignment();
        case 'PRINT': this.next(); return this.parsePrint();
        case 'INPUT': this.next(); return this.parseInput();
        case 'IF': this.next(); return this.parseIf();
        case 'FOR': this.next(); return this.parseFor();
        case 'NEXT': this.next(); return this.parseNext();
        case 'GOTO': this.next(); return { type: 'GOTO', target: this.parseExpr() };
        case 'GOSUB': this.next(); return { type: 'GOSUB', target: this.parseExpr() };
        case 'RETURN': this.next(); return { type: 'RETURN' };
        case 'END': this.next(); return { type: 'END' };
        case 'STOP': this.next(); return { type: 'END' };
        case 'DIM': this.next(); return this.parseDim();
        case 'DATA': this.next(); return this.parseData();
        case 'READ': this.next(); return this.parseRead();
        case 'RESTORE': this.next(); return { type: 'RESTORE' };
        case 'CLS': this.next(); return { type: 'CLS' };
        case 'REM': this.pos = this.tokens.length; return { type: 'REM' };
        default: this.error(`Instruction inconnue : ${t.value}`);
      }
    }

    if (t.type === 'IDENT') return this.parseAssignment();
    this.error('Instruction attendue');
    return null;
  }

  parseLValue() {
    const nameTok = this.next();
    if (!nameTok || nameTok.type !== 'IDENT') this.error('Nom de variable attendu');
    let indices = null;
    if (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === '(') {
      this.next();
      indices = [this.parseExpr()];
      while (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ',') {
        this.next();
        indices.push(this.parseExpr());
      }
      this.expectOp(')');
    }
    return { name: nameTok.value, indices };
  }

  parseAssignment() {
    const target = this.parseLValue();
    this.expectOp('=');
    const expr = this.parseExpr();
    return { type: 'LET', target, expr };
  }

  parsePrint() {
    const parts = [];
    while (!this.atEnd()) {
      const t = this.peek();
      if (t.type === 'OP' && t.value === ':') break;
      if (t.type === 'OP' && (t.value === ';' || t.value === ',')) {
        parts.push({ kind: 'sep', value: t.value });
        this.next();
        continue;
      }
      const node = this.parseExpr();
      parts.push({ kind: 'expr', node });
    }
    return { type: 'PRINT', parts };
  }

  parseInput() {
    let prompt = null;
    if (!this.atEnd() && this.peek().type === 'STRING') {
      prompt = this.next().value;
      if (!this.atEnd() && this.peek().type === 'OP' && (this.peek().value === ';' || this.peek().value === ',')) {
        this.next();
      }
    }
    const vars = [this.parseLValue()];
    while (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ',') {
      this.next();
      vars.push(this.parseLValue());
    }
    return { type: 'INPUT', prompt, vars };
  }

  parseIf() {
    const cond = this.parseExpr();
    if (!this.isKeyword(this.next(), 'THEN')) this.error('"THEN" attendu');

    let thenStmts;
    if (!this.atEnd() && this.peek().type === 'NUMBER') {
      const num = this.next().value;
      thenStmts = [{ type: 'GOTO', target: { type: 'NUM', value: num } }];
    } else {
      thenStmts = this.parseStmtListUntilElse();
    }

    let elseStmts = null;
    if (!this.atEnd() && this.isKeyword(this.peek(), 'ELSE')) {
      this.next();
      if (!this.atEnd() && this.peek().type === 'NUMBER') {
        const num = this.next().value;
        elseStmts = [{ type: 'GOTO', target: { type: 'NUM', value: num } }];
      } else {
        elseStmts = this.parseStmtListUntilElse();
      }
    }
    return { type: 'IF', cond, thenStmts, elseStmts };
  }

  parseFor() {
    const varTok = this.next();
    if (!varTok || varTok.type !== 'IDENT') this.error('Variable attendue après FOR');
    this.expectOp('=');
    const start = this.parseExpr();
    if (!this.isKeyword(this.next(), 'TO')) this.error('"TO" attendu');
    const end = this.parseExpr();
    let step = null;
    if (!this.atEnd() && this.isKeyword(this.peek(), 'STEP')) {
      this.next();
      step = this.parseExpr();
    }
    return { type: 'FOR', varName: varTok.value, start, end, step };
  }

  parseNext() {
    const vars = [];
    while (!this.atEnd() && this.peek().type === 'IDENT' && !KEYWORDS.has(this.peek().value)) {
      vars.push(this.next().value);
      if (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ',') this.next();
      else break;
    }
    return { type: 'NEXT', vars };
  }

  parseDim() {
    const decls = [];
    while (true) {
      const nameTok = this.next();
      if (!nameTok || nameTok.type !== 'IDENT') this.error('Nom de tableau attendu après DIM');
      this.expectOp('(');
      const dims = [this.parseExpr()];
      while (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ',') {
        this.next();
        dims.push(this.parseExpr());
      }
      this.expectOp(')');
      decls.push({ name: nameTok.value, dims });
      if (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ',') { this.next(); continue; }
      break;
    }
    return { type: 'DIM', decls };
  }

  parseData() {
    const values = [];
    while (!this.atEnd()) {
      let sign = 1;
      if (this.peek().type === 'OP' && this.peek().value === '-') { sign = -1; this.next(); }
      const t = this.next();
      if (t.type === 'NUMBER') values.push(t.value * sign);
      else if (t.type === 'STRING') values.push(t.value);
      else this.error('Valeur DATA invalide');
      if (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ',') { this.next(); continue; }
      break;
    }
    return { type: 'DATA', values };
  }

  parseRead() {
    const vars = [this.parseLValue()];
    while (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ',') {
      this.next();
      vars.push(this.parseLValue());
    }
    return { type: 'READ', vars };
  }

  // --- Expressions (précédence croissante) ---
  parseExpr() { return this.parseOr(); }

  parseOr() {
    let left = this.parseAnd();
    while (!this.atEnd() && this.isKeyword(this.peek(), 'OR')) {
      this.next();
      const right = this.parseAnd();
      left = { type: 'BIN', op: 'OR', left, right };
    }
    return left;
  }

  parseAnd() {
    let left = this.parseNot();
    while (!this.atEnd() && this.isKeyword(this.peek(), 'AND')) {
      this.next();
      const right = this.parseNot();
      left = { type: 'BIN', op: 'AND', left, right };
    }
    return left;
  }

  parseNot() {
    if (!this.atEnd() && this.isKeyword(this.peek(), 'NOT')) {
      this.next();
      return { type: 'UNARY', op: 'NOT', expr: this.parseNot() };
    }
    return this.parseCompare();
  }

  parseCompare() {
    let left = this.parseAdd();
    if (!this.atEnd() && this.peek().type === 'OP' && ['=', '<>', '<', '>', '<=', '>='].includes(this.peek().value)) {
      const op = this.next().value;
      const right = this.parseAdd();
      left = { type: 'BIN', op, left, right };
    }
    return left;
  }

  parseAdd() {
    let left = this.parseMul();
    while (!this.atEnd() && this.peek().type === 'OP' && (this.peek().value === '+' || this.peek().value === '-')) {
      const op = this.next().value;
      const right = this.parseMul();
      left = { type: 'BIN', op, left, right };
    }
    return left;
  }

  parseMul() {
    let left = this.parseUnary();
    while (!this.atEnd() && (
      (this.peek().type === 'OP' && (this.peek().value === '*' || this.peek().value === '/')) ||
      this.isKeyword(this.peek(), 'MOD')
    )) {
      const opTok = this.next();
      const op = opTok.type === 'OP' ? opTok.value : 'MOD';
      const right = this.parseUnary();
      left = { type: 'BIN', op, left, right };
    }
    return left;
  }

  parseUnary() {
    if (!this.atEnd() && this.peek().type === 'OP' && (this.peek().value === '-' || this.peek().value === '+')) {
      const op = this.next().value;
      const expr = this.parseUnary();
      return op === '-' ? { type: 'UNARY', op: '-', expr } : expr;
    }
    return this.parsePow();
  }

  parsePow() {
    const base = this.parsePrimary();
    if (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === '^') {
      this.next();
      const exp = this.parseUnary();
      return { type: 'BIN', op: '^', left: base, right: exp };
    }
    return base;
  }

  parsePrimary() {
    const t = this.next();
    if (!t) this.error('Expression inattendue : fin de ligne');

    if (t.type === 'NUMBER') return { type: 'NUM', value: t.value };
    if (t.type === 'STRING') return { type: 'STR', value: t.value };

    if (t.type === 'OP' && t.value === '(') {
      const e = this.parseExpr();
      this.expectOp(')');
      return e;
    }

    if (t.type === 'IDENT') {
      const isFn = FUNCTION_NAMES.has(t.value);
      if (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === '(') {
        this.next();
        const args = [];
        if (!(this.peek().type === 'OP' && this.peek().value === ')')) {
          args.push(this.parseExpr());
          while (!this.atEnd() && this.peek().type === 'OP' && this.peek().value === ',') {
            this.next();
            args.push(this.parseExpr());
          }
        }
        this.expectOp(')');
        if (isFn) return { type: 'CALL', name: t.value, args };
        return { type: 'VAR', name: t.value, indices: args };
      }
      if (isFn) this.error(`La fonction ${t.value} nécessite des parenthèses`);
      return { type: 'VAR', name: t.value, indices: null };
    }

    this.error(`Symbole inattendu : ${t.value}`);
    return null;
  }
}

// ----------------------------- Compilation -----------------------------

function compileProgram(source) {
  const rawLines = source.split('\n');
  const linesMap = new Map();

  for (const rawLine of rawLines) {
    const line = rawLine.trim();
    if (!line) continue;
    const m = line.match(/^(\d+)\s*(.*)$/);
    if (!m) continue; // ligne sans numéro : ignorée
    const lineNo = parseInt(m[1], 10);
    const rest = m[2];

    let statements;
    if (/^REM\b/i.test(rest) || rest.startsWith("'")) {
      statements = [{ type: 'REM' }];
    } else {
      const tokens = tokenize(rest);
      const parser = new Parser(tokens, lineNo);
      statements = parser.parseProgramLine();
    }
    linesMap.set(lineNo, { statements });
  }

  const order = Array.from(linesMap.keys()).sort((a, b) => a - b);
  const lineIndex = new Map(order.map((no, idx) => [no, idx]));
  const program = { lines: linesMap, order, lineIndex };

  linkForNext(program);
  return program;
}

function linkForNext(program) {
  const stack = [];
  for (let pcIndex = 0; pcIndex < program.order.length; pcIndex++) {
    const line = program.lines.get(program.order[pcIndex]);
    for (let stmtIndex = 0; stmtIndex < line.statements.length; stmtIndex++) {
      const stmt = line.statements[stmtIndex];
      if (stmt.type === 'FOR') {
        stack.push(stmt);
      } else if (stmt.type === 'NEXT') {
        const forStmt = stack.pop();
        if (forStmt) forStmt.afterNext = { pcIndex, stmtIndex: stmtIndex + 1 };
      }
    }
  }
}

// ----------------------------- Runtime ----------------------------------

const FUNS = {
  ABS: (a) => Math.abs(a),
  INT: (a) => Math.floor(a),
  SGN: (a) => (a > 0 ? 1 : a < 0 ? -1 : 0),
  SQR: (a) => Math.sqrt(a),
  SIN: (a) => Math.sin(a),
  COS: (a) => Math.cos(a),
  TAN: (a) => Math.tan(a),
  ATN: (a) => Math.atan(a),
  LOG: (a) => Math.log(a),
  EXP: (a) => Math.exp(a),
  RND: () => Math.random(),
  LEN: (s) => String(s).length,
  'LEFT$': (s, n) => String(s).substring(0, Math.floor(n)),
  'RIGHT$': (s, n) => { const str = String(s); return str.substring(Math.max(0, str.length - Math.floor(n))); },
  'MID$': (s, start, len) => {
    const str = String(s);
    const i = Math.max(0, Math.floor(start) - 1);
    return len === undefined ? str.substring(i) : str.substr(i, Math.floor(len));
  },
  'CHR$': (n) => String.fromCharCode(Math.floor(n)),
  ASC: (s) => String(s).charCodeAt(0) || 0,
  'STR$': (n) => String(n),
  VAL: (s) => parseFloat(s) || 0,
  INSTR: (...args) => {
    let start = 1, s, sub;
    if (args.length === 2) { [s, sub] = args; } else { [start, s, sub] = args; }
    const idx = String(s).indexOf(String(sub), Math.max(0, Math.floor(start) - 1));
    return idx === -1 ? 0 : idx + 1;
  },
  'SPACE$': (n) => ' '.repeat(Math.max(0, Math.floor(n))),
  'STRING$': (n, ch) => {
    const c = typeof ch === 'string' ? ch[0] : String.fromCharCode(Math.floor(ch));
    return c.repeat(Math.max(0, Math.floor(n)));
  },
};

function formatNumber(n) {
  if (Number.isNaN(n)) return 'NaN';
  if (!Number.isFinite(n)) return n > 0 ? 'Infini' : '-Infini';
  if (Number.isInteger(n)) return String(n);
  const s = parseFloat(n.toPrecision(10));
  return String(s);
}

function toInt32(x) { return Math.trunc(x) | 0; }

class Interpreter {
  constructor(io) {
    this.io = io;
  }

  load(source) {
    this.program = compileProgram(source);
  }

  async run() {
    this.vars = Object.create(null);
    this.arrays = Object.create(null);
    this.forStack = [];
    this.gosubStack = [];
    this.dataList = [];
    this.dataPtr = 0;
    this.running = true;
    this.stopRequested = false;

    for (const lineNo of this.program.order) {
      for (const stmt of this.program.lines.get(lineNo).statements) {
        if (stmt.type === 'DATA') this.dataList.push(...stmt.values);
      }
    }

    let pcIndex = 0;
    let stmtIndex = 0;
    let steps = 0;

    try {
      while (this.running) {
        if (pcIndex >= this.program.order.length) break;
        if (this.stopRequested) { this.io.printLine('* Programme arrêté *'); break; }

        const lineNo = this.program.order[pcIndex];
        const line = this.program.lines.get(lineNo);
        if (stmtIndex >= line.statements.length) { pcIndex++; stmtIndex = 0; continue; }

        const stmt = line.statements[stmtIndex];
        const ctx = { lineNo, pcIndex, stmtIndex };
        const jump = await this.execStmt(stmt, ctx);

        steps++;
        if (steps % 2000 === 0) {
          await new Promise((resolve) => setTimeout(resolve, 0));
          if (this.stopRequested) { this.io.printLine('* Programme arrêté *'); break; }
        }

        if (jump && jump.type === 'end') break;
        if (jump && jump.type === 'goto') {
          pcIndex = jump.pcIndex;
          stmtIndex = jump.stmtIndex;
        } else {
          stmtIndex++;
        }
      }
    } catch (e) {
      if (e instanceof BasicError) {
        this.io.printLine(`ERREUR${e.lineNo ? ' ligne ' + e.lineNo : ''} : ${e.message}`);
      } else {
        this.io.printLine(`ERREUR INTERNE : ${e.message}`);
      }
    }
    this.running = false;
    if (this.io.onEnd) this.io.onEnd();
  }

  stop() { this.stopRequested = true; }

  gotoLine(lineNo, ctx) {
    const pcIndex = this.program.lineIndex.get(lineNo);
    if (pcIndex === undefined) throw new BasicError(`Ligne ${lineNo} introuvable`, ctx.lineNo);
    return { type: 'goto', pcIndex, stmtIndex: 0 };
  }

  async execStmt(stmt, ctx) {
    switch (stmt.type) {
      case 'REM': return null;
      case 'LET': return this.execLet(stmt, ctx);
      case 'PRINT': return this.execPrint(stmt, ctx);
      case 'INPUT': return this.execInput(stmt, ctx);
      case 'IF': return this.execIf(stmt, ctx);
      case 'FOR': return this.execFor(stmt, ctx);
      case 'NEXT': return this.execNext(stmt, ctx);
      case 'GOTO': return this.gotoLine(this.evalExpr(stmt.target, ctx), ctx);
      case 'GOSUB': {
        this.gosubStack.push({ pcIndex: ctx.pcIndex, stmtIndex: ctx.stmtIndex + 1 });
        return this.gotoLine(this.evalExpr(stmt.target, ctx), ctx);
      }
      case 'RETURN': {
        const ret = this.gosubStack.pop();
        if (!ret) throw new BasicError('RETURN sans GOSUB correspondant', ctx.lineNo);
        return { type: 'goto', pcIndex: ret.pcIndex, stmtIndex: ret.stmtIndex };
      }
      case 'END': return { type: 'end' };
      case 'DIM': return this.execDim(stmt, ctx);
      case 'DATA': return null;
      case 'READ': return this.execRead(stmt, ctx);
      case 'RESTORE': this.dataPtr = 0; return null;
      case 'CLS': this.io.clear(); return null;
      default: throw new BasicError(`Instruction non gérée : ${stmt.type}`, ctx.lineNo);
    }
  }

  execLet(stmt, ctx) {
    const value = this.evalExpr(stmt.expr, ctx);
    this.assign(stmt.target, value, ctx);
    return null;
  }

  assign(target, value, ctx) {
    if (target.indices) {
      const idx = target.indices.map((e) => Math.floor(this.evalExpr(e, ctx)));
      this.setArray(target.name, idx, value, ctx);
    } else {
      this.vars[target.name] = value;
    }
  }

  execPrint(stmt, ctx) {
    let suppressNewline = false;
    for (const part of stmt.parts) {
      if (part.kind === 'sep') {
        if (part.value === ',') this.io.tabToNextZone();
        suppressNewline = true;
      } else {
        suppressNewline = false;
        const node = part.node;
        if (node.type === 'CALL' && node.name === 'TAB') {
          const col = this.evalExpr(node.args[0], ctx);
          this.io.tabToColumn(col);
        } else {
          const val = this.evalExpr(node, ctx);
          this.io.write(typeof val === 'number' ? formatNumber(val) : String(val));
        }
      }
    }
    if (!suppressNewline) this.io.newline();
    return null;
  }

  async execInput(stmt, ctx) {
    for (let i = 0; i < stmt.vars.length; i++) {
      const target = stmt.vars[i];
      const label = i === 0 && stmt.prompt !== null ? stmt.prompt : (target.name + ' ');
      const raw = await this.io.input(label);
      const isString = target.name.endsWith('$');
      const value = isString ? raw : (parseFloat(raw) || 0);
      this.assign(target, value, ctx);
    }
    return null;
  }

  execIf(stmt, ctx) {
    const cond = this.evalExpr(stmt.cond, ctx);
    const list = cond !== 0 ? stmt.thenStmts : stmt.elseStmts;
    if (!list) return null;
    return this.execStmtListSync(list, ctx);
  }

  // Exécute une liste de statements en ligne (utilisé pour IF/THEN); ne gère
  // pas les statements asynchrones (INPUT) imbriqués — limitation assumée.
  execStmtListSync(list, ctx) {
    for (const stmt of list) {
      const result = this.execStmtSyncOnly(stmt, ctx);
      if (result) return result;
    }
    return null;
  }

  execStmtSyncOnly(stmt, ctx) {
    switch (stmt.type) {
      case 'LET': return this.execLet(stmt, ctx);
      case 'PRINT': return this.execPrint(stmt, ctx);
      case 'GOTO': return this.gotoLine(this.evalExpr(stmt.target, ctx), ctx);
      case 'GOSUB': {
        this.gosubStack.push({ pcIndex: ctx.pcIndex, stmtIndex: ctx.stmtIndex + 1 });
        return this.gotoLine(this.evalExpr(stmt.target, ctx), ctx);
      }
      case 'RETURN': {
        const ret = this.gosubStack.pop();
        if (!ret) throw new BasicError('RETURN sans GOSUB correspondant', ctx.lineNo);
        return { type: 'goto', pcIndex: ret.pcIndex, stmtIndex: ret.stmtIndex };
      }
      case 'END': return { type: 'end' };
      case 'CLS': this.io.clear(); return null;
      case 'DIM': return this.execDim(stmt, ctx);
      case 'READ': return this.execRead(stmt, ctx);
      case 'RESTORE': this.dataPtr = 0; return null;
      case 'REM': return null;
      default: throw new BasicError(`Instruction non autorisée après THEN/ELSE : ${stmt.type}`, ctx.lineNo);
    }
  }

  execFor(stmt, ctx) {
    const start = this.evalExpr(stmt.start, ctx);
    const end = this.evalExpr(stmt.end, ctx);
    const step = stmt.step !== null ? this.evalExpr(stmt.step, ctx) : 1;
    this.vars[stmt.varName] = start;

    const continues = step >= 0 ? start <= end : start >= end;
    if (!continues) {
      if (!stmt.afterNext) throw new BasicError('NEXT manquant pour ce FOR', ctx.lineNo);
      return { type: 'goto', pcIndex: stmt.afterNext.pcIndex, stmtIndex: stmt.afterNext.stmtIndex };
    }

    this.forStack.push({
      varName: stmt.varName,
      endVal: end,
      stepVal: step,
      returnPos: { pcIndex: ctx.pcIndex, stmtIndex: ctx.stmtIndex + 1 },
    });
    return null;
  }

  execNext(stmt, ctx) {
    const names = stmt.vars.length ? stmt.vars : [null];
    for (const nm of names) {
      if (this.forStack.length === 0) throw new BasicError('NEXT sans FOR correspondant', ctx.lineNo);
      let idx = this.forStack.length - 1;
      if (nm) {
        idx = -1;
        for (let k = this.forStack.length - 1; k >= 0; k--) {
          if (this.forStack[k].varName === nm) { idx = k; break; }
        }
        if (idx < 0) throw new BasicError(`NEXT ${nm} sans FOR correspondant`, ctx.lineNo);
      }
      const frame = this.forStack[idx];
      this.forStack.length = idx + 1;
      const val = (this.vars[frame.varName] || 0) + frame.stepVal;
      this.vars[frame.varName] = val;
      const cont = frame.stepVal >= 0 ? val <= frame.endVal : val >= frame.endVal;
      if (cont) {
        return { type: 'goto', pcIndex: frame.returnPos.pcIndex, stmtIndex: frame.returnPos.stmtIndex };
      }
      this.forStack.pop();
    }
    return null;
  }

  execDim(stmt, ctx) {
    for (const decl of stmt.decls) {
      const sizes = decl.dims.map((e) => Math.floor(this.evalExpr(e, ctx)));
      this.arrays[decl.name] = { dims: sizes, store: Object.create(null) };
    }
    return null;
  }

  execRead(stmt, ctx) {
    for (const target of stmt.vars) {
      if (this.dataPtr >= this.dataList.length) throw new BasicError('Plus de données DATA disponibles', ctx.lineNo);
      const raw = this.dataList[this.dataPtr++];
      const isString = target.name.endsWith('$');
      const value = isString ? String(raw) : (typeof raw === 'number' ? raw : parseFloat(raw) || 0);
      this.assign(target, value, ctx);
    }
    return null;
  }

  ensureArray(name, indices) {
    if (!this.arrays[name]) {
      this.arrays[name] = { dims: indices.map(() => 10), store: Object.create(null) };
    }
    return this.arrays[name];
  }

  getArray(name, indices, ctx) {
    const arr = this.ensureArray(name, indices);
    indices.forEach((v, k) => {
      if (v < 0 || (arr.dims[k] !== undefined && v > arr.dims[k])) {
        throw new BasicError(`Indice hors limites pour ${name}`, ctx.lineNo);
      }
    });
    const key = indices.join(',');
    if (key in arr.store) return arr.store[key];
    return name.endsWith('$') ? '' : 0;
  }

  setArray(name, indices, value, ctx) {
    const arr = this.ensureArray(name, indices);
    indices.forEach((v, k) => {
      if (v < 0 || (arr.dims[k] !== undefined && v > arr.dims[k])) {
        throw new BasicError(`Indice hors limites pour ${name}`, ctx.lineNo);
      }
    });
    arr.store[indices.join(',')] = value;
  }

  evalExpr(node, ctx) {
    switch (node.type) {
      case 'NUM': return node.value;
      case 'STR': return node.value;
      case 'VAR': {
        if (node.indices) {
          const idx = node.indices.map((e) => Math.floor(this.evalExpr(e, ctx)));
          return this.getArray(node.name, idx, ctx);
        }
        if (node.name in this.vars) return this.vars[node.name];
        return node.name.endsWith('$') ? '' : 0;
      }
      case 'CALL': {
        const fn = FUNS[node.name];
        if (!fn) throw new BasicError(`Fonction inconnue : ${node.name}`, ctx.lineNo);
        const args = node.args.map((a) => this.evalExpr(a, ctx));
        return fn(...args);
      }
      case 'UNARY': {
        const v = this.evalExpr(node.expr, ctx);
        if (node.op === '-') return -v;
        if (node.op === 'NOT') return ~toInt32(v);
        return v;
      }
      case 'BIN': {
        const a = this.evalExpr(node.left, ctx);
        const b = this.evalExpr(node.right, ctx);
        return this.evalBin(node.op, a, b, ctx);
      }
      default:
        throw new BasicError(`Nœud d'expression inconnu : ${node.type}`, ctx.lineNo);
    }
  }

  evalBin(op, a, b, ctx) {
    switch (op) {
      case '+': return (typeof a === 'string' || typeof b === 'string') ? String(a) + String(b) : a + b;
      case '-': return a - b;
      case '*': return a * b;
      case '/':
        if (b === 0) throw new BasicError('Division par zéro', ctx.lineNo);
        return a / b;
      case '^': return Math.pow(a, b);
      case 'MOD': return a - b * Math.floor(a / b);
      case '=': return a === b ? -1 : 0;
      case '<>': return a !== b ? -1 : 0;
      case '<': return a < b ? -1 : 0;
      case '>': return a > b ? -1 : 0;
      case '<=': return a <= b ? -1 : 0;
      case '>=': return a >= b ? -1 : 0;
      case 'AND': return toInt32(a) & toInt32(b);
      case 'OR': return toInt32(a) | toInt32(b);
      default: throw new BasicError(`Opérateur inconnu : ${op}`, ctx.lineNo);
    }
  }
}

if (typeof window !== 'undefined') {
  window.BasicInterpreter = { Interpreter, BasicError, compileProgram, tokenize };
}
