const baseURL = "http://localhost:3001";

async function fetchHealth() {
  const response = await fetch(`${baseURL}/health`);
  const data = await response.json().catch(() => ({}));
  document.getElementById("health").textContent = data.status || "API Health Status Not Available";
}

async function fetchStockData() {
  const response = await fetch(`${baseURL}/api/stocks/gainers-losers`);
  const stocks = await response.json();
  const container = document.getElementById("stock-list");
  container.innerHTML = "";
  stocks.forEach(stock => {
    const div = document.createElement("div");
    div.textContent = `${stock.symbol}: Price ${stock.price}, Change: ${stock.changePercent}%`;
    container.appendChild(div);
  });
}

async function fetchMarketIndices() {
  const response = await fetch(`${baseURL}/api/indices`);
  const indices = await response.json();
  const container = document.getElementById("market-indices");
  container.innerHTML = "";
  indices.forEach(index => {
    const div = document.createElement("div");
    div.textContent = `${index.name}: ${index.value} (${index.change}%)`;
    container.appendChild(div);
  });
}

async function fetchMarketNews() {
  const response = await fetch(`${baseURL}/api/news`);
  const newsItems = await response.json();
  const container = document.getElementById("market-news");
  container.innerHTML = "";
  newsItems.forEach(item => {
    const div = document.createElement("div");
    div.innerHTML = `<a href="${item.url}" target="_blank">${item.headline}</a>`;
    container.appendChild(div);
  });
}

function initializeDashboard() {
  fetchHealth();
  fetchStockData();
  fetchMarketIndices();
  fetchMarketNews();
}

window.onload = initializeDashboard;
