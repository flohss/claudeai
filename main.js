(function () {
  const gameGrid = document.getElementById("gameGrid");
  const menu = document.getElementById("menu");
  const gameScreen = document.getElementById("gameScreen");
  const gameTitle = document.getElementById("gameTitle");
  const gameScore = document.getElementById("gameScore");
  const gameHint = document.getElementById("gameHint");
  const backBtn = document.getElementById("backBtn");
  const canvas = document.getElementById("canvas");

  let stopCurrentGame = null;

  function renderMenu() {
    gameGrid.innerHTML = "";
    window.ARCADE_GAMES.forEach((game) => {
      const card = document.createElement("div");
      card.className = "game-card";
      card.style.setProperty("--accent", game.accent);
      card.innerHTML = `
        <span class="icon">${game.icon}</span>
        <h3>${game.name}</h3>
        <p>${game.description}</p>
      `;
      card.addEventListener("click", () => openGame(game));
      gameGrid.appendChild(card);
    });
  }

  function openGame(game) {
    menu.classList.add("hidden");
    gameScreen.classList.remove("hidden");
    backBtn.classList.remove("hidden");
    gameTitle.textContent = `${game.icon} ${game.name}`;
    gameHint.textContent = game.hint || "";
    gameScore.textContent = "";

    stopCurrentGame = game.start(canvas, (text) => {
      gameScore.textContent = text;
    });
  }

  function closeGame() {
    if (stopCurrentGame) {
      stopCurrentGame();
      stopCurrentGame = null;
    }
    gameScreen.classList.add("hidden");
    backBtn.classList.add("hidden");
    menu.classList.remove("hidden");
  }

  backBtn.addEventListener("click", closeGame);

  renderMenu();
})();
