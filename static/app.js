const scanBtn = document.getElementById("scanBtn");
const downloadBtn = document.getElementById("downloadBtn");
const tableBody = document.querySelector("#videoTable tbody");

scanBtn.onclick = async () => {
    const res = await fetch("/scan");
    const data = await res.json();

    tableBody.innerHTML = "";

    data.videos.forEach((v, index) => {
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

function toggleLog(index) {
    const logDiv = document.getElementById("log-" + index);
    logDiv.classList.toggle("collapsed");
}

async function pollStatus() {
    const res = await fetch("/status");
    const data = await res.json();

    let completed = 0;

    data.videos.forEach((v, index) => {
        const statusCell = document.getElementById("status-" + index);
        const logDiv = document.getElementById("log-" + index);
        const row = document.getElementById("row-" + index);

        row.classList.remove("downloading", "success", "failed");

        if (v.status === "success") {
            statusCell.textContent = "✔️";
            row.classList.add("success");
            completed++;
        }
        else if (v.status === "failed") {
            statusCell.textContent = "❌";
            row.classList.add("failed");
            completed++;
        }
        else if (v.status === "downloading") {
            statusCell.textContent = "⏳";
            row.classList.add("downloading");
        }

        logDiv.textContent = v.log.join("\n");
    });

    const total = data.videos.length;
    const percent = total === 0 ? 0 : (completed / total) * 100;
    document.getElementById("progressBar").style.width = percent + "%";

    if (!data.finished) {
        setTimeout(pollStatus, 800);
    }
}
