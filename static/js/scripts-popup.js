let mediaRecorder;
let audioChunks = [];
let currentArticleId = null;

document.addEventListener("DOMContentLoaded", function () {
    let recordingsList = document.getElementById("recordingsList");

    // Ensure scrolling works inside the popup
    recordingsList.style.overflowY = "auto";
    recordingsList.style.maxHeight = "250px";
});

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".record-btn").forEach(button => {
        button.addEventListener("click", function () {
            const article = this.closest(".recording-container");
            currentArticleId = article.getAttribute("data-id");
            openPopup();
        });
    });

    document.querySelector(".close-btn").addEventListener("click", closePopup);

    function openPopup() {
        document.getElementById("popup").style.display = "flex";
        loadRecordings();
    }

    function closePopup() {
        document.getElementById("popup").style.display = "none";
    }

    function loadRecordings() {
		const recordings = JSON.parse(localStorage.getItem(currentArticleId) || "[]");
		const recordingsList = document.getElementById("recordingsList");
		recordingsList.innerHTML = "";

		// ✅ Select the correct recording count element
		const countElement = document.querySelector(`[data-id="${currentArticleId}"] .record-count`);
		if (countElement) {
			countElement.textContent = recordings.length; // ✅ Update the count
		}

		recordings.forEach((recording, index) => {
			displayRecording(recording, index);
		});
	}



	
	function displayRecording(recording, index) {
		const recordingItem = document.createElement("div");
		recordingItem.classList.add("recordingItem");

		const audioWrapper = document.createElement("div");
		audioWrapper.classList.add("audioWrapper");

		const audio = document.createElement("audio");
		audio.controls = true;
		audio.src = recording.audioUrl;

		const deleteButton = document.createElement("button");
		deleteButton.classList.add("deleteButton");
		deleteButton.innerHTML = "🗑️";
		deleteButton.addEventListener("click", () => deleteRecording(index));

		const title = document.createElement("p");
		title.textContent = recording.title;
		title.classList.add("recording-title");

		audioWrapper.appendChild(audio);
		audioWrapper.appendChild(deleteButton);

		recordingItem.appendChild(audioWrapper);
		recordingItem.appendChild(title); // Title now below the recording

		document.getElementById("recordingsList").appendChild(recordingItem);
	}
	
	




    function deleteRecording(index) {
		let recordings = JSON.parse(localStorage.getItem(currentArticleId) || "[]");
		recordings.splice(index, 1);
		localStorage.setItem(currentArticleId, JSON.stringify(recordings));

		loadRecordings(); // ✅ Update the count after deletion
	}


    document.getElementById("recordButton").addEventListener("click", startRecording);
    document.getElementById("stopButton").addEventListener("click", stopRecording);

    async function startRecording() {
        try {
            audioChunks = [];
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);
            mediaRecorder.onstop = saveRecording;
            mediaRecorder.start();
            document.getElementById("recordButton").disabled = true;
            document.getElementById("stopButton").disabled = false;
        } catch (error) {
            alert("Microphone access denied. Please allow microphone access.");
        }
    }

    function stopRecording() {
        mediaRecorder.stop();
        document.getElementById("recordButton").disabled = false;
        document.getElementById("stopButton").disabled = true;
    }
	
	function saveRecording() {
		const title = document.getElementById("record-title").value.trim();
		if (!title) {
			alert("Please enter a title for the recording.");
			return;
		}

		const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
		const audioUrl = URL.createObjectURL(audioBlob);

		let recordings = JSON.parse(localStorage.getItem(currentArticleId) || "[]");
		recordings.push({ title, audioUrl });

		localStorage.setItem(currentArticleId, JSON.stringify(recordings));
		document.getElementById("record-title").value = ""; // Clear input

		loadRecordings(); // ✅ Update the count after adding a new recording
	}


});
