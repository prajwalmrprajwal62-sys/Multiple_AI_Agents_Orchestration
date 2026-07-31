<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Stock Research Agent</title>
  <style>
    body { font-family: sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; }
    input { padding: 10px; width: 250px; font-size: 16px; }
    button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-top: 16px; white-space: pre-wrap; }
    .loading { color: #888; }
  </style>
</head>
<body>
  <h1>Stock Research Agent</h1>
  <input id="ticker" placeholder="e.g. TCS.NS" />
  <button onclick="runAnalysis()">Analyze</button>

  <div id="results"></div>

  <script>
    const BACKEND_URL = "https://your-backend-url.onrender.com"; // update after deploying backend

    async function runAnalysis() {
      const ticker = document.getElementById("ticker").value.trim();
      const resultsDiv = document.getElementById("results");
      resultsDiv.innerHTML = "<p class='loading'>Running 4 agents, this can take 20-40s...</p>";

      try {
        const response = await fetch(`${BACKEND_URL}/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker })
        });
        const data = await response.json();

        resultsDiv.innerHTML = `
          <div class="card"><strong>Fundamental</strong>\n\n${data.fundamental}</div>
          <div class="card"><strong>Technical</strong>\n\n${data.technical}</div>
          <div class="card"><strong>News</strong>\n\n${data.news}</div>
          <div class="card"><strong>Final Verdict</strong>\n\n${data.verdict}</div>
        `;
      } catch (err) {
        resultsDiv.innerHTML = `<p style="color:red">Error: ${err.message}</p>`;
      }
    }
  </script>
</body>
</html>