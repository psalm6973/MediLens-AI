
const uploadForm = document.getElementById("upload-form");

if (uploadForm) {
    const fileInput = document.getElementById("report-file");
    const dropZone = document.getElementById("drop-zone");
    const selectedFile = document.getElementById("selected-file");
    const fileName = document.getElementById("file-name");
    const fileSize = document.getElementById("file-size");
    const removeButton = document.getElementById("remove-file");
    const errorMessage = document.getElementById("upload-error");
    const analyzeButton = document.getElementById("analyze-button");

    const allowedExtensions = ["pdf", "png", "jpg", "jpeg"];
    const maxFileSize = 10 * 1024 * 1024;

    function showError(message) {
        errorMessage.textContent = message;
    }

    function formatFileSize(bytes) {
        if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toFixed(1)} KB`;
        }

        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    function selectFile(file) {
        showError("");

        if (!file) return;

        const extension = file.name.split(".").pop().toLowerCase();

        if (!allowedExtensions.includes(extension)) {
            showError("Please select a PDF, PNG, JPG or JPEG file.");
            return;
        }

        if (file.size === 0) {
            showError("This file is empty. Please choose another file.");
            return;
        }

        if (file.size > maxFileSize) {
            showError("File size must not exceed 10 MB.");
            return;
        }

        const transfer = new DataTransfer();
        transfer.items.add(file);
        fileInput.files = transfer.files;

        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);

        dropZone.hidden = true;
        selectedFile.hidden = false;
    }

    function resetFile() {
        fileInput.value = "";
        selectedFile.hidden = true;
        dropZone.hidden = false;
        showError("");
    }

    fileInput.addEventListener("change", () => {
        selectFile(fileInput.files[0]);
    });

    removeButton.addEventListener("click", resetFile);

    // Drag and drop
    ["dragenter", "dragover"].forEach(eventName => {
        dropZone.addEventListener(eventName, event => {
            event.preventDefault();
            dropZone.classList.add("drag-over");
        });
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropZone.addEventListener(eventName, event => {
            event.preventDefault();
            dropZone.classList.remove("drag-over");
        });
    });

    dropZone.addEventListener("drop", event => {
        const files = event.dataTransfer.files;

        if (files.length > 0) {
            selectFile(files[0]);
        }
    });

    // Prevent browser navigation when a file is dropped.
    document.addEventListener("dragover", event => {
        event.preventDefault();
    });

    document.addEventListener("drop", event => {
        event.preventDefault();
    });

    // Paste an image or file.
    document.addEventListener("paste", event => {
        const items = event.clipboardData?.items || [];

        for (const item of items) {
            if (item.kind === "file") {
                const file = item.getAsFile();

                if (file) {
                    event.preventDefault();
                    selectFile(file);
                    return;
                }
            }
        }
    });

    // Upload and analyze.
    uploadForm.addEventListener("submit", async event => {
        event.preventDefault();

        const file = fileInput.files[0];

        if (!file) {
            showError("Please select or paste a medical report first.");
            return;
        }

        showError("");

        const originalButtonText = analyzeButton.innerHTML;

        analyzeButton.disabled = true;
        analyzeButton.innerHTML = "Analyzing your report...";

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || "Unable to process the report."
                );
            }

            const resultsResponse = await fetch("/results", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(result)
            });

            if (!resultsResponse.ok) {
                throw new Error("Unable to display the analysis results.");
            }

            const resultsHTML = await resultsResponse.text();

            document.open();
            document.write(resultsHTML);
            document.close();

        } catch (error) {
            showError(
                error.message || "Something went wrong. Please try again."
            );

            analyzeButton.disabled = false;
            analyzeButton.innerHTML = originalButtonText;
        }
    });
}
