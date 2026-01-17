const scanBtn = document.getElementById("scanBtn");
const downloadBtn = document.getElementById("downloadBtn");
const tableBody = document.querySelector("#videoTable tbody");

scanBtn.onclick = async () => {
    const res = await fetch("/scan");
    const data = await res.json();

    tableBody.innerHTML = "";

    data.videos.forEach((v, index) => {
        // Main video row
        const row = document.createElement("tr");
        row.id = "row-" + index;
        row.classList.add("video-row");

        row.innerHTML = `
            <td>${v.file}</td>
            <td>${v.code || "-"}</td>
            <td>${v.has_sub ? "Yes" : "No"}</td>
            <td class="status" id="status-${index}"></td>
            <td></td>
        `;

        // Log row (always visible)
        const logRow = document.createElement("tr");
        logRow.id = "log-row-" + index;
        logRow.classList.add("log-row");

        logRow.innerHTML = `
            <td colspan="5">
                <div class="log" id="log-${index}"></div>
            </td>
        `;

        tableBody.appendChild(row);
        tableBody.appendChild(logRow);
    });

    downloadBtn.disabled = false;
};

downloadBtn.onclick = async () => {
    await fetch("/download", { method: "POST" });
    pollStatus();
};

// ------------------------------------------------------------
// Color‑coding logic for log lines
// ------------------------------------------------------------
function getLogClass(line) {
    const lower = line.toLowerCase();

    if (lower.includes("success") || lower.includes("saved")) {
        return "log-success";
    }
    if (lower.includes("fail") || lower.includes("error")) {
        return "log-error";
    }
    if (lower.includes("warning") || lower.includes("no subtitle")) {
        return "log-warning";
    }
    if (
        lower.includes("searching") ||
        lower.includes("found subtitle") ||
        lower.includes("source")
    ) {
        return "log-subcat";
    }
    return "log-info";
}

// ------------------------------------------------------------
// Poll backend for status updates
// ------------------------------------------------------------
async function pollStatus() {
    const res = await fetch("/status");
    const data = await res.json();

    let completed = 0;

    data.videos.forEach((v, index) => {
        const statusCell = document.getElementById("status-" + index);
        const logDiv = document.getElementById("log-" + index);
        const row = document.getElementById("row-" + index);

        if (!statusCell || !logDiv || !row) return;

        // Reset row state
        row.classList.remove("downloading", "success", "failed");

        if (v.status === "success") {
            statusCell.textContent = "✔️";
            row.classList.add("success");
            completed++;
        } else if (v.status === "failed") {
            statusCell.textContent = "❌";
            row.classList.add("failed");
            completed++;
        } else if (v.status === "downloading") {
            statusCell.textContent = "⏳";
            row.classList.add("downloading");
        } else {
            statusCell.textContent = "";
        }

        // Render color‑coded logs
        logDiv.innerHTML = (v.log || [])
            .map(line => `<div class="${getLogClass(line)} log-line">${line}</div>`)
            .join("");
    });

    const total = data.videos.length;
    const percent = total === 0 ? 0 : (completed / total) * 100;
    document.getElementById("progressBar").style.width = percent + "%";

    if (!data.finished) {
        setTimeout(pollStatus, 800);
    }
}
