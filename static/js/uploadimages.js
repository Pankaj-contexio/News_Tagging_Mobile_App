function uploadimage(cardid, page, project_id){
    const addimage = document.getElementById("add-image");
    document.getElementById("card_id_input").value = cardid;
    document.getElementById("project_id_input").value = project_id;
    document.getElementById("page_input").value = page;
    const descriptionInput = document.getElementById('imageDescriptionInput');
    descriptionInput.value = ""; // Clear the description input
    const imageInput = document.getElementById('imageInput');
    imageInput.value = ""; // Clear the file input
    addimage.style.display = "block";
}

document.getElementById('uploadButton').addEventListener('click', async function () {
    const imageInput = document.getElementById('imageInput');
    const cardIdInput = document.getElementById('card_id_input');
    const project_id = document.getElementById("project_id_input").value;
    const page = document.getElementById("page_input").value;
    const descriptionInput = document.getElementById('imageDescriptionInput').value;


    const file = imageInput.files[0];
    const cardId = cardIdInput.value;
    const card = document.getElementById(cardId);
    const table = card.querySelector(`table`); // Assuming card has id "card-<id>"
    const lastRow = table.querySelector("tr:last-child");
    if (!file) {
        alertPopup("Please select a file");
        return;
    }

    const formData = new FormData();
    formData.append('image', file);
    formData.append('card_id', cardId);
    formData.append('project_id', project_id);
    formData.append('page', page);
    formData.append('description', descriptionInput);

    try {
        const response = await fetch('/api/image/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) {
            alertPopup(data.error || 'Upload failed');
            const addimage = document.getElementById("add-image");
            addimage.style.display = "none";
            return;
        }
        const imageUrl = data.image_url;
        const description = data.description;
        // Create the <li> element
        const newTd = document.createElement('td');
        newTd.className = "image-preview";
        newTd.style = "text-align: center; padding: 10px;";
        newTd.innerHTML = `
            <img src="${imageUrl}" alt="Full Preview" style="width:150px; height: 150px; object-fit: cover; cursor: pointer;" onclick="openImageModal('${imageUrl}')">
            ${description ? `<p style="margin-top: 4px; font-size: 12px;">${description}</p>
            <button class="remove-image-btn btn btn-danger" onclick="deleteImage('${imageUrl}', '${cardId}', '${project_id}', '${page}')"
                            style="border: none; font-size: 12px; padding: 6px; line-height: 1;"><i class="fa fa-trash-o" style="margin-right: 2px;"></i> Delete</button>` : ""}
                                    
        `;

        // Insert before the last <td> in the last <tr>
        const lastTds = lastRow.querySelectorAll("td");
        const lastTd = lastTds[lastTds.length - 1];
        lastRow.insertBefore(newTd, lastTd);
        
        // Insert <img> here if needed
        const addimage = document.getElementById("add-image");
        addimage.style.display = "none";


    } catch (error) {
        console.error('Upload failed:', error);
    }
});

async function deleteImage(imageUrl, cardId, project_id, page) {
    const confirmDelete = await confirmWithCustomPopup("Are you sure you want to delete this Image?");
    if (!confirmDelete) return;
    
    fetch('/api/image/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ image_url: imageUrl, card_id: cardId, project_id: project_id, page:page})
    })
    .then(response => response.json())
    .then(data => {
        
        const card = document.getElementById(cardId);
        const ul = card.querySelector('.image-preview-table tr:last-child');
        const imageLi = ul.querySelector(`td img[src="${imageUrl}"]`).parentElement;
        ul.removeChild(imageLi);
        
        
    })
    .catch(error => console.error('Error deleting image:', error));
}